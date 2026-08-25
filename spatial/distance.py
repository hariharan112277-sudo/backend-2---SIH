"""
OTE - Observation Trust Engine
Member 2: Haversine Geographic Distance Metric
"""

import math
from typing import Optional
from spatial.interfaces import Station
from spatial.station_registry import is_valid_coordinate

# Mean Earth radius in kilometers (WGS-84 / IUGG standard mean)
EARTH_RADIUS_KM: float = 6371.0088


def haversine_distance_km(
    lat1: Optional[float],
    lon1: Optional[float],
    lat2: Optional[float],
    lon2: Optional[float],
) -> float:
    """
    Calculate the great-circle distance between two geographic points in kilometers
    using the Haversine formula.

    Raises:
        ValueError: If any coordinate is missing, non-finite, or out of physical bounds.
    """
    if not is_valid_coordinate(lat1, lon1) or not is_valid_coordinate(lat2, lon2):
        raise ValueError(
            f"Invalid geographic coordinate pair: ({lat1}, {lon1}), ({lat2}, {lon2})"
        )

    # Identical coordinate fast-path
    if lat1 == lat2 and lon1 == lon2:
        return 0.0

    # Convert decimal degrees to radians
    phi1 = math.radians(float(lat1))  # type: ignore
    phi2 = math.radians(float(lat2))  # type: ignore
    delta_phi = math.radians(float(lat2) - float(lat1))  # type: ignore
    delta_lambda = math.radians(float(lon2) - float(lon1))  # type: ignore

    # Haversine formula
    sin_dphi_2 = math.sin(delta_phi / 2.0)
    sin_dlambda_2 = math.sin(delta_lambda / 2.0)

    a = (sin_dphi_2 * sin_dphi_2) + (
        math.cos(phi1) * math.cos(phi2) * sin_dlambda_2 * sin_dlambda_2
    )
    # Numerical clamping to protect against floating point drift
    a = min(1.0, max(0.0, a))

    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_RADIUS_KM * c


def station_distance_km(station_a: Station, station_b: Station) -> float:
    """
    Calculate the geographic distance in kilometers between two Station instances.
    """
    return haversine_distance_km(
        station_a.latitude,
        station_a.longitude,
        station_b.latitude,
        station_b.longitude,
    )
