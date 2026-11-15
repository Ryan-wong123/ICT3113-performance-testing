import unittest

from scripts.run_a2_accuracy_test import build_accuracy_report


class Assignment2AccuracyTests(unittest.TestCase):
    def test_report_has_counts_confusion_and_escalation_groups(self):
        rows = [
            {
                "row": 8004,
                "true_label": "Mortgage",
                "ok": True,
                "category": "Mortgage",
                "latency_s": 1.0,
                "cascade_mode": "on",
                "escalated": False,
            },
            {
                "row": 8006,
                "true_label": "Mortgage",
                "ok": True,
                "category": "Credit card",
                "latency_s": 2.0,
                "cascade_mode": "on",
                "escalated": True,
            },
        ]
        report = build_accuracy_report(rows, "cascade_A", "test")
        self.assertEqual(report["overall"]["correct"], 1)
        self.assertEqual(report["overall"]["wrong"], 1)
        self.assertEqual(report["per_category"]["Mortgage"]["correct"], 1)
        self.assertEqual(report["per_category"]["Mortgage"]["wrong"], 1)
        self.assertEqual(report["confusion_matrix"]["Mortgage"]["Credit card"], 1)
        self.assertEqual(report["cascade"]["escalated_count"], 1)
        self.assertNotIn("p99_s", report["latency_seconds"])


if __name__ == "__main__":
    unittest.main()
