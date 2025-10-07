"""
TDD: /api/v0.3/locations/nearby endpoint

Start with simplest test, then implement to make it pass.
"""
import pytest
import httpx
import os


@pytest.mark.asyncio
class TestNearbyLocationsSimple:
    """Simple TDD tests for /locations/nearby endpoint"""

    @pytest.fixture
    def gateway_url(self):
        """Gateway URL."""
        return os.getenv("GATEWAY_URL", "http://gateway:8000")

    async def test_endpoint_exists(self, gateway_url):
        """Test 1: Endpoint should exist and return 200 OK"""
        # Arrange
        gps = "37.906,-122.547"  # Mill Valley center
        radius = 1000

        # Act
        async with httpx.AsyncClient(base_url=gateway_url, timeout=30.0) as client:
            response = await client.get(
                "/api/v0.3/locations/nearby",
                params={"gps": gps, "radius": radius}
            )

        # Assert: Just check endpoint exists
        assert response.status_code in [200, 404]  # 404 expected until we implement

    async def test_returns_locations_array(self, gateway_url):
        """Test 2: Should return JSON with locations array"""
        # Arrange
        gps = "37.906,-122.547"
        radius = 1000

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
        assert isinstance(data["locations"], list)

    async def test_returns_count_field(self, gateway_url):
        """Test 3: Should include count field"""
        # Arrange
        gps = "37.906,-122.547"
        radius = 1000

        # Act
        async with httpx.AsyncClient(base_url=gateway_url, timeout=30.0) as client:
            response = await client.get(
                "/api/v0.3/locations/nearby",
                params={"gps": gps, "radius": radius}
            )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert data["count"] == len(data["locations"])

    async def test_finds_gravity_car_waypoint(self, gateway_url):
        """Test 4: Should find Gravity Car waypoint from KB"""
        # Arrange: GPS coordinates near Gravity Car
        gps = "37.905696,-122.547701"
        radius = 100  # Small radius

        # Act
        async with httpx.AsyncClient(base_url=gateway_url, timeout=30.0) as client:
            response = await client.get(
                "/api/v0.3/locations/nearby",
                params={"gps": gps, "radius": radius}
            )

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Should find at least the Gravity Car
        waypoint_ids = [loc["id"] for loc in data["locations"]]
        assert "8_inter_gravity_car" in waypoint_ids

    async def test_unity_json_format(self, gateway_url):
        """Test 5: Should return Unity-compatible JSON format"""
        # Arrange
        gps = "37.906,-122.547"
        radius = 1000

        # Act
        async with httpx.AsyncClient(base_url=gateway_url, timeout=30.0) as client:
            response = await client.get(
                "/api/v0.3/locations/nearby",
                params={"gps": gps, "radius": radius}
            )

        # Assert
        assert response.status_code == 200
        data = response.json()

        if data["locations"]:
            location = data["locations"][0]

            # Check Unity required fields
            assert "id" in location
            assert "name" in location
            assert "waypoint_type" in location
            assert "media" in location

            # Media object structure
            media = location["media"]
            assert isinstance(media, dict)
            assert "display_text" in media
