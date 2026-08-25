"""
Unit tests for Phase 7: Multi-Variable Spatial Evidence / SpatialAnalyzer
Authoritative Source: OTE_Member2_Implementation_Bible.pdf (Phase 7 & Section 9.2)
"""

import math
import unittest
from spatial.interfaces import Station, ObservationSnapshot
from spatial.station_registry import InMemoryStationRegistry
from spatial.analyzer import SpatialAnalyzer, SUPPORTED_VARIABLES


class TestSpatialAnalyzer(unittest.TestCase):

    def setUp(self):
        self.registry = InMemoryStationRegistry()
        self.target = Station("AWS_01", 12.0, 77.0)
        self.registry.register_station(self.target)

        # Register neighbor stations
        for i in range(2, 10):
            stn = Station(f"AWS_0{i}", 12.0 + (0.01 * i), 77.0 + (0.01 * i))
            self.registry.register_station(stn)

        self.analyzer = SpatialAnalyzer(self.registry)

        # Base snapshot dictionary with natural dispersion
        self.snaps_agree = {
            "AWS_01": ObservationSnapshot(100.0, {"temperature": 25.0, "humidity": 60.0, "pressure": 1012.0}, valid=True),
        }
        for i in range(2, 10):
            idx = i - 2
            self.snaps_agree[f"AWS_0{i}"] = ObservationSnapshot(
                100.0,
                {
                    "temperature": 25.0 + (0.1 * (idx - 2)),
                    "humidity": 60.0 + (0.2 * (idx - 2)),
                    "pressure": 1012.0 + (0.1 * (idx - 2)),
                },
                valid=True,
            )

    def test_all_variables_agree(self):
        """Verify when all 3 variables match consensus, fleet status is AGREEMENT and strength is HIGH."""
        res = self.analyzer.analyze("AWS_01", self.snaps_agree)
        self.assertEqual(res["spatial_status"], "AGREEMENT")
        self.assertEqual(res["evidence_strength"], "HIGH")
        for var in SUPPORTED_VARIABLES:
            self.assertEqual(res["variables"][var]["status"], "AGREEMENT")
            self.assertIsNotNone(res["variables"][var]["consensus"])
            self.assertIsNotNone(res["variables"][var]["target_value"])

    def test_all_variables_disagree(self):
        """Verify when all 3 variables deviate, fleet status is DISAGREEMENT and strength is HIGH."""
        snaps = dict(self.snaps_agree)
        snaps["AWS_01"] = ObservationSnapshot(
            100.0,
            {"temperature": 40.0, "humidity": 10.0, "pressure": 980.0},
            valid=True,
        )
        res = self.analyzer.analyze("AWS_01", snaps)
        self.assertEqual(res["spatial_status"], "DISAGREEMENT")
        self.assertEqual(res["evidence_strength"], "HIGH")
        for var in SUPPORTED_VARIABLES:
            self.assertEqual(res["variables"][var]["status"], "DISAGREEMENT")

    def test_mixed_agreement_disagreement(self):
        """Verify 1 disagree + 2 agree produces fleet DISAGREEMENT per most-severe hierarchy."""
        snaps = dict(self.snaps_agree)
        snaps["AWS_01"] = ObservationSnapshot(
            100.0,
            {"temperature": 40.0, "humidity": 60.0, "pressure": 1012.0}, # temp disagrees
            valid=True,
        )
        res = self.analyzer.analyze("AWS_01", snaps)
        self.assertEqual(res["spatial_status"], "DISAGREEMENT")
        self.assertEqual(res["evidence_strength"], "HIGH")
        self.assertEqual(res["variables"]["temperature"]["status"], "DISAGREEMENT")
        self.assertEqual(res["variables"]["humidity"]["status"], "AGREEMENT")
        self.assertEqual(res["variables"]["pressure"]["status"], "AGREEMENT")

    def test_all_variables_insufficient(self):
        """Verify target valid=False produces INSUFFICIENT_SPATIAL_EVIDENCE and NONE strength."""
        snaps = dict(self.snaps_agree)
        snaps["AWS_01"] = ObservationSnapshot(100.0, {}, valid=False)
        res = self.analyzer.analyze("AWS_01", snaps)
        self.assertEqual(res["spatial_status"], "INSUFFICIENT_SPATIAL_EVIDENCE")
        self.assertEqual(res["evidence_strength"], "NONE")
        for var in SUPPORTED_VARIABLES:
            self.assertEqual(res["variables"][var]["status"], "INSUFFICIENT_SPATIAL_EVIDENCE")

    def test_partial_insufficient_medium_strength(self):
        """Verify 2 valid agree + 1 missing produces AGREEMENT and MEDIUM strength."""
        snaps = dict(self.snaps_agree)
        snaps["AWS_01"] = ObservationSnapshot(
            100.0,
            {"temperature": 25.0, "humidity": 60.0}, # pressure missing
            valid=True,
        )
        res = self.analyzer.analyze("AWS_01", snaps)
        self.assertEqual(res["spatial_status"], "AGREEMENT")
        self.assertEqual(res["evidence_strength"], "MEDIUM")
        self.assertEqual(res["variables"]["temperature"]["status"], "AGREEMENT")
        self.assertEqual(res["variables"]["humidity"]["status"], "AGREEMENT")
        self.assertEqual(res["variables"]["pressure"]["status"], "INSUFFICIENT_SPATIAL_EVIDENCE")

    def test_partial_insufficient_low_strength(self):
        """Verify 1 valid disagree + 2 missing produces DISAGREEMENT and LOW strength."""
        snaps = dict(self.snaps_agree)
        snaps["AWS_01"] = ObservationSnapshot(
            100.0,
            {"temperature": 40.0}, # humidity and pressure missing
            valid=True,
        )
        res = self.analyzer.analyze("AWS_01", snaps)
        self.assertEqual(res["spatial_status"], "DISAGREEMENT")
        self.assertEqual(res["evidence_strength"], "LOW")
        self.assertEqual(res["variables"]["temperature"]["status"], "DISAGREEMENT")
        self.assertEqual(res["variables"]["humidity"]["status"], "INSUFFICIENT_SPATIAL_EVIDENCE")
        self.assertEqual(res["variables"]["pressure"]["status"], "INSUFFICIENT_SPATIAL_EVIDENCE")

    def test_contamination_defense_integration(self):
        """Verify contaminated neighbor is excluded before IDW and consensus is protected."""
        snaps = dict(self.snaps_agree)
        snaps["AWS_02"] = ObservationSnapshot(
            100.0,
            {"temperature": 100.0, "humidity": 60.0, "pressure": 1012.0}, # extreme outlier
            valid=True,
        )
        res = self.analyzer.analyze("AWS_01", snaps)
        self.assertIn("AWS_02", res["excluded_neighbors"])
        self.assertEqual(res["variables"]["temperature"]["status"], "AGREEMENT")
        self.assertEqual(res["spatial_status"], "AGREEMENT")

    def test_included_and_excluded_neighbor_tracking(self):
        """Verify included and excluded neighbors are deterministically tracked."""
        res = self.analyzer.analyze("AWS_01", self.snaps_agree)
        self.assertTrue(len(res["included_neighbors"]) > 0)
        self.assertNotIn("AWS_01", res["included_neighbors"]) # target excluded from neighbors

    def test_section_9_2_output_schema_exactness(self):
        """Verify exact field presence for top-level and variable-level dictionary contract."""
        res = self.analyzer.analyze("AWS_01", self.snaps_agree)
        top_required = {
            "station_id", "variables", "spatial_status",
            "evidence_strength", "included_neighbors",
            "excluded_neighbors", "explanation"
        }
        self.assertTrue(top_required.issubset(res.keys()))

        var_required = {
            "neighbor_count", "valid_neighbor_count", "agreement_count",
            "disagreement_score", "consensus", "target_value",
            "standardized_residual", "status"
        }
        for var in SUPPORTED_VARIABLES:
            self.assertTrue(var_required.issubset(res["variables"][var].keys()))

    def test_generic_variable_pipeline_consistency(self):
        """Verify all supported variables use the generic single-variable path."""
        res = self.analyzer.analyze("AWS_01", self.snaps_agree)
        self.assertEqual(set(res["variables"].keys()), set(SUPPORTED_VARIABLES))

    def test_deterministic_repeated_execution(self):
        """Verify identical inputs produce bitwise identical analyzer outputs."""
        res1 = self.analyzer.analyze("AWS_01", self.snaps_agree)
        res2 = self.analyzer.analyze("AWS_01", self.snaps_agree)
        self.assertEqual(res1, res2)


if __name__ == "__main__":
    unittest.main()
