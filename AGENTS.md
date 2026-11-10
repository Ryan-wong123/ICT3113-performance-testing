# Project agent instructions

`docs/PROJECT_CONTEXT.md` is the authoritative assignment brief and team-decisions record (Sections 1–25 are Assignment 1; Section 26 onward is Assignment 2); `docs/task.md` records the tasks done.

The Assignment 1 evidence on branch `main` is the preserved baseline. Assignment 2 work is added on top of it on branch `assignment-2`; Assignment 1 files, results and behaviour are never rewritten (see "Assignment 2 guardrails").

## Documentation maintenance

After every repository change, review and update `docs/prd.md` and `docs/architecture.md` so they accurately describe this codebase, update `docs/task.md` when new tasks are implemented.

## Assignment guardrails

- Team 8 data scope is rows 8000–8999 inclusive.
- Treat `source_label` as noisy sampling metadata, not ground truth, and do not expose it to annotators when it could bias labels.
- Never send candidate or golden-set narratives to candidate models before the golden set is complete, resolved, frozen, and committed.
- Labelling is fully manual: two team members independently label every ticket, without conferring, agreement statistics are inter-human and must be described as such.
- Preserve the protocol, both annotator sheets, the agreement result, disagreement resolutions, and the final golden set.
- The Step 2 baseline service must stay synchronous, sequential, and unoptimised: no caching, no request queue, no batching, no background workers. Do not pre-optimise it — optimisation belongs to Assignment 2. (Assignment 1 rule; the Assignment 2 cascade is added behind an off-by-default switch and must leave this behaviour reproducible — see "Assignment 2 guardrails".)
- CPU-only inference only (`num_gpu: 0`); no public model API; the service calls only a local Ollama instance.
- Do not hardcode a specific candidate model into the service itself — `OLLAMA_MODEL` stays environment-driven; candidate selection/pinning lives in `docs/candidate_models.md`, not in `src/app/`.
- Log every request the service handles (success and failure) with the fields listed in `docs/architecture.md` ("Logged fields", Step 2 Baseline Service Architecture).
- Do not commit generated caches (e.g. `runtime/`), secrets, or artefacts that belong to Step 6 (the final recommendation/slides).
- Every public figure in the Step 3 workload model must have a cited, checkable source; every assumption must be labelled as an assumption with a stated reason. Never present an assumption as observed data.
- The ticket-length distribution must be computed from all 1,000 Team 8 rows (`labelling/team8_rows_8000_8999.csv`), not just the 175-ticket golden set.
- Peak/off-peak multipliers in the workload model must conserve the daily total volume, not inflate or shrink it.
- Verify a cited external figure against its primary source before trusting or reusing it — do not carry forward an uncited or unverified number from a reference branch.
- Every Step 4 candidate model must be pinned by exact Ollama tag and manifest digest, with licence text read from the actual manifest/blob, not assumed from memory.
- Do not pull, run, or benchmark any candidate model in Step 4 — that starts Step 5. Obtain digests/licences via the registry's manifest/blob endpoints only.
- Every requirement (response time, throughput, accuracy) must cite a specific figure from `analysis/workload_model.json` or another concrete source — never an unsourced round number.
- `predictions/prediction_record.md` is frozen once committed and must never be edited after the first benchmark run (Step 5) — if a prediction turns out wrong, that goes in Step 6's comparison, not as an edit to this file.
- Accuracy testing must send every golden-set ticket through the real `POST /tickets` endpoint — never bypass the service to score a model directly against Ollama. (Assignment 1 rule; Assignment 2 scores the even-row test set only, still through `POST /tickets`.)
- Load tests must be open-loop (JMeter's `PreciseThroughputTimer` or Open Model Thread Group) — never closed-loop; closed-loop results are not valid evidence for throughput/latency claims.
- Every reported latency/throughput/error number must reconcile with a raw `.jtl` file kept in `jmeter/results/`, or a JSON file in `analysis/accuracy/` — never an unreconciled figure typed into a doc.
- Disclose test-environment limitations (e.g. a co-located load generator) plainly rather than omitting them or presenting results as brief-compliant when they aren't.
- If a candidate fails a requirement, or a result contradicts a Step 4 prediction, say so plainly and diagnose it — do not adjust the requirement, the code, or the prediction record to make it pass after the fact.

## Assignment 2 guardrails

These add to, and do not replace, the Assignment 1 rules above. Where they differ, the Assignment 2 rule applies only to Assignment 2 work.

- Preserve the Assignment 1 baseline: with the cascade switch off (default), `POST /tickets` must behave exactly as in Assignment 1 (single model from `OLLAMA_MODEL`, synchronous, sequential, no caching/queue/batching/workers). Do not edit Assignment 1 result files, `docs/requirements.md` R1–R3, `docs/recommendation.md`, `predictions/prediction_record.md`, or `analysis/accuracy/*.json`.
- Assignment 2 adds files; it does not rewrite Assignment 1 ones. New artefacts: `docs/a2_accuracy_limits.md`, `docs/a2_escalation_rule.md`, `predictions/a2_prediction_record.md`, `analysis/a2/`, `jmeter/results/a2_*`, and an Assignment 2 speed-test row list.
- Fixed from Assignment 1: candidate tags/digests (no new models), the classification prompt and seven categories, the golden set and labels, the three endpoints, CPU-only Ollama, open-loop JMeter with three runs per configuration, and the test machines (no extra CPU/RAM). Report and explain any machine change.
- Not permitted: caching classification results, changing Ollama inference settings (threads, parallelism, context length) between configurations — record them once and hold them constant — fine-tuning, extra classifiers, retrieval, or any component not in the Assignment 1 system.
- The cascade is implemented inside `POST /tickets` (one ticket in, one category out; the caller cannot tell which model answered). Both models are environment-driven (e.g. `OLLAMA_SMALL_MODEL`, `OLLAMA_LARGE_MODEL`); never hardcode a model in `src/app/`. Both models must be resident together (`ollama ps` lists both) before any cascade is tested; if no Assignment 1 pair fits, report that and recommend a single model.
- Extend the request log with the cascade fields listed in `docs/architecture.md` ("Assignment 2 logged fields"); the escalation fraction must be derivable from the logs.
- Commit the odd/even golden-set split (odd rows = tuning, even rows = test) before anything else. Design and tune the escalation rule on the tuning set only; every reported accuracy number and every pass/fail decision uses the test set only.
- The accuracy limits are derived from the top Assignment 1 model's test-set accuracy: overall limit = that accuracy minus 10 percentage points; per-category limit = that category's accuracy minus 15 points. The Assignment 1 70%-per-category requirement does not apply. Show right/wrong counts beside every percentage and flag categories too small for a fair per-category test.
- Commit `predictions/a2_prediction_record.md` and `docs/a2_escalation_rule.md` before the first Assignment 2 benchmark run, and never edit them afterwards. Wrong predictions go in the comparison, not in an edit.
- Reuse of Assignment 1 single-model prediction records is allowed only if digest, prompt, Ollama version and machine are all unchanged; Assignment 1 accuracy was measured on the older i7 / Ollama 0.34.4 environment, so by default re-run test-set accuracy on the final machine and say so in the report.
- Speed tests: arrival rate = one ticket every 2×S seconds (S = middle of three timings of three different typical tickets on the top model, after a restart and warm-up); run length S minutes (minimum 5); same rate, run length and fixed ordered workload (rows outside the golden set, committed) for every configuration; three runs per configuration; Ollama restarted and warmed up before each run (both models for the cascade, confirmed with `ollama ps`); HTTP response timeout at least 10×S seconds and at least 5 minutes; trailing pause longer than the timeout; JMeter on a separate machine; record unfinished requests. Report p50 per run with mean and spread, p95 pooled across the three runs, throughput and error rate; do not report p99; do not reuse Assignment 1 speed figures.
- Compare the test rate with the client's peak rate from `analysis/workload_model.json` and state which side it falls on.
- If the cascade did not beat the best qualifying single model, or no configuration beat the top model, say so plainly and explain with the measured escalation fraction and latencies.
- The Assignment 2 deck is at most 8 slides (`GroupNum_A2.pptx`); every figure on slides 4–7 traces to a `.jtl` or log in the repository. The Assignment 1 12-slide deck rule is unchanged.

## Validation

Run the reproducibility commands recorded in `README.md` and `docs/task.md`. Every final label must reconcile with either agreement between the two annotator sheets or a recorded disagreement resolution before this branch is considered complete.
