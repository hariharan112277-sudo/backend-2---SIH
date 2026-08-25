"""
Unit tests for Numerical Edge Cases, Robustness & Reproducibility (Phase 8)
Authoritative Source: OTE_Member2_Implementation_Bible.pdf (Section 17 & Phase 8)
"""

import math
import unittest
from spatial.interfaces import Station, ObservationSnapshot
from spatial.station_registry import InMemoryStationRegistry
from spatial.analyzer import SpatialAnalyzer
from spatial.explanation import build_explanation
import spatial.fixtures.scenarios as sc


class TestSpatialEdgeCases(unittest.TestCase):

    def test_zero_distance_colocated_stations(self):
        """Co-located stations at distance 0.0 km execute safely without division by zero."""
        reg = InMemoryStationRegistry()
        target = Station("TARGET", 12.0, 77.0)
        co_located_1 = Station("CO_1", 12.0, 77.0)
        co_located_2 = Station("CO_2", 12.0, 77.0)
        reg.register_station(target)
        reg.register_station(co_located_1)
        reg.register_station(co_located_2)

        snaps = {
            "TARGET": ObservationSnapshot(100.0, {"temperature": 25.0, "humidity": 60.0, "pressure": 1012.0}, valid=True),
            "CO_1": ObservationSnapshot(100.0, {"temperature": 25.0, "humidity": 60.0, "pressure": 1012.0}, valid=True),
            "CO_2": ObservationSnapshot(100.0, {"temperature": 25.0, "humidity": 60.0, "pressure": 1012.0}, valid=True),
        }
        res = SpatialAnalyzer(reg).analyze("TARGET", snaps)
        self.assertEqual(res["spatial_status"], "AGREEMENT")
        self.assertEqual(res["variables"]["temperature"]["consensus"], 25.0)

    def test_duplicate_coordinates_multiple_stations(self):
        """Multiple stations sharing duplicate coordinates produce deterministic output."""
        reg = InMemoryStationRegistry()
        target = Station("TARGET", 12.0, 77.0)
        reg.register_station(target)
        for i in range(1, 5):
            reg.register_station(Station(f"DUP_{i}", 12.0, 77.0))

        snaps = {"TARGET": ObservationSnapshot(100.0, {"temperature": 25.0}, valid=True)}
        for i in range(1, 5):
            snaps[f"DUP_{i}"] = ObservationSnapshot(100.0, {"temperature": 25.0}, valid=True)

        res = SpatialAnalyzer(reg).analyze("TARGET", snaps)
        self.assertEqual(res["variables"]["temperature"]["valid_neighbor_count"], 4)

    def test_no_candidate_neighbors_isolated(self):
        """Completely isolated station produces INSUFFICIENT_SPATIAL_EVIDENCE and NONE strength."""
        reg = InMemoryStationRegistry()
        reg.register_station(Station("TARGET", 12.0, 77.0))
        snaps = {"TARGET": ObservationSnapshot(100.0, {"temperature": 25.0}, valid=True)}

        res = SpatialAnalyzer(reg).analyze("TARGET", snaps)
        self.assertEqual(res["spatial_status"], "INSUFFICIENT_SPATIAL_EVIDENCE")
        self.assertEqual(res["evidence_strength"], "NONE")

    def test_one_valid_neighbor_below_threshold(self):
        """1 valid neighbor (< min_valid_neighbors = 2) yields INSUFFICIENT_SPATIAL_EVIDENCE."""
        reg = InMemoryStationRegistry()
        reg.register_station(Station("TARGET", 12.0, 77.0))
        reg.register_station(Station("N_1", 12.01, 77.01))
        snaps = {
            "TARGET": ObservationSnapshot(100.0, {"temperature": 25.0}, valid=True),
            "N_1": ObservationSnapshot(100.0, {"temperature": 25.0}, valid=True),
        }
        res = SpatialAnalyzer(reg).analyze("TARGET", snaps)
        self.assertEqual(res["spatial_status"], "INSUFFICIENT_SPATIAL_EVIDENCE")

    def test_many_candidate_neighbors_dense_network(self):
        """Dense network with 20 stations respects k_neighbors and executes stably."""
        reg = InMemoryStationRegistry()
        reg.register_station(Station("TARGET", 12.0, 77.0))
        for i in range(1, 21):
            reg.register_station(Station(f"STN_{i}", 12.0 + (0.005 * i), 77.0 + (0.005 * i)))

        snaps = {"TARGET": ObservationSnapshot(100.0, {"temperature": 25.0, "humidity": 60.0, "pressure": 1012.0}, valid=True)}
        for i in range(1, 21):
            snaps[f"STN_{i}"] = ObservationSnapshot(100.0, {"temperature": 25.0, "humidity": 60.0, "pressure": 1012.0}, valid=True)

        res = SpatialAnalyzer(reg).analyze("TARGET", snaps)
        self.assertEqual(res["spatial_status"], "AGREEMENT")
        self.assertEqual(res["variables"]["temperature"]["neighbor_count"], 5)

    def test_invalid_coordinates_handling(self):
        """Stations with invalid coordinates fail candidacy filtering."""
        reg = InMemoryStationRegistry()
        valid_stn = Station("VALID", 12.0, 77.0)
        invalid_stn = Station("INVALID", 999.0, 77.0)
        reg.register_station(valid_stn)
        reg.register_station(invalid_stn)

        valid_ids = [s.station_id for s in reg.get_valid_stations()]
        all_ids = [s.station_id for s in reg.get_all_stations()]

        self.assertIn("VALID", valid_ids)
        self.assertNotIn("INVALID", valid_ids)
        self.assertIn("INVALID", all_ids)

    def test_missing_values_non_zero_treatment(self):
        """Missing values are never treated as zero; handled as insufficient."""
        reg, snaps, target_id = sc.fixture_all_neighbors_agree()
        snaps[target_id] = ObservationSnapshot(100.0, {"pressure": 1012.0}, valid=True)

        res = SpatialAnalyzer(reg).analyze(target_id, snaps)
        self.assertEqual(res["variables"]["temperature"]["status"], "INSUFFICIENT_SPATIAL_EVIDENCE")
        self.assertIsNone(res["variables"]["temperature"]["target_value"])
        self.assertNotEqual(res["variables"]["temperature"]["target_value"], 0.0)

    def test_invalid_observation_flag_exclusion(self):
        """Observations with valid=False are excluded prior to consensus."""
        reg, snaps, target_id = sc.fixture_all_neighbors_agree()
        for k in snaps:
            if k != target_id:
                snaps[k] = ObservationSnapshot(100.0, {"temperature": 25.0}, valid=False)

        res = SpatialAnalyzer(reg).analyze(target_id, snaps)
        self.assertEqual(res["spatial_status"], "INSUFFICIENT_SPATIAL_EVIDENCE")

    def test_one_corrupted_neighbor_defense(self):
        """Single corrupted neighbor excluded without affecting consensus."""
        res = SpatialAnalyzer(sc.fixture_one_bad_neighbor()[0]).analyze(
            sc.fixture_one_bad_neighbor()[2],
            sc.fixture_one_bad_neighbor()[1]
        )
        self.assertEqual(res["spatial_status"], "AGREEMENT")

    def test_multiple_corrupted_neighbors_peeling(self):
        """Multiple corrupted neighbors peeled sequentially."""
        res = SpatialAnalyzer(sc.fixture_multiple_bad_neighbors()[0]).analyze(
            sc.fixture_multiple_bad_neighbors()[2],
            sc.fixture_multiple_bad_neighbors()[1]
        )
        self.assertEqual(res["spatial_status"], "AGREEMENT")

    def test_equal_weights_symmetry(self):
        """Equidistant neighbors yield symmetric equal weighting."""
        res = SpatialAnalyzer(sc.fixture_equal_distance_neighbors()[0]).analyze(
            sc.fixture_equal_distance_neighbors()[2],
            sc.fixture_equal_distance_neighbors()[1]
        )
        self.assertEqual(res["spatial_status"], "AGREEMENT")

    def test_extreme_weight_differences_stability(self):
        """Sub-meter neighbor vs distant neighbor is numerically stable."""
        reg = InMemoryStationRegistry()
        reg.register_station(Station("TARGET", 12.0, 77.0))
        reg.register_station(Station("N_NEAR", 12.00001, 77.0)) # ~1 meter
        reg.register_station(Station("N_FAR", 12.4, 77.0))      # ~44 km (within max_radius_km)

        snaps = {
            "TARGET": ObservationSnapshot(100.0, {"temperature": 25.0, "humidity": 60.0, "pressure": 1012.0}, valid=True),
            "N_NEAR": ObservationSnapshot(100.0, {"temperature": 25.0, "humidity": 60.0, "pressure": 1012.0}, valid=True),
            "N_FAR": ObservationSnapshot(100.0, {"temperature": 25.2, "humidity": 60.5, "pressure": 1012.1}, valid=True),
        }
        res = SpatialAnalyzer(reg).analyze("TARGET", snaps)
        self.assertTrue(math.isfinite(res["variables"]["temperature"]["consensus"]))
        self.assertEqual(res["spatial_status"], "AGREEMENT")

    def test_correlated_fault_evidence_limitation(self):
        """Correlated faults produce spatial corroboration evidence without asserting ground truth."""
        res = SpatialAnalyzer(sc.fixture_correlated_multi_station_fault()[0]).analyze(
            sc.fixture_correlated_multi_station_fault()[2],
            sc.fixture_correlated_multi_station_fault()[1]
        )
        self.assertEqual(res["spatial_status"], "AGREEMENT")
        self.assertIn("Spatial corroboration provides supporting evidence.", res["explanation"])

    def test_reproducibility_across_all_fixtures(self):
        """Repeated runs of every fixture produce bitwise identical results."""
        all_fixtures = [
            sc.fixture_all_neighbors_agree,
            sc.fixture_target_isolated_anomaly,
            sc.fixture_one_bad_neighbor,
            sc.fixture_multiple_bad_neighbors,
            sc.fixture_missing_neighbor,
            sc.fixture_insufficient_neighbors,
            sc.fixture_boundary_station,
            sc.fixture_equal_distance_neighbors,
            sc.fixture_extreme_distance_neighbor,
            sc.fixture_correlated_multi_station_fault,
            sc.fixture_propagating_spatial_weather_event,
            sc.fixture_mixed_evidence,
        ]
        for fixture_fn in all_fixtures:
            reg1, snaps1, t1 = fixture_fn()
            res1 = SpatialAnalyzer(reg1).analyze(t1, snaps1)

            reg2, snaps2, t2 = fixture_fn()
            res2 = SpatialAnalyzer(reg2).analyze(t2, snaps2)

            self.assertEqual(res1, res2)

    def test_explanation_text_contract_driven(self):
        """Explanation generator operates strictly from contract dictionary."""
        mock_evidence = {
            "station_id": "STN_TEST",
            "spatial_status": "DISAGREEMENT",
            "evidence_strength": "HIGH",
            "variables": {
                "temperature": {"status": "DISAGREEMENT", "target_value": 35.0, "consensus": 25.0, "standardized_residual": 3.5},
            },
            "included_neighbors": ["N1", "N2"],
            "excluded_neighbors": [],
        }
        exp = build_explanation(mock_evidence)
        self.assertIn("STN_TEST", exp)
        self.assertIn("spatial disagreement", exp)
        self.assertIn("temperature", exp)


if __name__ == "__main__":
    unittest.main()
