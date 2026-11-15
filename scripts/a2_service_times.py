#!/usr/bin/env python3
"""Per-request service time and offered load for the Assignment 2 speed runs.

The service serialises every Ollama call behind one lock, so requests are
processed one at a time. A request's service time is therefore
    request_end - max(request_start, previous request_end)
taken from its run's service-log segment, and the rest of its latency is time
spent waiting behind earlier requests. Comparing mean service time with the
mean offered gap between arrivals (arrival window / requests sent, from the
JTL) shows whether a
configuration could keep up with the offered rate (utilisation < 1) or built a
queue that grew for the whole run (utilisation >= 1).
"""

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

CONFIGS = ("qwen2.5_7b", "cascade_a", "cascade_b")


def _ts(value: str) -> float:
    return datetime.fromisoformat(value).timestamp()


def service_times(events: list[dict]) -> list[dict]:
    tickets = sorted(
        (e for e in events if e.get("endpoint") == "/tickets"),
        key=lambda e: _ts(e["request_end"]),
    )
    rows, previous_end = [], 0.0
    for event in tickets:
        start, end = _ts(event["request_start"]), _ts(event["request_end"])
        service = end - max(start, previous_end)
        rows.append(
            {
                "ticket_row": event.get("ticket_row_if_available"),
                "escalated": event.get("escalated"),
                "http_status": event.get("http_status"),
                "service_s": round(service, 3),
                "wait_s": round((end - start) - service, 3),
            }
        )
        previous_end = end
    return rows


def mean_arrival_gap(jtl_rows: list[dict], arrival_window_s: float) -> float:
    if not jtl_rows:
        raise ValueError("empty JTL")
    return arrival_window_s / len(jtl_rows)


def summarize(values: list[float]) -> dict:
    ordered = sorted(values)
    return {
        "mean": round(sum(ordered) / len(ordered), 3),
        "p50": ordered[(len(ordered) - 1) // 2],
        "max": ordered[-1],
    }


def build(root: Path, outlier_s: float, arrival_window_s: float) -> dict:
    report = {
        "method": __doc__.strip().splitlines()[0],
        "arrival_window_s": arrival_window_s,
        "outlier_threshold_s": outlier_s,
        "configs": {},
    }
    for config in CONFIGS:
        runs = []
        for run in (1, 2, 3):
            log = root / f"analysis/a2/speed/logs/{config}_run{run}.jsonl"
            jtl = root / f"jmeter/results/a2_{config}_run{run}.jtl"
            events = [json.loads(line) for line in log.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
            with jtl.open(encoding="utf-8-sig") as handle:
                jtl_rows = list(csv.DictReader(handle))
            rows = service_times(events)
            gap = mean_arrival_gap(jtl_rows, arrival_window_s)
            service = summarize([r["service_s"] for r in rows])
            runs.append(
                {
                    "run": run,
                    "service_log": str(log.relative_to(root)).replace("\\", "/"),
                    "jtl": str(jtl.relative_to(root)).replace("\\", "/"),
                    "tickets_in_log": len(rows),
                    "service_s": service,
                    "wait_s": summarize([r["wait_s"] for r in rows]),
                    "requests_sent": len(jtl_rows),
                    "mean_offered_gap_s": round(gap, 3),
                    "utilisation": round(service["mean"] / gap, 3),
                    "outliers": [r for r in rows if r["service_s"] >= outlier_s],
                }
            )
        report["configs"][config] = runs
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--outlier-seconds", type=float, default=30.0)
    parser.add_argument("--arrival-window-seconds", type=float, default=300.0)
    parser.add_argument("--output", default="analysis/a2/speed/service_times.json")
    args = parser.parse_args()
    report = build(Path(args.root), args.outlier_seconds, args.arrival_window_seconds)
    text = json.dumps(report, indent=2)
    Path(args.output).write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
