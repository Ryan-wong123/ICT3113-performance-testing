import unittest

from scripts.summarize_a2_speed import build_speed_report


def sample(timestamp, elapsed, success="true"):
    return {"timeStamp": str(timestamp), "elapsed": str(elapsed), "success": success}


class Assignment2SpeedTests(unittest.TestCase):
    def test_three_run_summary_reports_unfinished_spread_and_pooled_p95(self):
        rows = [
            [sample(1000, 100), sample(2000, 200)],
            [sample(1000, 300), sample(2000, 400, "false")],
            [sample(1000, 500)],
        ]
        report = build_speed_report(rows, ["a.jtl", "b.jtl", "c.jtl"], 2, 10)
        self.assertEqual(report["runs"][2]["unfinished"], 1)
        self.assertEqual(report["runs"][1]["errored"], 1)
        self.assertEqual(report["p50_ms_across_runs"]["values"], [100.0, 300.0, 500.0])
        self.assertEqual(report["p50_ms_across_runs"]["spread"], 400.0)
        self.assertEqual(report["pooled_p95_ms"], 500.0)
        self.assertEqual(report["pooled_sample_count"], 5)
        self.assertNotIn("p99", report)


if __name__ == "__main__":
    unittest.main()
