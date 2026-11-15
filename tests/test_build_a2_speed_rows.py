import unittest

from scripts.build_a2_speed_rows import choose_rows


class Assignment2SpeedRowTests(unittest.TestCase):
    def test_rows_are_distinct_exclude_golden_and_have_required_roles(self):
        source = [
            {"row": str(8000 + index), "narrative": "x" * (100 + index * 10)}
            for index in range(60)
        ]
        excluded = {8001, 8002, 8003}
        rows = choose_rows(source, excluded, p50=300, p95=600)
        self.assertEqual(len(rows), 36)
        self.assertEqual(len({row["row"] for row in rows}), 36)
        self.assertFalse({row["row"] for row in rows} & excluded)
        self.assertEqual(sum(row["role"] == "timing" for row in rows), 3)
        self.assertEqual(sum(row["role"] == "warmup" for row in rows), 3)
        self.assertEqual(sum(row["role"] == "workload" for row in rows), 30)


if __name__ == "__main__":
    unittest.main()
