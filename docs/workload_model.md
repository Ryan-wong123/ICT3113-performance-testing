# Step 3: Client Workload Model

## Purpose and scope

This document defines the expected workload for the ticket-classification service before performance testing. It separates public evidence from modelling assumptions so later JMeter plans can reproduce the rates without presenting estimates as observed production traffic.

The model covers:

- `POST /tickets` submission traffic;
- `GET /search` analyst traffic;
- the full Team 8 narrative-length distribution; and
- average, peak, and off-peak arrival rates.

Health checks and `GET /stats` are excluded from the client workload because they are operational traffic, not complaint-processing demand. They should be tested separately with a low fixed cadence.

## Evidence base

The CFPB reports receiving approximately **3,187,900 complaints during 2024**.[1] It sent approximately 2,829,400, or 89%, to companies for review and response.[1] The same report says 98% were submitted through the CFPB website, which supports modelling intake as predominantly digital rather than call-centre-only traffic.[1]

The CFPB cautions that its complaint database is not a statistical sample and is not necessarily representative of every consumer's experience.[2] It also says complaint volume should be interpreted with company size or market share.[2] The public total is therefore used only as a benchmark; the client share and daily profile below are explicit scenario assumptions, not claims about a real unnamed company.

## Assumptions

| ID | Assumption | Value | Reason |
|---|---|---:|---|
| A1 | Client share of the CFPB annual benchmark | 1% | Represents a medium-to-large hypothetical provider while obeying the CFPB's instruction to contextualise volume by market share.[2] |
| A2 | Intake operates | 24 hours/day, 365 days/year | Digital submission traffic can arrive outside office hours. |
| A3 | Peak window | 09:00-17:00 local time, every day | Eight-hour analyst/customer activity window; no source data identifies the client's actual hourly profile. |
| A4 | Peak submission multiplier | 2.0 times the 24-hour average | Conservative planning assumption for daytime concentration. |
| A5 | Off-peak multiplier | 0.5 times the 24-hour average | Derived so eight peak hours and sixteen off-peak hours preserve the daily total. |
| A6 | Search-to-submission ratio | 0.20 | Assumes analysts perform 20 narrative searches for every 100 submitted tickets. This must be replaced when production telemetry exists. |
| A7 | Search profile | Same peak/off-peak multipliers as submissions | Analyst activity is assumed to follow the same daily shape for this baseline model. |
| A8 | Arrival process for later open-loop tests | Independent arrivals at the stated mean rate | The baseline specifies rates, not a fixed concurrency level. A Poisson timer is suitable for the eventual JMeter workload. |

## Calculations

### Annual client volume

```text
2024 CFPB benchmark                 = 3,187,900 complaints
Assumed client share                = 1% = 0.01
Expected annual ticket submissions  = 3,187,900 × 0.01
                                    = 31,879 tickets/year
```

This corresponds to 2,656.583333 tickets per average month, 611.378082 per average seven-day week, and 87.339726 per day. Fractional values are expected rates, not possible observed counts.

### Average submission rate

```text
Per day    = 31,879 ÷ 365       = 87.339726 tickets/day
Per hour   = 87.339726 ÷ 24     = 3.639155 tickets/hour
Per minute = 3.639155 ÷ 60      = 0.060653 tickets/minute
```

This is approximately one submission every **16.49 minutes** at the annual-average rate.

### Peak and off-peak profile

The off-peak multiplier is constrained by conservation of the daily total:

```text
(8 peak hours × 2.0) + (16 off-peak hours × x) = 24 hours × 1.0
16 + 16x = 24
x = 0.5
```

The model therefore does not inflate the annual volume when it introduces a daytime peak.

| Period | Hours/day | Multiplier | `POST /tickets` per hour | `POST /tickets` per minute |
|---|---:|---:|---:|---:|
| Off-peak, 17:00-09:00 | 16 | 0.5× | 1.819578 | 0.030326 |
| 24-hour average | 24 | 1.0× | 3.639155 | 0.060653 |
| Peak, 09:00-17:00 | 8 | 2.0× | 7.278311 | 0.121305 |

Expected inter-arrival times are approximately 32.98 minutes off-peak, 16.49 minutes on average, and 8.24 minutes at peak.

## Search workload

Assumption A6 produces:

```text
Annual searches = 31,879 submissions × 0.20
                = 6,375.8 expected searches/year
```

The decimal is an expected value; an observed annual count would be a whole number. Searches should use narrative keywords because the current `/search` implementation performs a case-insensitive substring match on `narrative`. Use the default `limit=20` for the representative workload; a separate edge case can exercise `limit=100`.

| Period | `GET /search` per hour | `GET /search` per minute | Combined client requests/hour |
|---|---:|---:|---:|
| Off-peak | 0.363916 | 0.006065 | 2.183494 |
| 24-hour average | 0.727831 | 0.012131 | 4.366986 |
| Peak | 1.455662 | 0.024261 | 8.733973 |

At peak, the endpoint mix is therefore 83.33% submissions and 16.67% searches, equivalent to a 5:1 submission-to-search ratio.

## Ticket-length distribution

The expected payload distribution is the observed distribution of all 1,000 assigned Team 8 narratives in `labelling/team8_rows_8000_8999.csv`, not only the 175-ticket golden set. It is reproducible with:

```bash
python3 scripts/calculate_ticket_length_stats.py
```

The script uses Unicode-aware word matching and nearest-rank percentiles. Its machine-readable output is `analysis/ticket_length_statistics.json`.

### Summary statistics

| Measure | Characters | Words |
|---|---:|---:|
| Minimum | 200 | 32 |
| Maximum | 2,000 | 395 |
| Mean | 879.016 | 156.818 |
| p50 | 777 | 141 |
| p95 | 1,757 | 310 |
| p99 | 1,935 | 354 |

### Character-count buckets

| Characters | Tickets | Share |
|---|---:|---:|
| 0-499 | 272 | 27.2% |
| 500-999 | 348 | 34.8% |
| 1,000-1,499 | 250 | 25.0% |
| 1,500-1,999 | 129 | 12.9% |
| 2,000+ | 1 | 0.1% |

### Word-count buckets

| Words | Tickets | Share |
|---|---:|---:|
| 0-99 | 323 | 32.3% |
| 100-199 | 378 | 37.8% |
| 200-299 | 234 | 23.4% |
| 300-399 | 65 | 6.5% |
| 400+ | 0 | 0.0% |

Later load tests should sample narratives from all 1,000 records without truncation and preserve these proportions. They should report latency by length band or at least compare median-length, p95-length, and maximum-length requests.

## Workload scenarios for later tests

These are client-workload targets, not performance requirements and not predictions of service capacity.

| Scenario | Submission rate | Search rate | Purpose |
|---|---:|---:|---|
| Expected off-peak | 0.030326/min | 0.006065/min | Validate low-demand behaviour. |
| Expected average | 0.060653/min | 0.012131/min | Represent the annual mean. |
| Expected peak | 0.121305/min | 0.024261/min | Primary realistic-load scenario. |
| Capacity/stress steps | Above 0.121305 submissions/min | Keep search at 1 per 5 submissions | Discover the knee point and saturation; do not label these higher rates as expected production demand. |

Because the realistic rates are low, short tests would contain too few samples for stable latency percentiles. A later test plan may run a longer realistic-rate test and separate accelerated capacity tests. It must keep those purposes and results distinct.

## Reproduction

Regenerate both machine-readable inputs from the repository root:

```bash
python3 scripts/calculate_ticket_length_stats.py
python3 scripts/build_workload_model.py
```

`analysis/workload_model.json` contains the benchmark, assumptions, and calculated rates that should feed later JMeter plans. Each period reports `per_hour`, `per_minute`, and `expected_per_window`; the last field is the expected volume during that period's actual `hours_per_day`, rather than a misleading 24-hour projection. The peak and off-peak window volumes sum to the expected daily volume. Command-line flags allow sensitivity checks without silently editing the documented baseline; `--peak-start-hour` and `--peak-hours` derive the displayed peak window, including windows that cross midnight.

## Limitations and update triggers

- The CFPB data is a regulatory complaint dataset, not the client's own telemetry and not a representative statistical sample.[2]
- The 1% market-share proxy, hourly multipliers, and search ratio are assumptions.
- Public complaint volume can differ materially from internal service-ticket volume.
- The model does not yet include day-of-week, holiday, campaign, incident, or seasonal effects.
- Replace A1-A7 and regenerate the JSON when actual client intake and search logs become available.
- Re-baseline if product scope, client size, operating hours, endpoint behaviour, or the source dataset changes.

## Sources

[1] https://files.consumerfinance.gov/f/documents/cfpb_cr-annual-report_2025-05.pdf — CFPB Consumer Response Annual Report 2024
[2] https://www.consumerfinance.gov/data-research/consumer-complaints — CFPB Consumer Complaint Database
