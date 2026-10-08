# Step 4: Performance and Accuracy Requirements

Each requirement below is a number, a percentile (where relevant), and a load condition, per the assignment brief. Each applies to **every candidate model independently** (Step 6's recommendation is exactly about which candidates meet which requirements). All rate figures are taken directly from `analysis/workload_model.json` (Step 3); none are invented here.

## R1 — Response time

> Under the peak expected arrival rate (7.278311 tickets/hour, i.e. one ticket roughly every 8.24 minutes — `analysis/workload_model.json`, `periods.peak.submissions.per_hour`), **p95 `POST /tickets` latency must remain below 10 seconds**, measured after the model is warm (excludes the one-time model load into memory on first request).

**Justification:**
- At the peak rate, inter-arrival time (≈8.24 min) is so much larger than any plausible single-request latency that this requirement is really "does a single warm classification finish in acceptable time," not a queueing/concurrency test — that's intentional; Step 3's own workload model already notes the realistic rate is too low to stress the service, and a separate stress test (Step 5) exists precisely to find the actual breaking point at unrealistic rates.
- 10 seconds is chosen from the *already-observed* single-request warm latency for one candidate (`llama3.2:3b`: mean 2.79s across 3 clean warm requests during Step 2 development — 2697.7ms, 2704.1ms, 2978.2ms, in `logs/requests.jsonl`), giving roughly 3.6× headroom for `qwen2.5:7b`'s expected slower inference (see `predictions/prediction_record.md`) before it would be considered to violate this requirement. A number tighter than this would almost certainly fail the larger candidate by construction rather than by genuine measurement; a number far looser would not be a meaningful requirement at all.
- Usability: this is a backend classification call in a synchronous baseline, not an interactive UI action — 10 seconds is generous for a backend job, but not so generous that it hides an actually-unacceptable model (e.g. multi-minute latency).

## R2 — Throughput

> The service must sustain **at least 8 ticket classifications per hour** indefinitely, for each candidate model, under open-loop arrival at the peak expected rate (7.278311/hour) — i.e. the queue must not grow unboundedly at the rate the workload model itself predicts.

**Justification:**
- Directly from `analysis/workload_model.json`, `periods.peak.submissions.per_hour` = 7.278311, rounded up to 8/hour as a clean, slightly conservative target (a service that cannot sustain even the workload model's own predicted peak rate indefinitely is not viable at all).
- This is a deliberately modest bar, not a capacity target — every candidate is expected to clear it easily, since even the slowest predicted candidate (`qwen2.5:7b`, predicted ≈8s/ticket warm — see predictions) implies a theoretical max of ~450/hour if run back-to-back, far above 8/hour. The requirement exists so that Step 5 has an explicit, falsifiable pass/fail line tied to the workload model, not just a reported number with no threshold. Finding the *actual* upper limit (where throughput saturates or errors appear) is the separate Step 5 stress test, not this requirement.

## R3 — Classification accuracy

> On the frozen 175-ticket golden test set (`labelling/golden_test_set.csv`), each candidate model must achieve **overall accuracy ≥ 85%**, and **no single category below 70% accuracy**, measured by sending every golden-set ticket through `POST /tickets` and comparing the returned category against `final_label`.

**Justification:**
- **Overall 85%:** the raw `source_label` in the course dataset is known to be noisy — that's the entire reason Step 1 built a separate golden set rather than trusting it. A model performing only marginally better than that noisy baseline would provide little value over the status quo (a human manually reading every ticket); 85% is set as a bar clearly distinguishing "materially better than noisy self-reported labels" from "roughly as unreliable."
- **Per-category floor of 70%, lower than the overall bar:** Step 1's own disagreement evidence shows some category *pairs* are genuinely harder to separate even for two independent trained humans — of 175 tickets, 5 disagreements occurred, and 3 of those (rows 8590, 8699, 8762 — see `labelling/agreement_results.md` and `labelling/labelling_protocol.md`'s Revision log) required *new* protocol rules because no existing rule covered that category pair (`Money transfer or service` vs `Credit card`; `Credit reporting` vs `Debt collection`; `Credit card` vs `Bank account or service`). If trained humans following a written protocol only reached agreement on these pairs after the protocol itself was extended, it is realistic that a model — with no equivalent of that discussion-and-resolution step — will do measurably worse specifically on tickets touching those categories. A single organisation-wide 85% floor applied per-category would likely fail on `Debt collection` (only 14 of 175 golden tickets, the smallest category, and involved in 2 of the 5 disagreements) for reasons that reflect genuine task ambiguity, not a fixable model defect — so the per-category floor is set lower, at 70%, while still being a real, testable requirement no category may fall beneath.
- **Staffing/misrouting cost:** in the client's real workflow, a misrouted ticket means a human still has to notice and re-route it — the requirement is not "the model must be perfect" but "the model must be reliably better than noisy self-labelling, on every category, not just on average" (a model that is 95% accurate overall but 30% accurate on one category would silently create a costly blind spot for that category, which an aggregate-only requirement would hide).

## Peak-condition note

All three requirements are explicitly anchored to the **peak** period from Step 3's workload model, not the 24-hour average, per the brief's instruction that "If your model implies peak periods, your requirements must cater for the peak." R1 and R2 use `periods.peak...` values from `analysis/workload_model.json`; R3 has no time-of-day dimension (accuracy is measured once per candidate against the static golden set) so it isn't peak/off-peak-conditional by nature.

## Not yet done

- These requirements are not yet measured against any candidate — that's Step 5.
- No requirement yet exists for `GET /search` latency specifically (the brief allows either `POST /tickets` or `GET /search` latency as the response-time requirement; this team chose `POST /tickets` since it's the higher-stakes, model-dependent path — `GET /search` is a plain SQLite substring query and was already observed to complete in 16–22ms in Step 2 testing, an order of magnitude faster than any plausible requirement would need to guard against).
