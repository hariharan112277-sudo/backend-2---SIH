"""
OTE - Observation Trust Engine
Member 2: Spatial Residual & Local Standardization Computation
"""

import math
from typing import List, Optional, Tuple
from spatial.interfaces import SpatialNeighbor
from spatial.config import DEFAULT_SPATIAL_CONFIG


def compute_local_dispersion(
    consensus: float,
    used_neighbors: List[SpatialNeighbor],
) -> float:
    """
    Compute the weighted local standard deviation (dispersion) around consensus:
    sigma_local = sqrt( sum( w_i * (x_i - consensus)^2 ) )
    """
    if not used_neighbors or not math.isfinite(consensus):
        return 0.0

    weighted_var = sum(
        neighbor.weight * ((neighbor.observed_value - consensus) ** 2)
        for neighbor in used_neighbors
    )
    return math.sqrt(max(0.0, weighted_var))


def compute_spatial_residual(
    target_value: Optional[float],
    consensus: Optional[float],
    used_neighbors: List[SpatialNeighbor],
    variance_epsilon: float = DEFAULT_SPATIAL_CONFIG.variance_epsilon,
) -> Tuple[Optional[float], Optional[float], float]:
    """
    Compute raw spatial residual and standardized residual (Z-score).

    Returns:
        Tuple of (raw_residual, standardized_residual, local_scale_sigma)
        If target_value or consensus is None/non-finite, returns (None, None, 0.0).
    """
    if target_value is None or consensus is None:
        return None, None, 0.0

    if not (math.isfinite(target_value) and math.isfinite(consensus)):
        return None, None, 0.0

    # Raw residual: r = x_target - x_consensus
    residual = target_value - consensus

    # Local scale
    sigma_local = compute_local_dispersion(consensus, used_neighbors)

    # Standardized residual
    if math.isclose(residual, 0.0, abs_tol=1e-12):
        standardized_residual = 0.0
    else:
        denom = max(sigma_local, variance_epsilon)
        standardized_residual = residual / denom

    return residual, standardized_residual, sigma_local
