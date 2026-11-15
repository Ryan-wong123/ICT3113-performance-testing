#!/usr/bin/env python3
"""Copy one speed run's lines out of the append-only service log.

logs/requests.jsonl is never truncated. Record its line count after the
warm-up (before JMeter starts) and again after the run has drained, then copy
lines (before, after] into analysis/a2/speed/logs/<config>_run<n>.jsonl.
"""

import argparse
from pathlib import Path


def extract(log_path: str, after_line: int, through_line: int) -> list[str]:
    if after_line < 0 or through_line < after_line:
        raise ValueError("need 0 <= --after-line <= --through-line")
    lines = Path(log_path).read_text(encoding="utf-8").splitlines(keepends=True)
    if through_line > len(lines):
        raise ValueError(f"{log_path} has only {len(lines)} lines, not {through_line}")
    return lines[after_line:through_line]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", default="logs/requests.jsonl")
    parser.add_argument("--after-line", type=int, required=True, help="line count recorded before the run")
    parser.add_argument("--through-line", type=int, required=True, help="line count recorded after the run")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    segment = extract(args.log, args.after_line, args.through_line)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(segment), encoding="utf-8")
    print(f"Wrote {len(segment)} lines ({args.after_line + 1}-{args.through_line}) to {output}")


if __name__ == "__main__":
    main()
