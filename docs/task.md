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
