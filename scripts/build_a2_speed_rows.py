#!/usr/bin/env python3
"""Build the fixed A2 timing, warm-up, and speed-workload row list."""

import argparse
import csv
import io
import json
from pathlib import Path


FIELDS = ("sequence", "role", "length_band", "row", "character_count", "narrative")


def choose_rows(source_rows: list[dict], excluded_rows: set[int], p50: int, p95: int) -> list[dict]:
    candidates = []
    for source in source_rows:
        row_number = int(source["row"])
        if row_number not in excluded_rows:
            candidates.append(
                {
                    "row": row_number,
                    "narrative": source["narrative"],
                    "character_count": len(source["narrative"]),
                }
            )
    typical = sorted(candidates, key=lambda row: (abs(row["character_count"] - p50), row["row"]))
    long = sorted(candidates, key=lambda row: (abs(row["character_count"] - p95), row["row"]))
    used = set()

    def take(pool: list[dict], count: int) -> list[dict]:
        selected = []
        for row in pool:
            if row["row"] in used:
                continue
            used.add(row["row"])
            selected.append(row)
            if len(selected) == count:
                return selected
        raise ValueError("Not enough distinct non-golden rows to build the A2 workload")

    groups = [
        ("timing", "typical_p50", take(typical, 3)),
        ("warmup", "typical_p50", take(typical, 2)),
        ("warmup", "long_p95", take(long, 1)),
    ]
    typical_workload = take(typical, 15)
    long_workload = take(long, 15)
    interleaved = [item for pair in zip(typical_workload, long_workload) for item in pair]
    groups.append(("workload", "mixed", interleaved))

    output = []
    for role, band, rows in groups:
        for row in rows:
            actual_band = band
            if role == "workload":
                actual_band = "typical_p50" if row in typical_workload else "long_p95"
            output.append(
                {
                    "sequence": len(output) + 1,
                    "role": role,
                    "length_band": actual_band,
                    **row,
                }
            )
    return output


def render_csv(rows: list[dict]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="jmeter/test_plans/load_test_narratives.csv")
    parser.add_argument("--golden-set", default="labelling/golden_test_set.csv")
    parser.add_argument("--length-stats", default="analysis/ticket_length_statistics.json")
    parser.add_argument("--output", default="analysis/a2/speed_test_rows.csv")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    with open(args.source, encoding="utf-8") as handle:
        source_rows = list(csv.DictReader(handle))
    with open(args.golden_set, encoding="utf-8") as handle:
        excluded = {int(row["row"]) for row in csv.DictReader(handle)}
    stats = json.loads(Path(args.length_stats).read_text(encoding="utf-8"))
    rows = choose_rows(
        source_rows,
        excluded,
        int(stats["character_count"]["p50"]),
        int(stats["character_count"]["p95"]),
    )
    rendered = render_csv(rows)
    output = Path(args.output)
    if args.check:
        if not output.exists() or output.read_text(encoding="utf-8") != rendered:
            raise SystemExit(f"{output} is missing or stale; rerun without --check")
        print(f"Verified {output}: 3 timing, 3 warm-up, and 30 workload rows")
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    print(f"Wrote {output}: 3 timing, 3 warm-up, and 30 workload rows")


if __name__ == "__main__":
    main()
