# Step 1 — Golden Test Set Task Record

## Completed workflow

- [x] Confirm the course CSV columns and extract exactly Team 8 rows 8000–8999 (`labelling/team8_rows_8000_8999.csv`).
- [x] Write the labelling protocol before producing final labels (`labelling/labelling_protocol.md`).
- [x] Two team members independently label all 175 tickets, without conferring and without seeing `source_label`.
- [x] Calculate inter-human Cohen's kappa and retain the machine-readable result (`labelling/agreement_results.md`).
- [x] Record the five disagreements, final reviewed labels, and rationales (`labelling/disagreement_resolutions.csv`).
- [x] Generate `labelling/golden_test_set.csv` containing 175 final labels.
- [x] Freeze the Step 1 evidence in version control before candidate benchmarking.

## Verification

```bash
python3 -c "
import csv
from collections import Counter

def load(f, key='human_label'):
    with open(f, encoding='utf-8') as fh:
        return {row['row']: row[key] for row in csv.DictReader(fh)}

a = load('labelling/annotator_A.csv')
b = load('labelling/annotator_B.csv')
g = load('labelling/golden_test_set.csv', 'final_label')
dis = load('labelling/disagreement_resolutions.csv', 'final_label')

assert set(a) == set(b) == set(g), 'row sets must match'
diffs = {k for k in a if a[k] != b[k]}
assert diffs == set(dis), 'disagreements must match recorded resolutions'
for k in a:
    expected = dis[k] if k in dis else a[k]
    assert g[k] == expected, f'row {k} final label does not reconcile'

n = len(a)
po = sum(1 for k in a if a[k] == b[k]) / n
labels = sorted(set(a.values()) | set(b.values()))
ca, cb = Counter(a.values()), Counter(b.values())
pe = sum((ca[l] / n) * (cb[l] / n) for l in labels)
kappa = (po - pe) / (1 - pe)
print(f'OK: n={n} disagreements={len(diffs)} po={po:.4f} kappa={kappa:.4f}')
"
```

This validates the Team 8 row bounds, matching row sets across all four files, a one-to-one correspondence between annotator disagreements and recorded resolutions, and that every final label reconciles with either agreement or a recorded resolution.

## Methodological note

Labelling is fully manual and inter-human: two team members each independently labelled all 175 tickets.

---

# Step 2 — Baseline Service Task Record

## Completed workflow

- [x] Implement `POST /tickets` (synchronous classification, storage, returns category), `GET /search`, `GET /stats`.
- [x] Serialise every Ollama call behind a single lock — no parallel inference, no caching, no queue, no batching, no background workers.
- [x] Force CPU-only inference (`num_gpu: 0`) and call only a local Ollama instance (no public model API).
- [x] Log every request (success and failure) with timestamp, request id, endpoint, model, ticket row, start/end time, latency, HTTP status, predicted category, and error, to `logs/requests.jsonl`.
- [x] Containerise the service (`Dockerfile`, `docker-compose.yml`) reaching Ollama on the host via `host.docker.internal`.
- [x] Build and run the actual container (`docker compose up --build`) against a real local Ollama instance (not a stub) — verified working.
- [x] Install Ollama on the host, pull `llama3.2:3b`, and confirm `ollama ps` reports `100% CPU` — CPU-only inference is genuinely enforced, not just requested, even though this host has an NVIDIA GPU.
- [x] Smoke-test all three endpoints end to end against the real container + real Ollama: `POST /tickets` (4 real tickets, all classified into plausible/correct categories), `GET /search` (including case-insensitivity and `limit`), `GET /stats`.
- [x] Confirm sequential (non-overlapping) processing under concurrent load, from request start/end timestamps in `logs/requests.jsonl`.
- [x] Confirm input validation: empty narrative and out-of-Team-8-range `ticket_row` both rejected with 422.
- [x] Confirm the Ollama-unreachable failure path: 502, logged with the error, against both a stub and (incidentally, before Ollama was started) the real container.
- [x] Confirm every request (success, validation failure, and Ollama failure) produces one log line in `logs/requests.jsonl` with the required fields, reconciling exactly with what happened.

## Follow-up status

- [x] Pin the candidate tags/digests in Step 4 and pull/verify all three candidates in Step 5; the service itself remains environment-driven through `OLLAMA_MODEL`.
- [ ] Automated tests for the service (none exist yet; validation so far was manual curl-based smoke testing).
- [x] Exercise the malformed/off-format model-output path against real candidates; these responses produced documented HTTP 502s in both accuracy and load testing.
- [x] Preserve the append-only request log instead of deleting historical evidence, and explicitly reconcile the historical block, warm-ups, remote samples that reached FastAPI, and connection timeouts that did not (`docs/load_test_results.md`).

## Verification

```bash
# 1. Run a local Ollama and pull a model, e.g.:
ollama pull llama3.2:3b

# 2. Build and start the service:
docker compose up --build

# 3. Exercise the three endpoints:
curl -X POST http://localhost:8000/tickets -H "Content-Type: application/json" \
  -d '{"narrative": "My card was charged twice for the same purchase", "ticket_row": 8762}'
curl "http://localhost:8000/search?q=charged"
curl http://localhost:8000/stats

# 4. Confirm CPU-only inference:
ollama ps   # PROCESSOR column should read "100% CPU"

# 5. Confirm every call above produced a line in logs/requests.jsonl with the required fields.
```

---

# Step 3 — Workload Model Task Record

## Completed workflow

- [x] Compute character/word-count statistics (min/max/mean/p50/p95/p99, bucketed histograms) over all 1,000 Team 8 narratives (`scripts/calculate_ticket_length_stats.py` → `analysis/ticket_length_statistics.json`).
- [x] Model annual/monthly/weekly/daily submission and search volume from a cited public benchmark, with peak/off-peak rates that conserve the daily total (`scripts/build_workload_model.py` → `analysis/workload_model.json`).
- [x] Write up the evidence, assumptions (each labelled with an ID and a stated reason), calculations, resulting test scenarios, and limitations/re-baseline triggers (`docs/workload_model.md`).
- [x] Independently verify every cited public figure against the primary source, not just trust the reference draft — see "Verification" below.
- [x] Regenerate both JSON artefacts from our actual repo data (`labelling/team8_rows_8000_8999.csv`) and confirm the numbers match.
- [x] Run the generator's unit tests (`tests/test_build_workload_model.py`) against our code — all 4 pass.

## Follow-up status

- [x] Use the workload figures to derive Step 4 requirements and anchor Step 5's test-rate rationale. The short JMeter runs use disclosed accelerated rates because the realistic peak would produce too few samples for useful percentiles.
- [ ] The model has no day-of-week, holiday, campaign, incident, or seasonal effects (explicitly noted as a limitation in `docs/workload_model.md`).

## Verification

```bash
# Regenerate both machine-readable artefacts and confirm they match what's committed:
python3 scripts/calculate_ticket_length_stats.py
python3 scripts/build_workload_model.py

# Run the generator's unit tests:
python3 -m unittest tests.test_build_workload_model -v
```

Every public figure cited in `docs/workload_model.md` was checked directly against its primary source during development (not just copied from a prior draft):

| Citation | Verified against |
| --- | --- |
| "CFPB received approximately 3,187,900 complaints" in 2024 | Extracted text of the CFPB's 2024 Consumer Response Annual Report PDF, Section 1 — matched verbatim. |
| "98% of complaints [submitted] by visiting the CFPB's website" | Same PDF, same section — matched verbatim. |
| "sent approximately 2,829,400 (or 89%) to companies for review and response" | Same PDF, Section 2 — matched verbatim. |
| Database "is not a statistical sample... not necessarily representative" | CFPB Consumer Complaint Database disclaimer page — matched near-verbatim. |

---

# Step 4 — Candidate Models, Requirements, Predictions Task Record

## Completed workflow

- [x] Select 3 candidate models spanning 2 size classes: `llama3.2:1b` (small), `llama3.2:3b` (small, already tested in Step 2), `qwen2.5:7b` (large).
- [x] Obtain each candidate's exact manifest digest via the Ollama registry API, without pulling the model, and cross-verify the method against `llama3.2:3b`'s already-known local ID (matched exactly).
- [x] Obtain each candidate's actual licence text from its manifest's licence-layer blob (not from memory): Llama 3.2 Community License + Acceptable Use Policy for both `llama3.2` models, Apache License 2.0 for `qwen2.5:7b`.
- [x] Write `docs/candidate_models.md`: pins, sizes, licences, and justification for the set.
- [x] Derive R1 (response time), R2 (throughput), R3 (accuracy) in `docs/requirements.md`, each citing a specific `analysis/workload_model.json` figure plus non-workload justification (usability, misrouting cost, Step 1's disagreement evidence).
- [x] Write `predictions/prediction_record.md`: bottleneck prediction, per-candidate accuracy/latency predictions (with reasoning method disclosed), and hardest-category predictions, grounded in Step 1's and Step 2's actual evidence rather than general reasoning.
- [x] Confirm no candidate model was pulled, run, or benchmarked during this step.

## Follow-up status

- [x] Pull all three candidates in Step 5 and verify their local IDs against the frozen digests.
- [x] Document the actual Step 5 environment, including the separate JMeter Machine B and service/Ollama Machine A.
- [x] Measure R1/R2/R3 against every candidate without editing `predictions/prediction_record.md`.
- [ ] Complete the formal prediction-by-prediction comparison and recommendation in Step 6.

## Verification

```bash
# Recompute a candidate's manifest digest without pulling it, and confirm it against a locally-pulled model's ID (llama3.2:3b, already pulled in Step 2):
curl -s -o /tmp/manifest_3b.json -H "Accept: application/vnd.docker.distribution.manifest.v2+json" \
  "https://registry.ollama.ai/v2/library/llama3.2/manifests/3b"
sha256sum /tmp/manifest_3b.json   # first 12 hex chars must equal `ollama list`'s ID for llama3.2:3b

# Confirm the requirement numbers trace to Step 3's workload model:
python -c "import json; d=json.load(open('analysis/workload_model.json')); print(d['periods']['peak']['submissions']['per_hour'])"
# must print 7.278311, matching docs/requirements.md's R1/R2 citations
```

---

# Step 5 — Test and Measure Task Record

## Completed workflow

- [x] Document the original co-located environment and its limitation, then re-run the full load/stress workload with JMeter on separate Machine B and service/Ollama on Machine A.
- [x] Pull all 3 candidate models for real; confirm each local model ID matches the digest recorded in `docs/candidate_models.md` in Step 4 (all three matched).
- [x] Run the accuracy test (`scripts/run_accuracy_test.py`) for all 3 candidates against the real, running Docker container — every golden-set ticket through `POST /tickets`, never bypassed.
- [x] Discover and diagnose a genuine non-determinism finding (identical prompt/model replayed twice produced two different valid answers) — documented in `docs/accuracy_results.md`, not hidden.
- [x] Build and debug the JMeter open-loop test plan (`jmeter/test_plans/ticket_triage_load_test.jmx`); found and fixed a real bug (missing `throughputPeriod` property causing an `OutOfMemoryError`) by reading JMeter's own bundled javadoc, then smoke-tested before trusting it.
- [x] Run the load test matrix: 3 models × 2 accelerated low/high rates × 3 repeats = 18 JMeter runs, all open-loop. The rates were selected from latency on the older i7 environment and are not described as below/above the faster final i9 Machine A's capacity.
- [x] Report the arithmetic mean and observed range across the three repeats for latency percentiles, completed throughput, successful throughput, and error rate; keep offered arrivals separate and include queued drain time in the throughput denominator.
- [x] Run three remote `llama3.2:1b` stress repeats at both 40/min and 60/min. All 40/min runs were stable; at 60/min, one run collapsed, one developed severe late-window queueing, and one remained stable. The demonstrated reliability boundary is therefore 40–60/min on this environment.
- [x] Import and preserve 24 separate-machine JTL files (18 matrix runs plus six stress runs), then reconcile all 1,197 samples with `logs/requests.jsonl`.
- [x] Reconcile every requirement (R1, R2, R3) against measured data for every candidate — result: no candidate meets all three.
- [x] Diagnose the bottleneck with evidence (Ollama CPU-bound inference behind the single lock, confirmed matching the Step 4 prediction).
- [x] Confirm `predictions/prediction_record.md` was not edited.

## Remaining work and disclosed limitations

- [x] Formal predictions-vs-actual comparison table and final recommendation (Step 6 — see below).
- [x] Apply the “three runs per reported configuration” rule to stress as well: three retained runs at 40/min and three at 60/min, with per-run, pooled, mean, and spread reporting.
- [ ] A genuine multi-hour realistic-rate test was not run. The matrix uses short, accelerated rates because the real peak (~7.28/hour) would produce too few samples for stable percentiles; this is a disclosed limitation rather than omitted evidence.
- [x] Record Machine B's exact environment: Acer Nitro AN515-54, Intel i7-9750H (6 cores / 12 logical processors), 15.85 GiB RAM, Windows 11 Home build 22631, JMeter 5.6.3, and Microsoft OpenJDK 21.0.12.101.
- [x] State how the environment-specific results can and cannot scale to client hardware; do not extrapolate linearly from core count.
- [x] Correct `scripts/summarize_jtl.py` to measure through the final completion, add an arrival-window floor for sparse tests, and distinguish completed from successful throughput.

## Verification

```bash
# Re-summarise any raw .jtl file:
python3 scripts/summarize_jtl.py jmeter/results/<file>.jtl --arrival-window-seconds <configured-duration>

# Re-run the accuracy scorer against a running container (see docs/test_playbook.md for full steps):
python3 scripts/run_accuracy_test.py --model-label <tag>

# Confirm a candidate's locally-pulled model ID still matches its Step 4 digest:
ollama list   # first 12 hex chars of each ID must match docs/candidate_models.md
```

---

# Step 6 — Recommendation Task Record

## Completed workflow

- [x] Derive every Step 6 figure from committed evidence with `scripts/build_step6_analysis.py` → `analysis/step6_analysis.json` (accuracy JSONs, golden set, `source_label`, workload model, request log, remote JTLs) — no hand-typed numbers.
- [x] Add 95% Wilson intervals to every overall and per-category accuracy, and state which R3 failures are statistically clear (all three overall failures; `qwen2.5:7b`'s `Consumer loan` floor failure is measured but not conclusive at n=24).
- [x] Measure the status-quo baseline the client already has — the consumer-selected `source_label`, scored against the frozen golden labels after the freeze — and compare it with each model, paired on the same tickets (exact McNemar) and re-weighted by `source_label` stratum to all 1,000 Team 8 rows.
- [x] Take the brief's required position (misrouting costs more than slow triage at the modelled volume) and quantify it as a labelled derived estimate (measured error rate × Step 3 daily volume).
- [x] Compare every frozen prediction with the actual result, on the hardware the prediction was made for (i7 accuracy-run latency), and explain each miss with evidence: narrative length vs latency (Spearman 0.915–0.944), default-category collapse in the confusion matrices, first-request-after-switch latencies from `logs/requests.jsonl`.
- [x] Write the recommendation and its defence against R1–R3 (`docs/recommendation.md`): no candidate is recommended for automatic routing; `qwen2.5:7b` is the only candidate carried forward, as an agreement-gated pilot whose limits are stated.
- [x] Unit-test the new statistics helpers (`tests/test_build_step6_analysis.py`).
- [x] Confirm `predictions/prediction_record.md`, `docs/requirements.md`'s R1–R3 thresholds, `src/app/`, and the golden set were not edited.


## Verification

```bash
# Regenerate the Step 6 figures and confirm the committed JSON is unchanged:
python3 scripts/build_step6_analysis.py
git diff --exit-code analysis/step6_analysis.json

# Unit tests (on a machine where a pip package shadows the repo's tests/ folder, add -s):
python3 -m unittest tests.test_build_step6_analysis tests.test_summarize_jtl tests.test_build_workload_model -v
```

---

# Assignment 2 — Fast Triage Within an Accuracy Floor Task Record

The Assignment 1 baseline (Steps 1–6 above) is preserved. Assignment 2 is added on branch `assignment-2`. Brief: `docs/PROJECT_CONTEXT.md` Section 26. Due 2359, Friday 27 November. The steps below follow the brief's own Steps 1–5 and Deliverables. Order matters: items marked **(commit first)** must be committed before the later work they gate.

Legend for the cascade switch (not yet implemented): **off** = Assignment 1 single-model path (`OLLAMA_MODEL`); **on** = cascade.

## Execution plan by machine

Every unchecked item below states the machine it needs and its workstream (`WS1`–`WS5`, owners in the table):

- `[machine: any]` — code, scripts, docs and commit-gated lists; no real model runs (a stub Ollama is fine).
- `[machine: any, after i9 data]` — analysis or writing that can be done on any computer once the relevant i9 outputs are committed.
- `[machine: i9]` — runs the service and a model on the final Machine A (memory check, accuracy runs, timing S). No load generator needed.
- `[machine: i9 + JMeter machine]` — speed runs: the service and Ollama on Machine A, and JMeter 5.6.3 plus a JDK on a separate load-generator machine (the Assignment 1 Machine B, or another computer whose hardware is recorded). Both must be available and set up.

Only the i9 operator does the two `i9` kinds, and commits the raw outputs (`analysis/a2/accuracy/*.json`, `.jtl` files, logs) so others can pull them. Every configuration must be measured on one machine, so do not run real models on another computer for evidence.

Step-by-step prompts for running the remaining work in order on the i9 (one fresh session per prompt): `docs/a2_handoff_prompts.md`.

### Workstreams and owners

| WS | Workstream | Machine | Owner | Items |
| --- | --- | --- | --- | --- |
| WS1 | Service code: cascade switch, pluggable rule, log fields, `/health`, unit tests, baseline unchanged | any machine | TBD | Step 2 implementation items |
| WS2 | Scripts and data lists: split script, accuracy runner, speed helpers, speed-test row list | any machine | TBD | Step 1 split, Step 4 runner, speed rows |
| WS3 | i9 operator: memory check, all accuracy and speed runs, environment record, committing raw outputs | i9 for accuracy/S timing; i9 + JMeter machine for speed runs | TBD | all `[machine: i9]` and `[machine: i9 + JMeter machine]` items |
| WS4 | Analysis and design: limits, rule choice and write-up, predictions, accuracy/speed analysis, results doc, recommendation | any machine, after WS3 data | TBD | all `[machine: any, after i9 data · WS4]` items |
| WS5 | Deck, references, licences, AI declaration, final traceability check | any machine | TBD | Deliverables |

Fill in the Owner column when the team agrees the split. Hand-offs are by commits on `assignment-2`; keep the commit gates in order (split → rule → predictions → speed runs) and freeze the service code before the first benchmark.

**Phase A — any computer, in this order**
1. Split script and commit `analysis/a2/golden_split.csv` (nothing else is committed before this).
2. Cascade implementation behind the off-by-default switch, with the rule as a pluggable function/config (thresholds chosen later), the new log fields and `/health` cascade mode; unit tests against a stub; baseline (switch off) unchanged.
3. Accuracy runner and speed-run helpers (tested against a stub).
4. Commit `analysis/a2/speed_test_rows.csv`: about 30 workload rows outside the golden set (typical and long), plus three timing tickets for S and three warm-up tickets, all disjoint.
5. Deck skeleton, acknowledgements and AI-declaration drafts; keep `docs/prd.md`, `docs/architecture.md` and this file current.

**Phase B — i9 (Machine A), in this order**
1. `git pull`; record the code commit hash; do the memory check (ideally before Phase A step 2 if the i9 is reachable first, because the brief says to check it before building).
2. Top-model test-set accuracy, then derive the limits.
3. Single-model runs for the tuning set; choose the rule approach and two settings; write and commit `docs/a2_escalation_rule.md`.
4. Write and commit `predictions/a2_prediction_record.md` (before any further benchmark).
5. Cascade and remaining single-model test-set accuracy; time S; set the rate; three speed runs per configuration on the separate JMeter machine.

**Phase C — finalise (i9 results in hand)**: reconcile every figure, recommendation, `docs/a2_results.md`, fill the deck.

## When to turn the cascade switch on

The switch is off by default so the Assignment 1 baseline stays reproducible. Turn it **on only for cascade runs**, from the cascade accuracy test onwards; everything before that, and every single-model configuration, runs with it off.

| Work | Switch |
| --- | --- |
| Step 1: split, top-model test-set accuracy, limits | off |
| Step 2: memory check (`ollama ps` with both models), rule design on the tuning set | off |
| Step 3: predictions | n/a |
| Step 4: single-model accuracy (each other model) | off |
| Step 4: **cascade accuracy, setting A and B** | **on** |
| Step 4: speed set-up (timing S on the top model) | off |
| Step 4: speed runs, single models | off |
| Step 4: **speed runs, cascade setting A and B** | **on** |

How (names are a proposal until the switch is implemented): the switch is an environment setting read when the container starts, so recreate the container for every configuration.

```bash
# Single model (cascade off):
docker compose down && OLLAMA_MODEL=<tag> docker compose up -d

# Cascade (on), once for rule setting A and once for B:
docker compose down && CASCADE_ENABLED=true OLLAMA_SMALL_MODEL=<small tag> \
  OLLAMA_LARGE_MODEL=<large tag> CASCADE_RULE_SETTING=A docker compose up -d
```

Before every cascade run, confirm: `GET /health` reports cascade on with the intended models and setting; `ollama ps` lists both models; and the first log lines show `cascade_mode=on` with some `escalated=true`. A "cascade" run with no escalations and `cascade_mode=off` is a mislabelled single-model run and its numbers must not be used.

## Setup — brief, guardrails and planning docs (done)

- [x] Record the Assignment 2 brief, scope (fixed / may change / not permitted), steps, deliverables and assessment in `docs/PROJECT_CONTEXT.md` Section 26.
- [x] Add Assignment 2 guardrails to `AGENTS.md`; scope the Assignment 1 rules that Assignment 2 deliberately changes.
- [x] Document the Assignment 2 PRD (`docs/prd.md`), cascade architecture design (`docs/architecture.md`), test-environment additions (`docs/test_environment.md`), speed-test playbook (`docs/test_playbook.md`) and the accuracy-limit method (`docs/a2_accuracy_limits.md`).
- [x] Preserve the Assignment 1 baseline on branch `main`; develop Assignment 2 on `assignment-2`.

## Step 1 — Define the accuracy limits (switch: off)

- [x] `[machine: any · WS2]` **(commit first)** Write the split script and commit the odd/even split of the 175 golden tickets (odd rows = tuning, even rows = test) to `analysis/a2/golden_split.csv`; record the tuning/test counts. Done: `scripts/split_golden_set.py` → `analysis/a2/golden_split.csv` (175 = 90 tuning / 85 test; odd `row` value = tuning, even = test); tests in `tests/test_split_golden_set.py`.
- [ ] `[machine: i9 · WS3]` Run the top model (`qwen2.5:7b`) on the test set through `POST /tickets` on the final machine; save `analysis/a2/accuracy/qwen2.5_7b.json`. (Assignment 1 accuracy was recorded on the older i7 / Ollama 0.34.4; reuse is only valid if digest, prompt, Ollama version and machine are unchanged.)
- [ ] `[machine: any, after i9 data · WS4]` Derive the overall limit (test-set accuracy − 10 points) and each per-category limit (category accuracy − 15 points); fill the table in `docs/a2_accuracy_limits.md`.
- [ ] `[machine: any, after i9 data · WS4]` Show right/wrong counts beside every percentage; flag categories too small for a fair per-category test.
- [ ] `[machine: any · WS4]` State the caveat that the test set is not new data (all models ran on the full golden set in Assignment 1).

## Step 2 — Design the cascade

- [ ] `[machine: i9 · WS3]` **Memory check first (switch: off / Ollama only):** load both models of each candidate pair, run a few tickets through each, confirm `ollama ps` lists both and they stay loaded; save the output in `docs/test_environment.md` (Assignment 2 section). If no pair fits, record that a cascade is not feasible and recommend a single model.
- [ ] `[machine: any, after i9 data · WS4]` Choose the escalation approach on the tuning set only (category-based, agreement, self-reported confidence, ticket length, or a custom rule); justify the choice.
- [ ] `[machine: any, after i9 data · WS4]` Choose exactly two settings of the rule on the tuning set.
- [ ] `[machine: any, after i9 data · WS4]` Write `docs/a2_escalation_rule.md` so another team could implement it from the description. **(commit before the first benchmark run)**
- [ ] `[machine: any · WS1]` Implement the cascade inside `POST /tickets` behind an off-by-default, environment-driven switch (small model, large model, rule setting); no hardcoded model in `src/app/`; the response gives no hint which model answered.
- [ ] `[machine: any · WS1]` Keep the baseline intact: with the switch off, behaviour is exactly Assignment 1 (synchronous, sequential, no caching/queue/batching/workers; `num_gpu: 0`).
- [ ] `[machine: any · WS1]` Extend the request log with the Assignment 2 fields (`cascade_mode`, `rule_setting`, `small_model`, `large_model`, `small_category`, `final_model`, `escalated`) and report cascade mode in `GET /health`.
- [ ] `[machine: any · WS1]` Unit-test the rule and the split; update `docs/architecture.md` / `docs/prd.md` to match the code as built.

## Step 3 — Record predictions **(commit before any Assignment 2 benchmark; never edit afterwards)**

- [ ] `[machine: any, after i9 data · WS4]` Predict which configuration will be the fastest that satisfies the limits, with reasons.
- [ ] `[machine: any, after i9 data · WS4]` For the cascade at each setting: predict the escalation fraction, accuracy and median latency.
- [ ] `[machine: any, after i9 data · WS4]` Predict which categories lose the most accuracy when the small model's answer is accepted.
- [ ] `[machine: any, after i9 data · WS4]` Commit `predictions/a2_prediction_record.md` (specific enough to be shown wrong). Leave `predictions/prediction_record.md` untouched.

## Step 4 — Test and measure

### Accuracy test (test set only, through `POST /tickets`, once per configuration)

- [ ] `[machine: any · WS2]` Write the Assignment 2 accuracy runner (test set only, through `POST /tickets`) and the speed-run helpers; test them against a stub, not real models. Finish and commit the service code before the first benchmark and record the commit hash with the results.
- [ ] `[machine: i9 · WS3]` Each other single model alone (`llama3.2:3b`, `llama3.2:1b`) — switch: off.
- [ ] `[machine: i9 · WS3]` Cascade at setting A and at setting B — switch: **on**.
- [ ] `[machine: any, after i9 data · WS4]` Report overall accuracy (count and percentage), per-category accuracy against the per-category limit, and a confusion matrix for every configuration.
- [ ] `[machine: any, after i9 data · WS4]` For the cascade: number escalated, and accuracy of escalated vs non-escalated tickets.
- [ ] `[machine: any, after i9 data · WS4]` Mark which configurations pass both limits; optionally show tuning-set results, but only test-set results decide pass/fail.
- [ ] `[machine: any, after i9 data · WS4]` If any Assignment 1 single-model records are reused, score only test-set rows and say so in the report.

### Speed test — set-up (switch: off for S)

- [ ] `[machine: i9 · WS3]` Restart Ollama, warm up, send three different typical-length tickets one at a time to the top model; S = the middle time; record the three timings and ticket row numbers.
- [ ] `[machine: any, after i9 data · WS4]` Arrival rate = one ticket every 2×S seconds; run length = S minutes (minimum 5); same for every configuration.
- [ ] `[machine: any · WS2]` **(commit)** Fixed ordered workload (rows outside the golden set, typical and long) in `analysis/a2/speed_test_rows.csv`.
- [ ] `[machine: i9 + JMeter machine · WS3]` Record software versions, model digests and Ollama settings once; re-check before each configuration.
- [ ] `[machine: any, after i9 data · WS4]` Compare the test rate with the client's peak from `analysis/workload_model.json` and note which side it is on.
- [ ] `[machine: i9 + JMeter machine · WS3]` Use a separate load-generator machine (Machine B).

### Speed test — runs (three runs per configuration; switch: off for single models, **on** for the cascade)

- [ ] `[machine: i9 + JMeter machine · WS3]` Top model alone (required).
- [ ] `[machine: i9 + JMeter machine · WS3]` Each single model that passes both limits.
- [ ] `[machine: i9 + JMeter machine · WS3]` Cascade at both settings (tested whether or not it passes; mark "not passing accuracy" if it fails).
- [ ] `[machine: i9 + JMeter machine · WS3]` Each run: restart Ollama and confirm up; three fixed warm-up tickets (timings discarded); for the cascade warm both models and confirm both in `ollama ps`; note `GET /stats`; JMeter open-loop at the chosen rate and length; response timeout = max(10×S s, 5 min); trailing pause longer than the timeout by ≥ 1 min; note `GET /stats` again.
- [ ] `[machine: i9 + JMeter machine · WS3]` Keep every raw `.jtl` as `jmeter/results/a2_<config>_run<n>.jtl` and the service-log segment for each run.
- [ ] `[machine: any, after i9 data · WS4]` Report per run: requests sent, completed, errored, unfinished; p50 with mean and spread across runs; p95 pooled over the three runs (state the sample count); throughput and error rate; for the cascade the escalation fraction from the service logs (explain any large gap from the accuracy-test figure). No p99; no reuse of Assignment 1 speed figures.
- [ ] `[machine: i9 + JMeter machine · WS3]` Describe the test environment (or refer to Assignment 1 if unchanged) and any change from Assignment 1; disclose limitations plainly.

## Step 5 — Recommendation

- [ ] `[machine: any, after i9 data · WS4]` Recommend one configuration that passes both limits on the test set and is the fastest of those that do, by the team's own measurements at the chosen rate.
- [ ] `[machine: any, after i9 data · WS4]` State how much faster it is than the top model and how much accuracy it gives up, overall and by category.
- [ ] `[machine: any, after i9 data · WS4]` If the cascade was not the fastest qualifying configuration, say so and explain with the measured escalation fraction and latencies; if nothing but the top model qualifies, recommend it and describe what was tried and what it cost.
- [ ] `[machine: any, after i9 data · WS4]` Compare predictions with outcomes and explain differences without editing the prediction record.
- [ ] `[machine: any, after i9 data · WS4]` Write `docs/a2_results.md`; every figure must reconcile with a `.jtl`, log or JSON in the repository.

## Deliverables

- [ ] `[machine: any (skeleton now; fill results after i9 data) · WS5]` `GroupNum_A2.pptx` (e.g. `Group08_A2.pptx`), at most 8 slides: cover; cascade design; test environment and method; accuracy results; speed results; trade-off chart (accuracy vs latency, overall limit as a line); predictions, recommendation, defence; limitations, references, model licences, AI declaration.
- [ ] `[machine: any, after i9 data · WS4]` Supporting files committed: prediction record, written escalation rule, speed-test row list.
- [ ] `[machine: any, after i9 data · WS4]` Prediction record and escalation rule committed before the first Assignment 2 benchmark run.
- [ ] `[machine: i9 + JMeter machine · WS3]` Raw `.jtl` files and service logs for every reported run retained in the repository.
- [ ] `[machine: any, after i9 data · WS5]` Every figure on slides 4–7 traces to a log or `.jtl` file.
- [ ] `[machine: any · WS5]` Acknowledge the Consumer Complaint Database, Ollama and model licences; AI declaration states what the tools produced and what the team did.

## Verification

```bash
# Assignment 1 evidence is unchanged on this branch:
git diff --exit-code main -- analysis/accuracy predictions/prediction_record.md docs/requirements.md docs/recommendation.md src/app

# With the cascade switch off (default), the Assignment 1 baseline commands in README.md and above must still work unchanged.
# Assignment 2 golden-set split (implemented):
python3 scripts/split_golden_set.py --check
python3 -m unittest tests.test_split_golden_set -v
# Further Assignment 2 verification commands will be added here as each script is implemented.
```
