#!/usr/bin/env python3
"""Combine per-model accuracy JSON reports (from run_accuracy_test.py) into one summary."""

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model_labels", nargs="+", help="e.g. llama3.2:1b llama3.2:3b qwen2.5:7b")
    parser.add_argument("--input-dir", default="analysis/accuracy")
    parser.add_argument("--requirement-overall", type=float, default=0.85)
    parser.add_argument("--requirement-per-category", type=float, default=0.70)
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    print(f"{'Model':<16} {'Overall':>8} {'R3 overall (>=85%)':>20} {'Weakest category':>28} {'Weakest acc':>12} {'R3 per-cat (>=70%)':>20}")
    for label in args.model_labels:
        safe = label.replace(":", "_").replace("/", "_")
        path = input_dir / f"{safe}.json"
        report = json.loads(path.read_text(encoding="utf-8"))
        overall = report["overall_accuracy"]
        per_cat = report["per_category_accuracy"]
        weakest_label, weakest_stats = min(per_cat.items(), key=lambda kv: kv[1]["accuracy"] if kv[1]["accuracy"] is not None else 1)
        weakest_acc = weakest_stats["accuracy"]
        meets_overall = "PASS" if overall >= args.requirement_overall else "FAIL"
        meets_per_cat = "PASS" if weakest_acc >= args.requirement_per_category else "FAIL"
        print(f"{label:<16} {overall:>8.4f} {meets_overall:>20} {weakest_label:>28} {weakest_acc:>12.4f} {meets_per_cat:>20}")


if __name__ == "__main__":
    main()
