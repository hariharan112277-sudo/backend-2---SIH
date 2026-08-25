"""
OTE - Observation Trust Engine
Member 2: Spatial Residual & Local Standardization Computation
Authoritative Source: OTE_Member2_Implementation_Bible.pdf (Phase 5)
"""

import math
from typing import List, Optional, Tuple
from spatial.interfaces import SpatialNeighbor, SpatialStatus
from spatial.config import DEFAULT_SPATIAL_CONFIG

# Minimum valid neighbors for non-insufficient status
# [CALIBRATION PARAMETER -- Bible Section 15]
MIN_VALID_NEIGHBORS: int = 2

# Spatial anomaly Z-score threshold
# [CALIBRATION PARAMETER -- Bible Section 15]
DEFAULT_SPATIAL_Z_THRESHOLD: float = getattr(DEFAULT_SPATIAL_CONFIG, "anomaly_threshold_z", 2.5)


def compute_reference_scale(
    used_neighbors: List[SpatialNeighbor],
) -> float:
    """
    Compute reference scale from valid contributing neighbor observations.

    Reference-scale source:
    neighbor-value standard deviation
    [ASSUMPTION -- PROJECT OWNER CONFIRMATION REQUIRED]

    Returns:
        Sample standard deviation of neighbor values if N >= 2, else 0.0.
    """
    valid_values = [
        n.observed_value
        for n in used_neighbors
        if n.observed_value is not None and math.isfinite(n.observed_value)
    ]
    n = len(valid_values)
    if n < MIN_VALID_NEIGHBORS:
        return 0.0

    mean_val = sum(valid_values) / n
    variance = sum((x - mean_val) ** 2 for x in valid_values) / (n - 1)
    return math.sqrt(max(0.0, variance))


def compute_local_dispersion(
    consensus: float,
    used_neighbors: List[SpatialNeighbor],
) -> float:
    """
    Weighted local dispersion around IDW consensus.
    """
    if not used_neighbors or not math.isfinite(consensus):
        return 0.0

    weighted_var = sum(
        neighbor.weight * ((neighbor.observed_value - consensus) ** 2)
        for neighbor in used_neighbors
        if neighbor.observed_value is not None and math.isfinite(neighbor.observed_value)
    )
    return math.sqrt(max(0.0, weighted_var))


def compute_spatial_residual(
    target_value: Optional[float],
    consensus: Optional[float],
    used_neighbors: List[SpatialNeighbor],
    min_neighbors: int = MIN_VALID_NEIGHBORS,
    variance_epsilon: float = getattr(DEFAULT_SPATIAL_CONFIG, "variance_epsilon", 1e-6),
) -> Tuple[Optional[float], Optional[float], float]:
    """
    Compute raw spatial residual and standardized residual.

    Returns:
        Tuple of (raw_residual, standardized_residual, reference_scale)
        - If target_value, consensus, or used_neighbors is invalid/empty -> (None, None, 0.0)
        - If valid neighbors < min_neighbors (e.g. N=1) -> (raw_residual, None, 0.0)
        - If valid neighbors >= min_neighbors -> (raw_residual, standardized_residual, reference_scale)
    """
    if target_value is None or consensus is None:
        return None, None, 0.0

    if not (math.isfinite(target_value) and math.isfinite(consensus)):
        return None, None, 0.0

    # Count valid contributing neighbors
    valid_neighbor_count = sum(
        1
        for n in used_neighbors
        if n.observed_value is not None and math.isfinite(n.observed_value)
    )

    # 0 valid neighbors -> No spatial consensus or residual can exist
    if valid_neighbor_count == 0:
        return None, None, 0.0

    # Raw residual: r = x_target - x_consensus (sign preserved)
    raw_residual = target_value - consensus

    # Fewer than minimum valid neighbors (e.g., N=1 < 2) -> Cannot compute reference scale
    if valid_neighbor_count < min_neighbors:
        return raw_residual, None, 0.0

    # Reference scale: neighbor-value sample standard deviation
    # [ASSUMPTION -- PROJECT OWNER CONFIRMATION REQUIRED]
    reference_scale = compute_reference_scale(used_neighbors)

    if math.isclose(raw_residual, 0.0, abs_tol=1e-12):
        standardized_residual = 0.0
    else:
        denom = max(reference_scale, variance_epsilon)
        standardized_residual = raw_residual / denom

    return raw_residual, standardized_residual, reference_scale


def classify_spatial_status(
    standardized_residual: Optional[float],
    used_neighbors: List[SpatialNeighbor],
    spatial_z_threshold: float = DEFAULT_SPATIAL_Z_THRESHOLD,
    min_neighbors: int = MIN_VALID_NEIGHBORS,
) -> SpatialStatus:
    """
    Classify spatial evidence status based on standardized residual magnitude
    and evidence sufficiency.

    [CALIBRATION PARAMETER -- Bible Section 15]
    """
    if standardized_residual is None or not math.isfinite(standardized_residual):
        return SpatialStatus.INSUFFICIENT_NEIGHBORS

    valid_neighbor_count = sum(
        1
        for n in used_neighbors
        if n.observed_value is not None and math.isfinite(n.observed_value)
    )

    if valid_neighbor_count < min_neighbors:
        return SpatialStatus.INSUFFICIENT_NEIGHBORS

    # Disagreement vs Agreement boundary
    if abs(standardized_residual) > spatial_z_threshold:
        return SpatialStatus.SUSPECT

    return SpatialStatus.CONSISTENT
