"""
OTE - Observation Trust Engine
Member 2: Inverse Distance Weighting (IDW) Consensus Core
"""

import math
from typing import Dict, List, Optional, Tuple
from spatial.interfaces import ObservationSnapshot, SpatialNeighbor
from spatial.neighbors import NeighborCandidate
from spatial.config import IDW_POWER_P


def compute_idw_consensus(
    target_station_id: str,
    neighbors: List[NeighborCandidate],
    observations: Dict[str, ObservationSnapshot],
    variable_name: str,
    power_p: float = IDW_POWER_P,
) -> Tuple[Optional[float], List[SpatialNeighbor]]:
    """
    Compute IDW spatial consensus for a given variable across valid neighbor observations.

    Returns:
        Tuple of (consensus_value, list_of_used_SpatialNeighbor_objects)
        If no valid neighbor observations exist, returns (None, []).
    """
    # 1. Filter valid contributing neighbors
    contributing: List[Tuple[NeighborCandidate, float]] = []
    for cand in neighbors:
        stn_id = cand.station.station_id
        if stn_id == target_station_id:
            continue
        
        obs = observations.get(stn_id)
        if obs is None or not obs.valid:
            continue
        
        if variable_name not in obs.values:
            continue
        
        val = obs.values[variable_name]
        if val is None or not math.isfinite(val):
            continue

        contributing.append((cand, float(val)))

    if not contributing:
        return None, []

    # 2. Check for co-located stations (distance == 0.0)
    zero_distance_neighbors = [item for item in contributing if item[0].distance_km == 0.0]
    if zero_distance_neighbors:
        # Zero-distance dominance rule: arithmetic average of co-located stations
        mean_val = sum(val for _, val in zero_distance_neighbors) / len(zero_distance_neighbors)
        weight_per_zero = 1.0 / len(zero_distance_neighbors)
        
        used_neighbors: List[SpatialNeighbor] = []
        for cand, val in contributing:
            w = weight_per_zero if cand.distance_km == 0.0 else 0.0
            used_neighbors.append(
                SpatialNeighbor(
                    station_id=cand.station.station_id,
                    distance_km=cand.distance_km,
                    observed_value=val,
                    weight=w,
                )
            )
        return mean_val, used_neighbors

    # 3. Standard IDW calculation: w_i = 1 / (d_i ^ p)
    raw_weights: List[float] = []
    for cand, _ in contributing:
        raw_w = 1.0 / (cand.distance_km ** power_p)
        raw_weights.append(raw_w)

    sum_raw_weights = sum(raw_weights)
    if sum_raw_weights <= 0.0 or not math.isfinite(sum_raw_weights):
        return None, []

    # 4. Calculate consensus and normalized weights
    weighted_sum = sum(w * val for w, (_, val) in zip(raw_weights, contributing))
    consensus = weighted_sum / sum_raw_weights

    used_neighbors = []
    for (cand, val), raw_w in zip(contributing, raw_weights):
        norm_w = raw_w / sum_raw_weights
        used_neighbors.append(
            SpatialNeighbor(
                station_id=cand.station.station_id,
                distance_km=cand.distance_km,
                observed_value=val,
                weight=norm_w,
            )
        )

    return consensus, used_neighbors
