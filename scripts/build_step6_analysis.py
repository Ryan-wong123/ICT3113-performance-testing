#!/usr/bin/env python3
"""Derive every Step 6 comparison figure from committed Step 1-5 evidence."""

import argparse
import csv
import glob
import json
import math
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from summarize_jtl import nearest_rank  # noqa: E402

MODELS = {
    "llama3.2:1b": "llama3.2_1b",
    "llama3.2:3b": "llama3.2_3b",
    "qwen2.5:7b": "qwen2.5_7b",
}

# Copied verbatim from the frozen predictions/prediction_record.md (Section 2 table).
PREDICTIONS = {
    "llama3.2:1b": {"accuracy": 0.72, "warm_latency_s": 1.3, "cold_start_s": 42.0, "passes_r3": False},
    "llama3.2:3b": {"accuracy": 0.83, "warm_latency_s": 2.8, "cold_start_s": 67.0, "passes_r3": False},
    "qwen2.5:7b": {"accuracy": 0.90, "warm_latency_s": 8.0, "cold_start_s": 150.0, "passes_r3": True},
}

R3_OVERALL = 0.85
R3_PER_CATEGORY = 0.70
R1_P95_LIMIT_MS = 10_000


def wilson_interval(successes: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        raise ValueError("n must be positive")
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def mcnemar_exact_p(b: int, c: int) -> float:
    """Two-sided exact binomial McNemar test on the discordant pair counts."""
    n = b + c
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2**n
    return min(1.0, 2 * tail)


def average_ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2
        i = j + 1
    return ranks


def pearson(a: list[float], b: list[float]) -> float:
    ma, mb = statistics.fmean(a), statistics.fmean(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    den = math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))
    return num / den


def spearman(a: list[float], b: list[float]) -> float:
    return pearson(average_ranks(a), average_ranks(b))


def word_count(text: str) -> int:
    return len(text.split())


def pct(value: float) -> float:
    return round(value * 100, 2)


def interval_pct(interval: tuple[float, float]) -> list[float]:
    return [pct(interval[0]), pct(interval[1])]


def load_csv(path: Path) -> list[dict[str, str]]:
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def accuracy_section(accuracy: dict, golden: dict[str, str]) -> dict:
    result = {}
    for model, data in accuracy.items():
        correct, n = data["correct"], data["ticket_count"]
        per_category = {}
        for category, stats in sorted(data["per_category_accuracy"].items()):
            interval = wilson_interval(stats["correct"], stats["support"])
            per_category[category] = {
                "correct": stats["correct"],
                "support": stats["support"],
                "accuracy_pct": pct(stats["accuracy"]),
                "wilson95_pct": interval_pct(interval),
                "below_r3_floor": stats["accuracy"] < R3_PER_CATEGORY,
                "floor_failure_statistically_clear": interval[1] < R3_PER_CATEGORY,
            }
        predicted_totals: dict[str, int] = {}
        for row in data["confusion_matrix"].values():
            for label, count in row.items():
                predicted_totals[label] = predicted_totals.get(label, 0) + count
        ranked = sorted(per_category.items(), key=lambda item: item[1]["accuracy_pct"])
        overall_interval = wilson_interval(correct, n)
        result[model] = {
            "correct": correct,
            "n": n,
            "overall_accuracy_pct": pct(correct / n),
            "wilson95_pct": interval_pct(overall_interval),
            "r3_overall_failure_statistically_clear": overall_interval[1] < R3_OVERALL,
            "output_contract_errors": data["errors"],
            "valid_but_wrong": n - correct - data["errors"],
            "predicted_label_totals": dict(sorted(predicted_totals.items(), key=lambda kv: -kv[1])),
            "categories_weakest_first": [name for name, _ in ranked],
            "per_category": per_category,
        }
    return result


def self_label_section(golden: dict[str, str], source: dict[str, str]) -> dict:
    agree = sum(1 for row, label in golden.items() if source[row] == label)
    per_category = {}
    for category in sorted(set(golden.values())):
        rows = [row for row, label in golden.items() if label == category]
        hits = sum(1 for row in rows if source[row] == category)
        per_category[category] = {"correct": hits, "support": len(rows), "accuracy_pct": pct(hits / len(rows))}
    return {
        "description": (
            "Consumer-selected source_label scored against the frozen golden labels after "
            "labelling was complete. The golden set was sampled using source_label as a "
            "stratification aid, so this is a same-sample comparison, not a population estimate."
        ),
        "correct": agree,
        "n": len(golden),
        "overall_accuracy_pct": pct(agree / len(golden)),
        "wilson95_pct": interval_pct(wilson_interval(agree, len(golden))),
        "per_category": per_category,
    }


def paired_section(predictions: dict[str, dict[str, str | None]], golden: dict[str, str], source: dict[str, str]) -> dict:
    result = {}
    for model, pred in predictions.items():
        model_only = sum(1 for r in golden if pred[r] == golden[r] and source[r] != golden[r])
        self_only = sum(1 for r in golden if pred[r] != golden[r] and source[r] == golden[r])
        agreed = [r for r in golden if pred[r] == source[r]]
        agreed_correct = sum(1 for r in agreed if pred[r] == golden[r])
        result[model] = {
            "model_correct_self_label_wrong": model_only,
            "model_wrong_self_label_correct": self_only,
            "mcnemar_exact_p": round(mcnemar_exact_p(model_only, self_only), 5),
            "agreement_gate": {
                "description": (
                    "Post-hoc, offline: auto-route only when the model's answer equals the "
                    "consumer-selected label; send every other ticket to a human router. Not "
                    "implemented or tested through the service."
                ),
                "auto_routed": len(agreed),
                "auto_routed_share_pct": pct(len(agreed) / len(golden)),
                "auto_routed_correct": agreed_correct,
                "auto_routed_accuracy_pct": pct(agreed_correct / len(agreed)) if agreed else None,
                "auto_routed_accuracy_wilson95_pct": interval_pct(wilson_interval(agreed_correct, len(agreed))) if agreed else None,
                "sent_to_human": len(golden) - len(agreed),
                "sent_to_human_share_pct": pct((len(golden) - len(agreed)) / len(golden)),
            },
        }
    return result


def stratum_weighted_section(
    predictions: dict[str, dict[str, str | None]],
    golden: dict[str, str],
    source: dict[str, str],
) -> dict:
    """Re-weight per-stratum accuracy by each source_label stratum's share of all 1,000 Team 8 rows."""
    population: dict[str, int] = {}
    for label in source.values():
        population[label] = population.get(label, 0) + 1
    total = sum(population.values())
    strata: dict[str, list[str]] = {}
    for row in golden:
        strata.setdefault(source[row], []).append(row)
    raters = {**predictions, "consumer_self_label": {row: source[row] for row in golden}}
    weighted = {}
    for name, pred in raters.items():
        estimate = sum(
            population[stratum] / total * sum(1 for r in rows if pred[r] == golden[r]) / len(rows)
            for stratum, rows in strata.items()
        )
        weighted[name] = pct(estimate)
    return {
        "label": (
            "Golden set = 25 tickets per source_label stratum. Re-weighting each stratum by its share of "
            "the 1,000 Team 8 rows corrects the stratum proportions only; how tickets were chosen within "
            "a stratum is not recorded, so this is not a guaranteed-unbiased population estimate."
        ),
        "golden_per_stratum": {s: len(rows) for s, rows in sorted(strata.items())},
        "population_per_stratum": dict(sorted(population.items())),
        "weighted_accuracy_pct": weighted,
    }


def workload_section(workload: dict, accuracy: dict, self_label: dict, paired: dict) -> dict:
    per_day = workload["expected_volume"]["submissions"]["per_day"]
    peak = workload["periods"]["peak"]["submissions"]
    error_rates = {model: 1 - data["overall_accuracy_pct"] / 100 for model, data in accuracy.items()}
    error_rates["consumer_self_label"] = 1 - self_label["overall_accuracy_pct"] / 100
    gate = paired["qwen2.5:7b"]["agreement_gate"]
    gate_auto_share = gate["auto_routed"] / self_label["n"]
    gate_error = 1 - gate["auto_routed_correct"] / gate["auto_routed"]
    return {
        "label": (
            "DERIVED ESTIMATE: measured golden-set error rates multiplied by the Step 3 modelled volume. "
            "Assumes the golden-set mix transfers to the client's real ticket mix, which the stratified "
            "sample does not guarantee."
        ),
        "submissions_per_day": per_day,
        "peak_submissions_per_hour": peak["per_hour"],
        "peak_mean_inter_arrival_minutes": round(60 / peak["per_hour"], 2),
        "misrouted_per_day_if_fully_automatic": {k: round(v * per_day, 1) for k, v in error_rates.items()},
        "qwen_agreement_gate_per_day": {
            "auto_routed": round(per_day * gate_auto_share, 1),
            "auto_routed_misrouted": round(per_day * gate_auto_share * gate_error, 1),
            "sent_to_human": round(per_day * (1 - gate_auto_share), 1),
        },
    }


def latency_prediction_section(accuracy: dict, golden_words: dict[str, int]) -> dict:
    result = {}
    base = accuracy["llama3.2:3b"]["warm_latency_seconds"]["mean_s"]
    base_pred = PREDICTIONS["llama3.2:3b"]["warm_latency_s"]
    for model, data in accuracy.items():
        warm = data["warm_latency_seconds"]
        ok = [r for r in data["raw_results"] if r["ok"]]
        words = [golden_words[str(r["row"])] for r in ok]
        lat = [r["latency_s"] for r in ok]
        short = [l for l, w in zip(lat, words) if w < 100]
        long = [l for l, w in zip(lat, words) if w >= 200]
        result[model] = {
            "predicted_warm_s": PREDICTIONS[model]["warm_latency_s"],
            "measured_mean_s": warm["mean_s"],
            "measured_p50_s": warm["p50_s"],
            "measured_p95_s": warm["p95_s"],
            "mean_over_predicted": round(warm["mean_s"] / PREDICTIONS[model]["warm_latency_s"], 2),
            "predicted_ratio_to_3b": round(PREDICTIONS[model]["warm_latency_s"] / base_pred, 3),
            "measured_mean_ratio_to_3b": round(warm["mean_s"] / base, 3),
            "spearman_words_vs_latency": round(spearman(words, lat), 3),
            "median_latency_under_100_words_s": round(statistics.median(short), 2),
            "median_latency_200_plus_words_s": round(statistics.median(long), 2),
            "n_under_100_words": len(short),
            "n_200_plus_words": len(long),
        }
    return {
        "environment": "Original i7-9750H environment (the hardware the prediction record was written for), sequential single-request accuracy run, Ollama 0.34.4.",
        "golden_set_mean_words": round(statistics.fmean(golden_words.values()), 2),
        "per_model": result,
    }


def cold_start_section(log_path: Path) -> dict:
    """First POST /tickets after each model's first switch in the append-only log."""
    seen: dict[str, dict] = {}
    previous_model = None
    with open(log_path, encoding="utf-8") as fh:
        for line in fh:
            entry = json.loads(line)
            if entry["endpoint"] != "/tickets" or entry["method"] != "POST":
                continue
            model = entry["model"]
            if model != previous_model and model not in seen:
                seen[model] = {
                    "timestamp": entry["timestamp"],
                    "ticket_row": entry["ticket_row_if_available"],
                    "server_latency_s": round(entry["latency_ms"] / 1000, 2),
                }
            previous_model = model
    return {
        "label": (
            "Single observation per model: the first logged POST /tickets after switching to that model "
            "(the start of each model's accuracy run). Ollama load_duration is not logged, so this is "
            "evidence of first-request cost, not a controlled cold-start measurement."
        ),
        "per_model": {
            model: {"predicted_cold_s": PREDICTIONS[model]["cold_start_s"], **seen[model]}
            for model in MODELS
            if model in seen
        },
    }


def remote_load_section(results_dir: Path) -> dict:
    pattern = re.compile(r"^(?P<label>.+?)_rate(?P<rate>[\d.]+)_run(?P<run>\d)_remote\.jtl$")
    pooled: dict[tuple[str, str], list[float]] = {}
    run_p95: dict[tuple[str, str], list[float]] = {}
    errors: dict[tuple[str, str], int] = {}
    for path in sorted(glob.glob(str(results_dir / "*_remote.jtl"))):
        match = pattern.match(Path(path).name)
        if not match:
            continue
        key = (match["label"], match["rate"])
        rows = load_csv(Path(path))
        elapsed = [float(r["elapsed"]) for r in rows]
        pooled.setdefault(key, []).extend(elapsed)
        run_p95.setdefault(key, []).append(nearest_rank(elapsed, 0.95))
        errors[key] = errors.get(key, 0) + sum(1 for r in rows if r["success"] != "true")
    label_to_model = {v: k for k, v in MODELS.items()}
    result: dict[str, dict] = {}
    for (label, rate), values in sorted(pooled.items(), key=lambda kv: (kv[0][0], float(kv[0][1]))):
        result.setdefault(label_to_model[label], {})[f"{rate}/min"] = {
            "runs": len(run_p95[(label, rate)]),
            "n": len(values),
            "errors": errors[(label, rate)],
            "pooled_p95_ms": nearest_rank(values, 0.95),
            "pooled_p99_ms": nearest_rank(values, 0.99),
            "max_ms": max(values),
            "worst_run_p95_ms": max(run_p95[(label, rate)]),
            "every_run_p95_below_r1": all(v < R1_P95_LIMIT_MS for v in run_p95[(label, rate)]),
        }
    return {"environment": "Final separate-machine environment: i9-14900HX Machine A, JMeter on Machine B.", "per_model": result}


def prediction_scorecard(accuracy: dict) -> dict:
    return {
        model: {
            "predicted_accuracy_pct": pct(PREDICTIONS[model]["accuracy"]),
            "measured_accuracy_pct": accuracy[model]["overall_accuracy_pct"],
            "error_points": round(accuracy[model]["overall_accuracy_pct"] - pct(PREDICTIONS[model]["accuracy"]), 2),
            "predicted_passes_r3": PREDICTIONS[model]["passes_r3"],
            "measured_passes_r3": False,
            "r3_direction_correct": PREDICTIONS[model]["passes_r3"] is False,
        }
        for model in MODELS
    }


def build(repo: Path) -> dict:
    golden_rows = load_csv(repo / "labelling/golden_test_set.csv")
    golden = {r["row"]: r["final_label"] for r in golden_rows}
    golden_words = {r["row"]: word_count(r["narrative"]) for r in golden_rows}
    source = {r["row"]: r["source_label"] for r in load_csv(repo / "labelling/team8_rows_8000_8999.csv")}
    accuracy_raw = {
        model: json.loads((repo / f"analysis/accuracy/{label}.json").read_text(encoding="utf-8"))
        for model, label in MODELS.items()
    }
    predictions = {
        model: {str(r["row"]): (r["category"] if r["ok"] else None) for r in data["raw_results"]}
        for model, data in accuracy_raw.items()
    }
    workload = json.loads((repo / "analysis/workload_model.json").read_text(encoding="utf-8"))

    accuracy = accuracy_section(accuracy_raw, golden)
    self_label = self_label_section(golden, source)
    paired = paired_section(predictions, golden, source)
    return {
        "generated_by": "scripts/build_step6_analysis.py",
        "inputs": [
            "analysis/accuracy/*.json",
            "labelling/golden_test_set.csv",
            "labelling/team8_rows_8000_8999.csv (source_label, used only after the golden set was frozen)",
            "analysis/workload_model.json",
            "logs/requests.jsonl",
            "jmeter/results/*_remote.jtl",
            "predictions/prediction_record.md (values copied into PREDICTIONS)",
        ],
        "requirements": {"r1_p95_limit_ms": R1_P95_LIMIT_MS, "r3_overall_pct": pct(R3_OVERALL), "r3_per_category_pct": pct(R3_PER_CATEGORY)},
        "accuracy": accuracy,
        "accuracy_prediction_scorecard": prediction_scorecard(accuracy),
        "consumer_self_label_baseline": self_label,
        "model_vs_self_label": paired,
        "stratum_weighted_accuracy": stratum_weighted_section(predictions, golden, source),
        "workload_implications": workload_section(workload, accuracy, self_label, paired),
        "latency_vs_prediction": latency_prediction_section(accuracy_raw, golden_words),
        "first_request_after_model_switch": cold_start_section(repo / "logs/requests.jsonl"),
        "remote_load_r1_evidence": remote_load_section(repo / "jmeter/results"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--output", default="analysis/step6_analysis.json")
    args = parser.parse_args()
    repo = Path(args.repo)
    report = build(repo)
    output = repo / args.output
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
