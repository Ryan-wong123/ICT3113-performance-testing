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
- Do not commit generated caches, secrets, or unrelated service/benchmark artefacts to this Step 1 branch.

## Validation

Run the reproducibility commands recorded in `README.md` and `docs/task.md`. Every final label must reconcile with either agreement between the two annotator sheets or a recorded disagreement resolution before this branch is considered complete.
