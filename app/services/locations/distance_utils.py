"""
Distance calculation utilities for GPS-based waypoints.

Uses haversine formula for calculating distances between GPS coordinates.
"""
import math
from typing import Tuple


def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate distance between two GPS coordinates using haversine formula.

    Args:
        lat1: Latitude of first point
        lng1: Longitude of first point
        lat2: Latitude of second point
        lng2: Longitude of second point

    Returns:
        Distance in meters
    """
    # Earth's radius in meters
    R = 6371000

    # Convert to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)

    # Haversine formula
    a = (
        math.sin(delta_lat / 2) ** 2 +
        math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = R * c
    return distance


def is_within_radius(
    center_lat: float,
    center_lng: float,
    point_lat: float,
    point_lng: float,
    radius: float
) -> bool:
    """
    Check if a point is within a given radius of a center point.

    Args:
        center_lat: Latitude of center point
        center_lng: Longitude of center point
        point_lat: Latitude of point to check
        point_lng: Longitude of point to check
        radius: Radius in meters

    Returns:
        True if point is within radius, False otherwise
    """
    distance = calculate_distance(center_lat, center_lng, point_lat, point_lng)
    return distance <= radius
