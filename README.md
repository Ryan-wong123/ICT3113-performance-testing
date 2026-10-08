# ICT3113 Assignment 1 — Team 8

## Step 1 — Golden Test Set

## Scope

- Team 8 data is limited to source rows **8000–8999**.
- The golden set was labelled manually: two team members independently labelled all 175 tickets, without conferring.
- The frozen golden set contains **175** unique Team 8 tickets.
- No candidate model may receive a candidate or final golden-set narrative before the golden set is frozen and committed.

## Contents

- `labelling/ict3113_tickets.csv` — supplied course dataset.
- `labelling/team8_rows_8000_8999.csv` — verified Team 8 scope (rows 8000–8999).
- `labelling/labelling_protocol.md` — category definitions and decision rules, written before labelling.
- `labelling/annotator_A.csv`, `labelling/annotator_B.csv` — the two independent human label sheets.
- `labelling/agreement_results.md` — inter-human Cohen's kappa and observed agreement.
- `labelling/disagreement_resolutions.csv` — every disagreement, its final label, and rationale.
- `labelling/golden_test_set.csv` — final frozen labels (`row,narrative,final_label`).

## Reproducibility

The labelling itself is manual human judgement and is not something a script regenerates. Reproducibility here means two things:

1. **Verify the evidence.** Anyone can recompute the agreement statistic and confirm the frozen set reconciles with the two annotator sheets and the disagreement log, directly from the committed CSVs (command below).
2. **Repeat the procedure.** Anyone can redo the labelling from scratch and arrive at an equivalent result, because the full procedure — category definitions, decision rules for edge cases, and the independent-labelling process — is written down in `labelling/labelling_protocol.md`.

### Verify the evidence

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

This confirms: the two annotator sheets and the final set cover the same 175 rows; every disagreement between the annotators has a matching recorded resolution; every final label matches either agreement between the annotators or its recorded resolution; and it recomputes the observed agreement and Cohen's kappa reported in `labelling/agreement_results.md`.

## Step 2 — Baseline Service

A synchronous, unoptimised Ticket Triage Service: `POST /tickets`, `GET /search`, `GET /stats`, backed by SQLite, calling a local CPU-only Ollama instance. See `docs/prd.md` and `docs/architecture.md` for the full spec.

### Contents

- `src/app/` — the FastAPI service (`main.py`, `ollama_client.py`, `storage.py`, `categories.py`, `config.py`, `request_logging.py`).
- `Dockerfile`, `docker-compose.yml`, `requirements.txt`, `.env.example`.

### Run it

1. Pull and run a model locally with Ollama on the host machine (`ollama pull llama3.2:3b`, or whichever candidate model you're testing), and make sure `ollama serve` is reachable at `http://localhost:11434`.
2. Copy `.env.example` to `.env` and adjust `OLLAMA_MODEL` if needed.
3. `docker compose up --build`
4. The service listens on `http://localhost:8000`.

```bash
curl -X POST http://localhost:8000/tickets -H "Content-Type: application/json" \
  -d '{"narrative": "My card was charged twice for the same purchase", "ticket_row": 8762}'

curl "http://localhost:8000/search?q=charged"

curl http://localhost:8000/stats
```

Every request is appended to `logs/requests.jsonl` (bind-mounted out of the container) with the fields required for later reconciliation with JMeter results: timestamp, request id, endpoint, model, ticket row, start/end time, latency, HTTP status, predicted category, and error.

### Verified

Built and run for real with `docker compose up --build` against a real local Ollama instance (`llama3.2:3b`), not just a stub:

- All three endpoints work end to end: `POST /tickets` correctly classified 4 real tickets (e.g. a duplicate card charge → `Credit card`, a missing wire transfer → `Money transfer or service`); `GET /search` (including case-insensitivity and `limit`); `GET /stats`.
- **CPU-only inference is genuinely enforced**, not just requested: this host has an NVIDIA GPU, but `ollama ps` reports `100% CPU` for the loaded model.
- Sequential processing confirmed under concurrent load — two simultaneous `POST /tickets` calls did not overlap in Ollama call time (visible in `logs/requests.jsonl` request-start/end timestamps).
- Input validation: empty narrative and an out-of-Team-8-range `ticket_row` both rejected with 422.
- Failure path: Ollama unreachable → 502, logged with the error.
- Every one of the above produced a correctly-shaped log line in `logs/requests.jsonl`.

## Step 3 — Workload Model

A quantitative model of the client's expected traffic and ticket shape, built from a cited public benchmark plus explicit, labelled assumptions — not from a real client's telemetry (there isn't one). See `docs/workload_model.md` for the full model, `docs/prd.md`/`docs/architecture.md` for scope and design.

### Contents

- `docs/workload_model.md` — evidence, assumptions (each with an ID and stated reason), calculated rates, and stated limitations.
- `scripts/calculate_ticket_length_stats.py` → `analysis/ticket_length_statistics.json` — character/word-count distribution over all 1,000 Team 8 narratives.
- `scripts/build_workload_model.py` → `analysis/workload_model.json` — annual/peak/off-peak submission and search rates.
- `tests/test_build_workload_model.py` — unit tests for the generator.

### Reproduce it

```bash
python3 scripts/calculate_ticket_length_stats.py
python3 scripts/build_workload_model.py
python3 -m unittest tests.test_build_workload_model -v
```

### Verified

- Both scripts were run against the actual repo data (`labelling/team8_rows_8000_8999.csv`, all 1,000 rows) and regenerate the committed JSON exactly.
- All 4 unit tests in `tests/test_build_workload_model.py` pass.
- Every cited public figure in `docs/workload_model.md` was checked directly against the CFPB's own source text — not assumed correct from the prior draft. Confirmed verbatim/near-verbatim against the actual CFPB 2024 Consumer Response Annual Report PDF and the Consumer Complaint Database's disclaimer page: the 3,187,900 total-complaints figure, the 98%-via-website figure, the 2,829,400 (89%) sent-to-companies figure, and the "not a statistical sample" disclaimer.

Downstream use: Step 4 derived R1/R2 from this workload model, and Step 5 used the derived peak rate as the reference point for its deliberately accelerated test rates.

## Step 4 — Candidate Models, Requirements, Predictions

Three candidate Ollama models pinned by tag and manifest digest, three testable requirements derived from the Step 3 workload model, and a frozen prediction record — all written before any candidate model is pulled or benchmarked. See `docs/candidate_models.md`, `docs/requirements.md`, `predictions/prediction_record.md`.

### Contents

- `docs/candidate_models.md` — `llama3.2:1b`, `llama3.2:3b`, `qwen2.5:7b`: tags, manifest digests, weights sizes, licences, and why this set.
- `docs/requirements.md` — R1 (p95 `POST /tickets` < 10s at peak), R2 (≥8 tickets/hour sustained), R3 (≥85% overall accuracy, no category below 70%), each tied to a Step 3 figure.
- `predictions/prediction_record.md` — frozen predictions: bottleneck, per-model accuracy/latency, hardest categories — must not be edited after Step 5's first benchmark run.

### Verified

- Every candidate's manifest digest was obtained from the Ollama registry API (not copied from memory or a reference branch) and cross-checked: the `llama3.2:3b` digest computed this way matched `ollama list`'s local model ID exactly (first 12 hex chars).
- Every licence was read from the actual licence-text blob referenced in each model's manifest, not assumed: `llama3.2:1b`/`llama3.2:3b` carry Meta's custom Llama 3.2 Community License + Acceptable Use Policy; `qwen2.5:7b` carries Apache License 2.0.
- No candidate model was pulled or run in this step — only small manifest/licence-text lookups (a few KB each), per the team's decision to defer the multi-GB pulls to Step 5.
- Every requirement number traces to a specific figure in `analysis/workload_model.json` (Step 3) or an already-observed number in `logs/requests.jsonl` (Step 2) — none are invented.
- Every prediction's reasoning method is disclosed in `predictions/prediction_record.md` (e.g. latency predictions are scaled from `llama3.2:3b`'s already-observed warm latency by weights-file-size ratio), so the prediction can be judged, not just trusted.

Step 5 subsequently pulled and verified all three pinned models, measured R1–R3, and preserved the frozen prediction record unchanged.

## Step 5 — Test and Measure

All three candidates pulled and actually run: 175 golden-set tickets each through the real `POST /tickets` endpoint, plus an open-loop JMeter matrix and stress test with 3 repeats per reported rate. Final load was generated from separate Machine B against service/Ollama Machine A. See `docs/test_environment.md`, `docs/test_playbook.md`, `docs/accuracy_results.md`, `docs/load_test_results.md`.

### Headline result

**No candidate meets all three Step 4 requirements.**

| Requirement | `llama3.2:1b` | `llama3.2:3b` | `qwen2.5:7b` |
| --- | --- | --- | --- |
| R1 — p95 latency < 10s | PASS (2.067s) | PASS (2.498s) | PASS (4.840s; n=9 caveat) |
| R2 — ≥8 tickets/hour | PASS | PASS | PASS |
| R3 — ≥85% accuracy, no category <70% | FAIL (28.0%) | FAIL (32.0%) | FAIL (78.9%) |

`qwen2.5:7b` is the clear accuracy leader (78.9% vs 28–32% for the two smaller models) but the clear latency laggard; the reverse is true of `llama3.2:1b`. Full per-category breakdowns and confusion matrices are in `docs/accuracy_results.md`.

### An unplanned but important finding

The baseline never sets a `temperature` or `seed` on its Ollama calls. Replaying the exact same prompt against the same model twice produced two different valid-format answers — genuine non-determinism, not a bug. This is disclosed in `docs/accuracy_results.md` since it means a repeat accuracy run would likely not reproduce the exact same percentage (though the large gap between candidates is expected to be robust to this).

### Bottleneck (confirmed, matching the Step 4 prediction made before any of this data existed)

Ollama's CPU-bound inference time, serialised behind the service's single classification lock. On the final i9-14900HX Machine A, all three `llama3.2:1b` runs at 40/min were stable. At 60/min, one run collapsed with 154/181 failures, a second developed a 66.8-second p95 tail, and a third remained stable. The supported conclusion is therefore a reliability boundary between 40 and 60/min—not that 60/min fails identically on every run.

### Verified, not just run once and trusted

- A first version of the JMeter test plan crashed every run; root-caused by inspecting JMeter's own bundled javadoc for the real timer property schema (not guessed again), fixed, and smoke-tested before collecting any real data.
- Every reported number traces to a raw `.jtl` file in `jmeter/results/` or a JSON file in `analysis/accuracy/` — see `docs/load_test_results.md` and `docs/accuracy_results.md` for the reconciliation.
- `docs/test_environment.md` records both machines' exact hardware/software, the routed network topology, and the distinction between final `_remote.jtl` evidence and older co-located pipeline-validation files.

Not yet done: `predictions/prediction_record.md` has not been touched (correctly — it's frozen); the formal predictions-vs-actual comparison and the final recommendation are Step 6.
