#!/usr/bin/env python3
"""Calculate reproducible character and word-length statistics for a ticket CSV."""

import argparse
import csv
import json
from pathlib import Path
import re
from statistics import mean

WORD_PATTERN = re.compile(r"\b[\w]+(?:['-][\w]+)*\b", re.UNICODE)


def nearest_rank(values: list[int], percentile: float) -> int:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int((percentile * len(ordered) + 0.9999999999)) - 1))
    return ordered[index]


def summary(values: list[int]) -> dict[str, float | int]:
    return {
        "min": min(values),
        "max": max(values),
        "mean": round(mean(values), 3),
        "p50": nearest_rank(values, 0.50),
        "p95": nearest_rank(values, 0.95),
        "p99": nearest_rank(values, 0.99),
    }


def distribution(values: list[int], upper_bounds: tuple[int, ...]) -> list[dict[str, float | int | str]]:
    """Return inclusive histogram buckets with percentages of the full sample."""
    buckets: list[dict[str, float | int | str]] = []
    lower = 0
    for upper in upper_bounds:
        count = sum(lower <= value <= upper for value in values)
        buckets.append(
            {
                "range": f"{lower}-{upper}",
                "count": count,
                "percent": round(count * 100 / len(values), 1),
            }
        )
        lower = upper + 1
    count = sum(value >= lower for value in values)
    buckets.append(
        {
            "range": f"{lower}+",
            "count": count,
            "percent": round(count * 100 / len(values), 1),
        }
    )
    return buckets


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="labelling/team8_rows_8000_8999.csv")
    parser.add_argument("--output", default="analysis/ticket_length_statistics.json")
    args = parser.parse_args()

    with Path(args.input).open(encoding="utf-8-sig", newline="") as source:
        narratives = [row["narrative"] for row in csv.DictReader(source)]
    if not narratives:
        raise ValueError("No ticket narratives found")
    character_counts = [len(narrative) for narrative in narratives]
    word_counts = [len(WORD_PATTERN.findall(narrative)) for narrative in narratives]
    report = {
        "input": args.input,
        "ticket_count": len(narratives),
        "percentile_method": "nearest-rank",
        "character_count": {
            **summary(character_counts),
            "distribution": distribution(character_counts, (499, 999, 1499, 1999)),
        },
        "word_count": {
            **summary(word_counts),
            "distribution": distribution(word_counts, (99, 199, 299, 399)),
        },
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
