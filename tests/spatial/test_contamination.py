"""
Unit tests for Phase 6: Bad-Neighbor Contamination Defense
Authoritative Source: OTE_Member2_Implementation_Bible.pdf (Phase 6)
"""

import math
import unittest
from spatial.interfaces import Station, ObservationSnapshot, SpatialStatus
from spatial.neighbors import NeighborCandidate
from spatial.contamination import (
    filter_valid_neighbors,
    execute_spatial_pipeline_for_variable,
    ExclusionReason,
    DEFAULT_SELF_OUTLIER_Z_THRESHOLD,
)


class TestContaminationDefense(unittest.TestCase):

    def setUp(self):
        self.stations = [
            Station(station_id=f"STN_{i}", latitude=12.0 + (0.01 * i), longitude=77.0 + (0.01 * i))
            for i in range(10)
        ]
        self.candidates = [
            NeighborCandidate(station=self.stations[i], distance_km=5.0 + (1.0 * i))
            for i in range(10)
        ]

    def test_no_corruption_all_valid(self):
        """Verify all valid candidate neighbors are retained without false exclusions."""
        snaps = {
            f"STN_{i}": ObservationSnapshot(100.0, {"temp": 25.0 + (0.1 * i)}, valid=True)
            for i in range(10)
        }
        valid, excluded = filter_valid_neighbors(self.candidates, snaps, "temp")
        self.assertEqual(len(valid), 10)
        self.assertEqual(len(excluded), 0)

    def test_one_corrupted_neighbor_self_outlier(self):
        """Verify single corrupted neighbor is excluded and IDW consensus is protected."""
        snaps = {
            f"STN_{i}": ObservationSnapshot(100.0, {"temp": 20.0}, valid=True)
            for i in range(1, 10)
        }
        snaps["STN_0"] = ObservationSnapshot(100.0, {"temp": 100.0}, valid=True)

        valid, excluded = filter_valid_neighbors(self.candidates, snaps, "temp", self_outlier_z_threshold=3.0)
        self.assertEqual(len(valid), 9)
        self.assertEqual(len(excluded), 1)
        self.assertEqual(excluded[0][0].station.station_id, "STN_0")
        self.assertEqual(excluded[0][1], ExclusionReason.SELF_OUTLIER_Z_SCORE)

    def test_multiple_corrupted_neighbors_self_outliers(self):
        """Verify multiple corrupted neighbors are iteratively peeled without corrupting inliers."""
        snaps = {
            f"STN_{i}": ObservationSnapshot(100.0, {"temp": 20.0}, valid=True)
            for i in range(2, 10)
        }
        snaps["STN_0"] = ObservationSnapshot(100.0, {"temp": 100.0}, valid=True)
        snaps["STN_1"] = ObservationSnapshot(100.0, {"temp": 120.0}, valid=True)

        valid, excluded = filter_valid_neighbors(self.candidates, snaps, "temp", self_outlier_z_threshold=3.0)
        self.assertEqual(len(valid), 8)
        self.assertEqual(len(excluded), 2)
        excluded_ids = {ex[0].station.station_id for ex in excluded}
        self.assertEqual(excluded_ids, {"STN_0", "STN_1"})
        self.assertTrue(all(ex[1] == ExclusionReason.SELF_OUTLIER_Z_SCORE for ex in excluded))

    def test_all_neighbors_corrupted_insufficient_evidence(self):
        """Verify when all neighbors are corrupted, downstream status is INSUFFICIENT_NEIGHBORS."""
        snaps = {
            f"STN_{i}": ObservationSnapshot(100.0, {"temp": 20.0}, valid=False)
            for i in range(5)
        }
        res = execute_spatial_pipeline_for_variable(
            target_station_id="TARGET",
            target_value=20.0,
            candidate_neighbors=self.candidates[:5],
            snapshots=snaps,
            variable="temp",
        )
        self.assertEqual(res.candidate_count, 5)
        self.assertEqual(res.valid_count, 0)
        self.assertEqual(len(res.excluded_neighbors), 5)
        self.assertIsNone(res.consensus)
        self.assertEqual(res.status, SpatialStatus.INSUFFICIENT_NEIGHBORS)

    def test_missing_observation_reason(self):
        """Verify missing station snapshot or missing variable key records MISSING_OBSERVATION."""
        snaps = {
            "STN_0": ObservationSnapshot(100.0, {"temp": 20.0}, valid=True),
            # STN_1 missing from snaps
            "STN_2": ObservationSnapshot(100.0, {"humidity": 80.0}, valid=True), # missing "temp"
            "STN_3": ObservationSnapshot(100.0, {"temp": None}, valid=True),     # None value
        }
        valid, excluded = filter_valid_neighbors(self.candidates[:4], snaps, "temp")
        self.assertEqual(len(valid), 1)
        self.assertEqual(valid[0].station.station_id, "STN_0")
        self.assertEqual(len(excluded), 3)
        self.assertTrue(all(ex[1] == ExclusionReason.MISSING_OBSERVATION for ex in excluded))

    def test_invalid_observation_reason(self):
        """Verify invalid snapshot flag, NaN, or Inf records INVALID_OBSERVATION."""
        snaps = {
            "STN_0": ObservationSnapshot(100.0, {"temp": 20.0}, valid=True),
            "STN_1": ObservationSnapshot(100.0, {"temp": 20.0}, valid=False),
            "STN_2": ObservationSnapshot(100.0, {"temp": float("nan")}, valid=True),
            "STN_3": ObservationSnapshot(100.0, {"temp": float("inf")}, valid=True),
        }
        valid, excluded = filter_valid_neighbors(self.candidates[:4], snaps, "temp")
        self.assertEqual(len(valid), 1)
        self.assertEqual(valid[0].station.station_id, "STN_0")
        self.assertEqual(len(excluded), 3)
        self.assertTrue(all(ex[1] == ExclusionReason.INVALID_OBSERVATION for ex in excluded))

    def test_invalid_coordinates_reason(self):
        """Verify out-of-bounds or non-finite coordinates record INVALID_COORDINATES."""
        bad_stn = Station(station_id="STN_BAD_COORD", latitude=999.0, longitude=77.0)
        bad_candidate = NeighborCandidate(station=bad_stn, distance_km=10.0)
        snaps = {"STN_BAD_COORD": ObservationSnapshot(100.0, {"temp": 20.0}, valid=True)}

        valid, excluded = filter_valid_neighbors([bad_candidate], snaps, "temp")
        self.assertEqual(len(valid), 0)
        self.assertEqual(len(excluded), 1)
        self.assertEqual(excluded[0][1], ExclusionReason.INVALID_COORDINATES)

    def test_insufficient_comparison_pool_no_outlier_rejection(self):
        """Verify pool with < 3 candidates does not falsely exclude candidates due to lack of evidence."""
        snaps = {
            "STN_0": ObservationSnapshot(100.0, {"temp": 20.0}, valid=True),
            "STN_1": ObservationSnapshot(100.0, {"temp": 100.0}, valid=True),
        }
        valid, excluded = filter_valid_neighbors(self.candidates[:2], snaps, "temp")
        self.assertEqual(len(valid), 2)
        self.assertEqual(len(excluded), 0)

    def test_zero_dispersion_pool_with_epsilon_protection(self):
        """Verify identical neighbor pool with one deviating candidate uses epsilon guard correctly."""
        snaps = {
            f"STN_{i}": ObservationSnapshot(100.0, {"temp": 20.0}, valid=True)
            for i in range(3)
        }
        snaps["STN_3"] = ObservationSnapshot(100.0, {"temp": 22.0}, valid=True)
        valid, excluded = filter_valid_neighbors(self.candidates[:4], snaps, "temp", self_outlier_z_threshold=3.0)
        self.assertEqual(len(valid), 3)
        self.assertEqual(len(excluded), 1)
        self.assertEqual(excluded[0][0].station.station_id, "STN_3")
        self.assertEqual(excluded[0][1], ExclusionReason.SELF_OUTLIER_Z_SCORE)

    def test_deterministic_repeated_filtering(self):
        """Verify identical inputs produce bitwise identical pipeline results."""
        snaps = {
            f"STN_{i}": ObservationSnapshot(100.0, {"temp": 20.0 + (0.5 * i)}, valid=True)
            for i in range(6)
        }
        res1 = execute_spatial_pipeline_for_variable("TARGET", 21.0, self.candidates[:6], snaps, "temp")
        res2 = execute_spatial_pipeline_for_variable("TARGET", 21.0, self.candidates[:6], snaps, "temp")
        self.assertEqual(res1, res2)

    def test_pipeline_end_to_end_integration(self):
        """Verify full pre-step pipeline flow protects consensus and residual."""
        snaps = {
            f"STN_{i}": ObservationSnapshot(100.0, {"temp": 20.0}, valid=True)
            for i in range(1, 10)
        }
        snaps["STN_0"] = ObservationSnapshot(100.0, {"temp": 100.0}, valid=True) # outlier

        res = execute_spatial_pipeline_for_variable(
            target_station_id="TARGET",
            target_value=20.0,
            candidate_neighbors=self.candidates,
            snapshots=snaps,
            variable="temp",
        )
        self.assertEqual(res.candidate_count, 10)
        self.assertEqual(res.valid_count, 9)
        self.assertEqual(len(res.excluded_neighbors), 1)
        self.assertEqual(res.consensus, 20.0)
        self.assertEqual(res.raw_residual, 0.0)
        self.assertEqual(res.standardized_residual, 0.0)
        self.assertEqual(res.status, SpatialStatus.CONSISTENT)


if __name__ == "__main__":
    unittest.main()
