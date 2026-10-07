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

## Not yet done / left for later steps

- [ ] Pin and pull real candidate Ollama models (Step 4); `.env.example`'s `OLLAMA_MODEL` is a placeholder with no recorded digest yet.
- [ ] Automated tests for the service (none exist yet; validation so far was manual curl-based smoke testing).
- [ ] The malformed/off-format model output path (`categories.parse_category` raising on a non-matching reply → 502) has never actually fired against a real model — it's implemented but unexercised, since the model has so far always replied with an exact category.
- [ ] `logs/requests.jsonl` currently holds this development smoke-test traffic (a handful of tickets, a couple of induced failures) — clear it before the first real benchmark run in Step 5 so dev noise doesn't mix with reported evidence.

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

## Not yet done / left for later steps

- [ ] These rates aren't yet used anywhere — Step 4 must derive testable response-time/throughput/accuracy requirements from this model, and Step 5's JMeter plans must use these submission/search rates (and this ticket-length distribution) for realistic-load scenarios.
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
