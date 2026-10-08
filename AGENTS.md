# Project agent instructions

`docs/PROJECT_CONTEXT.md` is the authoritative assignment brief and team-decisions record; `docs/task.md` records the tasks done.

## Documentation maintenance

After every repository change, review and update `docs/prd.md` and `docs/architecture.md` so they accurately describe this codebase, update `docs/task.md` when new tasks are implemented.

## Assignment guardrails

- Team 8 data scope is rows 8000–8999 inclusive.
- Treat `source_label` as noisy sampling metadata, not ground truth, and do not expose it to annotators when it could bias labels.
- Never send candidate or golden-set narratives to candidate models before the golden set is complete, resolved, frozen, and committed.
- Labelling is fully manual: two team members independently label every ticket, without conferring, agreement statistics are inter-human and must be described as such.
- Preserve the protocol, both annotator sheets, the agreement result, disagreement resolutions, and the final golden set.
- The Step 2 baseline service must stay synchronous, sequential, and unoptimised: no caching, no request queue, no batching, no background workers. Do not pre-optimise it — optimisation belongs to Assignment 2.
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
- Accuracy testing must send every golden-set ticket through the real `POST /tickets` endpoint — never bypass the service to score a model directly against Ollama.
- Load tests must be open-loop (JMeter's `PreciseThroughputTimer` or Open Model Thread Group) — never closed-loop; closed-loop results are not valid evidence for throughput/latency claims.
- Every reported latency/throughput/error number must reconcile with a raw `.jtl` file kept in `jmeter/results/`, or a JSON file in `analysis/accuracy/` — never an unreconciled figure typed into a doc.
- Disclose test-environment limitations (e.g. a co-located load generator) plainly rather than omitting them or presenting results as brief-compliant when they aren't.
- If a candidate fails a requirement, or a result contradicts a Step 4 prediction, say so plainly and diagnose it — do not adjust the requirement, the code, or the prediction record to make it pass after the fact.

## Validation

Run the reproducibility commands recorded in `README.md` and `docs/task.md`. Every final label must reconcile with either agreement between the two annotator sheets or a recorded disagreement resolution before this branch is considered complete.
