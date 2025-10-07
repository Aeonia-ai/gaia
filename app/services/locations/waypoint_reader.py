"""
Read waypoint data from KB service via HTTP.

Gateway communicates with KB service via HTTP, not direct file access.
"""
import httpx
import logging
from typing import List, Dict, Any
from app.shared.config import settings

logger = logging.getLogger(__name__)


class WaypointReader:
    """
    Read and parse waypoint data from KB service via HTTP.
    """

    def __init__(self, kb_service_url: str = None):
        self.kb_service_url = kb_service_url or settings.KB_SERVICE_URL
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def get_waypoints_for_experience(
        self,
        experience: str = "wylding-woods"
    ) -> List[Dict[str, Any]]:
        """
        Get all waypoints for a specific experience from KB service via HTTP.

        Args:
            experience: Experience name (e.g., "wylding-woods")

        Returns:
            List of waypoint dictionaries from KB
        """
        try:
            # Call KB service waypoints endpoint
            url = f"{self.kb_service_url}/waypoints/{experience}"

            logger.debug(f"Fetching waypoints from KB service: {url}")

            response = await self.http_client.get(url)
            response.raise_for_status()

            data = response.json()

            if not data.get("success"):
                logger.error(f"KB service returned error: {data.get('error')}")
                return []

            waypoints = data.get("waypoints", [])
            logger.info(f"Loaded {len(waypoints)} waypoints for experience '{experience}' from KB service")

            return waypoints

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching waypoints from KB service: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Error loading waypoints for '{experience}': {e}", exc_info=True)
            return []


# Global instance
waypoint_reader = WaypointReader()
