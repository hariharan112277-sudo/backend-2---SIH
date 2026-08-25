"""
OTE - Observation Trust Engine
Member 2: Deterministic Neighbor Discovery Engine
"""

from dataclasses import dataclass
from typing import List, Optional
from spatial.interfaces import Station, StationRegistry
from spatial.config import SpatialConfig, DEFAULT_SPATIAL_CONFIG
from spatial.station_registry import is_valid_station
from spatial.distance import haversine_distance_km


@dataclass(frozen=True)
class NeighborCandidate:
    """Represents a discovered neighboring station and its geographic distance."""
    station: Station
    distance_km: float


def _get_sorted_candidates(
    target_station: Station,
    registry: StationRegistry,
) -> List[NeighborCandidate]:
    """
    Extract valid neighbor candidates, exclude self, compute distances,
    and sort deterministically by (distance_km ASC, station_id ASC).
    """
    if not is_valid_station(target_station):
        return []

    # Filter candidates from registry
    all_stations = registry.get_all_stations()
    candidates: List[NeighborCandidate] = []

    for stn in all_stations:
        # Self-exclusion
        if stn.station_id == target_station.station_id:
            continue
        # Spatial validity check
        if not is_valid_station(stn):
            continue

        dist = haversine_distance_km(
            target_station.latitude,
            target_station.longitude,
            stn.latitude,
            stn.longitude,
        )
        candidates.append(NeighborCandidate(station=stn, distance_km=dist))

    # Deterministic sorting: distance ascending, then station_id ascending for ties
    candidates.sort(key=lambda c: (c.distance_km, c.station.station_id))
    return candidates


def find_k_nearest_neighbors(
    target_station: Station,
    registry: StationRegistry,
    k: int = 5,
    max_radius_km: Optional[float] = None,
) -> List[NeighborCandidate]:
    """
    Discover up to k-nearest valid neighbor stations within optional max_radius_km.
    """
    candidates = _get_sorted_candidates(target_station, registry)
    if max_radius_km is not None:
        candidates = [c for c in candidates if c.distance_km <= max_radius_km]
    return candidates[:k]


def find_radius_neighbors(
    target_station: Station,
    registry: StationRegistry,
    radius_km: float = 50.0,
    max_neighbors: Optional[int] = None,
) -> List[NeighborCandidate]:
    """
    Discover all valid neighbor stations within radius_km (inclusive).
    """
    candidates = _get_sorted_candidates(target_station, registry)
    filtered = [c for c in candidates if c.distance_km <= radius_km]
    if max_neighbors is not None:
        return filtered[:max_neighbors]
    return filtered


def discover_neighbors(
    target_station: Station,
    registry: StationRegistry,
    config: SpatialConfig = DEFAULT_SPATIAL_CONFIG,
) -> List[NeighborCandidate]:
    """
    High-level neighbor discovery conforming to configured spatial rules.
    """
    if config.neighborhood_rule == "RADIUS_ONLY":
        return find_radius_neighbors(
            target_station,
            registry,
            radius_km=config.max_radius_km,
            max_neighbors=config.max_neighbors,
        )

    # Default RADIUS_OR_KNN: k-nearest bounded by max_radius_km
    return find_k_nearest_neighbors(
        target_station,
        registry,
        k=config.k_neighbors,
        max_radius_km=config.max_radius_km,
    )
