"""
Smoke tests for Member 2 Spatial Workstream Foundation (Phase 1).
"""

import unittest
from spatial.config import (
    SpatialConfig,
    DEFAULT_SPATIAL_CONFIG,
    NEIGHBORHOOD_RULE,
    K_NEIGHBORS,
    IDW_POWER_P,
    SELF_OUTLIER_Z_THRESHOLD,
)
from spatial.interfaces import (
    SpatialStatus,
    Station,
    ObservationSnapshot,
    StationRegistry,
    SpatialNeighbor,
    SpatialEvidenceResult,
    AbstractSpatialAnalyzer,
)


class TestSpatialFoundation(unittest.TestCase):

    def test_calibration_parameters_and_config(self):
        """Verify explicit calibration constants and immutability."""
        self.assertEqual(NEIGHBORHOOD_RULE, "RADIUS_OR_KNN")
        self.assertEqual(K_NEIGHBORS, 5)
        self.assertEqual(IDW_POWER_P, 2.0)
        self.assertEqual(SELF_OUTLIER_Z_THRESHOLD, 3.0)

        cfg = DEFAULT_SPATIAL_CONFIG
        self.assertEqual(cfg.k_neighbors, 5)
        self.assertEqual(cfg.idw_power_p, 2.0)
        self.assertEqual(cfg.self_outlier_z_threshold, 3.0)

        with self.assertRaises(Exception):
            cfg.k_neighbors = 10

    def test_bible_canonical_interfaces(self):
        """Verify Station, ObservationSnapshot, and supporting models."""
        station = Station(station_id="STN_001", latitude=12.9716, longitude=77.5946, elevation_m=920.0)
        self.assertEqual(station.station_id, "STN_001")
        self.assertEqual(station.latitude, 12.9716)
        self.assertEqual(station.longitude, 77.5946)
        self.assertEqual(station.elevation_m, 920.0)
        self.assertTrue(station.active)

        snapshot = ObservationSnapshot(timestamp=1700000000.0, values={"temperature": 28.5, "humidity": 65.0}, valid=True)
        self.assertEqual(snapshot.values["temperature"], 28.5)
        self.assertTrue(snapshot.valid)

        neighbor = SpatialNeighbor(station_id="STN_002", distance_km=10.5, observed_value=28.1, weight=0.5)
        self.assertEqual(neighbor.station_id, "STN_002")

        result = SpatialEvidenceResult(
            target_station_id="STN_001",
            variable_name="temperature",
            observed_value=28.5,
            consensus_value=28.1,
            residual=0.4,
            standardized_residual=0.6,
            status=SpatialStatus.CONSISTENT,
            neighbors_used=[neighbor],
        )
        self.assertEqual(result.status, SpatialStatus.CONSISTENT)

    def test_abstract_interfaces_enforcement(self):
        """Verify Abstract interfaces cannot be instantiated directly."""
        with self.assertRaises(TypeError):
            StationRegistry()

        with self.assertRaises(TypeError):
            AbstractSpatialAnalyzer()


if __name__ == "__main__":
    unittest.main()
