import json
import tempfile
import unittest
from pathlib import Path

from scripts.extract_a2_log_segment import extract
from scripts.summarize_a2_speed import build_speed_report, summarize_service_log


def sample(timestamp, elapsed, success="true", code="201"):
    return {"timeStamp": str(timestamp), "elapsed": str(elapsed), "success": success, "responseCode": code}


class Assignment2SpeedTests(unittest.TestCase):
    def test_three_run_summary_reports_unfinished_spread_and_pooled_p95(self):
        rows = [
            [sample(1000, 100), sample(2000, 200)],
            [sample(1000, 300), sample(2000, 400, "false", "502")],
            [sample(1000, 500)],
        ]
        report = build_speed_report(rows, ["a.jtl", "b.jtl", "c.jtl"], 2, 10)
        self.assertEqual(report["runs"][2]["unfinished"], 1)
        self.assertEqual(report["runs"][1]["errored"], 1)
        self.assertEqual(report["runs"][1]["error_codes"], {"502": 1})
        self.assertEqual(report["p50_ms_across_runs"]["values"], [100.0, 300.0, 500.0])
        self.assertEqual(report["p50_ms_across_runs"]["spread"], 400.0)
        self.assertEqual(report["pooled_p95_ms"], 500.0)
        self.assertEqual(report["pooled_sample_count"], 4)
        self.assertNotIn("p99", report)
        self.assertAlmostEqual(report["runs"][0]["throughput_completed_per_second"], 0.2)

    def test_failed_requests_are_excluded_from_latency_percentiles(self):
        slow_failure = sample(1000, 300000, "false", "Non HTTP response code: java.net.SocketTimeoutException")
        rows = [[sample(1000, 100), slow_failure], [sample(1000, 200)], [sample(1000, 300)]]
        report = build_speed_report(rows, ["a", "b", "c"], 2, 10)
        self.assertEqual(report["runs"][0]["p50_ms"], 100.0)
        self.assertEqual(report["pooled_p95_ms"], 300.0)

    def test_service_log_escalation_uses_successful_decisions_and_flags_duplicates(self):
        events = [
            {"endpoint": "/tickets", "cascade_mode": "on", "http_status": 201, "escalated": True, "ticket_row_if_available": 1},
            {"endpoint": "/tickets", "cascade_mode": "on", "http_status": 201, "escalated": False, "ticket_row_if_available": 2},
            {"endpoint": "/tickets", "cascade_mode": "on", "http_status": 502, "escalated": True, "ticket_row_if_available": 1},
            {"endpoint": "/stats", "cascade_mode": "on"},
        ]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "seg.jsonl"
            path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
            result = summarize_service_log(str(path))
        self.assertEqual(result["successful_decisions"], 2)
        self.assertEqual(result["failed_events"], 1)
        self.assertEqual(result["escalation_fraction"], 0.5)
        self.assertEqual(result["duplicate_ticket_rows"], [1])

    def test_log_segment_is_the_half_open_line_range(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "log.jsonl"
            path.write_text("a\nb\nc\nd\n", encoding="utf-8")
            self.assertEqual(extract(str(path), 1, 3), ["b\n", "c\n"])
            with self.assertRaises(ValueError):
                extract(str(path), 2, 9)


if __name__ == "__main__":
    unittest.main()
