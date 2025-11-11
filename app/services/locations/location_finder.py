"""
Shared location finding utilities.

Used by both REST API (/locations/nearby) and WebSocket (AOI delivery).
"""
from typing import List, Dict, Any, Tuple
import logging

from app.services.locations.waypoint_reader import waypoint_reader
from app.services.locations.distance_utils import is_within_radius, calculate_distance

logger = logging.getLogger(__name__)


async def find_nearby_locations(
    lat: float,
    lng: float,
    radius_m: int = 1000,
    experience: str = "wylding-woods"
) -> List[Dict[str, Any]]:
    """
    Find waypoints near GPS coordinates.

    Reusable function for both REST API and WebSocket handlers.

    Args:
        lat: Latitude
        lng: Longitude
        radius_m: Search radius in meters (default: 1000m)
        experience: Experience name

    Returns:
        List of waypoints sorted by distance (closest first)
        Empty list if no waypoints within radius
    """
    try:
        # Load all waypoints for this experience from KB
        waypoints = await waypoint_reader.get_waypoints_for_experience(experience)

        # Filter waypoints by distance and calculate distances for sorting
        nearby_waypoints: List[Tuple[Dict[str, Any], float]] = []

        for index, waypoint in enumerate(waypoints):
            if not isinstance(waypoint, dict):
                logger.warning(
                    "Skipping waypoint at index %s: expected dict but got %s",
                    index,
                    type(waypoint)
                )
                continue

            location = waypoint.get("location")
            if isinstance(location, dict):
                wp_lat = location.get("lat")
                wp_lng = location.get("lng")

                if isinstance(wp_lat, (int, float)) and isinstance(wp_lng, (int, float)):
                    try:
                        if is_within_radius(lat, lng, wp_lat, wp_lng, radius_m):
                            distance = calculate_distance(lat, lng, wp_lat, wp_lng)
                            nearby_waypoints.append((waypoint, distance))
                    except Exception as distance_error:
                        logger.warning(
                            "Skipping waypoint %s due to distance calculation error: %s",
                            waypoint.get("id", "<unknown>"),
                            distance_error
                        )

        # Sort by distance (closest first)
        nearby_waypoints.sort(key=lambda item: item[1])
        sorted_waypoints = [waypoint for waypoint, _ in nearby_waypoints]

        logger.debug(
            f"Found {len(sorted_waypoints)} waypoints near "
            f"({lat}, {lng}) within {radius_m}m radius"
        )

        return sorted_waypoints

    except Exception as e:
        logger.error(f"Error finding nearby locations: {e}", exc_info=True)
        return []
