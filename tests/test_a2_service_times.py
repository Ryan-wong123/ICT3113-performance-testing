import unittest

from scripts.a2_service_times import mean_arrival_gap, service_times


def event(row, start, end, status=201, escalated=None):
    return {
        "endpoint": "/tickets",
        "ticket_row_if_available": row,
        "request_start": f"2026-11-15T00:00:{start:06.3f}+00:00",
        "request_end": f"2026-11-15T00:00:{end:06.3f}+00:00",
        "http_status": status,
        "escalated": escalated,
    }


class ServiceTimeTests(unittest.TestCase):
    def test_queued_request_service_starts_when_previous_finishes(self):
        rows = service_times([
            event(1, 0.0, 4.0),
            event(2, 1.0, 9.0),   # waited 3 s behind row 1, then 5 s of service
            event(3, 20.0, 22.0),  # idle server: no wait
            {"endpoint": "/stats"},
        ])
        self.assertEqual([r["service_s"] for r in rows], [4.0, 5.0, 2.0])
        self.assertEqual([r["wait_s"] for r in rows], [0.0, 3.0, 0.0])

    def test_offered_gap_is_window_over_requests_sent(self):
        self.assertAlmostEqual(mean_arrival_gap([{}] * 56, 300.0), 300 / 56)


if __name__ == "__main__":
    unittest.main()
