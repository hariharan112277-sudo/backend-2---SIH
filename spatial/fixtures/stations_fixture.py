"""
OTE - Observation Trust Engine
Member 2: Deterministic Local Station Fixtures
"""

import random
from typing import List
from spatial.interfaces import Station

DEFAULT_FIXTURE_SEED = 42


def generate_local_stations_fixture(seed: int = DEFAULT_FIXTURE_SEED, count: int = 24) -> List[Station]:
    """
    Generate a deterministic set of ~24 stations with irregular/jittered 2D topology.
    Includes at least one station with missing/invalid coordinates for testing.
    """
    rng = random.Random(seed)
    stations: List[Station] = []
    
    # Regional anchor (e.g. Bangalore baseline coordinate box)
    base_lat = 12.9716
    base_lon = 77.5946
    
    for i in range(1, count):
        # Deterministic jitter within ~0.5 degree (~50km) bounding box
        lat_jitter = rng.uniform(-0.25, 0.25)
        lon_jitter = rng.uniform(-0.25, 0.25)
        elevation = round(rng.uniform(700.0, 1100.0), 1)
        
        station_id = f"STN_{i:03d}"
        stations.append(
            Station(
                station_id=station_id,
                latitude=round(base_lat + lat_jitter, 5),
                longitude=round(base_lon + lon_jitter, 5),
                elevation_m=elevation,
                active=True,
                metadata={"synthetic": True, "fixture_index": i},
            )
        )
    
    # Intentionally add one deterministic invalid/missing coordinate edge-case station
    invalid_station = Station(
        station_id=f"STN_{count:03d}",
        latitude=float("nan"),
        longitude=None,  # type: ignore
        elevation_m=0.0,
        active=True,
        metadata={"synthetic": True, "fixture_index": count, "edge_case": "invalid_coordinates"},
    )
    stations.append(invalid_station)
    
    return stations
