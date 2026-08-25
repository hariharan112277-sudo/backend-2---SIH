"""
OTE - Observation Trust Engine
Member 2: Concrete In-Memory Station Registry & Coordinate Validation
"""

import math
from typing import Dict, List, Optional
from spatial.interfaces import Station, StationRegistry


def is_valid_coordinate(latitude: Optional[float], longitude: Optional[float]) -> bool:
    """
    Validate geographic coordinates against physical domain constraints.
    - Latitude: [-90.0, 90.0]
    - Longitude: [-180.0, 180.0]
    - Rejects None, NaN, and Infinite values.
    """
    if latitude is None or longitude is None:
        return False
    
    try:
        lat_f = float(latitude)
        lon_f = float(longitude)
    except (ValueError, TypeError):
        return False

    if not (math.isfinite(lat_f) and math.isfinite(lon_f)):
        return False

    return (-90.0 <= lat_f <= 90.0) and (-180.0 <= lon_f <= 180.0)


def is_valid_station(station: Station) -> bool:
    """Check if a station has valid coordinates and is active."""
    return station.active and is_valid_coordinate(station.latitude, station.longitude)


class InMemoryStationRegistry(StationRegistry):
    """
    In-memory concrete implementation of StationRegistry.
    Stores station topology and provides deterministic lookup and candidacy filtering.
    """

    def __init__(self, stations: Optional[List[Station]] = None) -> None:
        self._stations: Dict[str, Station] = {}
        if stations:
            for station in stations:
                self.register_station(station)

    def register_station(self, station: Station) -> None:
        """Register or update a station."""
        self._stations[station.station_id] = station

    def get_station(self, station_id: str) -> Optional[Station]:
        """
        Diagnostic retrieval: retrieve station by unique ID regardless of validity.
        """
        return self._stations.get(station_id)

    def get_all_stations(self) -> List[Station]:
        """
        Retrieve all registered stations in deterministic order.
        """
        return [self._stations[sid] for sid in sorted(self._stations.keys())]

    def get_valid_stations(self) -> List[Station]:
        """
        Retrieve only active stations with valid coordinates for spatial candidacy.
        """
        return [
            self._stations[sid]
            for sid in sorted(self._stations.keys())
            if is_valid_station(self._stations[sid])
        ]
