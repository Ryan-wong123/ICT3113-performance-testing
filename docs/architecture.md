# Step 1 Golden Test Set Architecture

## Overview

This branch has no running service. It is a file-based evidence package for constructing the Assignment 1 golden test set through fully manual labelling.

```text
labelling/ict3113_tickets.csv (full course dataset)
        |
        v
labelling/team8_rows_8000_8999.csv (Team 8 rows 8000-8999)
        |
        v
labelling/labelling_protocol.md (categories + decision rules, written first)
        |
        v
Two independent human annotators
        |-------------------------------> labelling/annotator_A.csv
        |-------------------------------> labelling/annotator_B.csv
        v
labelling/agreement_results.md (Cohen's kappa, inter-human)
        |
        v
labelling/disagreement_resolutions.csv (reviewed final labels + rationale)
        |
        v
labelling/golden_test_set.csv (row, narrative, final_label)
```

## Components

| Component | Responsibility |
| --- | --- |
| `labelling/ict3113_tickets.csv` | Supplied course dataset. |
| `labelling/team8_rows_8000_8999.csv` | Team 8's 1,000-row scope (rows 8000–8999). |
| `labelling/labelling_protocol.md` | Category definitions and decision rules for ambiguous narratives, written before labelling started. |
| `labelling/annotator_A.csv`, `labelling/annotator_B.csv` | Two independent human label sheets (`row,human_label`) over the same 175 tickets. |
| `labelling/agreement_results.md` | Observed agreement and Cohen's kappa between the two annotators. |
| `labelling/disagreement_resolutions.csv` | Human-reviewed final decisions and rationales for every row where the annotators disagreed. |
| `labelling/golden_test_set.csv` | Final `row,narrative,final_label` file: agreed label where the annotators matched, resolved label otherwise. |

## Data flow and integrity

`source_label` in `team8_rows_8000_8999.csv` is a sampling/audit aid only; annotators do not see it while labelling and it is never used as ground truth. Every row in `golden_test_set.csv` reconciles with either (a) an identical label from both annotator sheets, or (b) a recorded resolution in `disagreement_resolutions.csv`.

---

# Step 2 Baseline Service Architecture

## Overview

A single FastAPI process, one SQLite file, and an append-only JSONL request log. No queue, no cache, no background worker — every `POST /tickets` call blocks on a synchronous call to a local Ollama instance running on the host, outside the container.

```text
Client / JMeter (Step 5)
        |
        v (HTTP)
FastAPI app (src/app/main.py)
        |
        |-- instrument_requests middleware --> logs/requests.jsonl (every request, incl. failures)
        |
        +-- POST /tickets --> OllamaClassifier.classify() [single lock, sequential]
        |                           |
        |                           v (HTTP, num_gpu=0)
        |                     Ollama on host (host.docker.internal:11434)
        |                           |
        |                     category text --> categories.parse_category() (must be an exact match)
        |                           |
        |                           v
        |                     TicketStore.insert() --> SQLite (runtime/tickets.db)
        |
        +-- GET /search?q=... --> TicketStore.search()  (LIKE match on narrative)
        |
        +-- GET /stats --> TicketStore.category_counts()
```

## Components

| Component | Responsibility |
| --- | --- |
| `src/app/main.py` | FastAPI app: the three required endpoints, request-logging middleware, request/response models. |
| `src/app/ollama_client.py` | Synchronous, lock-serialised HTTP client to local Ollama; forces `num_gpu: 0`; raises `OllamaError` on network failure, HTTP error, or malformed/invalid category output. |
| `src/app/categories.py` | The seven allowed category strings; builds the classification prompt; strictly parses the model's raw text into exactly one category or raises. |
| `src/app/storage.py` | SQLite-backed `TicketStore`: insert, substring search, per-category counts. No cache, no bulk import path. |
| `src/app/config.py` | Environment-driven `Settings` (Ollama URL/model/timeout, DB path, log path) — no hardcoded model choice. |
| `src/app/request_logging.py` | Thread-safe append-only JSONL writer for the logged fields (below). |
| `Dockerfile`, `docker-compose.yml` | Container build and run; `host.docker.internal` reaches Ollama on the host; `runtime/` and `logs/` are bind-mounted so both persist and are inspectable outside the container. |

## Logged fields

The brief (`docs/PROJECT_CONTEXT.md` Section 10) only requires that every request be logged and reconcile with reported numbers; it does not name specific fields. This implementation logs one JSON line per request to `logs/requests.jsonl` with:

```text
timestamp
request_id
endpoint
method
model
ticket_row_if_available
request_start
request_end
latency_ms
http_status
predicted_category
error
```

Every request produces exactly one line, success or failure (validation errors, Ollama-unreachable, invalid model output), via the `instrument_requests` middleware in `src/app/main.py`.

## Baseline-fidelity notes

- **Synchronous**: `POST /tickets` awaits `classifier.classify(...)` before responding; there is no background task or callback.
- **Sequential, not parallel**: `OllamaClassifier` holds a `threading.Lock` around every inference call, by design — an explicit constraint, not a bug, so concurrent load produces queueing delay inside the service rather than parallel Ollama calls.
- **No caching**: identical narratives are re-classified every time; nothing memoises a prompt or response.
- **No bulk import**: the service has no endpoint or script that loads the CSV directly — tickets only enter through `POST /tickets`, exactly as the brief requires.
- **CPU-only**: `options.num_gpu = 0` is sent on every Ollama request.

## Boundary

Step 2 excludes model selection/pinning (Step 4), workload modelling (Step 3), JMeter load/stress testing (Step 5), and the recommendation (Step 6). It also does not yet pull or pin any specific Ollama model — `OLLAMA_MODEL` in `.env.example` is a placeholder until Step 4 selects and pins the candidate set.

---

# Step 3 Workload Model Architecture

## Overview

Two independent, regenerable pipelines, both stdlib-only (no new dependencies): one turns Team 8's own narratives into a length distribution, the other turns a cited public benchmark plus explicit assumptions into arrival-rate estimates. Neither touches the service — this step produces planning inputs for Step 4's requirements and Step 5's JMeter plans, not code the service runs.

```text
labelling/team8_rows_8000_8999.csv (1,000 narratives)
        |
        v
scripts/calculate_ticket_length_stats.py --> analysis/ticket_length_statistics.json
                                                      |
                                                      v (feeds "Ticket-length distribution" section)
                                              docs/workload_model.md

CFPB Consumer Response Annual Report 2024 (cited, verified against source PDF)
        |
        v
scripts/build_workload_model.py (benchmark x assumptions A1-A8) --> analysis/workload_model.json
                                                      |
                                                      v (feeds rate/scenario sections)
                                              docs/workload_model.md
```

## Components

| Component | Responsibility |
| --- | --- |
| `scripts/calculate_ticket_length_stats.py` | Reads all 1,000 Team 8 narratives, computes character/word min/max/mean/p50/p95/p99 (nearest-rank) and bucketed histograms. Unicode-aware word matching. |
| `analysis/ticket_length_statistics.json` | Machine-readable output of the above; regenerable, not hand-edited. |
| `scripts/build_workload_model.py` | Takes the CFPB annual benchmark and eight explicit assumptions (market share, peak/off-peak hours and multipliers, search-to-submission ratio) as CLI args (with sane defaults), derives the off-peak multiplier so peak+off-peak conserves the daily total, and computes per-day/hour/minute submission and search rates for average/peak/off-peak periods. |
| `analysis/workload_model.json` | Machine-readable output of the above; regenerable, not hand-edited. |
| `tests/test_build_workload_model.py` | Unit tests: non-default peak windows compute correctly (including windows crossing midnight), non-finite CLI arguments are rejected without writing output, peak+off-peak volumes conserve the daily total, and the JSON output is strict (no NaN/Infinity). |
| `docs/workload_model.md` | The narrative document: cited evidence, assumptions table (each with an ID and stated reason), calculations, resulting scenarios for Step 5, and stated limitations/re-baseline triggers. |

## Evidence integrity

Every cited figure in `docs/workload_model.md` was checked directly against the CFPB's own primary source text (the 2024 Consumer Response Annual Report PDF, and the Consumer Complaint Database's own disclaimer page) during development — not assumed correct because a prior draft cited it. All four cited figures (3,187,900 total complaints; 98% via website; 2,829,400/89% sent to companies; the "not a statistical sample" disclaimer) matched the source text verbatim or near-verbatim.

Every assumption (market share, peak/off-peak hours, multipliers, search ratio) is explicitly labelled as an assumption with a stated reason, not presented as observed data — this is what lets `build_workload_model.py` accept CLI overrides for sensitivity checks without silently editing the documented baseline.

## Boundary

Step 3 does not set requirements (Step 4 derives testable response-time/throughput/accuracy requirements from this model) and does not touch the service or Ollama. It also does not yet reflect real client telemetry — the model explicitly states what would trigger a re-baseline once that exists.
