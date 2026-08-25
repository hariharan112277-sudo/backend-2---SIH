"""
Unit tests for Phase 3: Geographic Distance Calculation (spatial/distance.py)
"""

import math
import unittest
from spatial.interfaces import Station
from spatial.distance import haversine_distance_km, station_distance_km


class TestDistance(unittest.TestCase):

    def test_self_distance_zero(self):
        """Verify distance to self is exactly zero."""
        stn = Station(station_id="STN_01", latitude=12.9716, longitude=77.5946)
        self.assertEqual(station_distance_km(stn, stn), 0.0)

    def test_identical_coordinates_zero(self):
        """Verify distinct instances at identical coordinates yield zero distance."""
        d = haversine_distance_km(12.9716, 77.5946, 12.9716, 77.5946)
        self.assertEqual(d, 0.0)

    def test_distance_symmetry(self):
        """Verify distance(A, B) == distance(B, A)."""
        d1 = haversine_distance_km(12.9716, 77.5946, 13.0827, 80.2707)
        d2 = haversine_distance_km(13.0827, 80.2707, 12.9716, 77.5946)
        self.assertAlmostEqual(d1, d2, places=9)

    def test_known_geographic_reference_pair(self):
        """Verify reference pair (Bangalore to Chennai ~290 km)."""
        d = haversine_distance_km(12.9716, 77.5946, 13.0827, 80.2707)
        self.assertGreater(d, 285.0)
        self.assertLess(d, 295.0)

    def test_nearby_and_distant_points(self):
        """Verify nearby sub-kilometer and large trans-continental distances."""
        # Nearby (~1.1 km)
        d_near = haversine_distance_km(12.00, 77.00, 12.01, 77.00)
        self.assertGreater(d_near, 1.0)
        self.assertLess(d_near, 1.2)

        # Distant London to Tokyo (~9500-9600 km)
        d_far = haversine_distance_km(51.5074, -0.1278, 35.6762, 139.6503)
        self.assertGreater(d_far, 9500.0)
        self.assertLess(d_far, 9650.0)

    def test_extreme_geographic_boundaries(self):
        """Verify poles and antimeridian calculations."""
        # Pole to pole ~20,015 km
        d_poles = haversine_distance_km(90.0, 0.0, -90.0, 0.0)
        self.assertGreater(d_poles, 20000.0)
        self.assertLess(d_poles, 20050.0)

        # Antimeridian wrap (-180 and +180 same longitude line)
        d_anti = haversine_distance_km(0.0, -180.0, 0.0, 180.0)
        self.assertAlmostEqual(d_anti, 0.0, places=5)

    def test_invalid_and_missing_coordinates_raise(self):
        """Verify ValueError is raised on out-of-bounds, None, NaN, or Inf."""
        invalid_pairs = [
            (95.0, 0.0, 10.0, 10.0),
            (-95.0, 0.0, 10.0, 10.0),
            (0.0, 185.0, 10.0, 10.0),
            (0.0, -185.0, 10.0, 10.0),
            (None, 0.0, 10.0, 10.0),
            (10.0, 10.0, float("nan"), 0.0),
            (10.0, 10.0, 10.0, float("inf")),
        ]
        for lat1, lon1, lat2, lon2 in invalid_pairs:
            with self.assertRaises(ValueError):
                haversine_distance_km(lat1, lon1, lat2, lon2)


if __name__ == "__main__":
    unittest.main()
