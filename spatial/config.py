"""
OTE - Observation Trust Engine
Member 2: Spatial Configuration & Calibration Defaults
"""

from dataclasses import dataclass

# [CALIBRATION PARAMETER] Development default: Selection rule for neighborhood construction
# NOTE: This is an unvalidated development default and not a scientifically calibrated constant.
NEIGHBORHOOD_RULE: str = "RADIUS_OR_KNN"

# [CALIBRATION PARAMETER] Development default: Target number of spatial neighbors
# NOTE: This is an unvalidated development default and not a scientifically calibrated constant.
K_NEIGHBORS: int = 5

# [CALIBRATION PARAMETER] Development default: Inverse Distance Weighting power exponent
# NOTE: This is an unvalidated development default and not a scientifically calibrated constant.
IDW_POWER_P: float = 2.0

# [CALIBRATION PARAMETER] Development default: Critical Z-score threshold for outlier detection
# NOTE: This is an unvalidated development default and not a scientifically calibrated constant.
SELF_OUTLIER_Z_THRESHOLD: float = 3.0


@dataclass(frozen=True)
class SpatialConfig:
    """
    Configuration parameters and thresholds for spatial consistency analytics.
    Zero-algorithm parameter container.
    """
    neighborhood_rule: str = NEIGHBORHOOD_RULE
    k_neighbors: int = K_NEIGHBORS
    idw_power_p: float = IDW_POWER_P
    self_outlier_z_threshold: float = SELF_OUTLIER_Z_THRESHOLD
    max_radius_km: float = 50.0
    min_neighbors: int = 3
    z_score_threshold_warning: float = 2.0
    standard_lapse_rate_c_per_km: float = 6.5
    variance_epsilon: float = 1e-6


# Default configuration instance
DEFAULT_SPATIAL_CONFIG = SpatialConfig()
