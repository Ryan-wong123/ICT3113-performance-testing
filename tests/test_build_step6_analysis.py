import unittest

from scripts.build_step6_analysis import (
    average_ranks,
    mcnemar_exact_p,
    spearman,
    wilson_interval,
)


class Step6StatisticsTests(unittest.TestCase):
    def test_wilson_interval_matches_reference_value(self) -> None:
        low, high = wilson_interval(138, 175)
        self.assertAlmostEqual(low, 0.7222, places=4)
        self.assertAlmostEqual(high, 0.8425, places=4)

    def test_wilson_interval_stays_inside_unit_range(self) -> None:
        low, high = wilson_interval(0, 23)
        self.assertEqual(low, 0.0)
        self.assertLess(high, 0.15)

    def test_mcnemar_exact_is_two_sided_and_symmetric(self) -> None:
        self.assertAlmostEqual(mcnemar_exact_p(19, 30), 0.15241, places=5)
        self.assertEqual(mcnemar_exact_p(19, 30), mcnemar_exact_p(30, 19))
        self.assertEqual(mcnemar_exact_p(0, 0), 1.0)

    def test_average_ranks_share_ties(self) -> None:
        self.assertEqual(average_ranks([10, 20, 20, 30]), [0.0, 1.5, 1.5, 3.0])

    def test_spearman_is_one_for_monotonic_nonlinear_data(self) -> None:
        self.assertAlmostEqual(spearman([1, 2, 3, 4], [1, 8, 27, 64]), 1.0)


if __name__ == "__main__":
    unittest.main()
