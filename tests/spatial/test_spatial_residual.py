"""
Unit tests for Phase 4/5: Local Dispersion Helper (spatial/residual.py)
"""

import math
import unittest
from spatial.interfaces import SpatialNeighbor
from spatial.residual import compute_local_dispersion


class TestSpatialResidual(unittest.TestCase):

    def setUp(self):
        self.n1 = SpatialNeighbor(station_id="S1", distance_km=10.0, observed_value=18.0, weight=0.5)
        self.n2 = SpatialNeighbor(station_id="S2", distance_km=10.0, observed_value=22.0, weight=0.5)

    def test_weighted_local_dispersion(self):
        """Verify weighted local standard deviation calculation."""
        # Consensus = 20.0, Var = 0.5*(18-20)^2 + 0.5*(22-20)^2 = 4.0 -> Sigma = 2.0
        sigma = compute_local_dispersion(20.0, [self.n1, self.n2])
        self.assertAlmostEqual(sigma, 2.0)

    def test_weighted_local_dispersion_asymmetric(self):
        """Verify weighted local standard deviation with asymmetric weights."""
        n_a = SpatialNeighbor(station_id="S1", distance_km=5.0, observed_value=10.0, weight=0.8)
        n_b = SpatialNeighbor(station_id="S2", distance_km=20.0, observed_value=20.0, weight=0.2)
        # Consensus = 12.0, Var = 0.8*(10-12)^2 + 0.2*(20-12)^2 = 0.8*4 + 0.2*64 = 3.2 + 12.8 = 16.0 -> Sigma = 4.0
        sigma = compute_local_dispersion(12.0, [n_a, n_b])
        self.assertAlmostEqual(sigma, 4.0)

    def test_extreme_finite_values_stability(self):
        """Verify numerical stability on large magnitudes."""
        n_ext1 = SpatialNeighbor(station_id="S1", distance_km=10.0, observed_value=1e6, weight=0.5)
        n_ext2 = SpatialNeighbor(station_id="S2", distance_km=10.0, observed_value=1e6 + 4.0, weight=0.5)
        # Consensus = 1e6 + 2.0, Var = 0.5*(-2)^2 + 0.5*(2)^2 = 4.0 -> Sigma = 2.0
        sigma = compute_local_dispersion(1e6 + 2.0, [n_ext1, n_ext2])
        self.assertAlmostEqual(sigma, 2.0)


if __name__ == "__main__":
    unittest.main()
