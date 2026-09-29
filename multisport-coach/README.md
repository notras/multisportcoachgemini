# MultisportCoach

**MultisportCoach** is an AI-powered trainee assistant for endurance athletes across running, trail running, roller skiing, and cycling. Built on Google's Agent Development Kit (ADK) and deployed to Agent Runtime, it provides personalized workout planning, activity tracking, route geocoding, live weather safety checks, and custom AI media generation.

---

## Key Features & Wired Capabilities

MultisportCoach is backed by real Google Cloud infrastructure and tools:

* **Personalized Athlete Memory**: Wired to **Vertex AI Memory Bank** (`PreloadMemoryTool`) to remember athlete profiles, heart rate zones, terrain preferences, and training history across sessions.
* **Activity Tracking (Firestore)**:
  * `log_activity`: Logs workouts (sport, distance, duration, elevation, title, notes) directly to **Cloud Firestore**.
  * `list_activities`: Queries past workout history from Firestore.
* **Weather & Environmental Safety (`get_outdoor_weather_conditions`)**: Fetches temperature, wind speed, precipitation, and humidity to provide outdoor training advice.
* **Location & Venue Search (Google Maps)**:
  * `geocode_address`: Geocodes addresses and trailheads.
  * `find_nearby_places`: Discovers nearby parks, trails, and athletic spots.
* **AI Image Generation (`generate_multisport_image`)**: Generates custom athletic imagery using **Vertex AI Imagen 3** (`imagen-3.0-generate-002`) and stores output in **Google Cloud Storage (GCS)**.
* **AI Video Generation (`generate_multisport_video`)**: Generates short athletic video clips using **Google Gemini / Veo** and uploads them to a public Cloud Storage bucket.
* **Python Code Sandbox (`AgentEngineSandboxCodeExecutor`)**: Executes custom Python code for mathematical and statistical workout calculations.
* **Adaptive User Interface (A2UI)**: Renders structured, flat card components (Card, Column, Row, Text, Image) via `a2ui_callback`.

---

## Implemented Tools & Google Cloud Services

Based on `app/agent.py` and `agents-cli-manifest.yaml`, the following services and tools are fully wired:

| Category | Service / Tool | Description |
| :--- | :--- | :--- |
| **Agent Framework** | Google ADK 1.7.0 (`google-adk`) | Core agent orchestration runtime |
| **LLM Model** | Gemini 3.8 Flash (`gemini-3.8-flash`) | Primary reasoning model |
| **Memory** | Vertex AI Memory Bank | Stores and recalls trainee preferences |
| **Database** | Cloud Firestore | Workout activity storage (`log_activity`, `list_activities`) |
| **Media Storage** | Cloud Storage (GCS) | Asset hosting for generated images and videos |
| **Image Generation** | Vertex AI Imagen 3 | `generate_multisport_image` |
| **Video Generation** | Vertex AI Gemini Omni / Veo | `generate_multisport_video` |
| **Suunto Integration** | Suunto Cloud API & Watch Nav | `sync_suunto_workout`, `get_suunto_recovery_status`, `export_suunto_route` |
| **Strava Integration** | Strava API v3 | `sync_strava_activity` (Relative Effort, Suffer Score, Segment efforts) |
| **Garmin Integration** | Garmin Connect API | `get_garmin_connect_metrics` (Body Battery, HRV Status, Sleep & Training Readiness) |
| **COROS Integration** | COROS EvoLab (Irvine, CA) | `get_coros_evolab_metrics` (Base Fitness score, Fatigue Index, 4-Week Load Impact) |
| **Apple HealthKit** | Apple Watch (Cupertino, CA) | `sync_apple_healthkit_workout` (Running Power, Ground Contact Time, Active Kcal) |
| **Location Services** | Google Maps API | `geocode_address`, `find_nearby_places` |
| **Weather** | Open-Meteo Weather API | `get_outdoor_weather_conditions` |
| **Code Sandbox** | Agent Engine Sandbox Executor | Python mathematical analysis |
| **UI Protocol** | A2UI (0.8 Schema) | Generates structured A2UI Cards |

### Planned / Not Yet Implemented
The following features mentioned in early design drafts were planned but are not currently implemented in code:
* `get_gear_recommendation`: *Planned, not yet implemented.*
* A2UI Tables & Headings: *A2UI layout is restricted to flat Card/Column/Row/Text/Image components.*

---

## Local Setup & Run Instructions

To run the agent locally for testing or development, follow these steps:

### 1. Prerequisites
Ensure Python 3.11+ is installed and your environment has Google Cloud Application Default Credentials (ADC) configured.

```bash
gcloud auth application-default login
```

### 2. Install Dependencies
Create a virtual environment and install the required dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file in the project root with your project configuration:

```env
PROJECT_ID="your-gcp-project-id"
BUCKET_NAME="your-gcs-bucket-name"
```

### 4. Seed Firestore (Optional)
Populate sample activity data into Firestore:

```bash
python seed_firestore.py
```

### 5. Run the Local App
Start the local FastAPI server using Uvicorn:

```bash
uvicorn app.fast_api_app:app --host 0.0.0.0 --port 8000
```

To run the frontend proxy server:

```bash
python frontend/main.py
```
