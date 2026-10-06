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
- Do not commit generated caches (e.g. `runtime/`), secrets, or benchmark/analysis artefacts that belong to later steps (Steps 3–6).

## Validation

Run the reproducibility commands recorded in `README.md` and `docs/task.md`. Every final label must reconcile with either agreement between the two annotator sheets or a recorded disagreement resolution before this branch is considered complete.
