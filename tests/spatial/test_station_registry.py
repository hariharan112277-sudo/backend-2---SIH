"""
Unit tests for Phase 2: Station Registry & Coordinate Model
"""

import math
import unittest
from spatial.interfaces import Station
from spatial.station_registry import (
    InMemoryStationRegistry,
    is_valid_coordinate,
    is_valid_station,
)
from spatial.fixtures.stations_fixture import generate_local_stations_fixture


class TestStationRegistry(unittest.TestCase):

    def setUp(self):
        self.station1 = Station(station_id="STN_001", latitude=12.9716, longitude=77.5946, elevation_m=920.0)
        self.station2 = Station(station_id="STN_002", latitude=13.0350, longitude=77.5600, elevation_m=850.0)
        self.registry = InMemoryStationRegistry([self.station1, self.station2])

    def test_valid_station_retrieval(self):
        """Verify get_station() returns exact registered station."""
        stn = self.registry.get_station("STN_001")
        self.assertIsNotNone(stn)
        self.assertEqual(stn.station_id, "STN_001")
        self.assertEqual(stn.latitude, 12.9716)

    def test_unknown_station_retrieval(self):
        """Verify get_station() returns None for unknown IDs."""
        self.assertIsNone(self.registry.get_station("STN_NONEXISTENT"))

    def test_get_all_stations_deterministic(self):
        """Verify get_all_stations() returns stations deterministically sorted."""
        stations = self.registry.get_all_stations()
        self.assertEqual(len(stations), 2)
        self.assertEqual([s.station_id for s in stations], ["STN_001", "STN_002"])

    def test_coordinate_validation_boundaries(self):
        """Verify valid edge values for latitude and longitude."""
        self.assertTrue(is_valid_coordinate(90.0, 180.0))
        self.assertTrue(is_valid_coordinate(-90.0, -180.0))
        self.assertTrue(is_valid_coordinate(0.0, 0.0))

    def test_coordinate_validation_invalid(self):
        """Verify out-of-bound coordinates fail validation."""
        self.assertFalse(is_valid_coordinate(90.0001, 0.0))
        self.assertFalse(is_valid_coordinate(-90.0001, 0.0))
        self.assertFalse(is_valid_coordinate(0.0, 180.0001))
        self.assertFalse(is_valid_coordinate(0.0, -180.0001))

    def test_missing_and_non_finite_coordinates(self):
        """Verify None, NaN, and Infinite coordinates fail validation."""
        self.assertFalse(is_valid_coordinate(None, 77.0))
        self.assertFalse(is_valid_coordinate(12.0, None))
        self.assertFalse(is_valid_coordinate(float("nan"), 77.0))
        self.assertFalse(is_valid_coordinate(12.0, float("inf")))
        self.assertFalse(is_valid_coordinate(float("-inf"), 77.0))

    def test_diagnostic_retrieval_of_invalid_stations(self):
        """Verify invalid stations remain retrievable via get_station()."""
        invalid_stn = Station(station_id="STN_BAD", latitude=100.0, longitude=77.0)
        self.registry.register_station(invalid_stn)
        self.assertIsNotNone(self.registry.get_station("STN_BAD"))
        self.assertEqual(len(self.registry.get_all_stations()), 3)

    def test_valid_station_candidacy_filtering(self):
        """Verify get_valid_stations() filters out stations with invalid coordinates."""
        invalid_stn = Station(station_id="STN_BAD", latitude=100.0, longitude=77.0)
        self.registry.register_station(invalid_stn)
        valid_stations = self.registry.get_valid_stations()
        self.assertEqual(len(valid_stations), 2)
        self.assertNotIn("STN_BAD", [s.station_id for s in valid_stations])

    def test_deterministic_fixture_reproducibility(self):
        """Verify seeded fixture generation produces identical output."""
        f1 = generate_local_stations_fixture(seed=123, count=24)
        f2 = generate_local_stations_fixture(seed=123, count=24)
        self.assertEqual(len(f1), len(f2))
        for s1, s2 in zip(f1, f2):
            self.assertEqual(s1.station_id, s2.station_id)
            if math.isnan(s1.latitude):
                self.assertTrue(math.isnan(s2.latitude))
            else:
                self.assertEqual(s1.latitude, s2.latitude)
            self.assertEqual(s1.longitude, s2.longitude)

    def test_fixture_station_count_and_edge_case(self):
        """Verify ~24 station fleet contains exactly one invalid edge case."""
        fleet = generate_local_stations_fixture(seed=42, count=24)
        self.assertEqual(len(fleet), 24)
        reg = InMemoryStationRegistry(fleet)
        self.assertEqual(len(reg.get_all_stations()), 24)
        self.assertEqual(len(reg.get_valid_stations()), 23)
        self.assertIsNotNone(reg.get_station("STN_024"))


if __name__ == "__main__":
    unittest.main()
