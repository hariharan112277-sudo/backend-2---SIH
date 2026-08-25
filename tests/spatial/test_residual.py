"""
Unit tests for Phase 5: Standardized Spatial Residual & Status Classification
Authoritative Source: OTE_Member2_Implementation_Bible.pdf (Phase 5)
"""

import math
import unittest
from spatial.interfaces import SpatialNeighbor, SpatialStatus
from spatial.residual import (
    compute_spatial_residual,
    compute_reference_scale,
    classify_spatial_status,
    MIN_VALID_NEIGHBORS,
    DEFAULT_SPATIAL_Z_THRESHOLD,
)


class TestSpatialResidualAndStatus(unittest.TestCase):

    def setUp(self):
        self.n1 = SpatialNeighbor(station_id="S1", distance_km=10.0, observed_value=20.0, weight=0.5)
        self.n2 = SpatialNeighbor(station_id="S2", distance_km=10.0, observed_value=24.0, weight=0.5)
        # Neighbor sample std dev: mean = 22.0, var = ((20-22)^2 + (24-22)^2)/1 = 8.0 -> scale = sqrt(8) ~ 2.828427

    def test_target_equals_consensus(self):
        """Verify residual and standardized residual are 0.0 when target matches consensus."""
        r, z, s = compute_spatial_residual(22.0, 22.0, [self.n1, self.n2])
        self.assertEqual(r, 0.0)
        self.assertEqual(z, 0.0)
        self.assertAlmostEqual(s, math.sqrt(8.0))

    def test_positive_and_negative_residuals(self):
        """Verify sign preservation for positive and negative deviations."""
        scale = math.sqrt(8.0)
        # Positive
        r_pos, z_pos, _ = compute_spatial_residual(22.0 + scale, 22.0, [self.n1, self.n2])
        self.assertAlmostEqual(r_pos, scale)
        self.assertAlmostEqual(z_pos, 1.0)

        # Negative
        r_neg, z_neg, _ = compute_spatial_residual(22.0 - scale, 22.0, [self.n1, self.n2])
        self.assertAlmostEqual(r_neg, -scale)
        self.assertAlmostEqual(z_neg, -1.0)

    def test_standardization_with_known_scale(self):
        """Verify exact z = r / s computation."""
        scale = math.sqrt(8.0)
        r, z, s = compute_spatial_residual(22.0 + (2.0 * scale), 22.0, [self.n1, self.n2])
        self.assertAlmostEqual(r, 2.0 * scale)
        self.assertAlmostEqual(s, scale)
        self.assertAlmostEqual(z, 2.0)

    def test_reference_scale_calculation(self):
        """Verify sample standard deviation formula across multiple neighbors."""
        n_a = SpatialNeighbor("A", 10.0, 10.0, 0.33)
        n_b = SpatialNeighbor("B", 10.0, 20.0, 0.33)
        n_c = SpatialNeighbor("C", 10.0, 30.0, 0.33)
        # values = [10, 20, 30], mean = 20, var = ((10-20)^2 + 0 + (30-20)^2)/2 = 200/2 = 100 -> scale = 10.0
        scale = compute_reference_scale([n_a, n_b, n_c])
        self.assertAlmostEqual(scale, 10.0)

    def test_invalid_neighbor_exclusion_from_scale(self):
        """Verify None and non-finite neighbor values are excluded from scale."""
        n_valid1 = SpatialNeighbor("V1", 10.0, 10.0, 0.5)
        n_valid2 = SpatialNeighbor("V2", 10.0, 30.0, 0.5)
        n_invalid1 = SpatialNeighbor("INV1", 10.0, float("nan"), 0.5)
        n_invalid2 = SpatialNeighbor("INV2", 10.0, None, 0.5)
        # Only [10, 30] considered -> mean = 20, var = (100 + 100)/1 = 200 -> scale = sqrt(200) ~ 14.142
        scale = compute_reference_scale([n_valid1, n_valid2, n_invalid1, n_invalid2])
        self.assertAlmostEqual(scale, math.sqrt(200.0))

    def test_target_exclusion_from_neighbor_pool(self):
        """Verify only used_neighbors list is used for reference scale."""
        # used_neighbors contains only S1 and S2 (not target value 100.0)
        scale = compute_reference_scale([self.n1, self.n2])
        self.assertAlmostEqual(scale, math.sqrt(8.0))

    def test_zero_reference_scale_with_epsilon(self):
        """Verify identical neighbor values use variance epsilon guard."""
        n_same1 = SpatialNeighbor("S1", 10.0, 20.0, 0.5)
        n_same2 = SpatialNeighbor("S2", 10.0, 20.0, 0.5)
        # Matching target
        r0, z0, s0 = compute_spatial_residual(20.0, 20.0, [n_same1, n_same2], variance_epsilon=1e-6)
        self.assertEqual(r0, 0.0)
        self.assertEqual(z0, 0.0)
        self.assertEqual(s0, 0.0)

        # Deviating target
        r_diff, z_diff, s_diff = compute_spatial_residual(22.0, 20.0, [n_same1, n_same2], variance_epsilon=1e-6)
        self.assertAlmostEqual(r_diff, 2.0)
        self.assertEqual(s_diff, 0.0)
        self.assertAlmostEqual(z_diff, 2.0 / 1e-6)

    def test_deterministic_residual_repeatability(self):
        """Verify identical inputs produce bitwise identical residuals."""
        res1 = compute_spatial_residual(23.45, 21.12, [self.n1, self.n2])
        res2 = compute_spatial_residual(23.45, 21.12, [self.n1, self.n2])
        self.assertEqual(res1, res2)

    def test_clear_agreement_status(self):
        """Verify |z| <= 2.5 results in SpatialStatus.CONSISTENT."""
        self.assertEqual(classify_spatial_status(1.5, [self.n1, self.n2]), SpatialStatus.CONSISTENT)
        self.assertEqual(classify_spatial_status(-1.5, [self.n1, self.n2]), SpatialStatus.CONSISTENT)

    def test_clear_disagreement_status(self):
        """Verify |z| > 2.5 results in SpatialStatus.SUSPECT."""
        self.assertEqual(classify_spatial_status(3.0, [self.n1, self.n2]), SpatialStatus.SUSPECT)
        self.assertEqual(classify_spatial_status(-3.0, [self.n1, self.n2]), SpatialStatus.SUSPECT)

    def test_exact_threshold_boundary(self):
        """Verify exact boundary |z| = 2.5 is inclusive agreement (CONSISTENT)."""
        self.assertEqual(classify_spatial_status(2.5, [self.n1, self.n2], spatial_z_threshold=2.5), SpatialStatus.CONSISTENT)
        self.assertEqual(classify_spatial_status(-2.5, [self.n1, self.n2], spatial_z_threshold=2.5), SpatialStatus.CONSISTENT)

    def test_just_above_threshold_boundary(self):
        """Verify |z| = 2.500001 results in SUSPECT."""
        self.assertEqual(classify_spatial_status(2.500001, [self.n1, self.n2], spatial_z_threshold=2.5), SpatialStatus.SUSPECT)
        self.assertEqual(classify_spatial_status(-2.500001, [self.n1, self.n2], spatial_z_threshold=2.5), SpatialStatus.SUSPECT)

    def test_just_below_threshold_boundary(self):
        """Verify |z| = 2.499999 results in CONSISTENT."""
        self.assertEqual(classify_spatial_status(2.499999, [self.n1, self.n2], spatial_z_threshold=2.5), SpatialStatus.CONSISTENT)
        self.assertEqual(classify_spatial_status(-2.499999, [self.n1, self.n2], spatial_z_threshold=2.5), SpatialStatus.CONSISTENT)

    def test_insufficient_neighbors_zero(self):
        """Verify 0 neighbors results in INSUFFICIENT_NEIGHBORS."""
        r, z, s = compute_spatial_residual(20.0, 20.0, [])
        self.assertIsNone(r)
        self.assertIsNone(z)
        self.assertEqual(classify_spatial_status(z, []), SpatialStatus.INSUFFICIENT_NEIGHBORS)

    def test_insufficient_neighbors_one(self):
        """Verify 1 neighbor (< MIN_VALID_NEIGHBORS = 2) results in INSUFFICIENT_NEIGHBORS."""
        r, z, s = compute_spatial_residual(25.0, 20.0, [self.n1])
        self.assertAlmostEqual(r, 5.0)
        self.assertIsNone(z)
        self.assertEqual(classify_spatial_status(z, [self.n1]), SpatialStatus.INSUFFICIENT_NEIGHBORS)

    def test_invalid_target_status(self):
        """Verify None, NaN, and Inf targets result in INSUFFICIENT_NEIGHBORS."""
        for invalid_val in [None, float("nan"), float("inf"), float("-inf")]:
            r, z, s = compute_spatial_residual(invalid_val, 20.0, [self.n1, self.n2])
            self.assertIsNone(r)
            self.assertIsNone(z)
            self.assertEqual(classify_spatial_status(z, [self.n1, self.n2]), SpatialStatus.INSUFFICIENT_NEIGHBORS)

    def test_invalid_and_missing_neighbor_status(self):
        """Verify neighbor set with fewer than 2 valid entries results in INSUFFICIENT_NEIGHBORS."""
        n_inv = SpatialNeighbor("INV", 10.0, None, 0.5)
        r, z, s = compute_spatial_residual(25.0, 20.0, [self.n1, n_inv])
        self.assertAlmostEqual(r, 5.0)
        self.assertIsNone(z)
        self.assertEqual(classify_spatial_status(z, [self.n1, n_inv]), SpatialStatus.INSUFFICIENT_NEIGHBORS)


if __name__ == "__main__":
    unittest.main()
