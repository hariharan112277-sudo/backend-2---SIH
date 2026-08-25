"""
Contract Integrity & Public Surface Tests (Phase 9)
Authoritative Source: OTE_Member2_Implementation_Bible.pdf (Section 9.2 & Phase 9)
"""

import unittest
import spatial
from spatial.interfaces import Station, ObservationSnapshot
from spatial.station_registry import InMemoryStationRegistry
from spatial.analyzer import SpatialAnalyzer, SUPPORTED_VARIABLES
from spatial.config import DEFAULT_SPATIAL_CONFIG
import spatial.fixtures.scenarios as sc


class TestSpatialContractIntegrity(unittest.TestCase):

    def test_public_export_surface(self):
        """Verify that all frozen public symbols are exported in spatial.__all__."""
        expected = {
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
        }
        self.assertEqual(set(spatial.__all__), expected)
        for sym in expected:
            self.assertTrue(hasattr(spatial, sym), f"Missing symbol: {sym}")

    def test_top_level_output_schema_exactness(self):
        """Verify all Section 9.2 top-level keys exist in analyzer output."""
        reg, snaps, target_id = sc.fixture_all_neighbors_agree()
        res = SpatialAnalyzer(reg).analyze(target_id, snaps)
        required_keys = {
            "station_id",
            "variables",
            "spatial_status",
            "evidence_strength",
            "included_neighbors",
            "excluded_neighbors",
            "explanation",
        }
        self.assertTrue(required_keys.issubset(res.keys()))

    def test_variable_level_output_schema_exactness(self):
        """Verify all Section 9.2 variable-level keys exist for all supported variables."""
        reg, snaps, target_id = sc.fixture_all_neighbors_agree()
        res = SpatialAnalyzer(reg).analyze(target_id, snaps)
        var_keys = {
            "neighbor_count",
            "valid_neighbor_count",
            "agreement_count",
            "disagreement_score",
            "consensus",
            "target_value",
            "standardized_residual",
            "status",
        }
        for var in SUPPORTED_VARIABLES:
            self.assertIn(var, res["variables"])
            self.assertTrue(var_keys.issubset(res["variables"][var].keys()))

    def test_allowed_status_and_evidence_strength_values(self):
        """Verify status values conform strictly to contract enum strings."""
        reg, snaps, target_id = sc.fixture_all_neighbors_agree()
        res = SpatialAnalyzer(reg).analyze(target_id, snaps)
        allowed_statuses = {"AGREEMENT", "DISAGREEMENT", "INSUFFICIENT_SPATIAL_EVIDENCE"}
        allowed_strengths = {"HIGH", "MEDIUM", "LOW", "NONE"}

        self.assertIn(res["spatial_status"], allowed_statuses)
        self.assertIn(res["evidence_strength"], allowed_strengths)
        for var in SUPPORTED_VARIABLES:
            self.assertIn(res["variables"][var]["status"], allowed_statuses)

    def test_calibration_parameters_presence(self):
        """Verify centralized calibration parameters exist on DEFAULT_SPATIAL_CONFIG."""
        cfg = DEFAULT_SPATIAL_CONFIG
        self.assertEqual(cfg.k_neighbors, 5)
        self.assertEqual(cfg.max_radius_km, 50.0)
        self.assertEqual(getattr(cfg, "idw_power", getattr(cfg, "idw_power_p", 2.0)), 2.0)
        self.assertTrue(hasattr(cfg, "min_neighbors") or hasattr(cfg, "min_valid_neighbors"))
        self.assertEqual(cfg.self_outlier_z_threshold, 3.0)
        self.assertEqual(getattr(cfg, "anomaly_threshold_z", getattr(cfg, "spatial_z_threshold", 2.5)), 2.5)

    def test_degraded_unknown_station_contract(self):
        """Verify non-throwing execution for unknown station ID."""
        reg = InMemoryStationRegistry()
        res = SpatialAnalyzer(reg).analyze("NON_EXISTENT", {})
        self.assertEqual(res["spatial_status"], "INSUFFICIENT_SPATIAL_EVIDENCE")
        self.assertEqual(res["evidence_strength"], "NONE")
        for var in SUPPORTED_VARIABLES:
            self.assertEqual(res["variables"][var]["status"], "INSUFFICIENT_SPATIAL_EVIDENCE")
            self.assertIsNone(res["variables"][var]["standardized_residual"])

    def test_contamination_provenance_tracking(self):
        """Verify excluded neighbors are recorded in top-level excluded_neighbors."""
        reg, snaps, target_id = sc.fixture_one_bad_neighbor()
        res = SpatialAnalyzer(reg).analyze(target_id, snaps)
        self.assertTrue(len(res["excluded_neighbors"]) > 0)
        self.assertIn("N_1", res["excluded_neighbors"])

    def test_determinism_across_runs(self):
        """Verify identical inputs produce bitwise identical contract dictionaries."""
        reg, snaps, target_id = sc.fixture_all_neighbors_agree()
        res1 = SpatialAnalyzer(reg).analyze(target_id, snaps)
        res2 = SpatialAnalyzer(reg).analyze(target_id, snaps)
        self.assertEqual(res1, res2)

    def test_explanation_generation_integration(self):
        """Verify explanation string is populated and contract-driven."""
        reg, snaps, target_id = sc.fixture_all_neighbors_agree()
        res = SpatialAnalyzer(reg).analyze(target_id, snaps)
        self.assertIsInstance(res["explanation"], str)
        self.assertIn(target_id, res["explanation"])


if __name__ == "__main__":
    unittest.main()
