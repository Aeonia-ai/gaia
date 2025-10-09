"""
AR Locations API endpoints.

Provides waypoint and location data for AR experiences.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import logging

from app.services.locations.waypoint_reader import waypoint_reader
from app.services.locations.waypoint_transformer import transform_to_unity_format
from app.services.locations.distance_utils import is_within_radius

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

        # Filter waypoints by distance
        nearby_waypoints = []
        for waypoint in waypoints:
            # Check if waypoint has GPS coordinates
            if waypoint.get("location") and waypoint["location"]:
                wp_lat = waypoint["location"]["lat"]
                wp_lng = waypoint["location"]["lng"]

                # Check if within radius
                if is_within_radius(center_lat, center_lng, wp_lat, wp_lng, radius):
                    nearby_waypoints.append(waypoint)
            else:
                # Pathway waypoints (no GPS) - include them in results
                # Unity will handle rendering based on previous waypoint completion
                nearby_waypoints.append(waypoint)

        # Transform to Unity format
        unity_locations = [
            transform_to_unity_format(wp) for wp in nearby_waypoints
        ]

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
