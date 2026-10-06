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