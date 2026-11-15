#!/usr/bin/env python3
"""Summarize three Assignment 2 open-loop JTL runs without reporting p99.

Latency percentiles use the elapsed times of *successful* requests only, as the
brief requires ("Sort the elapsed times of the successful requests"). Failed
requests are counted as errors and reported separately. Throughput is reported
per second (the brief's unit) and per hour (the Assignment 1 unit).
"""

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


def nearest_rank(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(percentile * len(ordered) + 0.9999999999) - 1))
    return ordered[index]


def _successful_latencies(rows: list[dict[str, str]]) -> list[float]:
    return [float(row["elapsed"]) for row in rows if row.get("success") == "true"]


def summarize_run(rows: list[dict[str, str]], path: str, expected_sent: int, arrival_window_seconds: float) -> dict:
    completed = len(rows)
    if expected_sent < completed:
        raise ValueError(f"Expected sent count {expected_sent} is below {completed} JTL samples in {path}")
    successes = [row for row in rows if row.get("success") == "true"]
    failures = [row for row in rows if row.get("success") != "true"]
    latencies = _successful_latencies(rows)
    starts = [int(row["timeStamp"]) for row in rows]
    ends = [int(row["timeStamp"]) + int(row["elapsed"]) for row in rows]
    span = (max(ends) - min(starts)) / 1000 if rows else 0
    measurement_window = max(arrival_window_seconds, span)
    return {
        "jtl_file": path,
        "requests_sent": expected_sent,
        "completed": completed,
        "successful": len(successes),
        "errored": len(failures),
        "unfinished": expected_sent - completed,
        "error_codes": dict(Counter(row.get("responseCode", "") for row in failures)),
        "p50_ms": round(nearest_rank(latencies, 0.50), 1) if latencies else None,
        "p50_sample_count": len(latencies),
        "measurement_window_seconds": round(measurement_window, 3),
        "throughput_completed_per_second": round(completed / measurement_window, 5),
        "throughput_successful_per_second": round(len(successes) / measurement_window, 5),
        "throughput_completed_per_hour": round(completed / measurement_window * 3600, 3),
        "error_rate": round(len(failures) / expected_sent, 4),
    }


def summarize_service_log(path: str) -> dict:
    """Escalation fraction from one run's service-log segment.

    The denominator is successful cascade decisions (HTTP 201). Failed requests
    are counted separately because they have no completed decision. Duplicate
    ticket rows are reported so a recycled workload can be detected.
    """
    events = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            event = json.loads(line)
            if event.get("endpoint") == "/tickets" and event.get("cascade_mode") == "on":
                events.append(event)
    successful = [event for event in events if event.get("http_status") == 201]
    escalated = sum(event.get("escalated") is True for event in successful)
    rows = Counter(event.get("ticket_row_if_available") for event in events)
    return {
        "service_log": path,
        "cascade_ticket_events": len(events),
        "successful_decisions": len(successful),
        "failed_events": len(events) - len(successful),
        "escalated": escalated,
        "escalation_fraction": round(escalated / len(successful), 4) if successful else None,
        "duplicate_ticket_rows": sorted(row for row, count in rows.items() if count > 1 and row is not None),
    }


def build_speed_report(
    run_rows: list[list[dict[str, str]]],
    paths: list[str],
    expected_sent: int,
    arrival_window_seconds: float,
    service_logs: list[str] | None = None,
) -> dict:
    if len(run_rows) != 3 or len(paths) != 3:
        raise ValueError("Assignment 2 requires exactly three speed runs per configuration")
    runs = [
        summarize_run(rows, path, expected_sent, arrival_window_seconds)
        for rows, path in zip(run_rows, paths)
    ]
    pooled_latencies = [latency for rows in run_rows for latency in _successful_latencies(rows)]
    p50_values = [run["p50_ms"] for run in runs if run["p50_ms"] is not None]
    report = {
        "latency_basis": "successful requests only",
        "runs": runs,
        "p50_ms_across_runs": {
            "values": p50_values,
            "mean": round(sum(p50_values) / len(p50_values), 1) if p50_values else None,
            "min": min(p50_values) if p50_values else None,
            "max": max(p50_values) if p50_values else None,
            "spread": round(max(p50_values) - min(p50_values), 1) if p50_values else None,
        },
        "pooled_p95_ms": round(nearest_rank(pooled_latencies, 0.95), 1) if pooled_latencies else None,
        "pooled_sample_count": len(pooled_latencies),
    }
    if service_logs:
        if len(service_logs) != 3:
            raise ValueError("Supply exactly three service-log segments")
        log_reports = [summarize_service_log(path) for path in service_logs]
        total_decisions = sum(item["successful_decisions"] for item in log_reports)
        total_escalated = sum(item["escalated"] for item in log_reports)
        report["cascade"] = {
            "runs": log_reports,
            "total_successful_decisions": total_decisions,
            "total_escalated": total_escalated,
            "escalation_fraction": round(total_escalated / total_decisions, 4) if total_decisions else None,
        }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jtl", action="append", required=True, help="Repeat exactly three times")
    parser.add_argument("--service-log", action="append", help="Optional; repeat exactly three times")
    parser.add_argument("--expected-sent", type=int, required=True)
    parser.add_argument("--arrival-window-seconds", type=float, required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.expected_sent <= 0 or args.arrival_window_seconds <= 0:
        parser.error("--expected-sent and --arrival-window-seconds must be positive")

    run_rows = []
    for path in args.jtl:
        with open(path, encoding="utf-8") as handle:
            run_rows.append(list(csv.DictReader(handle)))
    report = build_speed_report(
        run_rows,
        args.jtl,
        args.expected_sent,
        args.arrival_window_seconds,
        args.service_log,
    )
    output = json.dumps(report, indent=2)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(output + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
