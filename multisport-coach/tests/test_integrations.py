import asyncio
import json
import os
import unittest
import httpx
import subprocess
from google.cloud import firestore, storage
from google.oauth2.credentials import Credentials

PROJECT_ID = "qwiklabs-gcp-02-8c87b93d83aa"
BUCKET_NAME = "multisport-coach-assets-qwiklabs-gcp-02-8c87b93d83aa"
CLOUD_RUN_URL = "https://multisport-coach-frontend-283685923116.us-east4.run.app"


class TestIntegrations(unittest.TestCase):

    def test_01_firestore_integration(self):
        """Test Firestore connectivity and activity logging."""
        try:
            token = subprocess.check_output(
                ["gcloud", "auth", "application-default", "print-access-token"],
                stderr=subprocess.DEVNULL,
            ).decode("utf-8").strip()
            db = firestore.Client(project=PROJECT_ID, credentials=Credentials(token))
        except Exception:
            db = firestore.Client(project=PROJECT_ID)

        doc_ref = db.collection("activities").document("test-activity-001")
        doc_ref.set({
            "id": "test-activity-001",
            "sport": "trail_running",
            "title": "Integration Test Run",
            "distance_km": 15.0,
            "duration_minutes": 90.0,
        })

        doc = doc_ref.get()
        self.assertTrue(doc.exists, "Firestore test activity document should exist")
        data = doc.to_dict()
        self.assertEqual(data["sport"], "trail_running")
        print("✅ Firestore Integration: Verified read/write")

    def test_02_gcs_public_bucket_integration(self):
        """Test Cloud Storage public bucket accessibility."""
        try:
            token = subprocess.check_output(
                ["gcloud", "auth", "application-default", "print-access-token"],
                stderr=subprocess.DEVNULL,
            ).decode("utf-8").strip()
            gcs_client = storage.Client(project=PROJECT_ID, credentials=Credentials(token))
        except Exception:
            gcs_client = storage.Client(project=PROJECT_ID)

        bucket = gcs_client.bucket(BUCKET_NAME)
        self.assertTrue(bucket.exists(), f"GCS bucket {BUCKET_NAME} should exist")
        print("✅ GCS Bucket Integration: Verified bucket access")

    def test_03_weather_and_maps_tools(self):
        """Test Weather and Google Maps tools."""
        from app.agent import get_outdoor_weather_conditions, geocode_address, find_nearby_places

        # 1. Geocode San Francisco (synchronous tool)
        res_geo = geocode_address("San Francisco, CA")
        self.assertIn("location", res_geo)
        self.assertIn("latitude", res_geo["location"])
        self.assertIn("longitude", res_geo["location"])
        lat = res_geo["location"]["latitude"]
        lng = res_geo["location"]["longitude"]
        print(f"✅ Maps Geocoding Tool: Verified ({lat}, {lng})")

        # 2. Weather for SF lat/lng
        res_weather = get_outdoor_weather_conditions(lat, lng, "trail_running")
        self.assertIn("temperature_c", res_weather)
        print("✅ Weather API Tool: Verified")

        # 3. Places near SF
        res_places = find_nearby_places(lat, lng, "park")
        self.assertIsInstance(res_places, list)
        print(f"✅ Maps Places Tool: Verified ({len(res_places)} places found)")

    def test_04_code_executor_and_gcs_tools(self):
        """Test Python Code Sandbox Executor initialization and GCS client helper."""
        from app.agent import code_executor, get_gcs_client, generate_multisport_video

        gcs_client = get_gcs_client()
        bucket = gcs_client.bucket(BUCKET_NAME)
        self.assertTrue(bucket.exists(), "GCS Bucket client should access target bucket")
        self.assertTrue(callable(generate_multisport_video), "generate_multisport_video tool should be callable")
        print("✅ Sandbox Code Executor, Video Generator Tool & GCS Upload Helpers: Verified")

    def test_05_cloud_run_endpoint(self):
        """Test live Cloud Run frontend /chat endpoint."""
        url = f"{CLOUD_RUN_URL}/chat"
        payload = {"message": "Suggest a 15k trail running workout in San Francisco with a map and weather forecast"}
        response = httpx.post(url, json=payload, timeout=90.0)
        self.assertEqual(response.status_code, 200, f"Cloud Run should return 200 OK: {response.text}")
        data = response.json()
        self.assertIn("parts", data, "Cloud Run response should contain 'parts'")
        self.assertGreater(len(data["parts"]), 0, "Cloud Run response parts should not be empty")
        full_text = json.dumps(data)
        self.assertNotIn("Cannot add session to memory", full_text, "Memory error should not occur")
        print(f"✅ Cloud Run Frontend Chat Endpoint: Verified ({len(data['parts'])} output parts received)")


if __name__ == "__main__":
    unittest.main()
