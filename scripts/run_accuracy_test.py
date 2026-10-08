#!/usr/bin/env python3
"""Send every golden-set ticket through POST /tickets and score the result.

Never bypasses the service: every narrative goes through the real HTTP
endpoint, one at a time, exactly as the brief requires for accuracy testing.
"""

import argparse
import csv
import json
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path


def load_golden_set(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


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
            return {"ok": True, "category": body["category"], "model": body["model"], "latency_s": time.perf_counter() - start}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return {"ok": False, "error": f"HTTP {exc.code}: {detail}", "latency_s": time.perf_counter() - start}
    except (urllib.error.URLError, TimeoutError) as exc:
        return {"ok": False, "error": str(exc), "latency_s": time.perf_counter() - start}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--golden-set", default="labelling/golden_test_set.csv")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--model-label", required=True, help="Candidate model tag, for the output filename and report")
    parser.add_argument("--output-dir", default="analysis/accuracy")
    parser.add_argument("--timeout", type=float, default=300.0)
    args = parser.parse_args()

    tickets = load_golden_set(args.golden_set)
    print(f"Loaded {len(tickets)} golden-set tickets. Sending each through {args.base_url}/tickets ...")

    rows = []
    for i, ticket in enumerate(tickets, start=1):
        result = post_ticket(args.base_url, ticket["narrative"], int(ticket["row"]), args.timeout)
        row = {
            "row": int(ticket["row"]),
            "true_label": ticket["final_label"],
            **result,
        }
        rows.append(row)
        status = row.get("category", row.get("error"))
        print(f"[{i}/{len(tickets)}] row={row['row']} true={row['true_label']!r} -> {status!r} ({row['latency_s']:.2f}s)")

    correct = sum(1 for r in rows if r.get("ok") and r["category"] == r["true_label"])
    errors = sum(1 for r in rows if not r.get("ok"))
    overall_accuracy = correct / len(rows)

    per_category = defaultdict(lambda: {"support": 0, "correct": 0})
    confusion = defaultdict(lambda: defaultdict(int))
    for r in rows:
        true_label = r["true_label"]
        per_category[true_label]["support"] += 1
        predicted = r["category"] if r.get("ok") else "ERROR"
        confusion[true_label][predicted] += 1
        if r.get("ok") and r["category"] == true_label:
            per_category[true_label]["correct"] += 1

    per_category_report = {
        label: {
            "support": stats["support"],
            "correct": stats["correct"],
            "accuracy": round(stats["correct"] / stats["support"], 4) if stats["support"] else None,
        }
        for label, stats in sorted(per_category.items())
    }

    labels = sorted(per_category.keys())
    confusion_report = {
        true_label: {predicted: confusion[true_label].get(predicted, 0) for predicted in labels + ["ERROR"]}
        for true_label in labels
    }

    latencies = sorted(r["latency_s"] for r in rows if r.get("ok"))
    latency_summary = None
    if latencies:
        def pct(p: float) -> float:
            index = max(0, min(len(latencies) - 1, int(p * len(latencies) + 0.9999999999) - 1))
            return round(latencies[index], 3)

        latency_summary = {
            "count": len(latencies),
            "min_s": round(latencies[0], 3),
            "max_s": round(latencies[-1], 3),
            "mean_s": round(sum(latencies) / len(latencies), 3),
            "p50_s": pct(0.50),
            "p95_s": pct(0.95),
            "p99_s": pct(0.99),
        }

    report = {
        "model": args.model_label,
        "golden_set": args.golden_set,
        "ticket_count": len(rows),
        "overall_accuracy": round(overall_accuracy, 4),
        "correct": correct,
        "errors": errors,
        "per_category_accuracy": per_category_report,
        "confusion_matrix": confusion_report,
        "warm_latency_seconds": latency_summary,
        "raw_results": rows,
    }

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_label = args.model_label.replace(":", "_").replace("/", "_")
    output_path = output_dir / f"{safe_label}.json"
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print()
    print(f"=== {args.model_label} ===")
    print(f"Overall accuracy: {overall_accuracy:.4f} ({correct}/{len(rows)}), errors: {errors}")
    for label, stats in per_category_report.items():
        print(f"  {label}: {stats['accuracy']} ({stats['correct']}/{stats['support']})")
    if latency_summary:
        print(f"Latency (successful requests): p50={latency_summary['p50_s']}s p95={latency_summary['p95_s']}s p99={latency_summary['p99_s']}s")
    print(f"Written to {output_path}")


if __name__ == "__main__":
    main()
