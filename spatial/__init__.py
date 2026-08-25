"""
OTE - Observation Trust Engine
Member 2: Spatial & Cross-Station Analytics
Authoritative Public Interface Specification (Phase 9 Frozen Export Surface)
"""

from spatial.interfaces import (
    Station,
    ObservationSnapshot,
    SpatialNeighbor,
    SpatialStatus,
)
from spatial.station_registry import (
    StationRegistry,
    InMemoryStationRegistry,
)
from spatial.config import (
    SpatialConfig,
    DEFAULT_SPATIAL_CONFIG,
)
from spatial.contamination import (
    ExclusionReason,
)
from spatial.analyzer import (
    SpatialAnalyzer,
    SUPPORTED_VARIABLES,
)
from spatial.explanation import (
    build_explanation,
)

__all__ = [
    "Station",
    "ObservationSnapshot",
    "SpatialNeighbor",
    "SpatialStatus",
    "StationRegistry",
    "InMemoryStationRegistry",
    "SpatialConfig",
    "DEFAULT_SPATIAL_CONFIG",
    "ExclusionReason",
    "SpatialAnalyzer",
    "SUPPORTED_VARIABLES",
    "build_explanation",
]
