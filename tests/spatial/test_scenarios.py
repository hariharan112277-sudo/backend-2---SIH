"""
Unit tests for 12 Canonical Scenario Fixtures (Phase 8)
Authoritative Source: OTE_Member2_Implementation_Bible.pdf (Section 11 & Phase 8)
"""

import unittest
from spatial.analyzer import SpatialAnalyzer
import spatial.fixtures.scenarios as sc


class TestCanonicalScenarios(unittest.TestCase):

    def _execute(self, fixture_fn):
        reg, snaps, target_id = fixture_fn()
        analyzer = SpatialAnalyzer(reg)
        return analyzer.analyze(target_id, snaps)

    def test_scenario_all_neighbors_agree(self):
        res = self._execute(sc.fixture_all_neighbors_agree)
        self.assertEqual(res["spatial_status"], "AGREEMENT")
        self.assertEqual(res["evidence_strength"], "HIGH")
        self.assertIn("corroborated", res["explanation"])

    def test_scenario_target_isolated_anomaly(self):
        res = self._execute(sc.fixture_target_isolated_anomaly)
        self.assertEqual(res["spatial_status"], "DISAGREEMENT")
        self.assertEqual(res["evidence_strength"], "HIGH")
        self.assertEqual(res["variables"]["temperature"]["status"], "DISAGREEMENT")

    def test_scenario_one_bad_neighbor(self):
        res = self._execute(sc.fixture_one_bad_neighbor)
        self.assertEqual(res["spatial_status"], "AGREEMENT")
        self.assertEqual(res["evidence_strength"], "HIGH")
        self.assertTrue(len(res["excluded_neighbors"]) >= 1)

    def test_scenario_multiple_bad_neighbors(self):
        res = self._execute(sc.fixture_multiple_bad_neighbors)
        self.assertEqual(res["spatial_status"], "AGREEMENT")
        self.assertEqual(res["evidence_strength"], "HIGH")
        self.assertTrue(len(res["excluded_neighbors"]) >= 2)

    def test_scenario_missing_neighbor(self):
        res = self._execute(sc.fixture_missing_neighbor)
        self.assertEqual(res["spatial_status"], "AGREEMENT")
        self.assertEqual(res["evidence_strength"], "HIGH")

    def test_scenario_insufficient_neighbors(self):
        res = self._execute(sc.fixture_insufficient_neighbors)
        self.assertEqual(res["spatial_status"], "INSUFFICIENT_SPATIAL_EVIDENCE")
        self.assertEqual(res["evidence_strength"], "NONE")

    def test_scenario_boundary_station(self):
        res = self._execute(sc.fixture_boundary_station)
        self.assertEqual(res["spatial_status"], "AGREEMENT")
        self.assertEqual(res["evidence_strength"], "HIGH")

    def test_scenario_equal_distance_neighbors(self):
        res = self._execute(sc.fixture_equal_distance_neighbors)
        self.assertEqual(res["spatial_status"], "AGREEMENT")
        self.assertEqual(res["evidence_strength"], "HIGH")

    def test_scenario_extreme_distance_neighbor(self):
        res = self._execute(sc.fixture_extreme_distance_neighbor)
        self.assertEqual(res["spatial_status"], "AGREEMENT")
        self.assertEqual(res["evidence_strength"], "HIGH")

    def test_scenario_correlated_multi_station_fault(self):
        res = self._execute(sc.fixture_correlated_multi_station_fault)
        self.assertEqual(res["spatial_status"], "AGREEMENT")
        self.assertEqual(res["evidence_strength"], "HIGH")
        # Evidence generated, no final OTE decision made
        self.assertIn("Spatial corroboration provides supporting evidence.", res["explanation"])

    def test_scenario_propagating_spatial_weather_event(self):
        res = self._execute(sc.fixture_propagating_spatial_weather_event)
        self.assertEqual(res["spatial_status"], "AGREEMENT")
        self.assertEqual(res["evidence_strength"], "HIGH")

    def test_scenario_mixed_evidence(self):
        res = self._execute(sc.fixture_mixed_evidence)
        self.assertEqual(res["spatial_status"], "DISAGREEMENT")
        self.assertEqual(res["evidence_strength"], "HIGH")
        self.assertEqual(res["variables"]["temperature"]["status"], "DISAGREEMENT")
        self.assertEqual(res["variables"]["humidity"]["status"], "AGREEMENT")


if __name__ == "__main__":
    unittest.main()
