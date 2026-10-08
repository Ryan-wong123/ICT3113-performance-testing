#!/usr/bin/env python3
"""Summarize one JMeter JTL into latency, completion-throughput, and error metrics."""

import argparse
import csv
import json
from pathlib import Path


def nearest_rank(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(percentile * len(ordered) + 0.9999999999) - 1))
    return ordered[index]


def build_report(
    rows: list[dict[str, str]],
    jtl_path: str,
    arrival_window_seconds: float | None = None,
) -> dict:
    if not rows:
        raise ValueError(f"No samples found in {jtl_path}")

    latencies_ms = [float(row["elapsed"]) for row in rows]
    successes = [row for row in rows if row["success"] == "true"]
    failures = [row for row in rows if row["success"] != "true"]

    starts_ms = [int(row["timeStamp"]) for row in rows]
    ends_ms = [int(row["timeStamp"]) + int(row["elapsed"]) for row in rows]
    sample_wall_span_s = (max(ends_ms) - min(starts_ms)) / 1000.0

    # A sparse open-loop run may not emit its first sample at time zero.  Using
    # only first-sample to last-completion time would then overstate throughput.
    # When the configured arrival window is known, retain it as the minimum
    # measurement window; extend it when queued work drains after arrivals stop.
    measurement_window_s = max(sample_wall_span_s, arrival_window_seconds or 0.0)
    if measurement_window_s <= 0:
        raise ValueError(
            "Cannot calculate throughput from a zero-length sample span; "
            "supply --arrival-window-seconds"
        )
    completed_per_hour = len(rows) / measurement_window_s * 3600
    successful_per_hour = len(successes) / measurement_window_s * 3600

    error_codes: dict[str, int] = {}
    for row in failures:
        code = row.get("responseCode", "unknown")
        error_codes[code] = error_codes.get(code, 0) + 1

    report = {
        "jtl_file": jtl_path,
        "sample_count": len(rows),
        "success_count": len(successes),
        "error_count": len(failures),
        "error_rate": round(len(failures) / len(rows), 4),
        "error_codes": error_codes,
        "sample_wall_span_seconds": round(sample_wall_span_s, 2),
        "configured_arrival_window_seconds": arrival_window_seconds,
        "measurement_window_seconds": round(measurement_window_s, 2),
        "completed_throughput_per_hour": round(completed_per_hour, 2),
        "successful_throughput_per_hour": round(successful_per_hour, 2),
        # Backward-compatible alias. "Completed" is the preferred name because
        # it distinguishes completions from the offered arrival rate.
        "achieved_throughput_per_hour": round(completed_per_hour, 2),
        "latency_ms": {
            "min": round(min(latencies_ms), 1),
            "max": round(max(latencies_ms), 1),
            "mean": round(sum(latencies_ms) / len(latencies_ms), 1),
            "p50": round(nearest_rank(latencies_ms, 0.50), 1),
            "p95": round(nearest_rank(latencies_ms, 0.95), 1),
            "p99": round(nearest_rank(latencies_ms, 0.99), 1),
        },
    }
    if arrival_window_seconds is not None:
        report["offered_arrival_rate_per_hour"] = round(
            len(rows) / arrival_window_seconds * 3600,
            2,
        )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jtl_path")
    parser.add_argument("--output")
    parser.add_argument(
        "--arrival-window-seconds",
        type=float,
        help=(
            "Configured arrival window. When supplied, throughput uses the longer "
            "of this window and first-sample-to-last-completion time, so sparse runs "
            "are not overstated and queued drain time is retained."
        ),
    )
    args = parser.parse_args()

    if args.arrival_window_seconds is not None and args.arrival_window_seconds <= 0:
        parser.error("--arrival-window-seconds must be greater than zero")

    with open(args.jtl_path, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    report = build_report(rows, args.jtl_path, args.arrival_window_seconds)

    output = json.dumps(report, indent=2)
    print(output)
    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
