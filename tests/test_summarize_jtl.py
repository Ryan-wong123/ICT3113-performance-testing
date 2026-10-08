import unittest

from scripts.summarize_jtl import build_report


class SummarizeJtlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rows = [
            {
                "timeStamp": "1000",
                "elapsed": "100",
                "success": "true",
                "responseCode": "201",
            },
            {
                "timeStamp": "2000",
                "elapsed": "4000",
                "success": "false",
                "responseCode": "502",
            },
        ]

    def test_completion_span_includes_elapsed_time(self) -> None:
        report = build_report(self.rows, "example.jtl")

        self.assertEqual(report["sample_wall_span_seconds"], 5.0)
        self.assertEqual(report["completed_throughput_per_hour"], 1440.0)
        self.assertEqual(report["successful_throughput_per_hour"], 720.0)

    def test_configured_window_prevents_sparse_run_overstatement(self) -> None:
        report = build_report(self.rows, "example.jtl", arrival_window_seconds=10.0)

        self.assertEqual(report["measurement_window_seconds"], 10.0)
        self.assertEqual(report["offered_arrival_rate_per_hour"], 720.0)
        self.assertEqual(report["completed_throughput_per_hour"], 720.0)
        self.assertEqual(report["successful_throughput_per_hour"], 360.0)


if __name__ == "__main__":
    unittest.main()
