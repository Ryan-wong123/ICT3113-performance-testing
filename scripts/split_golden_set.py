#!/usr/bin/env python3
"""Split the frozen golden set into the Assignment 2 tuning and test sets.

Rule (Assignment 2 brief, Step 1; team reading recorded in docs/a2_accuracy_limits.md):
a ticket whose `row` value is odd is in the tuning set, and one whose `row` value
is even is in the test set. The split depends only on the row number, so it is
deterministic and independent of input order.

No model is run and the golden labels are not changed.
"""

import argparse
import csv
import sys
from pathlib import Path

TEAM_ROW_MIN = 8000
TEAM_ROW_MAX = 8999
TUNING = "tuning"
TEST = "test"
FIELDNAMES = ["row", "final_label", "split"]

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "labelling" / "golden_test_set.csv"
DEFAULT_OUTPUT = ROOT / "analysis" / "a2" / "golden_split.csv"


def split_for_row(row: int) -> str:
    """Odd row number -> tuning set; even row number -> test set."""
    return TUNING if row % 2 == 1 else TEST


def load_golden(path: Path) -> list[tuple[int, str]]:
    seen: set[int] = set()
    tickets: list[tuple[int, str]] = []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = {"row", "final_label"} - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path} is missing column(s): {', '.join(sorted(missing))}")
        for record in reader:
            row = int(record["row"])
            label = record["final_label"].strip()
            if not TEAM_ROW_MIN <= row <= TEAM_ROW_MAX:
                raise ValueError(f"row {row} is outside Team 8's range {TEAM_ROW_MIN}-{TEAM_ROW_MAX}")
            if row in seen:
                raise ValueError(f"duplicate row {row}")
            if not label:
                raise ValueError(f"row {row} has no final_label")
            seen.add(row)
            tickets.append((row, label))
    if not tickets:
        raise ValueError(f"{path} contains no tickets")
    return sorted(tickets)


def build_split(tickets: list[tuple[int, str]]) -> list[dict[str, str | int]]:
    return [{"row": row, "final_label": label, "split": split_for_row(row)} for row, label in tickets]


def render(rows: list[dict[str, str | int]]) -> str:
    import io

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=FIELDNAMES, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def summarise(rows: list[dict[str, str | int]]) -> str:
    counts = {TUNING: 0, TEST: 0}
    per_category: dict[str, dict[str, int]] = {}
    for record in rows:
        counts[str(record["split"])] += 1
        category = per_category.setdefault(str(record["final_label"]), {TUNING: 0, TEST: 0})
        category[str(record["split"])] += 1
    lines = [f"tickets={len(rows)} tuning={counts[TUNING]} test={counts[TEST]}"]
    for label in sorted(per_category):
        lines.append(f"  {label}: tuning={per_category[label][TUNING]} test={per_category[label][TEST]}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="do not write; exit 1 if the existing output differs from a fresh split",
    )
    args = parser.parse_args()

    rows = build_split(load_golden(args.input))
    text = render(rows)

    if args.check:
        if not args.output.exists() or args.output.read_text(encoding="utf-8") != text:
            print(f"MISMATCH: {args.output} does not match a fresh split of {args.input}", file=sys.stderr)
            return 1
        print(f"OK: {args.output} matches a fresh split")
        print(summarise(rows))
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8", newline="")
    print(f"wrote {args.output}")
    print(summarise(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
