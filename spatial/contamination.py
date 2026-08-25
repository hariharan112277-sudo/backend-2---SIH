"""
OTE - Observation Trust Engine
Member 2: Bad-Neighbor Contamination Defense
Authoritative Source: OTE_Member2_Implementation_Bible.pdf (Phase 6)
"""

import math
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple
from spatial.interfaces import Station, ObservationSnapshot, SpatialNeighbor, SpatialStatus
from spatial.neighbors import NeighborCandidate
from spatial.config import DEFAULT_SPATIAL_CONFIG
from spatial.idw import compute_idw_consensus
from spatial.residual import compute_spatial_residual, classify_spatial_status

# Self-outlier threshold
# [CALIBRATION PARAMETER -- Bible Section 15]
DEFAULT_SELF_OUTLIER_Z_THRESHOLD: float = getattr(DEFAULT_SPATIAL_CONFIG, "self_outlier_z_threshold", 3.0)


class ExclusionReason(str, Enum):
    MISSING_OBSERVATION = "MISSING_OBSERVATION"
    INVALID_OBSERVATION = "INVALID_OBSERVATION"
    INVALID_COORDINATES = "INVALID_COORDINATES"
    SELF_OUTLIER_Z_SCORE = "SELF_OUTLIER_Z_SCORE"


@dataclass(frozen=True)
class SingleVariableSpatialResult:
    """End-to-end single-variable spatial evaluation result."""
    target_station_id: str
    variable: str
    target_value: Optional[float]
    candidate_count: int
    valid_count: int
    excluded_neighbors: List[Tuple[NeighborCandidate, ExclusionReason]]
    consensus: Optional[float]
    used_neighbors: List[SpatialNeighbor]
    raw_residual: Optional[float]
    standardized_residual: Optional[float]
    reference_scale: float
    status: SpatialStatus


def _is_valid_coordinate(lat: Optional[float], lon: Optional[float]) -> bool:
    """Validate latitude and longitude boundaries."""
    if lat is None or lon is None:
        return False
    if not (math.isfinite(lat) and math.isfinite(lon)):
        return False
    return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0


def filter_valid_neighbors(
    neighbors: List[NeighborCandidate],
    snapshots: Dict[str, ObservationSnapshot],
    variable: str,
    self_outlier_z_threshold: float = DEFAULT_SELF_OUTLIER_Z_THRESHOLD,
    variance_epsilon: float = getattr(DEFAULT_SPATIAL_CONFIG, "variance_epsilon", 1e-6),
) -> Tuple[List[NeighborCandidate], List[Tuple[NeighborCandidate, ExclusionReason]]]:
    """
    Filter candidate neighbors based on observation presence, coordinate validity,
    upstream validity flags, and iterative self-outlier Z-score detection.

    Evaluation Order per Bible Section 10:
    1. Coordinate validity
    2. Observation present
    3. Upstream valid flag & finite value
    4. Iterative self-outlier Z-score vs remaining neighbor pool

    [CALIBRATION PARAMETER -- Bible Section 15: self_outlier_z_threshold = 3.0]
    [ASSUMPTION -- PROJECT OWNER CONFIRMATION REQUIRED: Sample std dev for leave-one-out pool]

    Returns:
        Tuple of:
            - valid_neighbors: List of candidates passing all checks
            - excluded_neighbors: List of (candidate, ExclusionReason) tuples
    """
    surviving_candidates: List[NeighborCandidate] = []
    excluded_candidates: List[Tuple[NeighborCandidate, ExclusionReason]] = []

    # Foundational checks (Pass 1)
    for candidate in neighbors:
        stn = candidate.station
        # 1. Coordinate check
        if not _is_valid_coordinate(stn.latitude, stn.longitude):
            excluded_candidates.append((candidate, ExclusionReason.INVALID_COORDINATES))
            continue

        # 2. Observation present check
        if stn.station_id not in snapshots:
            excluded_candidates.append((candidate, ExclusionReason.MISSING_OBSERVATION))
            continue

        snap = snapshots[stn.station_id]
        if snap.values is None or variable not in snap.values or snap.values[variable] is None:
            excluded_candidates.append((candidate, ExclusionReason.MISSING_OBSERVATION))
            continue

        # 3. Upstream valid flag & finite value check
        val = snap.values[variable]
        if (not snap.valid) or (not isinstance(val, (int, float))) or (not math.isfinite(val)):
            excluded_candidates.append((candidate, ExclusionReason.INVALID_OBSERVATION))
            continue

        surviving_candidates.append(candidate)

    # Iterative self-outlier filtering (Pass 2)
    while len(surviving_candidates) >= 3:
        values = [
            snapshots[c.station.station_id].values[variable]
            for c in surviving_candidates
        ]
        n_surviving = len(values)
        worst_z = 0.0
        worst_idx = -1

        for i in range(n_surviving):
            # Leave-one-out comparison pool
            pool = [values[j] for j in range(n_surviving) if j != i]
            n_pool = len(pool)
            mean_pool = sum(pool) / n_pool
            variance_pool = sum((x - mean_pool) ** 2 for x in pool) / (n_pool - 1)
            std_pool = math.sqrt(max(0.0, variance_pool))

            diff = abs(values[i] - mean_pool)
            if math.isclose(diff, 0.0, abs_tol=1e-12):
                z_score = 0.0
            else:
                denom = max(std_pool, variance_epsilon)
                z_score = diff / denom

            if z_score > worst_z:
                worst_z = z_score
                worst_idx = i

        if worst_idx >= 0 and worst_z > self_outlier_z_threshold:
            outlier_candidate = surviving_candidates.pop(worst_idx)
            excluded_candidates.append((outlier_candidate, ExclusionReason.SELF_OUTLIER_Z_SCORE))
        else:
            break

    return surviving_candidates, excluded_candidates


def execute_spatial_pipeline_for_variable(
    target_station_id: str,
    target_value: Optional[float],
    candidate_neighbors: List[NeighborCandidate],
    snapshots: Dict[str, ObservationSnapshot],
    variable: str,
    self_outlier_z_threshold: float = DEFAULT_SELF_OUTLIER_Z_THRESHOLD,
    power_p: float = getattr(DEFAULT_SPATIAL_CONFIG, "idw_power", 2.0),
    spatial_z_threshold: float = getattr(DEFAULT_SPATIAL_CONFIG, "anomaly_threshold_z", 2.5),
) -> SingleVariableSpatialResult:
    """
    Mandatory pre-step pipeline integration:
    candidates -> contamination filter -> valid neighbors -> IDW -> residual & status.
    """
    # 1. Contamination filtering (Mandatory Pre-Step)
    valid_candidates, excluded = filter_valid_neighbors(
        candidate_neighbors,
        snapshots,
        variable,
        self_outlier_z_threshold=self_outlier_z_threshold,
    )

    # 2. IDW Consensus using ONLY valid candidates
    consensus, used_neighbors = compute_idw_consensus(
        target_station_id,
        valid_candidates,
        snapshots,
        variable,
        power_p=power_p,
    )

    # 3. Residual and Status Classification
    raw_res, std_res, scale = compute_spatial_residual(
        target_value=target_value,
        consensus=consensus,
        used_neighbors=used_neighbors,
    )

    status = classify_spatial_status(
        standardized_residual=std_res,
        used_neighbors=used_neighbors,
        spatial_z_threshold=spatial_z_threshold,
    )

    return SingleVariableSpatialResult(
        target_station_id=target_station_id,
        variable=variable,
        target_value=target_value,
        candidate_count=len(candidate_neighbors),
        valid_count=len(valid_candidates),
        excluded_neighbors=excluded,
        consensus=consensus,
        used_neighbors=used_neighbors,
        raw_residual=raw_res,
        standardized_residual=std_res,
        reference_scale=scale,
        status=status,
    )
