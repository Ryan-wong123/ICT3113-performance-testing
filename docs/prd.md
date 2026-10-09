# Step 1 Golden Test Set PRD

## Objective

Create a frozen, reproducible golden test set of 150–200 Team 8 complaint tickets for later classification-accuracy measurement. The completed set contains 175 tickets.

## Scope and constraints

- Use only rows 8000–8999 from `ict3113_tickets.csv`.
- Treat `source_label` as noisy sampling metadata, never as the final label, and do not show it to annotators.
- Define the seven permitted categories in a written protocol before annotation.
- Two team members label every ticket independently, without conferring; preserve both sheets, the agreement statistic, and every disagreement resolution.
- Freeze and commit the final set before candidate model benchmarking.
- Do not send candidate or final golden-set narratives to candidate models before that freeze.

## Required evidence

| Evidence | Location |
| --- | --- |
| Full course dataset | `labelling/ict3113_tickets.csv` |
| Team scope extract | `labelling/team8_rows_8000_8999.csv` |
| Protocol | `labelling/labelling_protocol.md` |
| Independent annotator sheets | `labelling/annotator_A.csv`, `labelling/annotator_B.csv` |
| Agreement statistic | `labelling/agreement_results.md` |
| Reviewed disagreements | `labelling/disagreement_resolutions.csv` |
| Frozen final set | `labelling/golden_test_set.csv` |

## Method

Labelling is fully manual: two team members each independently label all 175 tickets, following the written protocol, without conferring and without seeing `source_label`.

## Acceptance criteria

- The final set has 150–200 unique rows, all in the Team 8 range (8000–8999).
- Each final label is one of the required seven categories.
- Both annotator sheets contain the same 175 rows.
- Cohen's kappa between the two annotators is calculated and reported as inter-human agreement.
- Each disagreement between the two annotators has a resolution with a rationale.
- Every row in `golden_test_set.csv` matches the two annotators' agreed label, or the recorded resolution where they disagreed.

---

# Step 2 Baseline Service PRD

## Objective

Build the Ticket Triage Service exactly as specified in the assignment brief: a synchronous, single-model, unoptimised baseline that classifies one ticket narrative per request by calling a local CPU-only Ollama model. This baseline exists to be measured in Step 5, not to be fast.

## Scope and constraints

- Three endpoints only: `POST /tickets`, `GET /search`, `GET /stats`.
- Classification is synchronous: `POST /tickets` does not return until Ollama has classified the ticket.
- Deliberately naive: sequential model calls, no caching, no request queue, no batching, no background workers, no pre-optimisation.
- CPU-only inference. `num_gpu: 0` is passed to Ollama explicitly, and inference is serialised behind a lock so the baseline never issues parallel model calls.
- No public model API — the service only ever calls a local Ollama instance over HTTP.
- The service starts empty; tickets enter only through `POST /tickets`. The golden-set CSV is never bulk-loaded into the service.
- Every request is logged (fields listed in `docs/architecture.md`, "Logged fields") for later reconciliation with JMeter results, per `docs/PROJECT_CONTEXT.md` Section 10.
- Runs in Docker via `docker compose up`.

## Required evidence

| Evidence | Location |
| --- | --- |
| Service source | `src/app/` (`main.py`, `ollama_client.py`, `storage.py`, `categories.py`, `config.py`, `request_logging.py`) |
| Container definition | `Dockerfile`, `docker-compose.yml` |
| Dependencies | `requirements.txt` |
| Configuration template | `.env.example` |
| Request logs (generated at runtime) | `logs/requests.jsonl` |

## Acceptance criteria

- `POST /tickets` accepts one narrative, classifies it into exactly one of the seven categories, stores it, and returns the assigned category; a narrative that fails Ollama's output contract or an unreachable Ollama both surface as a clear error (`502`) and are logged, not silently misclassified.
- `GET /search?q=...` returns previously stored tickets whose narrative matches the query.
- `GET /stats` returns ticket counts grouped by assigned category.
- No two model calls run concurrently (verified: an explicit lock serialises every classification).
- Every request — success or failure — produces one JSON log line with timestamp, request id, endpoint, model, ticket row (if supplied), start/end time, latency, HTTP status, predicted category, and error.
- The service builds and runs under `docker compose up`, reaching a local Ollama instance on the host.

---

# Step 3 Workload Model PRD

## Objective

Quantitatively model the client's expected ticket-submission and search traffic, and the shape of the narratives themselves, so Step 4's requirements are derived from an explicit, sourced model rather than guessed.

## Scope and constraints

- Estimate `POST /tickets` volume (annual/monthly/weekly/daily, average/peak/off-peak) and `GET /search` volume, from a cited public source.
- Cite every figure; separate observed public data from scenario assumptions. Do not present an assumption as an observed fact.
- Compute the ticket-length distribution (character and word count: min, max, mean, p50, p95, p99, and bucketed histograms) from all 1,000 of Team 8's own narratives, not just the 175-ticket golden set.
- Exclude `GET /stats` and `/health` from the modelled client workload — they're operational traffic, not complaint-processing demand.
- Keep the model regenerable from source data and stated assumptions, not hand-edited.

## Required evidence

| Evidence | Location |
| --- | --- |
| Workload model document (evidence, assumptions, calculations, sources) | `docs/workload_model.md` |
| Machine-readable workload model | `analysis/workload_model.json` |
| Ticket-length statistics generator | `scripts/calculate_ticket_length_stats.py` |
| Machine-readable ticket-length statistics | `analysis/ticket_length_statistics.json` |
| Workload model generator | `scripts/build_workload_model.py` |
| Unit tests for the generator | `tests/test_build_workload_model.py` |

## Acceptance criteria

- Every public figure has a cited, checkable source; every assumption is labelled as an assumption with a stated reason.
- Peak and off-peak multipliers conserve the daily total (they don't inflate or shrink annual volume by introducing a peak).
- The ticket-length distribution is computed from the full 1,000-row Team 8 extract (`labelling/team8_rows_8000_8999.csv`), reproducibly.
- Both JSON artefacts regenerate byte-for-byte-equivalent numbers from the two scripts, and the generator's unit tests pass.
- The model states its own limitations and what would trigger a re-baseline (e.g. real client telemetry becoming available).

---

# Step 4 PRD — Candidate Models, Requirements, Predictions

## Objective

Choose the candidate model set, set testable performance/accuracy requirements derived from Step 3's workload model, and freeze a falsifiable prediction record — all before any candidate model is pulled, run against the golden set, or load-tested.

## Scope and constraints

- 3–5 candidate models, spanning at least two parameter-size classes, each pinned by exact Ollama tag and manifest digest.
- At least one response-time requirement, one throughput requirement, and one accuracy requirement (overall + per-category), each a testable number/percentile/load-condition, justified from Step 3's workload model.
- If the workload model implies peak periods, requirements must cater for the peak, not the average.
- A prediction record covering: expected bottleneck and why; per-candidate expected accuracy and single-request latency; expected hardest categories and why — specific enough to be provably wrong.
- The prediction record must be frozen (committed) before the first benchmark run and never revised afterward.
- Do not pull, run, or benchmark any candidate model before this record is committed.

## Required evidence

| Evidence | Location |
| --- | --- |
| Candidate model selection, pins, licences, justification | `docs/candidate_models.md` |
| Performance and accuracy requirements | `docs/requirements.md` |
| Prediction record (frozen) | `predictions/prediction_record.md` |

## Acceptance criteria

- Each candidate model's tag and manifest digest is independently verifiable (not copied from memory) and its licence is quoted from the actual licence text, not assumed.
- Every requirement cites the specific Step 3 workload-model figure it's derived from, plus non-workload justification (usability, misrouting cost) where relevant.
- Every prediction is a specific number or named category, with its reasoning method disclosed, not a vague directional claim.
- Nothing in this step touches a real candidate model — no pulls, no inference calls, no benchmark runs.

---

# Step 5 PRD — Test and Measure

## Objective

Actually pull, run, and measure all three frozen candidates against the frozen golden set and open-loop JMeter load, to test the Step 4 requirements and predictions against reality.

## Scope and constraints

- Describe the test environment (hardware, software, network path, and factors that could make results unrepresentative) before reporting any numbers. Final load/stress evidence must use a separate JMeter Machine B and service/Ollama Machine A; co-located files may remain only as clearly labelled historical pipeline-validation evidence.
- Accuracy: every golden-set ticket through the real `POST /tickets` endpoint, per candidate, never bypassing the service.
- Load: JMeter, open-loop only (`PreciseThroughputTimer` or Open Model Thread Group — never closed-loop), at multiple arrival rates, 3 repeats per configuration, reporting p50/p95/p99/completed throughput/successful throughput/error rate. Offered arrivals must not be mislabeled as achieved throughput; queued drain time after arrivals stop remains part of the throughput measurement. Raw `.jtl` files are kept in the repository.
- Repeated-load reporting: retain the per-run values and report the arithmetic mean plus observed minimum–maximum spread across the three repeats; pooled percentiles may be shown additionally but do not replace this repeatability view.
- Stress: at least one test that finds a genuine limit (unbounded latency growth, saturating throughput, or rising errors) for at least one candidate.
- Diagnose the bottleneck with evidence, not assertion.
- Every reported number must reconcile with a kept `.jtl` file or `analysis/accuracy/*.json` file.
- Explain how the environment-specific measurements can and cannot scale to the client's deployment; do not extrapolate linearly from CPU core count.

## Required evidence

| Evidence | Location |
| --- | --- |
| Test environment description and known limitations | `docs/test_environment.md` |
| Test playbooks (accuracy, load, stress) | `docs/test_playbook.md` |
| Accuracy results, per-category, confusion matrices | `docs/accuracy_results.md`, `analysis/accuracy/*.json` |
| Load/stress results, requirement reconciliation, bottleneck diagnosis | `docs/load_test_results.md` |
| Raw JMeter samples | `jmeter/results/*_remote.jtl` (final separate-machine evidence); older non-remote files retained for comparison |
| JMeter test plan and load-test narrative pool | `jmeter/test_plans/` |

## Acceptance criteria

- Every candidate model is pulled and actually run (not just referenced by digest, as in Step 4).
- Every requirement from `docs/requirements.md` (R1–R3) is explicitly checked against measured data for every candidate, with a clear pass/fail.
- The stress test's "limit" claim is supported by a genuine, visible divergence in the data (not asserted without evidence).
- The 40/min and 60/min stress configurations each have three retained runs, with per-run and across-run reporting. The conclusion must preserve the observed variance: 40/min was consistently stable, while 60/min was unreliable rather than universally failing.
- Any place a candidate fails a requirement is noted plainly, with a diagnosis, not hidden or glossed over.
- The prediction record (`predictions/prediction_record.md`) is not edited — divergences between prediction and actual result are recorded in the results docs, not by rewriting the prediction.

---

# Step 6 PRD — Recommendation

## Objective

Answer the client's question — given CPU-only hardware and no public model API, what should they deploy and what service quality can be promised — with a recommendation that follows from this team's own requirements and measurements, plus a prediction-by-prediction account of where Step 4 was wrong.

## Scope and constraints

- The recommendation must hold against R1–R3 as written in `docs/requirements.md`; requirements are not adjusted after the fact, and a finding that no candidate meets them is reported plainly.
- Take an explicit position on whether a misrouted ticket or a slow triage costs the client more, grounded in the workload model and measurements.
- Every figure must come from committed evidence (`analysis/accuracy/*.json`, `jmeter/results/*_remote.jtl`, `logs/requests.jsonl`, `analysis/workload_model.json`) via a regenerable script. Measurements combined with workload assumptions are labelled as derived estimates; analysis not run through the service is labelled offline.
- Compare latency predictions on the hardware they were made for (the i7 accuracy-run measurements); the prediction record forbids using the later hardware change to excuse a miss.
- `source_label` may be scored against the frozen golden labels as a status-quo baseline, never used as ground truth.
- No service, golden-set, prediction-record, or requirement changes.

## Required evidence

| Evidence | Location |
| --- | --- |
| Recommendation, position, requirement defence, predictions vs actual, account of errors, conditions | `docs/recommendation.md` |
| Machine-readable Step 6 figures | `analysis/step6_analysis.json` |
| Generator | `scripts/build_step6_analysis.py` |
| Unit tests for its statistics | `tests/test_build_step6_analysis.py` |

## Acceptance criteria

- Every number in `docs/recommendation.md` appears in `analysis/step6_analysis.json` or the Step 5 results documents, and the JSON regenerates unchanged from the committed inputs.
- Every frozen prediction has an actual value and a right/partly right/wrong verdict with an evidence-based explanation.
- Every unmet requirement is stated plainly per candidate.
- Uncertainty is quantified (confidence intervals, paired significance test) and every limit of the recommended pilot is disclosed.
