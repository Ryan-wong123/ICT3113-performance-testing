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
