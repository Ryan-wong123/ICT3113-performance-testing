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

---

# Step 4 Architecture — Candidate Models, Requirements, Predictions

## Overview

This step is pure documentation and registry lookups — no code, no service changes, and critically, no candidate model is pulled or run. The one piece of "engineering" is how the candidate models' tags were pinned without downloading them:

```text
Ollama registry API (registry.ollama.ai)
        |
        v
GET /v2/library/<name>/manifests/<tag>   (small JSON, no model weights downloaded)
        |
        +--> sha256sum of the exact response bytes = the manifest digest
        |       (cross-checked against `ollama list`'s local ID for llama3.2:3b — matched)
        |
        v
GET /v2/library/<name>/blobs/<licence-layer-digest>   (redirects to R2, small text file)
        |
        v
docs/candidate_models.md (tags, digests, sizes, licences, justification)
        |
        v (combined with analysis/workload_model.json from Step 3)
        v
docs/requirements.md (R1 response time, R2 throughput, R3 accuracy)
        |
        v (combined with Step 2's observed logs/requests.jsonl latencies,
        v  and Step 1's labelling/agreement_results.md disagreement evidence)
        v
predictions/prediction_record.md (frozen before any benchmark)
```

## Components

| Component | Responsibility |
| --- | --- |
| `docs/candidate_models.md` | The 3 pinned candidates (tag, manifest digest, weights size, licence), how each digest/licence was obtained, and why this set demonstrates the required size/accuracy/latency trade-off. |
| `docs/requirements.md` | R1 (response time), R2 (throughput), R3 (accuracy) — each a testable number tied to a specific Step 3 workload-model figure, plus non-workload justification. |
| `predictions/prediction_record.md` | Frozen bottleneck/accuracy/latency/hardest-category predictions, each with its reasoning method disclosed. |

## Why no model was pulled in this step

The team chose to record each candidate's exact tag and manifest digest via the Ollama registry's manifest endpoint rather than pulling all three models (which would mean several GB of downloads) before Step 5. The manifest digest obtained this way is identical to what `ollama pull` would produce locally — verified directly: the digest computed for `llama3.2:3b` via this method reproduced `ollama list`'s local model ID exactly. This keeps Step 4 fast and focused on the paperwork the brief actually asks for (pin, justify, set requirements, predict), while deferring the real multi-gigabyte pulls to Step 5, immediately before benchmarking.

## Boundary

Step 4 does not benchmark, pull, or run any candidate model — that is Step 5. It also does not yet document the Step 5 test environment (separate machines for the load generator and the service, hardware/software versions) — the hardware referenced in `predictions/prediction_record.md` is this team's development machine, used only to make the prediction record concrete and falsifiable, not a claim about the eventual Step 5 test environment.

---

# Step 5 Architecture — Test and Measure

## Overview

Three independent measurement pipelines drive the real Docker container (never bypassing it), sharing the same container/Ollama pair one candidate model at a time (switched via `docker compose down && OLLAMA_MODEL=<tag> docker compose up -d`). For the final load/stress pipeline, JMeter runs on separate Machine B and reaches the container on Machine A over TCP 8000; it is not co-located with Ollama:

```text
labelling/golden_test_set.csv (175 tickets)
        |
        v
scripts/run_accuracy_test.py --model-label <tag>
        |  (POST /tickets, one at a time, per ticket)
        v
analysis/accuracy/<tag>.json (overall/per-category accuracy, confusion matrix, warm latency)
        |
        v (feeds R1, R3)
docs/accuracy_results.md

jmeter/test_plans/load_test_narratives.csv (825 non-golden-set rows)
        |
        v
jmeter/test_plans/ticket_triage_load_test.jmx (PreciseThroughputTimer, open-loop)
        |  (Machine B, 3 repeats per rate; direct non-GUI invocation)
        v
Machine A POST /tickets -> synchronous classifier lock -> CPU-only Ollama
        v
jmeter/results/*_remote.jtl
        |
        v
scripts/summarize_jtl.py (p50/p95/p99, completed/successful throughput, error rate)
        |
        v (feeds R2, stress-test limit, bottleneck diagnosis)
docs/load_test_results.md
```

## Components

| Component | Responsibility |
| --- | --- |
| `scripts/run_accuracy_test.py` | Sends every golden-set narrative through the real `POST /tickets` endpoint (never a bulk/bypass path), scores overall/per-category accuracy and a confusion matrix, and records warm single-request latency percentiles. |
| `jmeter/test_plans/ticket_triage_load_test.jmx` | One parameterised JMeter plan (rate, duration, host/port, narrative CSV all via `-J` properties) covering every load/stress configuration — no per-run XML editing. Uses JMeter core's `PreciseThroughputTimer` (Poisson-process open-loop pacing, not a plugin) and a `JSR223PreProcessor` (Groovy `JsonOutput.toJson`) to safely build the JSON body regardless of quotes/newlines in a narrative. |
| `jmeter/test_plans/load_test_narratives.csv` | The 825 Team 8 rows *not* in the golden set — load-test traffic never touches the frozen accuracy-evaluation data. |
| `scripts/run_jmeter_test.sh` | Thin wrapper: one call = one (model, rate, duration, run number) → one `.jtl` file under `jmeter/results/`. |
| `scripts/summarize_jtl.py` | Turns a raw `.jtl` into p50/p95/p99 latency, completed throughput, successful throughput, offered arrival rate, and error rate/codes. Its measurement window is the longer of the configured arrival window and first-sample-to-final-completion time, so sparse traffic is not overstated and queued drain time is retained. |
| `docs/test_environment.md` | Hardware/software and network roles for separate Machine A (service/Ollama) and Machine B (JMeter), remaining environment limitations, and the explicit boundary on scaling these measurements to client hardware. |
| `docs/test_playbook.md` | Step-by-step reproduction instructions for all three test types. |
| `docs/accuracy_results.md`, `docs/load_test_results.md` | Results, three-run mean/range and pooled load summaries, requirement reconciliation (R1–R3 per candidate), and bottleneck diagnosis. |

## A real implementation bug found and fixed during this step

The first version of `ticket_triage_load_test.jmx` crashed every run (`OutOfMemoryError: Requested array size exceeds VM limit`) because the `PreciseThroughputTimer` element was missing its required `throughputPeriod` property (and carried a stray empty `randomSeed`) — both fabricated from memory rather than the actual bean schema. This was found by inspecting JMeter's own bundled javadoc (`docs/api/.../PreciseThroughputTimer.html`) for the real property list, rather than guessing again, and confirmed fixed with a small smoke test before any real data was collected on it.

The final remote stress runs establish an environment-specific reliability boundary rather than a universal constant. `llama3.2:1b` sustained 40 arrivals/minute in all three 180-second repeats. At 60/minute, one repeat saturated the sequential path and request/socket backlog (152 connect timeouts plus one 300-second read timeout), a second developed a 66.8-second p95 latency tail, and a third remained stable. The supported claim is therefore that 60/min is not repeatably sustainable on the recorded Machine A and the reliability transition lies between 40 and 60/min—not that every 60/min run must fail.

Both the normal matrix and stress rates have three repeats and report per-run values, pooled values, and arithmetic mean with minimum–maximum spread.

Offered arrivals, completed throughput, and successful throughput are kept distinct. This is essential for the 60/min stress runs: one run needed almost six minutes to finish a three-minute arrival window, and another drained for roughly four minutes. Dividing only by the configured arrival period would mislabel queued work as achieved capacity.

## Boundary

Step 5 measures the frozen candidates and requirements; it does not choose a different candidate set, does not revise `predictions/prediction_record.md`, and does not make the final recommendation — that is Step 6, which compares this step's actual results against Step 4's predictions and requirements.

---

# Step 6 Architecture — Recommendation

## Overview

One stdlib-only, regenerable script turns the frozen Step 1–5 evidence into every figure the recommendation uses. It reads only committed files and never calls the service or Ollama.

```text
analysis/accuracy/*.json ─┐
labelling/golden_test_set.csv ─┤
labelling/team8_rows_8000_8999.csv (source_label, post-freeze baseline only) ─┤
analysis/workload_model.json ─┼─> scripts/build_step6_analysis.py ─> analysis/step6_analysis.json ─> docs/recommendation.md
logs/requests.jsonl ─┤          (reuses summarize_jtl.nearest_rank)
jmeter/results/*_remote.jtl ─┤
predictions/prediction_record.md (values copied into PREDICTIONS) ─┘
```

## Components

| Component | Responsibility |
| --- | --- |
| `scripts/build_step6_analysis.py` | Wilson 95% intervals for overall/per-category accuracy; consumer self-label baseline; paired exact McNemar test of each model vs the self-label; stratum-weighted accuracy over all 1,000 Team 8 rows; offline agreement-gate analysis; derived misroutes/day from the Step 3 volume; latency-vs-prediction ratios and narrative-length Spearman correlation; first request after each model switch from the request log; pooled and worst-run p95 from the remote JTLs. |
| `analysis/step6_analysis.json` | Machine-readable output of the above; regenerable, not hand-edited. |
| `tests/test_build_step6_analysis.py` | Unit tests for the Wilson interval, exact McNemar test, tie-aware ranking, and Spearman correlation. |
| `docs/recommendation.md` | The client recommendation, the misrouting-vs-latency position, requirement defence, predictions vs actual, account of where and why predictions failed, and conditions. |

## Boundary

Step 6 changes no service code, golden label, requirement threshold, or prediction. The agreement-gated pilot it recommends would require a service change (accepting the consumer-selected label) and is therefore Assignment 2 work, not part of this baseline.
