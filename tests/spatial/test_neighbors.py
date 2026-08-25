"""
Unit tests for Phase 3: Neighbor Discovery Engine (spatial/neighbors.py)
"""

import math
import unittest
from spatial.interfaces import Station
from spatial.station_registry import InMemoryStationRegistry
from spatial.neighbors import (
    find_k_nearest_neighbors,
    find_radius_neighbors,
    discover_neighbors,
)
from spatial.fixtures.stations_fixture import generate_local_stations_fixture
from spatial.distance import haversine_distance_km


class TestNeighbors(unittest.TestCase):

    def setUp(self):
        self.target = Station(station_id="TARGET", latitude=12.0, longitude=77.0)
        self.n_tie_b = Station(station_id="STN_TIE_B", latitude=12.01, longitude=77.0)
        self.n_tie_a = Station(station_id="STN_TIE_A", latitude=12.01, longitude=77.0)
        self.n_mid = Station(station_id="STN_MID", latitude=12.10, longitude=77.0)
        self.n_far = Station(station_id="STN_FAR", latitude=13.00, longitude=77.0)
        self.n_invalid = Station(station_id="STN_INVALID", latitude=120.0, longitude=77.0)
        self.n_nan = Station(station_id="STN_NAN", latitude=float("nan"), longitude=77.0)

        self.registry = InMemoryStationRegistry([
            self.target,
            self.n_tie_b,
            self.n_tie_a,
            self.n_mid,
            self.n_far,
            self.n_invalid,
            self.n_nan,
        ])

    def test_k_nearest_selection_basic(self):
        """Verify discovery of k nearest neighbors."""
        neighbors = find_k_nearest_neighbors(self.target, self.registry, k=2)
        self.assertEqual(len(neighbors), 2)
        self.assertEqual(neighbors[0].station.station_id, "STN_TIE_A")
        self.assertEqual(neighbors[1].station.station_id, "STN_TIE_B")

    def test_self_exclusion(self):
        """Verify query station is never returned as its own neighbor."""
        neighbors = find_k_nearest_neighbors(self.target, self.registry, k=10)
        ids = [n.station.station_id for n in neighbors]
        self.assertNotIn("TARGET", ids)

    def test_candidate_validity_filtering(self):
        """Verify invalid or NaN stations are not selected as neighbors."""
        neighbors = find_k_nearest_neighbors(self.target, self.registry, k=10)
        ids = [n.station.station_id for n in neighbors]
        self.assertNotIn("STN_INVALID", ids)
        self.assertNotIn("STN_NAN", ids)

    def test_deterministic_ordering_and_tie_breaking(self):
        """Verify distance ordering and alphabetical tie-breaking on station_id."""
        neighbors = find_k_nearest_neighbors(self.target, self.registry, k=4)
        ids = [n.station.station_id for n in neighbors]
        self.assertEqual(ids, ["STN_TIE_A", "STN_TIE_B", "STN_MID", "STN_FAR"])

    def test_sparse_network_fewer_than_k(self):
        """Verify network with fewer valid candidates returns available candidates."""
        sparse_reg = InMemoryStationRegistry([self.target, self.n_mid])
        neighbors = find_k_nearest_neighbors(self.target, sparse_reg, k=5)
        self.assertEqual(len(neighbors), 1)
        self.assertEqual(neighbors[0].station.station_id, "STN_MID")

    def test_co_located_stations(self):
        """Verify distinct stations at distance 0.0 remain valid neighbors."""
        coloc = Station(station_id="STN_COLOC", latitude=12.0, longitude=77.0)
        reg = InMemoryStationRegistry([self.target, coloc])
        neighbors = find_k_nearest_neighbors(self.target, reg, k=5)
        self.assertEqual(len(neighbors), 1)
        self.assertEqual(neighbors[0].station.station_id, "STN_COLOC")
        self.assertEqual(neighbors[0].distance_km, 0.0)

    def test_empty_neighbor_set(self):
        """Verify empty registry or isolated station returns empty list."""
        isolated_reg = InMemoryStationRegistry([self.target])
        self.assertEqual(find_k_nearest_neighbors(self.target, isolated_reg, k=5), [])

    def test_radius_search_inclusive_boundary(self):
        """Verify radius selection includes exact boundary matches."""
        exact_dist = haversine_distance_km(12.0, 77.0, 12.10, 77.0)
        reg = InMemoryStationRegistry([self.target, self.n_mid])
        res_exact = find_radius_neighbors(self.target, reg, radius_km=exact_dist)
        self.assertEqual(len(res_exact), 1)
        self.assertEqual(res_exact[0].station.station_id, "STN_MID")

        res_under = find_radius_neighbors(self.target, reg, radius_km=exact_dist - 0.001)
        self.assertEqual(len(res_under), 0)

    def test_invalid_target_station_returns_empty(self):
        """Verify evaluating an invalid target station yields empty list."""
        bad_target = Station(station_id="BAD_TGT", latitude=150.0, longitude=77.0)
        self.assertEqual(find_k_nearest_neighbors(bad_target, self.registry, k=5), [])

    def test_deterministic_execution_against_fixture(self):
        """Verify neighbor selection against Phase-2 24-station fixture is repeatable."""
        fleet = generate_local_stations_fixture(seed=42, count=24)
        reg = InMemoryStationRegistry(fleet)
        target = fleet[0]

        res1 = discover_neighbors(target, reg)
        res2 = discover_neighbors(target, reg)

        self.assertEqual(len(res1), len(res2))
        self.assertTrue(len(res1) > 0)
        for n1, n2 in zip(res1, res2):
            self.assertEqual(n1.station.station_id, n2.station.station_id)
            self.assertEqual(n1.distance_km, n2.distance_km)


if __name__ == "__main__":
    unittest.main()
