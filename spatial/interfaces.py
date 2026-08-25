"""
OTE - Observation Trust Engine
Member 2: Spatial Interfaces and Data Contracts
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any


class SpatialStatus(str, Enum):
    """Spatial consistency classification states."""
    CONSISTENT = "CONSISTENT"
    SUSPECT = "SUSPECT"
    ANOMALOUS = "ANOMALOUS"
    ISOLATED = "ISOLATED"
    INSUFFICIENT_NEIGHBORS = "INSUFFICIENT_NEIGHBORS"


@dataclass(frozen=True)
class Station:
    """Canonical Station representation."""
    station_id: str
    latitude: float
    longitude: float
    elevation_m: float = 0.0
    active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ObservationSnapshot:
    """Canonical multi-variable or point observation snapshot at a given timestamp."""
    timestamp: float
    values: Dict[str, float]
    valid: bool = True
    station_id: Optional[str] = None


class StationRegistry(ABC):
    """Abstract registry interface for station topology discovery."""

    @abstractmethod
    def get_station(self, station_id: str) -> Optional[Station]:
        """Retrieve station metadata by unique station ID."""
        pass

    @abstractmethod
    def get_all_stations(self) -> List[Station]:
        """Retrieve all registered stations."""
        pass


@dataclass(frozen=True)
class SpatialNeighbor:
    """Identified neighboring station data point."""
    station_id: str
    distance_km: float
    observed_value: float
    weight: float


@dataclass(frozen=True)
class SpatialEvidenceResult:
    """Evaluation output contract for spatial cross-station analytics."""
    target_station_id: str
    variable_name: str
    observed_value: float
    consensus_value: Optional[float]
    residual: Optional[float]
    standardized_residual: Optional[float]
    status: SpatialStatus
    neighbors_used: List[SpatialNeighbor] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


class AbstractSpatialAnalyzer(ABC):
    """Abstract base class contract for spatial analyzers."""

    @abstractmethod
    def evaluate_station(
        self,
        target_station_id: str,
        observations: Dict[str, ObservationSnapshot],
        registry: StationRegistry,
    ) -> SpatialEvidenceResult:
        """Evaluate spatial consistency for a target station."""
        pass
