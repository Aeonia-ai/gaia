"""
AR Locations API endpoints.

Provides waypoint and location data for AR experiences.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Any, Dict, List, Optional, Tuple
import logging

from app.services.locations.waypoint_reader import waypoint_reader
from app.services.locations.waypoint_transformer import transform_to_unity_format
from app.services.locations.distance_utils import (
    is_within_radius,
    calculate_distance
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v0.3/locations", tags=["locations"])


@router.get("/nearby")
async def get_nearby_locations(
    gps: str = Query(..., description="GPS coordinates in format 'lat,lng'"),
    radius: int = Query(1000, description="Search radius in meters", ge=1, le=10000),
    experience: str = Query("wylding-woods", description="Experience name")
):
    """
    Get waypoints near a GPS location.

    This endpoint reads waypoint data from KB markdown files and returns
    Unity-compatible JSON format.

    Args:
        gps: GPS coordinates as "lat,lng" (e.g., "37.906,-122.547")
        radius: Search radius in meters (default: 1000m)
        experience: Experience name (default: "wylding-woods")

    Returns:
        {
            "locations": [...],  # List of waypoints in Unity format
            "count": int         # Number of locations returned
        }
    """
    try:
        # Parse GPS coordinates
        try:
            lat_str, lng_str = gps.split(",")
            center_lat = float(lat_str.strip())
            center_lng = float(lng_str.strip())
        except (ValueError, AttributeError) as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid GPS format. Expected 'lat,lng', got '{gps}'"
            )

        # Validate coordinates
        if not (-90 <= center_lat <= 90):
            raise HTTPException(
                status_code=400,
                detail=f"Latitude must be between -90 and 90, got {center_lat}"
            )
        if not (-180 <= center_lng <= 180):
            raise HTTPException(
                status_code=400,
                detail=f"Longitude must be between -180 and 180, got {center_lng}"
            )

        # Load all waypoints for this experience from KB
        waypoints = await waypoint_reader.get_waypoints_for_experience(experience)

        # Filter waypoints by distance and calculate distances for sorting
        nearby_waypoints: List[Tuple[Dict[str, Any], float]] = []
        non_gps_waypoints: List[Dict[str, Any]] = []

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
                lat = location.get("lat")
                lng = location.get("lng")

                if isinstance(lat, (int, float)) and isinstance(lng, (int, float)):
                    try:
                        if is_within_radius(center_lat, center_lng, lat, lng, radius):
                            distance = calculate_distance(center_lat, center_lng, lat, lng)
                            nearby_waypoints.append((waypoint, distance))
                    except Exception as distance_error:
                        logger.warning(
                            "Skipping waypoint %s due to distance calculation error: %s",
                            waypoint.get("id", "<unknown>"),
                            distance_error
                        )
                else:
                    logger.debug(
                        "Waypoint %s has non-numeric GPS coordinates: %s",
                        waypoint.get("id", "<unknown>"),
                        location
                    )
                    non_gps_waypoints.append(waypoint)
            else:
                # Pathway waypoints (no GPS) - include separately after GPS-filtered entries
                non_gps_waypoints.append(waypoint)

        # Sort GPS-based waypoints by distance (closest first)
        # Note: Pathway waypoints (non-GPS) are excluded from GPS-based queries
        # They should only be included when part of an active mission context
        nearby_waypoints.sort(key=lambda item: item[1])
        ordered_waypoints = [waypoint for waypoint, _ in nearby_waypoints]

        unity_locations: List[Dict[str, Any]] = []
        for waypoint in ordered_waypoints:
            try:
                unity_locations.append(transform_to_unity_format(waypoint))
            except Exception as transform_error:
                logger.warning(
                    "Skipping waypoint %s due to transform error: %s",
                    waypoint.get("id", "<unknown>"),
                    transform_error,
                    exc_info=True
                )

        logger.info(
            f"Found {len(unity_locations)} waypoints near "
            f"({center_lat}, {center_lng}) within {radius}m radius"
        )

        return {
            "locations": unity_locations,
            "count": len(unity_locations)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting nearby locations: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve locations: {str(e)}"
        )
