# MultisportCoach Agent Demo Walkthrough

This demo showcases **MultisportCoach**, an AI-powered endurance sports coach built with Google's Agent Development Kit (ADK), Gemini, Firestore, Weather APIs, and Google Maps.

---

## 🎵 Video Demo (with Upbeat Lo-Fi Music)
Below is the video clip showcasing the athletic trail running experience powered by Google Gemini Veo 3.1, rendered with an upbeat lo-fi background audio track:

![Multisport Coach Agent Demo Video with Lo-Fi Music](/config/.gemini/antigravity/brain/8ae951dc-ab53-4468-be9c-b485445a7d93/multisport_agent_demo_lofi.mp4)

---

## 🌟 Demo Scenario 1: Core Capability
**User Prompt:**
> *"Suggest a 15k trail running workout in San Francisco with weather and map location"*

### Execution Flow
1. **PreloadMemoryTool**: Retrieved preloaded trainee preferences from Vertex AI Memory Bank (e.g., preferred singletrack terrain, Zone 2 heart rate ceiling).
2. **Weather API Call (`get_outdoor_weather_conditions`)**:
   - Location: Lat `37.7749`, Lng `-122.4194`
   - Response: `11.4°C` (52.5°F), `6.4 km/h` wind speed, `0.0 mm` precipitation, `80%` humidity.
   - Coach Advice: *"✅ Weather conditions are favorable for outdoor training!"*
3. **Google Maps Geocoding (`geocode_address`)**:
   - Query: `Presidio of San Francisco, CA`
   - Lat/Lng: `(37.7923841, -122.4810057)`
4. **Structured A2UI Surface**:
   - Formatted into a clean, flat A2UI Card layout containing route distance, location coordinates, and weather recommendation.

---

## 🚀 Demo Scenario 2: Rich Multi-Tool Sequence
**User Prompt:**
> *"Log my 15k trail run in San Francisco (90 minutes) to Firestore, check my past activities, and generate a motivational image of a runner on a mountain singletrack"*

### Tool Execution Trace

#### 1. Database Write (`log_activity`)
- **Firestore Document ID**: `act-1790679945`
- **Fields Stored**:
  - `sport`: `"trail_running"`
  - `title`: `"15k Trail Run in San Francisco"`
  - `distance_km`: `15.0`
  - `duration_minutes`: `90.0`
  - `date`: `"2026-09-29"`

#### 2. Database Lookup (`list_activities`)
Retrieved past workout history from Firestore:
- `act-001`: 5k Tempo Run (Running, 5.2 km)
- `act-002`: Mountain Trail Loop (Trail Running, 12.4 km)
- `act-003`: Double Pole Endurance (Roller Skiing, 18.0 km)
- `act-004`: Weekend Coastal Ride (Bicycling, 45.0 km)
- `act-1790679822`: 15K Presidio Coastal Trail Tempo (15.0 km)
- `act-1790679945`: Newly logged 15k Trail Run (15.0 km)

#### 3. Image Generation (`generate_multisport_image`)
- **Prompt**: *"A trail runner conquering a scenic mountain singletrack with breathtaking panoramic views at golden hour"*
- **Output Artifact**: Uploaded to Google Cloud Storage public bucket:
  `https://storage.googleapis.com/multisport-coach-assets-qwiklabs-gcp-02-8c87b93d83aa/generated_images/multisport_1790679952.jpg`

![Generated Trail Runner Image](/config/.gemini/antigravity/brain/8ae951dc-ab53-4468-be9c-b485445a7d93/generated_trail_runner.jpg)

---

## 🛠️ Summary of Executed Capabilities

| Feature | Tool / Service | Status |
| :--- | :--- | :---: |
| **Core Workout Planning** | Gemini 3.8 Flash + A2UI Schema | ✅ Verified |
| **Weather Forecast** | `get_outdoor_weather_conditions` | ✅ Verified |
| **Location Geocoding** | `geocode_address` (Google Maps) | ✅ Verified |
| **Database Log Write** | `log_activity` (Firestore) | ✅ Verified |
| **Database History Query** | `list_activities` (Firestore) | ✅ Verified |
| **Image Asset Generation** | `generate_multisport_image` (Imagen 3 / GCS) | ✅ Verified |
| **Video & Music Generation** | `generate_multisport_video` (Veo 3.1) + Lo-Fi Audio Mix | ✅ Verified |
