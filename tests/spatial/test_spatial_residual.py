"""
Unit tests for Phase 4: Spatial Residual & Local Dispersion (spatial/residual.py)
"""

import math
import unittest
from spatial.interfaces import SpatialNeighbor
from spatial.residual import compute_spatial_residual, compute_local_dispersion


class TestSpatialResidual(unittest.TestCase):

    def setUp(self):
        self.n1 = SpatialNeighbor(station_id="S1", distance_km=10.0, observed_value=18.0, weight=0.5)
        self.n2 = SpatialNeighbor(station_id="S2", distance_km=10.0, observed_value=22.0, weight=0.5)
        # Consensus = 20.0, Var = 0.5*(18-20)^2 + 0.5*(22-20)^2 = 4.0 -> Sigma = 2.0

    def test_zero_residual_on_exact_match(self):
        """Verify residual and standardized residual are 0.0 when target equals consensus."""
        r, z, sigma = compute_spatial_residual(20.0, 20.0, [self.n1, self.n2])
        self.assertEqual(r, 0.0)
        self.assertEqual(z, 0.0)
        self.assertAlmostEqual(sigma, 2.0)

    def test_positive_and_negative_residuals(self):
        """Verify positive and negative signs are preserved."""
        # Positive: target = 24.0 -> r = +4.0, z = +2.0
        r_pos, z_pos, _ = compute_spatial_residual(24.0, 20.0, [self.n1, self.n2])
        self.assertAlmostEqual(r_pos, 4.0)
        self.assertAlmostEqual(z_pos, 2.0)

        # Negative: target = 16.0 -> r = -4.0, z = -2.0
        r_neg, z_neg, _ = compute_spatial_residual(16.0, 20.0, [self.n1, self.n2])
        self.assertAlmostEqual(r_neg, -4.0)
        self.assertAlmostEqual(z_neg, -2.0)

    def test_weighted_local_dispersion(self):
        """Verify weighted local standard deviation calculation."""
        n_unweighted_a = SpatialNeighbor(station_id="S1", distance_km=5.0, observed_value=10.0, weight=0.8)
        n_unweighted_b = SpatialNeighbor(station_id="S2", distance_km=20.0, observed_value=20.0, weight=0.2)
        # Consensus = 0.8*10 + 0.2*20 = 12.0
        # Var = 0.8*(10-12)^2 + 0.2*(20-12)^2 = 0.8*4 + 0.2*64 = 3.2 + 12.8 = 16.0 -> Sigma = 4.0
        sigma = compute_local_dispersion(12.0, [n_unweighted_a, n_unweighted_b])
        self.assertAlmostEqual(sigma, 4.0)

    def test_standardized_residual_z_score(self):
        """Verify z = r / sigma."""
        r, z, sigma = compute_spatial_residual(23.0, 20.0, [self.n1, self.n2])
        self.assertAlmostEqual(r, 3.0)
        self.assertAlmostEqual(sigma, 2.0)
        self.assertAlmostEqual(z, 1.5)

    def test_zero_dispersion_epsilon_guard(self):
        """Verify zero dispersion uses variance epsilon guard."""
        n_c1 = SpatialNeighbor(station_id="S1", distance_km=10.0, observed_value=20.0, weight=0.5)
        n_c2 = SpatialNeighbor(station_id="S2", distance_km=10.0, observed_value=20.0, weight=0.5)
        # Consensus = 20.0, Sigma = 0.0, Target = 21.0 -> r = 1.0, z = 1.0 / 1e-6
        r, z, sigma = compute_spatial_residual(21.0, 20.0, [n_c1, n_c2], variance_epsilon=1e-6)
        self.assertAlmostEqual(r, 1.0)
        self.assertAlmostEqual(sigma, 0.0)
        self.assertAlmostEqual(z, 1.0 / 1e-6)

    def test_invalid_target_and_consensus_returns_none(self):
        """Verify None or non-finite inputs return (None, None, 0.0)."""
        self.assertEqual(compute_spatial_residual(None, 20.0, [self.n1]), (None, None, 0.0))
        self.assertEqual(compute_spatial_residual(20.0, None, [self.n1]), (None, None, 0.0))
        self.assertEqual(compute_spatial_residual(float("nan"), 20.0, [self.n1]), (None, None, 0.0))
        self.assertEqual(compute_spatial_residual(20.0, float("inf"), [self.n1]), (None, None, 0.0))

    def test_extreme_finite_values_stability(self):
        """Verify numerical stability on large magnitudes."""
        n_ext1 = SpatialNeighbor(station_id="S1", distance_km=10.0, observed_value=1e6, weight=0.5)
        n_ext2 = SpatialNeighbor(station_id="S2", distance_km=10.0, observed_value=1e6 + 4.0, weight=0.5)
        # Consensus = 1e6 + 2.0, Var = 0.5*(-2)^2 + 0.5*(2)^2 = 4.0 -> Sigma = 2.0
        r, z, sigma = compute_spatial_residual(1e6 + 6.0, 1e6 + 2.0, [n_ext1, n_ext2])
        self.assertAlmostEqual(r, 4.0)
        self.assertAlmostEqual(sigma, 2.0)
        self.assertAlmostEqual(z, 2.0)


if __name__ == "__main__":
    unittest.main()
