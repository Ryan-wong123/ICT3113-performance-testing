#!/usr/bin/env python3
"""Build the documented Step 3 workload model from explicit assumptions."""

import argparse
import json
import math
from pathlib import Path


def rounded(value: float) -> float:
    return round(value, 6)


def finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise argparse.ArgumentTypeError("value must be finite")
    return parsed


def rates(annual_count: float, multiplier: float, window_hours: int) -> dict[str, float]:
    per_hour = annual_count / 365 / 24 * multiplier
    return {
        "expected_per_window": rounded(per_hour * window_hours),
        "per_hour": rounded(per_hour),
        "per_minute": rounded(per_hour / 60),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="analysis/workload_model.json")
    parser.add_argument("--benchmark-complaints", type=int, default=3_187_900)
    parser.add_argument("--client-market-share", type=finite_float, default=0.01)
    parser.add_argument("--search-ratio", type=finite_float, default=0.20)
    parser.add_argument("--peak-start-hour", type=int, default=9)
    parser.add_argument("--peak-hours", type=int, default=8)
    parser.add_argument("--peak-multiplier", type=finite_float, default=2.0)
    args = parser.parse_args()

    if args.benchmark_complaints <= 0:
        raise ValueError("benchmark complaints must be positive")
    if not 0 < args.client_market_share <= 1:
        raise ValueError("client market share must be in (0, 1]")
    if args.search_ratio < 0:
        raise ValueError("search ratio must be non-negative")
    if not 0 <= args.peak_start_hour < 24:
        raise ValueError("peak start hour must be between 0 and 23")
    if not 0 < args.peak_hours < 24:
        raise ValueError("peak hours must be between 1 and 23")
    if args.peak_multiplier <= 0:
        raise ValueError("peak multiplier must be positive")

    off_peak_hours = 24 - args.peak_hours
    off_peak_multiplier = (24 - args.peak_hours * args.peak_multiplier) / off_peak_hours
    if off_peak_multiplier < 0:
        raise ValueError("peak profile implies a negative off-peak arrival rate")

    annual_submissions = args.benchmark_complaints * args.client_market_share
    annual_searches = annual_submissions * args.search_ratio
    peak_end_hour = (args.peak_start_hour + args.peak_hours) % 24
    peak_window = f"{args.peak_start_hour:02d}:00-{peak_end_hour:02d}:00 local time"

    periods = {}
    for name, multiplier, hours in (
        ("average", 1.0, 24),
        ("peak", args.peak_multiplier, args.peak_hours),
        ("off_peak", off_peak_multiplier, off_peak_hours),
    ):
        submission_rates = rates(annual_submissions, multiplier, hours)
        search_rates = rates(annual_searches, multiplier, hours)
        periods[name] = {
            "hours_per_day": hours,
            "multiplier": rounded(multiplier),
            "submissions": submission_rates,
            "searches": search_rates,
            "combined_per_hour": rounded(submission_rates["per_hour"] + search_rates["per_hour"]),
            "combined_per_minute": rounded(submission_rates["per_minute"] + search_rates["per_minute"]),
        }

    report = {
        "model_version": 1,
        "basis": {
            "source": "CFPB Consumer Response Annual Report 2024",
            "source_url": "https://files.consumerfinance.gov/f/documents/cfpb_cr-annual-report_2025-05.pdf",
            "benchmark_complaints": args.benchmark_complaints,
            "days_per_year": 365,
        },
        "assumptions": {
            "client_market_share": args.client_market_share,
            "searches_per_submission": args.search_ratio,
            "peak_window": peak_window,
            "peak_start_hour": args.peak_start_hour,
            "peak_hours_per_day": args.peak_hours,
            "peak_multiplier": args.peak_multiplier,
            "off_peak_hours_per_day": off_peak_hours,
            "off_peak_multiplier": rounded(off_peak_multiplier),
        },
        "expected_volume": {
            "submissions": {
                "per_year": rounded(annual_submissions),
                "per_month": rounded(annual_submissions / 12),
                "per_week": rounded(annual_submissions / (365 / 7)),
                "per_day": rounded(annual_submissions / 365),
            },
            "searches": {
                "per_year": rounded(annual_searches),
                "per_month": rounded(annual_searches / 12),
                "per_week": rounded(annual_searches / (365 / 7)),
                "per_day": rounded(annual_searches / 365),
            },
        },
        "expected_annual_submissions": rounded(annual_submissions),
        "expected_annual_searches": rounded(annual_searches),
        "periods": periods,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    serialized_report = json.dumps(report, indent=2, allow_nan=False)
    output.write_text(serialized_report + "\n", encoding="utf-8")
    print(serialized_report)


if __name__ == "__main__":
    main()
