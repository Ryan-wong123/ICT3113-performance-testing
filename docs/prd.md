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
