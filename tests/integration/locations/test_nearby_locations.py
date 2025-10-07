"""
Integration tests for /api/v0.3/locations/nearby endpoint

TDD approach: Write tests first, then implement the endpoint
"""
import pytest
import httpx
import os
from tests.fixtures.test_auth import TestUserFactory


@pytest.mark.asyncio
class TestNearbyLocations:
    """Test /locations/nearby endpoint with real KB waypoint data"""

    @pytest.fixture
    def gateway_url(self):
        """Gateway URL."""
        return os.getenv("GATEWAY_URL", "http://gateway:8000")

    async def test_get_nearby_locations_basic(self, gateway_url):
        """Test basic nearby locations query returns waypoints"""
        # Arrange: Mill Valley center coordinates
        gps = "37.906,-122.547"
        radius = 1000  # 1km radius should capture test waypoints

        # Act
        async with httpx.AsyncClient(base_url=gateway_url, timeout=30.0) as client:
            response = await client.get(
                "/api/v0.3/locations/nearby",
                params={"gps": gps, "radius": radius}
            )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "locations" in data
        assert "count" in data
        assert data["count"] > 0
        assert isinstance(data["locations"], list)

    async def test_nearby_locations_returns_gravity_car(self, gateway_url):
        """Test that Gravity Car waypoint is returned (known GPS coordinates)"""
        # Arrange: GPS very close to Gravity Car location
        gps = "37.905696,-122.547701"
        radius = 100  # 100m radius

        # Act
        response = await async_client.get(
            "/api/v0.3/locations/nearby",
            params={"gps": gps, "radius": radius}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Should find the Gravity Car waypoint
        waypoint_ids = [loc["id"] for loc in data["locations"]]
        assert "8_inter_gravity_car" in waypoint_ids

    async def test_nearby_locations_unity_format(self, async_client: AsyncClient):
        """Test that response matches Unity's expected JSON format"""
        # Arrange
        gps = "37.906,-122.547"
        radius = 1000

        # Act
        response = await async_client.get(
            "/api/v0.3/locations/nearby",
            params={"gps": gps, "radius": radius}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Check Unity format for first location
        if data["locations"]:
            location = data["locations"][0]

            # Required Unity fields
            assert "id" in location
            assert "name" in location
            assert "waypoint_type" in location
            assert "media" in location

            # GPS field (optional - VPS waypoints may not have it)
            if "gps" in location:
                assert isinstance(location["gps"], list)
                assert len(location["gps"]) == 2
                assert isinstance(location["gps"][0], float)  # lat
                assert isinstance(location["gps"][1], float)  # lng

            # Media fields
            media = location["media"]
            assert "audio" in media
            assert "visual_fx" in media
            assert "interaction" in media
            assert "display_text" in media

    async def test_nearby_locations_filters_by_distance(self, async_client: AsyncClient):
        """Test that waypoints outside radius are not returned"""
        # Arrange: Very small radius
        gps = "37.905696,-122.547701"  # Gravity Car location
        radius = 10  # Only 10 meters

        # Act
        response = await async_client.get(
            "/api/v0.3/locations/nearby",
            params={"gps": gps, "radius": radius}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Should only find Gravity Car itself (or nothing if GPS isn't exact)
        assert data["count"] <= 1

    async def test_nearby_locations_includes_pathway_waypoints(self, async_client: AsyncClient):
        """Test that pathway waypoints (no GPS) are included in results"""
        # Arrange
        gps = "37.906,-122.547"
        radius = 1000

        # Act
        response = await async_client.get(
            "/api/v0.3/locations/nearby",
            params={"gps": gps, "radius": radius}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Check for pathway waypoint (e.g., "3_fx_lyric_line")
        waypoint_types = [loc["waypoint_type"] for loc in data["locations"]]
        assert "pathway" in waypoint_types

    async def test_nearby_locations_invalid_gps_format(self, async_client: AsyncClient):
        """Test error handling for invalid GPS format"""
        # Arrange: Invalid GPS format
        gps = "invalid"
        radius = 1000

        # Act
        response = await async_client.get(
            "/api/v0.3/locations/nearby",
            params={"gps": gps, "radius": radius}
        )

        # Assert: Should return 400 Bad Request
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    async def test_nearby_locations_experience_filter(self, async_client: AsyncClient):
        """Test filtering by experience parameter"""
        # Arrange
        gps = "37.906,-122.547"
        radius = 1000
        experience = "wylding-woods"

        # Act
        response = await async_client.get(
            "/api/v0.3/locations/nearby",
            params={"gps": gps, "radius": radius, "experience": experience}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["count"] > 0

        # All returned waypoints should be from Wylding Woods
        for location in data["locations"]:
            # Check that ID follows Wylding Woods naming pattern
            assert location["id"] in [
                "8_inter_gravity_car",
                "1_inter_woander_storefront",
                "3_fx_lyric_line",
                # ... etc
            ] or location["id"].startswith("0_test_")


@pytest.mark.asyncio
class TestWaypointTransformation:
    """Test KB YAML to Unity JSON transformation"""

    async def test_transform_gps_waypoint(self):
        """Test transforming a GPS-based waypoint"""
        from app.services.locations.waypoint_transformer import transform_to_unity_format

        # Arrange: KB YAML format (from our markdown files)
        kb_waypoint = {
            "id": "8_inter_gravity_car",
            "name": "#8 INTER  Gravity Car",
            "location": {
                "lat": 37.905696,
                "lng": -122.547700999999
            },
            "waypoint_type": "vps",
            "media": {
                "audio_desc": "Metallic creak, train whistle",
                "audio": "8-gravity-car-sounds.wav",
                "visual_fx": "spark_jump",
                "interaction": "wheel_rotation",
                "image_ref": "6-gravity-car.jpg",
                "display_text": "The historic Gravity Car awaits your touch."
            }
        }

        # Act
        unity_format = transform_to_unity_format(kb_waypoint)

        # Assert
        assert unity_format["id"] == "8_inter_gravity_car"
        assert unity_format["name"] == "#8 INTER  Gravity Car"
        assert unity_format["gps"] == [37.905696, -122.547700999999]
        assert unity_format["waypoint_type"] == "vps"
        assert unity_format["media"]["audio"] == "8-gravity-car-sounds.wav"
        assert unity_format["media"]["display_text"] == "The historic Gravity Car awaits your touch."

    async def test_transform_pathway_waypoint_no_gps(self):
        """Test transforming a pathway waypoint without GPS coordinates"""
        from app.services.locations.waypoint_transformer import transform_to_unity_format

        # Arrange: Pathway waypoint (no location)
        kb_waypoint = {
            "id": "3_fx_lyric_line",
            "name": "#3  FX - Lyric Line",
            "location": None,
            "waypoint_type": "pathway",
            "media": {
                "audio": "3-upbeat-melody-loop.wav",
                "visual_fx": "pink_shimmer_line",
                "interaction": "none",
                "display_text": "Follow the shimmering pink line"
            }
        }

        # Act
        unity_format = transform_to_unity_format(kb_waypoint)

        # Assert
        assert unity_format["id"] == "3_fx_lyric_line"
        assert unity_format["gps"] is None
        assert unity_format["waypoint_type"] == "pathway"


@pytest.mark.asyncio
class TestDistanceCalculation:
    """Test haversine distance calculation"""

    async def test_haversine_distance_same_point(self):
        """Test distance calculation for same point (should be 0)"""
        from app.services.locations.distance_utils import calculate_distance

        # Arrange
        lat1, lng1 = 37.906, -122.547
        lat2, lng2 = 37.906, -122.547

        # Act
        distance = calculate_distance(lat1, lng1, lat2, lng2)

        # Assert
        assert distance == 0.0

    async def test_haversine_distance_known_distance(self):
        """Test distance calculation with known reference"""
        from app.services.locations.distance_utils import calculate_distance

        # Arrange: Two points ~111 meters apart (0.001 degrees latitude)
        lat1, lng1 = 37.906, -122.547
        lat2, lng2 = 37.907, -122.547

        # Act
        distance = calculate_distance(lat1, lng1, lat2, lng2)

        # Assert: Should be approximately 111 meters
        assert 100 < distance < 120

    async def test_distance_within_radius(self):
        """Test helper function for checking if point is within radius"""
        from app.services.locations.distance_utils import is_within_radius

        # Arrange
        center_lat, center_lng = 37.906, -122.547
        point_lat, point_lng = 37.907, -122.547  # ~111m away
        radius = 200  # 200 meters

        # Act
        within = is_within_radius(center_lat, center_lng, point_lat, point_lng, radius)

        # Assert
        assert within is True

    async def test_distance_outside_radius(self):
        """Test helper function for point outside radius"""
        from app.services.locations.distance_utils import is_within_radius

        # Arrange
        center_lat, center_lng = 37.906, -122.547
        point_lat, point_lng = 37.910, -122.547  # ~444m away
        radius = 200  # 200 meters

        # Act
        within = is_within_radius(center_lat, center_lng, point_lat, point_lng, radius)

        # Assert
        assert within is False
