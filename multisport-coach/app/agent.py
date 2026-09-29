# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import json
import os
import subprocess
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from dotenv import load_dotenv
from google import genai
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.memory import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.adk.tools.tool_context import ToolContext
from google.cloud import firestore, storage
from google.genai import types
from google.oauth2.credentials import Credentials

from .a2ui_utils import a2ui_callback

# Load local environment variables from .env
load_dotenv()

MODEL = "gemini-3.8-flash"

# Hardcoded project ID and GCS bucket name as required
PROJECT_ID = "qwiklabs-gcp-02-8c87b93d83aa"
BUCKET_NAME = "multisport-coach-assets-qwiklabs-gcp-02-8c87b93d83aa"


def get_agent_engine_id() -> str:
    """Loads the remote Agent Engine resource ID from deployment_metadata.json if available."""
    metadata_path = os.path.join(os.path.dirname(__file__), "..", "deployment_metadata.json")
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("remote_agent_runtime_id", "")
        except Exception:
            pass
    return ""


AGENT_ENGINE_ID = get_agent_engine_id()
MEMORY_BANK_ID = AGENT_ENGINE_ID.split("/")[-1] if AGENT_ENGINE_ID else "4799961991521239040"

# Initialize Sandbox Code Executor from Agent Engine resource name
code_executor = (
    AgentEngineSandboxCodeExecutor(agent_engine_resource_name=AGENT_ENGINE_ID)
    if AGENT_ENGINE_ID
    else None
)


def memory_bank_service_builder() -> VertexAiMemoryBankService:
    """Returns a configured VertexAiMemoryBankService instance for Agent Platform deployments."""
    return VertexAiMemoryBankService(
        project=PROJECT_ID,
        location="us-east4",
        agent_engine_id=MEMORY_BANK_ID,
    )


memory_service = memory_bank_service_builder()


async def generate_memories_callback(callback_context: CallbackContext):
    """Sends session events to Memory Bank after each turn to extract durable user facts and preferences."""
    try:
        mem_service = getattr(callback_context._invocation_context, "memory_service", None)
        if mem_service is not None:
            await callback_context.add_session_to_memory()
        elif memory_service is not None:
            session = getattr(callback_context._invocation_context, "session", None)
            if session:
                await memory_service.add_session_to_memory(session)
    except Exception as e:
        print(f"Memory Bank sync notice: {e}")
    return None



def get_db_client() -> firestore.Client:
    """Returns a Firestore client configured with the hardcoded project ID."""
    try:
        token = subprocess.check_output(
            ["gcloud", "auth", "application-default", "print-access-token"],
            stderr=subprocess.DEVNULL,
        ).decode("utf-8").strip()
        if token:
            return firestore.Client(project=PROJECT_ID, credentials=Credentials(token))
    except Exception:
        pass
    return firestore.Client(project=PROJECT_ID)


def get_gcs_client() -> storage.Client:
    """Returns a Cloud Storage client configured with the hardcoded project ID."""
    try:
        token = subprocess.check_output(
            ["gcloud", "auth", "application-default", "print-access-token"],
            stderr=subprocess.DEVNULL,
        ).decode("utf-8").strip()
        if token:
            return storage.Client(project=PROJECT_ID, credentials=Credentials(token))
    except Exception:
        pass
    return storage.Client(project=PROJECT_ID)


def list_activities(sport: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves logged athletic workouts from Firestore collection 'activities'.

    Args:
        sport: Optional sport to filter by (e.g. 'running', 'trail_running', 'roller_skiing', 'bicycling').

    Returns:
        List of activity dictionaries containing workout details.
    """
    db = get_db_client()
    query_ref = db.collection("activities")
    if sport:
        query_ref = query_ref.where("sport", "==", sport.lower().strip())
    
    docs = query_ref.stream()
    activities = [doc.to_dict() for doc in docs]
    return activities


def log_activity(
    sport: str,
    title: str,
    distance_km: float,
    duration_minutes: float,
    elevation_gain_m: float = 0.0,
    avg_hr: int = 0,
    notes: str = "",
) -> Dict[str, Any]:
    """Logs a new workout session to the Firestore 'activities' collection.

    Args:
        sport: Sport type ('running', 'trail_running', 'roller_skiing', 'bicycling').
        title: Short title or summary of the session.
        distance_km: Distance covered in kilometers.
        duration_minutes: Total duration in minutes.
        elevation_gain_m: Total elevation gain in meters.
        avg_hr: Average heart rate during the session.
        notes: Workout notes or comments.

    Returns:
        The newly created activity dictionary.
    """
    db = get_db_client()
    now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    act_id = f"act-{int(datetime.datetime.now(datetime.timezone.utc).timestamp())}"
    
    activity_data = {
        "id": act_id,
        "sport": sport.lower().strip(),
        "title": title,
        "date": now_str,
        "distance_km": float(distance_km),
        "duration_minutes": float(duration_minutes),
        "elevation_gain_m": float(elevation_gain_m),
        "avg_hr": int(avg_hr),
        "notes": notes,
    }
    
    db.collection("activities").document(act_id).set(activity_data)
    return activity_data


def generate_training_plan(
    sport: str,
    target_distance_km: float,
    weeks: int = 4,
    fitness_level: str = "intermediate",
) -> Dict[str, Any]:
    """Generates a structured multi-week training plan for a specific sport and target goal.

    Args:
        sport: Target sport ('running', 'trail_running', 'roller_skiing', 'bicycling').
        target_distance_km: Goal distance in kilometers (e.g., 21.1 for half marathon, 50.0 for trail ultra).
        weeks: Duration of the training block in weeks (default 4).
        fitness_level: Athlete fitness level ('beginner', 'intermediate', 'advanced').

    Returns:
        Dictionary containing overall plan structure, weekly targets, key workouts, and sport focus tips.
    """
    sport_clean = sport.lower().strip()
    multiplier = {"beginner": 0.7, "intermediate": 1.0, "advanced": 1.3}.get(fitness_level.lower(), 1.0)
    
    weekly_breakdown = []
    for w in range(1, weeks + 1):
        if w == weeks:
            phase = "Taper & Race Prep"
            volume_percent = 0.5
            key_workout = f"Race Pace Simulation ({round(target_distance_km * 0.3 * multiplier, 1)} km Z3) + Taper rest"
        elif w == weeks - 1:
            phase = "Peak Load"
            volume_percent = 1.0
            key_workout = f"Long Peak Session ({round(target_distance_km * 0.8 * multiplier, 1)} km Z2 endurance)"
        elif w % 2 == 0:
            phase = "Build Phase"
            volume_percent = 0.85
            key_workout = f"Intervals & Tempo ({round(target_distance_km * 0.4 * multiplier, 1)} km Z3-Z4 efforts)"
        else:
            phase = "Base Aerobic"
            volume_percent = 0.75
            key_workout = f"Easy Aerobic Base ({round(target_distance_km * 0.6 * multiplier, 1)} km Z2)"
            
        weekly_volume_km = round(target_distance_km * 1.5 * volume_percent * multiplier, 1)
        weekly_breakdown.append({
            "week": w,
            "phase": phase,
            "target_weekly_volume_km": weekly_volume_km,
            "key_session": key_workout,
            "sessions_per_week": 3 if fitness_level == "beginner" else (4 if fitness_level == "intermediate" else 5),
        })

    sport_tips = {
        "running": "Focus on high cadence (170-180 bpm) and adequate recovery days.",
        "trail_running": "Incorporate hill repeats and technical downhill footwork practice.",
        "roller_skiing": "Prioritize double-poling core engagement and upper body stability.",
        "bicycling": "Maintain high pedaling cadence (85-95 RPM) and practice fuel intake on rides over 2 hours.",
    }

    return {
        "sport": sport_clean,
        "target_distance_km": target_distance_km,
        "fitness_level": fitness_level,
        "total_weeks": weeks,
        "sport_focus_tip": sport_tips.get(sport_clean, "Focus on consistent aerobic Zone 2 pacing."),
        "weekly_schedule": weekly_breakdown,
    }


def get_outdoor_weather_conditions(
    latitude: float = 37.7749,
    longitude: float = -122.4194,
    sport: str = "running",
) -> Dict[str, Any]:
    """Fetches real-time outdoor weather and training safety conditions from Open-Meteo API.

    Args:
        latitude: Latitude coordinate for the training location (default 37.7749 for San Francisco).
        longitude: Longitude coordinate for the training location (default -122.4194 for San Francisco).
        sport: Sport type ('running', 'trail_running', 'roller_skiing', 'bicycling').

    Returns:
        Dictionary containing current weather, temperature, wind speed, precipitation, and sport safety recommendations.
    """
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={latitude}&longitude={longitude}"
        f"&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "MultisportCoach/1.0"})
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode("utf-8"))
    
    current = data.get("current", {})
    temp_c = current.get("temperature_2m", 15.0)
    wind_kmh = current.get("wind_speed_10m", 0.0)
    precip_mm = current.get("precipitation", 0.0)
    humidity = current.get("relative_humidity_2m", 50)
    
    sport_clean = sport.lower().strip()
    if sport_clean == "roller_skiing" and precip_mm > 0.1:
        advice = "⚠️ Caution: Wet asphalt reported. Roller ski wheels can slip easily on wet pavement."
    elif sport_clean == "bicycling" and wind_kmh > 25.0:
        advice = f"💨 High winds detected ({wind_kmh} km/h). Use low-profile wheels and watch crosswinds."
    elif sport_clean == "trail_running" and precip_mm > 0.5:
        advice = "🌧️ Muddy trail conditions expected. Wear high-traction trail shoes."
    elif temp_c > 28.0:
        advice = "☀️ High heat! Bring extra hydration/electrolytes and wear sun protection."
    else:
        advice = "✅ Weather conditions are favorable for outdoor training!"

    return {
        "location": {"latitude": latitude, "longitude": longitude},
        "sport": sport_clean,
        "temperature_c": temp_c,
        "temperature_f": round((temp_c * 9 / 5) + 32, 1),
        "wind_speed_kmh": wind_kmh,
        "precipitation_mm": precip_mm,
        "humidity_percent": humidity,
        "coach_advice": advice,
    }


def geocode_address(address: str) -> Dict[str, Any]:
    """Converts a street address or location landmark into latitude and longitude coordinates using Google Maps Geocoding API.

    Args:
        address: The location address or landmark to geocode (e.g. 'Golden Gate Park, San Francisco').

    Returns:
        Dictionary containing input address name, formatted address, and geographic location coordinates.
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    if not api_key:
        return {"error": "GOOGLE_MAPS_API_KEY is not configured in environment."}

    encoded_address = urllib.parse.quote(address)
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={encoded_address}&key={api_key}"

    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode("utf-8"))

    results = data.get("results", [])
    if not results:
        return {"error": f"No geocoding results found for address: '{address}'"}

    first = results[0]
    loc = first.get("geometry", {}).get("location", {})
    return {
        "name": address,
        "address": first.get("formatted_address", address),
        "location": {
            "latitude": loc.get("lat"),
            "longitude": loc.get("lng"),
        },
    }


def find_nearby_places(
    latitude: float,
    longitude: float,
    place_type: str = "park",
    radius_meters: float = 5000.0,
) -> List[Dict[str, Any]]:
    """Finds nearby points of interest (e.g. parks, sports grounds, gyms) around coordinates using Google Places API (New).

    Args:
        latitude: Latitude coordinate of search center.
        longitude: Longitude coordinate of search center.
        place_type: Type of place to search for (e.g. 'park', 'sports_complex', 'gym').
        radius_meters: Search radius in meters (default 5000.0).

    Returns:
        List of nearby place dictionaries containing name, address, location, and place types.
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    if not api_key:
        return [{"error": "GOOGLE_MAPS_API_KEY is not configured in environment."}]

    url = "https://places.googleapis.com/v1/places:searchNearby"
    payload = {
        "includedTypes": [place_type.lower().strip()],
        "maxResultCount": 5,
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": float(latitude),
                    "longitude": float(longitude),
                },
                "radius": float(radius_meters),
            }
        },
    }

    req_body = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location,places.types",
    }

    req = urllib.request.Request(url, data=req_body, headers=headers, method="POST")
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode("utf-8"))

    raw_places = data.get("places", [])
    results = []
    for p in raw_places:
        name_obj = p.get("displayName", {})
        loc = p.get("location", {})
        results.append({
            "name": name_obj.get("text", "Unknown Place"),
            "address": p.get("formattedAddress", ""),
            "location": {
                "latitude": loc.get("latitude"),
                "longitude": loc.get("longitude"),
            },
            "types": p.get("types", []),
        })

    return results


def generate_multisport_image(
    prompt: str,
    tool_context: ToolContext,
) -> Dict[str, Any]:
    """Generates an image for endurance sports using gemini-3.1-flash-lite-image in the global region.
    Saves the generated image in Playground Artifacts and uploads bytes to public Cloud Storage.

    Args:
        prompt: Detailed description of the image to generate (e.g., 'A trail runner sprinting along a mountain ridge at sunset').
        tool_context: ADK tool context for saving Playground artifacts.

    Returns:
        Dictionary containing public Cloud Storage HTTPS URL, artifact filename, and prompt.
    """
    genai_client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
    response = genai_client.models.generate_content(
        model="gemini-3.1-flash-lite-image",
        contents=prompt,
    )

    image_bytes = None
    mime_type = "image/jpeg"
    for part in response.candidates[0].content.parts:
        if part.inline_data:
            image_bytes = part.inline_data.data
            mime_type = part.inline_data.mime_type or "image/jpeg"
            break

    if not image_bytes:
        return {"error": "Failed to generate image bytes from model."}

    # 1. Save artifact for Playground Artifacts panel
    timestamp_str = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    filename = f"multisport_{timestamp_str}.jpg"
    part_artifact = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    tool_context.save_artifact(filename=filename, artifact=part_artifact)

    # 2. Upload same bytes directly from memory to public Cloud Storage bucket
    gcs_object_name = f"generated_images/{filename}"
    storage_client = get_gcs_client()
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(gcs_object_name)
    blob.upload_from_string(image_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{gcs_object_name}"

    return {
        "public_url": public_url,
        "artifact_filename": filename,
        "prompt": prompt,
    }


def generate_multisport_video(
    prompt: str,
    tool_context: ToolContext,
) -> Dict[str, Any]:
    """Generates a short athletic endurance sport video using Google's Omni model (gemini-omni-flash-preview) in the global region.
    Saves the generated video in Playground Artifacts panel and uploads bytes to public Cloud Storage.

    Args:
        prompt: Detailed description of the video to generate (e.g., 'A high-speed video of a trail runner navigating a technical mountain ridge').
        tool_context: ADK tool context for saving Playground artifacts.

    Returns:
        Dictionary containing public Cloud Storage HTTPS URL, artifact filename, and prompt.
    """
    genai_client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
    response = genai_client.models.generate_content(
        model="gemini-omni-flash-preview",
        contents=prompt,
    )

    video_bytes = None
    mime_type = "video/mp4"
    for part in response.candidates[0].content.parts:
        if part.inline_data:
            video_bytes = part.inline_data.data
            mime_type = part.inline_data.mime_type or "video/mp4"
            break

    if not video_bytes:
        return {"error": "Failed to generate video bytes from model."}

    # 1. Save artifact for Playground Artifacts panel
    timestamp_str = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    filename = f"multisport_video_{timestamp_str}.mp4"
    part_artifact = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
    tool_context.save_artifact(filename=filename, artifact=part_artifact)

    # 2. Upload same bytes directly from memory to public Cloud Storage bucket
    gcs_object_name = f"generated_videos/{filename}"
    storage_client = get_gcs_client()
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(gcs_object_name)
    blob.upload_from_string(video_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{gcs_object_name}"

    return {
        "video_url": public_url,
        "public_url": public_url,
        "artifact_filename": filename,
        "prompt": prompt,
    }


schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

a2ui_instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are MultisportCoach, an expert AI trainee assistant for endurance sports "
        "(running, trail running, roller skiing, bicycling)."
    ),
    workflow_description="Analyze the user request, call appropriate tools, and return structured A2UI components when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)

domain_memory_instruction = (
    "PERSONAL TRAINEE MEMORY & PREFERENCE DIRECTIVES:\n"
    "1. You maintain specific, personal memory profiles for every trainee across sessions via Vertex AI Memory Bank.\n"
    "2. Always recall and strictly respect preloaded trainee preferences regarding:\n"
    "   - Preferred Terrain (e.g., technical singletrack, asphalt roads, gravel paths, steep mountain grade)\n"
    "   - Weather & Environmental Condition Tolerances (e.g., wet pavement safety limits, heat/cold sensitivities, rain preferences)\n"
    "   - Sport Types & Technique Style (e.g., classic vs skate roller skiing, road vs trail running, cadence goals)\n"
    "   - Pace Levels, Heart Rate Zones & Fitness Thresholds (e.g., Zone 2 aerobic ceiling, target 5k/marathon pace)\n"
    "   - Personal Training Objectives & Gear (e.g., upcoming ultra-marathon goals, favorite shoes/bikes)\n"
    "3. When a trainee states a preference, acknowledge it warmly and confirm it is stored in their personal Memory Bank profile.\n"
    "4. Always tailor training plans, weather safety advice, location search queries, and Python code calculations "
    "specifically to the active trainee's personal preloaded memories.\n\n"
    "TOOLS & CAPABILITIES:\n"
    "- Consult Firestore via list_activities to analyze past workouts.\n"
    "- Log new sessions via log_activity.\n"
    "- Create periodized plans via generate_training_plan.\n"
    "- Check live weather conditions via get_outdoor_weather_conditions.\n"
    "- Locate places & venue spots via geocode_address and find_nearby_places.\n"
    "- Generate athletic imagery via generate_multisport_image.\n"
    "- Generate short athletic video clips via generate_multisport_video.\n"
    "- PreloadMemoryTool automatically retrieves the trainee's personal preferences at turn start.\n"
    "- Run custom mathematical or statistical workout analyses using AgentEngineSandboxCodeExecutor."
)

full_instruction = f"{a2ui_instruction}\n\n{domain_memory_instruction}"

root_agent = Agent(
    name="multisport_coach",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=full_instruction,
    code_executor=code_executor,
    tools=[
        list_activities,
        log_activity,
        generate_training_plan,
        get_outdoor_weather_conditions,
        geocode_address,
        find_nearby_places,
        generate_multisport_image,
        generate_multisport_video,
        PreloadMemoryTool(),
    ],
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
