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
- Do not pin or hardcode a specific candidate model in this branch — model selection and pinning by tag/digest belongs to Step 4.
- Log every request the service handles (success and failure) with the fields listed in `docs/architecture.md` ("Logged fields", Step 2 Baseline Service Architecture).
- Do not commit generated caches (e.g. `runtime/`), secrets, or benchmark/analysis artefacts that belong to later steps (Steps 5–6).
- Every public figure in the Step 3 workload model must have a cited, checkable source; every assumption must be labelled as an assumption with a stated reason. Never present an assumption as observed data.
- The ticket-length distribution must be computed from all 1,000 Team 8 rows (`labelling/team8_rows_8000_8999.csv`), not just the 175-ticket golden set.
- Peak/off-peak multipliers in the workload model must conserve the daily total volume, not inflate or shrink it.
- Verify a cited external figure against its primary source before trusting or reusing it — do not carry forward an uncited or unverified number from a reference branch.

## Validation

Run the reproducibility commands recorded in `README.md` and `docs/task.md`. Every final label must reconcile with either agreement between the two annotator sheets or a recorded disagreement resolution before this branch is considered complete.
