#!/usr/bin/env python3
"""Summarize three Assignment 2 open-loop JTL runs without reporting p99."""

import argparse
import csv
import json
from pathlib import Path


def nearest_rank(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(percentile * len(ordered) + 0.9999999999) - 1))
    return ordered[index]


def summarize_run(rows: list[dict[str, str]], path: str, expected_sent: int, arrival_window_seconds: float) -> dict:
    completed = len(rows)
    if expected_sent < completed:
        raise ValueError(f"Expected sent count {expected_sent} is below {completed} JTL samples in {path}")
    successes = [row for row in rows if row.get("success") == "true"]
    failures = [row for row in rows if row.get("success") != "true"]
    latencies = [float(row["elapsed"]) for row in rows]
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
        "p50_ms": round(nearest_rank(latencies, 0.50), 1) if latencies else None,
        "measurement_window_seconds": round(measurement_window, 3),
        "throughput_completed_per_hour": round(completed / measurement_window * 3600, 3),
        "error_rate": round(len(failures) / expected_sent, 4),
    }


def summarize_service_log(path: str) -> dict:
    events = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            event = json.loads(line)
            if event.get("endpoint") == "/tickets" and event.get("cascade_mode") == "on":
                events.append(event)
    escalated = sum(event.get("escalated") is True for event in events)
    return {
        "service_log": path,
        "cascade_ticket_events": len(events),
        "escalated": escalated,
        "escalation_fraction": round(escalated / len(events), 4) if events else None,
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
    pooled_latencies = [float(row["elapsed"]) for rows in run_rows for row in rows]
    p50_values = [run["p50_ms"] for run in runs]
    report = {
        "runs": runs,
        "p50_ms_across_runs": {
            "values": p50_values,
            "mean": round(sum(p50_values) / len(p50_values), 1),
            "min": min(p50_values),
            "max": max(p50_values),
            "spread": round(max(p50_values) - min(p50_values), 1),
        },
        "pooled_p95_ms": round(nearest_rank(pooled_latencies, 0.95), 1),
        "pooled_sample_count": len(pooled_latencies),
    }
    if service_logs:
        if len(service_logs) != 3:
            raise ValueError("Supply exactly three service-log segments")
        log_reports = [summarize_service_log(path) for path in service_logs]
        total_events = sum(item["cascade_ticket_events"] for item in log_reports)
        total_escalated = sum(item["escalated"] for item in log_reports)
        report["cascade"] = {
            "runs": log_reports,
            "total_ticket_events": total_events,
            "total_escalated": total_escalated,
            "escalation_fraction": round(total_escalated / total_events, 4) if total_events else None,
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
    Path(args.output).write_text(output + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
