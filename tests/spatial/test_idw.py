"""
Unit tests for Phase 4: IDW Spatial Consensus Engine (spatial/idw.py)
"""

import math
import unittest
from spatial.interfaces import Station, ObservationSnapshot
from spatial.neighbors import NeighborCandidate
from spatial.idw import compute_idw_consensus


class TestIDWConsensus(unittest.TestCase):

    def setUp(self):
        self.target = Station(station_id="STN_TGT", latitude=12.0, longitude=77.0)
        self.s1 = Station(station_id="STN_1", latitude=12.1, longitude=77.0)
        self.s2 = Station(station_id="STN_2", latitude=12.2, longitude=77.0)
        self.s_co = Station(station_id="STN_CO", latitude=12.0, longitude=77.0)

        self.c1 = NeighborCandidate(station=self.s1, distance_km=10.0)
        self.c2 = NeighborCandidate(station=self.s2, distance_km=20.0)

    def test_single_neighbor_consensus(self):
        """Verify single neighbor consensus equals its value with weight 1.0."""
        obs = {"STN_1": ObservationSnapshot(timestamp=100.0, values={"temp": 24.5}, valid=True)}
        consensus, used = compute_idw_consensus("STN_TGT", [self.c1], obs, "temp")
        self.assertIsNotNone(consensus)
        self.assertAlmostEqual(consensus, 24.5)
        self.assertEqual(len(used), 1)
        self.assertEqual(used[0].weight, 1.0)

    def test_multi_neighbor_inverse_distance_weighting(self):
        """Verify inverse distance weighting with power p=2."""
        # d1=10 -> w1=0.01; d2=20 -> w2=0.0025; sum_w=0.0125
        # norm_w1=0.8, norm_w2=0.2
        # val1=20.0, val2=30.0 -> consensus = 0.8*20 + 0.2*30 = 22.0
        obs = {
            "STN_1": ObservationSnapshot(timestamp=100.0, values={"temp": 20.0}, valid=True),
            "STN_2": ObservationSnapshot(timestamp=100.0, values={"temp": 30.0}, valid=True),
        }
        consensus, used = compute_idw_consensus("STN_TGT", [self.c1, self.c2], obs, "temp", power_p=2.0)
        self.assertIsNotNone(consensus)
        self.assertAlmostEqual(consensus, 22.0)
        self.assertAlmostEqual(used[0].weight, 0.8)
        self.assertAlmostEqual(used[1].weight, 0.2)

    def test_configured_power_exponent(self):
        """Verify power p=1 linear inverse weighting."""
        # d1=10 -> w1=0.1; d2=20 -> w2=0.05; sum_w=0.15
        # norm_w1=2/3, norm_w2=1/3
        # val1=20.0, val2=35.0 -> consensus = (2/3)*20 + (1/3)*35 = 40/3 + 35/3 = 75/3 = 25.0
        obs = {
            "STN_1": ObservationSnapshot(timestamp=100.0, values={"temp": 20.0}, valid=True),
            "STN_2": ObservationSnapshot(timestamp=100.0, values={"temp": 35.0}, valid=True),
        }
        consensus, used = compute_idw_consensus("STN_TGT", [self.c1, self.c2], obs, "temp", power_p=1.0)
        self.assertAlmostEqual(consensus, 25.0)
        self.assertAlmostEqual(used[0].weight, 2.0 / 3.0)
        self.assertAlmostEqual(used[1].weight, 1.0 / 3.0)

    def test_invalid_observation_filtering(self):
        """Verify invalid, missing, None, NaN, and Inf observations are ignored."""
        s3 = Station(station_id="STN_3", latitude=12.3, longitude=77.0)
        s4 = Station(station_id="STN_4", latitude=12.4, longitude=77.0)
        c3 = NeighborCandidate(station=s3, distance_km=30.0)
        c4 = NeighborCandidate(station=s4, distance_km=40.0)

        obs = {
            "STN_1": ObservationSnapshot(100.0, {"temp": 20.0}, valid=True),
            "STN_2": ObservationSnapshot(100.0, {"temp": 50.0}, valid=False),  # invalid flag
            "STN_3": ObservationSnapshot(100.0, {"humidity": 80.0}, valid=True),  # missing variable
            "STN_4": ObservationSnapshot(100.0, {"temp": float("nan")}, valid=True),  # non-finite
        }
        consensus, used = compute_idw_consensus("STN_TGT", [self.c1, self.c2, c3, c4], obs, "temp")
        self.assertAlmostEqual(consensus, 20.0)
        self.assertEqual(len(used), 1)
        self.assertEqual(used[0].station_id, "STN_1")

    def test_target_station_self_exclusion(self):
        """Verify target station cannot contribute to its own IDW consensus."""
        c_target = NeighborCandidate(station=self.target, distance_km=0.0)
        obs = {
            "STN_TGT": ObservationSnapshot(100.0, {"temp": 100.0}, valid=True),
            "STN_1": ObservationSnapshot(100.0, {"temp": 20.0}, valid=True),
        }
        consensus, used = compute_idw_consensus("STN_TGT", [c_target, self.c1], obs, "temp")
        self.assertAlmostEqual(consensus, 20.0)
        self.assertEqual(len(used), 1)
        self.assertEqual(used[0].station_id, "STN_1")

    def test_co_located_stations_zero_distance_dominance(self):
        """Verify co-located zero-distance stations dominate with equal weight."""
        s_co2 = Station(station_id="STN_CO2", latitude=12.0, longitude=77.0)
        c_co1 = NeighborCandidate(station=self.s_co, distance_km=0.0)
        c_co2 = NeighborCandidate(station=s_co2, distance_km=0.0)

        obs = {
            "STN_CO": ObservationSnapshot(100.0, {"temp": 22.0}, valid=True),
            "STN_CO2": ObservationSnapshot(100.0, {"temp": 26.0}, valid=True),
            "STN_1": ObservationSnapshot(100.0, {"temp": 100.0}, valid=True),  # distant
        }
        consensus, used = compute_idw_consensus("STN_TGT", [c_co1, c_co2, self.c1], obs, "temp")
        self.assertAlmostEqual(consensus, 24.0)
        self.assertEqual(len(used), 3)
        self.assertAlmostEqual(used[0].weight, 0.5)
        self.assertAlmostEqual(used[1].weight, 0.5)
        self.assertAlmostEqual(used[2].weight, 0.0)

    def test_empty_neighbor_and_observation_set(self):
        """Verify empty candidates or observations return (None, [])."""
        consensus, used = compute_idw_consensus("STN_TGT", [], {}, "temp")
        self.assertIsNone(consensus)
        self.assertEqual(used, [])

    def test_deterministic_idw_repeatability(self):
        """Verify IDW calculation produces identical results across repeated calls."""
        obs = {
            "STN_1": ObservationSnapshot(100.0, {"temp": 21.345}, valid=True),
            "STN_2": ObservationSnapshot(100.0, {"temp": 28.678}, valid=True),
        }
        res1, used1 = compute_idw_consensus("STN_TGT", [self.c1, self.c2], obs, "temp")
        res2, used2 = compute_idw_consensus("STN_TGT", [self.c1, self.c2], obs, "temp")
        self.assertEqual(res1, res2)
        for u1, u2 in zip(used1, used2):
            self.assertEqual(u1.weight, u2.weight)


if __name__ == "__main__":
    unittest.main()
