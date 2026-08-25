"""
OTE - Observation Trust Engine
Member 2: Spatial & Cross-Station Analytics
Module: Canonical Scenario Fixtures (Phase 8)
Authoritative Source: OTE_Member2_Implementation_Bible.pdf (Section 11 & Phase 8)
"""

from typing import Dict, List, Optional, Tuple
from spatial.interfaces import Station, ObservationSnapshot
from spatial.station_registry import InMemoryStationRegistry

ScenarioFixtureResult = Tuple[InMemoryStationRegistry, Dict[str, ObservationSnapshot], str]


def create_scenario_station(station_id: str, lat: float, lon: float) -> Station:
    """Create a validated station instance."""
    return Station(station_id=station_id, latitude=lat, longitude=lon)


def create_snapshot(
    timestamp: float = 1000.0,
    values: Optional[Dict[str, Optional[float]]] = None,
    valid: bool = True,
) -> ObservationSnapshot:
    """Create a validated observation snapshot instance."""
    return ObservationSnapshot(
        timestamp=timestamp,
        values=values if values is not None else {},
        valid=valid,
    )


def create_base_scenario(
    target_id: str,
    target_coord: Tuple[float, float],
    target_values: Dict[str, Optional[float]],
    target_valid: bool,
    neighbor_coords: List[Tuple[str, float, float]],
    neighbor_values: List[Dict[str, Optional[float]]],
    neighbor_valid: Optional[List[bool]] = None,
    timestamp: float = 1000.0,
) -> ScenarioFixtureResult:
    """Construct a deterministic isolated scenario fixture."""
    registry = InMemoryStationRegistry()

    # Register target
    target_station = create_scenario_station(target_id, target_coord[0], target_coord[1])
    registry.register_station(target_station)

    # Register neighbors
    for n_id, n_lat, n_lon in neighbor_coords:
        registry.register_station(create_scenario_station(n_id, n_lat, n_lon))

    # Construct snapshots
    snapshots: Dict[str, ObservationSnapshot] = {
        target_id: create_snapshot(timestamp, target_values, target_valid),
    }

    n_count = len(neighbor_coords)
    valid_flags = neighbor_valid if neighbor_valid is not None else [True] * n_count

    for i in range(n_count):
        n_id = neighbor_coords[i][0]
        n_val = neighbor_values[i] if i < len(neighbor_values) else {}
        n_vflag = valid_flags[i] if i < len(valid_flags) else True
        snapshots[n_id] = create_snapshot(timestamp, n_val, n_vflag)

    return registry, snapshots, target_id


# ---------------------------------------------------------------------------
# 12 Canonical Scenario Fixtures per Bible Section 11
# ---------------------------------------------------------------------------

def fixture_all_neighbors_agree() -> ScenarioFixtureResult:
    """1. All neighbors agree with target within normal physical dispersion."""
    target_coord = (12.0, 77.0)
    target_val = {"temperature": 25.0, "humidity": 60.0, "pressure": 1012.0}
    neighbors = [(f"N_{i}", 12.0 + (0.01 * i), 77.0 + (0.01 * i)) for i in range(1, 6)]
    n_vals = [
        {
            "temperature": 25.0 + (0.1 * (i - 3)),
            "humidity": 60.0 + (0.2 * (i - 3)),
            "pressure": 1012.0 + (0.1 * (i - 3)),
        }
        for i in range(1, 6)
    ]
    return create_base_scenario("TARGET", target_coord, target_val, True, neighbors, n_vals)


def fixture_target_isolated_anomaly() -> ScenarioFixtureResult:
    """2. Target exhibits an isolated sensor spike while neighbors agree."""
    target_coord = (12.0, 77.0)
    target_val = {"temperature": 45.0, "humidity": 60.0, "pressure": 1012.0} # Temp anomaly
    neighbors = [(f"N_{i}", 12.0 + (0.01 * i), 77.0 + (0.01 * i)) for i in range(1, 6)]
    n_vals = [
        {
            "temperature": 25.0 + (0.1 * (i - 3)),
            "humidity": 60.0 + (0.2 * (i - 3)),
            "pressure": 1012.0 + (0.1 * (i - 3)),
        }
        for i in range(1, 6)
    ]
    return create_base_scenario("TARGET", target_coord, target_val, True, neighbors, n_vals)


def fixture_one_bad_neighbor() -> ScenarioFixtureResult:
    """3. Neighborhood contains one corrupted neighbor (100.0 C). Target is normal."""
    target_coord = (12.0, 77.0)
    target_val = {"temperature": 25.0, "humidity": 60.0, "pressure": 1012.0}
    neighbors = [(f"N_{i}", 12.0 + (0.01 * i), 77.0 + (0.01 * i)) for i in range(1, 8)]
    n_vals = [
        {
            "temperature": 25.0 + (0.1 * (i - 4)),
            "humidity": 60.0 + (0.2 * (i - 4)),
            "pressure": 1012.0 + (0.1 * (i - 4)),
        }
        for i in range(1, 8)
    ]
    n_vals[0] = {"temperature": 100.0, "humidity": 60.0, "pressure": 1012.0} # Bad neighbor
    return create_base_scenario("TARGET", target_coord, target_val, True, neighbors, n_vals)


def fixture_multiple_bad_neighbors() -> ScenarioFixtureResult:
    """4. Neighborhood contains two corrupted neighbors (100.0 C and 120.0 C)."""
    target_coord = (12.0, 77.0)
    target_val = {"temperature": 25.0, "humidity": 60.0, "pressure": 1012.0}
    neighbors = [(f"N_{i}", 12.0 + (0.01 * i), 77.0 + (0.01 * i)) for i in range(1, 9)]
    n_vals = [
        {
            "temperature": 25.0 + (0.1 * (i - 5)),
            "humidity": 60.0 + (0.2 * (i - 5)),
            "pressure": 1012.0 + (0.1 * (i - 5)),
        }
        for i in range(1, 9)
    ]
    n_vals[0] = {"temperature": 100.0, "humidity": 60.0, "pressure": 1012.0}
    n_vals[1] = {"temperature": 120.0, "humidity": 60.0, "pressure": 1012.0}
    return create_base_scenario("TARGET", target_coord, target_val, True, neighbors, n_vals)


def fixture_missing_neighbor() -> ScenarioFixtureResult:
    """5. Neighbors have missing observation snapshots or invalid flags."""
    target_coord = (12.0, 77.0)
    target_val = {"temperature": 25.0, "humidity": 60.0, "pressure": 1012.0}
    neighbors = [(f"N_{i}", 12.0 + (0.01 * i), 77.0 + (0.01 * i)) for i in range(1, 7)]
    n_vals = [
        {
            "temperature": 25.0 + (0.1 * (i - 3)),
            "humidity": 60.0 + (0.2 * (i - 3)),
            "pressure": 1012.0 + (0.1 * (i - 3)),
        }
        for i in range(1, 7)
    ]
    n_valid = [True, True, True, False, False, True] # 2 invalid neighbors
    return create_base_scenario("TARGET", target_coord, target_val, True, neighbors, n_vals, neighbor_valid=n_valid)


def fixture_insufficient_neighbors() -> ScenarioFixtureResult:
    """6. Target station is isolated with only 1 neighbor (< MIN_VALID_NEIGHBORS = 2)."""
    target_coord = (12.0, 77.0)
    target_val = {"temperature": 25.0, "humidity": 60.0, "pressure": 1012.0}
    neighbors = [("N_1", 12.01, 77.01)] # Only 1 neighbor
    n_vals = [{"temperature": 25.0, "humidity": 60.0, "pressure": 1012.0}]
    return create_base_scenario("TARGET", target_coord, target_val, True, neighbors, n_vals)


def fixture_boundary_station() -> ScenarioFixtureResult:
    """7. Station located near coordinate boundaries (lat 89.0, lon 179.0)."""
    target_coord = (89.0, 179.0)
    target_val = {"temperature": -30.0, "humidity": 40.0, "pressure": 1020.0}
    neighbors = [(f"N_{i}", 89.0 + (0.01 * i), 179.0 + (0.01 * i)) for i in range(1, 5)]
    n_vals = [
        {
            "temperature": -30.0 + (0.1 * (i - 2)),
            "humidity": 40.0 + (0.2 * (i - 2)),
            "pressure": 1020.0 + (0.1 * (i - 2)),
        }
        for i in range(1, 5)
    ]
    return create_base_scenario("TARGET", target_coord, target_val, True, neighbors, n_vals)


def fixture_equal_distance_neighbors() -> ScenarioFixtureResult:
    """8. Target surrounded symmetrically by equidistant neighbors."""
    target_coord = (12.0, 77.0)
    target_val = {"temperature": 25.0, "humidity": 60.0, "pressure": 1012.0}
    # 4 neighbors positioned exactly ~0.02 deg North, South, East, West
    neighbors = [
        ("N_NORTH", 12.02, 77.00),
        ("N_SOUTH", 11.98, 77.00),
        ("N_EAST", 12.00, 77.02),
        ("N_WEST", 12.00, 76.98),
    ]
    n_vals = [
        {"temperature": 25.1, "humidity": 60.2, "pressure": 1012.1},
        {"temperature": 24.9, "humidity": 59.8, "pressure": 1011.9},
        {"temperature": 25.0, "humidity": 60.0, "pressure": 1012.0},
        {"temperature": 25.0, "humidity": 60.0, "pressure": 1012.0},
    ]
    return create_base_scenario("TARGET", target_coord, target_val, True, neighbors, n_vals)


def fixture_extreme_distance_neighbor() -> ScenarioFixtureResult:
    """9. Includes a distant neighbor station (> 100 km) beyond max_radius_km."""
    target_coord = (12.0, 77.0)
    target_val = {"temperature": 25.0, "humidity": 60.0, "pressure": 1012.0}
    neighbors = [
        ("N_CLOSE_1", 12.01, 77.01),
        ("N_CLOSE_2", 12.02, 77.02),
        ("N_CLOSE_3", 12.03, 77.03),
        ("N_FAR", 15.00, 80.00), # ~400 km distant
    ]
    n_vals = [
        {"temperature": 25.1, "humidity": 60.2, "pressure": 1012.1},
        {"temperature": 24.9, "humidity": 59.8, "pressure": 1011.9},
        {"temperature": 25.0, "humidity": 60.0, "pressure": 1012.0},
        {"temperature": 35.0, "humidity": 90.0, "pressure": 1000.0}, # Distant value
    ]
    return create_base_scenario("TARGET", target_coord, target_val, True, neighbors, n_vals)


def fixture_correlated_multi_station_fault() -> ScenarioFixtureResult:
    """10. Regional cluster of stations exhibiting matching erroneous readings."""
    target_coord = (12.0, 77.0)
    target_val = {"temperature": 60.0, "humidity": 99.0, "pressure": 900.0} # Regional fault
    neighbors = [(f"N_{i}", 12.0 + (0.01 * i), 77.0 + (0.01 * i)) for i in range(1, 6)]
    n_vals = [
        {
            "temperature": 60.0 + (0.1 * (i - 3)),
            "humidity": 99.0 + (0.1 * (i - 3)),
            "pressure": 900.0 + (0.1 * (i - 3)),
        }
        for i in range(1, 6)
    ]
    return create_base_scenario("TARGET", target_coord, target_val, True, neighbors, n_vals)


def fixture_propagating_spatial_weather_event() -> ScenarioFixtureResult:
    """11. Coherent meteorological event across regional network."""
    target_coord = (12.0, 77.0)
    target_val = {"temperature": 18.0, "humidity": 95.0, "pressure": 995.0} # Storm front
    neighbors = [(f"N_{i}", 12.0 + (0.01 * i), 77.0 + (0.01 * i)) for i in range(1, 6)]
    n_vals = [
        {
            "temperature": 18.0 + (0.2 * (i - 3)),
            "humidity": 95.0 + (0.2 * (i - 3)),
            "pressure": 995.0 + (0.2 * (i - 3)),
        }
        for i in range(1, 6)
    ]
    return create_base_scenario("TARGET", target_coord, target_val, True, neighbors, n_vals)


def fixture_mixed_evidence() -> ScenarioFixtureResult:
    """12. Mixed spatial evidence across variables (temp disagrees, hum/pres agree)."""
    target_coord = (12.0, 77.0)
    target_val = {"temperature": 40.0, "humidity": 60.0, "pressure": 1012.0} # Temp spike
    neighbors = [(f"N_{i}", 12.0 + (0.01 * i), 77.0 + (0.01 * i)) for i in range(1, 6)]
    n_vals = [
        {
            "temperature": 25.0 + (0.1 * (i - 3)),
            "humidity": 60.0 + (0.2 * (i - 3)),
            "pressure": 1012.0 + (0.1 * (i - 3)),
        }
        for i in range(1, 6)
    ]
    return create_base_scenario("TARGET", target_coord, target_val, True, neighbors, n_vals)
