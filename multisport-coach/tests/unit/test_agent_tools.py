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
"""
Unit tests for MultisportCoach agent tools and wearable platform integrations (Suunto, Strava, Garmin, COROS, Apple HealthKit).
"""

import unittest
from unittest.mock import MagicMock, patch

from app.agent import (
    export_suunto_route,
    find_nearby_places,
    generate_training_plan,
    geocode_address,
    get_coros_evolab_metrics,
    get_garmin_connect_metrics,
    get_outdoor_weather_conditions,
    get_suunto_recovery_status,
    list_activities,
    log_activity,
    root_agent,
    sync_apple_healthkit_workout,
    sync_strava_activity,
    sync_suunto_workout,
)


class TestAgentToolsUnit(unittest.TestCase):

    @patch("app.agent.get_db_client")
    def test_log_and_list_activity(self, mock_db_client):
        """Test logging and listing activities in Firestore."""
        mock_doc = MagicMock()
        mock_collection = MagicMock()
        mock_db = MagicMock()
        mock_db.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_doc
        mock_db_client.return_value = mock_db

        # Test log_activity
        res = log_activity(
            sport="trail_running",
            title="Presidio Trail Run",
            distance_km=12.0,
            duration_minutes=75.0,
        )
        self.assertEqual(res["sport"], "trail_running")
        self.assertEqual(res["title"], "Presidio Trail Run")
        self.assertEqual(res["distance_km"], 12.0)
        mock_doc.set.assert_called_once()

    @patch("app.agent.get_db_client")
    def test_suunto_tools(self, mock_db_client):
        """Test Suunto integration tools: sync, recovery, and route export."""
        mock_doc = MagicMock()
        mock_collection = MagicMock()
        mock_db = MagicMock()
        mock_db.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_doc
        mock_db_client.return_value = mock_db

        # 1. Sync Suunto Workout
        suunto_res = sync_suunto_workout(
            sport="trail_running",
            title="Suunto Alpine Loop",
            distance_km=15.0,
            duration_minutes=90.0,
            peak_training_effect_pte=4.1,
            epoc_ml_kg=120.0,
            recovery_time_hours=24,
            device_model="Suunto Vertical",
        )
        self.assertEqual(suunto_res["source"], "Suunto Cloud API")
        self.assertEqual(suunto_res["suunto_metrics"]["pte"], 4.1)

        # 2. Get Suunto Recovery Status
        rec_res = get_suunto_recovery_status()
        self.assertIn("readiness_status", rec_res)
        self.assertIn("recommended_recovery_time_hours", rec_res)

        # 3. Export Suunto Route GPX
        with patch("app.agent.get_gcs_client") as mock_gcs:
            mock_bucket = MagicMock()
            mock_blob = MagicMock()
            mock_gcs.return_value.bucket.return_value = mock_bucket
            mock_bucket.blob.return_value = mock_blob

            route_res = export_suunto_route(
                route_name="Presidio Coastal Trail",
                waypoints=[{"lat": 37.792, "lng": -122.481}],
            )
            self.assertEqual(route_res["route_name"], "Presidio Coastal Trail")
            self.assertIn("suunto_gpx_url", route_res)

    @patch("app.agent.get_db_client")
    def test_strava_tool(self, mock_db_client):
        """Test Strava API v3 activity sync."""
        mock_doc = MagicMock()
        mock_collection = MagicMock()
        mock_db = MagicMock()
        mock_db.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_doc
        mock_db_client.return_value = mock_db

        strava_res = sync_strava_activity(
            sport="bicycling",
            title="Hawk Hill Climb",
            distance_km=32.0,
            duration_minutes=80.0,
            relative_effort=140,
            suffer_score=95,
        )
        self.assertEqual(strava_res["source"], "Strava API v3")
        self.assertEqual(strava_res["strava_metrics"]["relative_effort"], 140)

    def test_garmin_tool(self):
        """Test Garmin Connect biometric metrics."""
        garmin_res = get_garmin_connect_metrics()
        self.assertEqual(garmin_res["source"], "Garmin Connect API")
        self.assertIn("body_battery", garmin_res)
        self.assertIn("hrv_status", garmin_res)
        self.assertIn("training_readiness", garmin_res)

    def test_coros_evolab_tool(self):
        """Test COROS EvoLab metrics (Irvine, California)."""
        coros_res = get_coros_evolab_metrics()
        self.assertIn("COROS", coros_res["source"])
        self.assertIn("base_fitness_score", coros_res)
        self.assertIn("fatigue_index", coros_res)

    @patch("app.agent.get_db_client")
    def test_apple_healthkit_tool(self, mock_db_client):
        """Test Apple HealthKit workout sync (Cupertino, California)."""
        mock_doc = MagicMock()
        mock_collection = MagicMock()
        mock_db = MagicMock()
        mock_db.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_doc
        mock_db_client.return_value = mock_db

        apple_res = sync_apple_healthkit_workout(
            sport="running",
            title="Golden Gate Park 10k",
            distance_km=10.0,
            duration_minutes=48.0,
            avg_running_power_watts=255.0,
        )
        self.assertIn("Apple", apple_res["source"])
        self.assertEqual(apple_res["apple_metrics"]["running_power_watts"], 255.0)

    def test_weather_and_maps_tools(self):
        """Test Weather and Google Maps helper functions."""
        # Weather tool
        w_res = get_outdoor_weather_conditions(37.7749, -122.4194, "running")
        self.assertIn("temperature_c", w_res)
        self.assertIn("coach_advice", w_res)

        # Maps Geocoding
        g_res = geocode_address("San Francisco, CA")
        self.assertIn("location", g_res)

        # Maps Nearby Places
        p_res = find_nearby_places(37.7749, -122.4194, "park")
        self.assertIsInstance(p_res, list)

    def test_training_plan_generation(self):
        """Test generate_training_plan periodization logic."""
        plan = generate_training_plan("trail_running", target_distance_km=21.1, weeks=4, fitness_level="intermediate")
        self.assertEqual(plan["sport"], "trail_running")
        self.assertEqual(plan["fitness_level"], "intermediate")
        self.assertEqual(len(plan["weekly_schedule"]), 4)

    def test_root_agent_tool_registration(self):
        """Verify all expected tools are registered on root_agent."""
        registered_tool_names = [
            t.__name__ if hasattr(t, "__name__") else t.__class__.__name__
            for t in root_agent.tools
        ]
        expected_tools = [
            "list_activities",
            "log_activity",
            "sync_suunto_workout",
            "get_suunto_recovery_status",
            "export_suunto_route",
            "sync_strava_activity",
            "get_garmin_connect_metrics",
            "get_coros_evolab_metrics",
            "sync_apple_healthkit_workout",
            "generate_training_plan",
            "get_outdoor_weather_conditions",
            "geocode_address",
            "find_nearby_places",
            "generate_multisport_image",
            "generate_multisport_video",
            "PreloadMemoryTool",
        ]
        for tool_name in expected_tools:
            self.assertIn(tool_name, registered_tool_names, f"Tool '{tool_name}' must be registered on root_agent")


if __name__ == "__main__":
    unittest.main()
