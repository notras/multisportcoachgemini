import subprocess
from google.cloud import firestore
from google.oauth2.credentials import Credentials

# Hardcoded project ID as required to avoid runtime resolution to project number
PROJECT_ID = "qwiklabs-gcp-02-8c87b93d83aa"


def get_db_client():
    """Initializes Firestore client with hardcoded project ID, utilizing ADC token when available locally."""
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


db = get_db_client()

SEEDED_ACTIVITIES = [
    {
        "id": "act-001",
        "sport": "running",
        "title": "5k Tempo Run",
        "date": "2026-09-25",
        "distance_km": 5.2,
        "duration_minutes": 25.5,
        "elevation_gain_m": 45,
        "avg_hr": 155,
        "notes": "Felt good, solid Z3 effort.",
    },
    {
        "id": "act-002",
        "sport": "trail_running",
        "title": "Mountain Trail Loop",
        "date": "2026-09-26",
        "distance_km": 12.4,
        "duration_minutes": 78.0,
        "elevation_gain_m": 420,
        "avg_hr": 162,
        "notes": "Steep technical climbs, strong downhill pace.",
    },
    {
        "id": "act-003",
        "sport": "roller_skiing",
        "title": "Double Pole Endurance",
        "date": "2026-09-27",
        "distance_km": 18.0,
        "duration_minutes": 65.0,
        "elevation_gain_m": 110,
        "avg_hr": 148,
        "notes": "Smooth technique, focus on upper body power.",
    },
    {
        "id": "act-004",
        "sport": "bicycling",
        "title": "Weekend Coastal Ride",
        "date": "2026-09-28",
        "distance_km": 45.0,
        "duration_minutes": 110.0,
        "elevation_gain_m": 350,
        "avg_hr": 138,
        "notes": "Steady Z2 aerobic ride, high cadence.",
    },
]


def seed_database():
    print(f"Seeding Firestore collection 'activities' in project '{PROJECT_ID}'...")
    collection_ref = db.collection("activities")
    for item in SEEDED_ACTIVITIES:
        doc_ref = collection_ref.document(item["id"])
        doc_ref.set(item)
        print(f"  ✓ Seeded: {item['id']} - {item['title']} ({item['sport']})")
    print("Firestore seeding complete!")


if __name__ == "__main__":
    seed_database()
