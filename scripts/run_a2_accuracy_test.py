#!/usr/bin/env python3
"""Run one Assignment 2 split through POST /tickets and preserve scored evidence."""

import argparse
import csv
import json
import time
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path


def load_split_tickets(golden_path: str, split_path: str, selected_split: str) -> list[dict]:
    with open(golden_path, encoding="utf-8") as handle:
        golden = {int(row["row"]): row for row in csv.DictReader(handle)}
    with open(split_path, encoding="utf-8") as handle:
        split_rows = list(csv.DictReader(handle))

    selected = []
    for split_row in split_rows:
        if split_row["split"] != selected_split:
            continue
        row_number = int(split_row["row"])
        if row_number not in golden:
            raise ValueError(f"Split row {row_number} is missing from the golden set")
        ticket = golden[row_number]
        if ticket["final_label"] != split_row["final_label"]:
            raise ValueError(f"Split label differs from the golden set for row {row_number}")
        selected.append(ticket)
    if not selected:
        raise ValueError(f"No rows found for split {selected_split!r}")
    return sorted(selected, key=lambda row: int(row["row"]))


def post_ticket(base_url: str, narrative: str, ticket_row: int, timeout: float) -> dict:
    payload = json.dumps({"narrative": narrative, "ticket_row": ticket_row}).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/tickets",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
            return {
                "ok": True,
                "category": body["category"],
                "latency_s": time.perf_counter() - start,
                "request_id": response.headers.get("X-Request-ID"),
            }
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return {
            "ok": False,
            "error": f"HTTP {exc.code}: {detail}",
            "latency_s": time.perf_counter() - start,
            "request_id": exc.headers.get("X-Request-ID"),
        }
    except (urllib.error.URLError, TimeoutError) as exc:
        return {"ok": False, "error": str(exc), "latency_s": time.perf_counter() - start, "request_id": None}


def load_request_events(path: str, request_ids: set[str]) -> dict[str, dict]:
    events = {}
    log_path = Path(path)
    if not log_path.exists():
        return events
    with log_path.open(encoding="utf-8") as handle:
        for line in handle:
            event = json.loads(line)
            request_id = event.get("request_id")
            if request_id in request_ids:
                events[request_id] = event
    return events


def nearest_rank(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(percentile * len(ordered) + 0.9999999999) - 1))
    return ordered[index]


def build_accuracy_report(rows: list[dict], model_label: str, selected_split: str) -> dict:
    if not rows:
        raise ValueError("Cannot score an empty result set")
    correct = sum(1 for row in rows if row.get("ok") and row.get("category") == row["true_label"])
    errors = sum(1 for row in rows if not row.get("ok"))
    per_category = defaultdict(lambda: {"support": 0, "correct": 0})
    confusion = defaultdict(lambda: defaultdict(int))
    for row in rows:
        true_label = row["true_label"]
        predicted = row.get("category") if row.get("ok") else "ERROR"
        per_category[true_label]["support"] += 1
        confusion[true_label][predicted] += 1
        if predicted == true_label:
            per_category[true_label]["correct"] += 1

    true_labels = sorted(per_category)
    matrix_labels = sorted(
        set(per_category)
        | {row["category"] for row in rows if row.get("ok") and row.get("category")}
    )
    category_report = {}
    for label in true_labels:
        support = per_category[label]["support"]
        category_correct = per_category[label]["correct"]
        category_report[label] = {
            "support": support,
            "correct": category_correct,
            "wrong": support - category_correct,
            "accuracy": round(category_correct / support, 4),
        }

    latencies = [row["latency_s"] for row in rows if row.get("ok")]
    latency_report = None
    if latencies:
        latency_report = {
            "count": len(latencies),
            "min_s": round(min(latencies), 3),
            "max_s": round(max(latencies), 3),
            "mean_s": round(sum(latencies) / len(latencies), 3),
            "p50_s": round(nearest_rank(latencies, 0.50), 3),
            "p95_s": round(nearest_rank(latencies, 0.95), 3),
        }

    logged = [row for row in rows if row.get("cascade_mode") == "on" and isinstance(row.get("escalated"), bool)]
    escalation_report = None
    if logged:
        groups = {}
        for escalated in (False, True):
            group = [row for row in logged if row["escalated"] is escalated]
            group_correct = sum(row.get("ok") and row.get("category") == row["true_label"] for row in group)
            groups["escalated" if escalated else "not_escalated"] = {
                "count": len(group),
                "correct": group_correct,
                "wrong": len(group) - group_correct,
                "accuracy": round(group_correct / len(group), 4) if group else None,
            }
        escalated_count = groups["escalated"]["count"]
        escalation_report = {
            "logged_count": len(logged),
            "escalated_count": escalated_count,
            "not_escalated_count": len(logged) - escalated_count,
            "escalation_fraction": round(escalated_count / len(logged), 4),
            **groups,
        }

    return {
        "assignment": 2,
        "configuration": model_label,
        "split": selected_split,
        "ticket_count": len(rows),
        "overall": {
            "correct": correct,
            "wrong": len(rows) - correct,
            "errors": errors,
            "accuracy": round(correct / len(rows), 4),
        },
        "per_category": category_report,
        "confusion_matrix": {
            true_label: {predicted: confusion[true_label].get(predicted, 0) for predicted in matrix_labels + ["ERROR"]}
            for true_label in true_labels
        },
        "latency_seconds": latency_report,
        "cascade": escalation_report,
        "raw_results": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--golden-set", default="labelling/golden_test_set.csv")
    parser.add_argument("--split-file", default="analysis/a2/golden_split.csv")
    parser.add_argument("--split", choices=("test", "tuning"), default="test")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--configuration", required=True)
    parser.add_argument("--output-dir", default="analysis/a2/accuracy")
    parser.add_argument("--request-log", default="logs/requests.jsonl")
    parser.add_argument("--expect-cascade", action="store_true")
    parser.add_argument("--timeout", type=float, default=300.0)
    args = parser.parse_args()

    tickets = load_split_tickets(args.golden_set, args.split_file, args.split)
    print(f"Loaded {len(tickets)} {args.split}-set tickets; sending each through POST /tickets")
    rows = []
    for index, ticket in enumerate(tickets, start=1):
        result = post_ticket(args.base_url, ticket["narrative"], int(ticket["row"]), args.timeout)
        row = {"row": int(ticket["row"]), "true_label": ticket["final_label"], **result}
        rows.append(row)
        print(f"[{index}/{len(tickets)}] row={row['row']} -> {row.get('category', row.get('error'))}")

    request_ids = {row["request_id"] for row in rows if row.get("request_id")}
    events = load_request_events(args.request_log, request_ids)
    cascade_fields = (
        "cascade_mode",
        "rule_setting",
        "small_model",
        "large_model",
        "small_category",
        "final_model",
        "escalated",
    )
    for row in rows:
        event = events.get(row.get("request_id"), {})
        row.update({field: event.get(field) for field in cascade_fields})
    if args.expect_cascade and any(row.get("cascade_mode") != "on" for row in rows):
        raise SystemExit("Expected cascade evidence, but one or more request-log events are missing or not cascade_mode=on")

    report = build_accuracy_report(rows, args.configuration, args.split)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_name = args.configuration.replace(":", "_").replace("/", "_")
    output_path = output_dir / f"{safe_name}.json"
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["overall"], indent=2))
    print(f"Written to {output_path}")


if __name__ == "__main__":
    main()
