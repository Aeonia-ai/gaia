"""
Transform KB YAML waypoint format to Unity JSON format.
"""
from typing import Dict, Any, Optional


def transform_to_unity_format(waypoint: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert KB YAML waypoint to Unity-compatible JSON format.

    Args:
        waypoint: Waypoint data from KB markdown (parsed YAML)

    Returns:
        Unity-compatible JSON structure
    """
    # Extract location coordinates if present
    gps = None
    if waypoint.get("location") and waypoint["location"]:
        gps = [
            waypoint["location"]["lat"],
            waypoint["location"]["lng"]
        ]

    # Build Unity format
    unity_waypoint = {
        "id": waypoint["id"],
        "name": waypoint["name"],
        "waypoint_type": waypoint["waypoint_type"],
        "gps": gps,
        "media": {
            "audio": waypoint["media"].get("audio"),
            "visual_fx": waypoint["media"].get("visual_fx"),
            "interaction": waypoint["media"].get("interaction"),
            "image_ref": waypoint["media"].get("image_ref"),
            "display_text": waypoint["media"].get("display_text"),
        }
    }

    # Add optional fields if present
    if "vps_anchor_id" in waypoint:
        unity_waypoint["vps_anchor_id"] = waypoint["vps_anchor_id"]

    # Generate asset bundle URL (if we have CDN setup)
    # For now, just construct expected URL pattern
    unity_waypoint["asset_bundle_url"] = f"https://cdn.aeonia.ai/assets/{waypoint['id']}.unity3d"

    return unity_waypoint
