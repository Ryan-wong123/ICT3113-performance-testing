# Inter-Annotator Agreement — Team 8 Golden Test Set

## Method

Two team members (Annotator A, Annotator B) independently labelled all 175 candidate tickets from Team 8's rows (8000–8999), following `labelling_protocol.md`, without conferring and without seeing `source_label`. Agreement is calculated directly between the two independent human sheets (`annotator_A.csv`, `annotator_B.csv`).

This is **inter-human** agreement.

## Overall result

- Tickets labelled: 175
- Rows in agreement: 170
- Rows in disagreement: 5
- Observed agreement (p_o): 0.9714 (97.14%)
- Expected chance agreement (p_e): 0.1524
- Cohen's kappa: 0.9663 (almost perfect agreement, Landis & Koch 1977 scale)

## Per-category support and agreement

Support = number of tickets either annotator assigned to that category. Agreement rate = rows both annotators agreed on, divided by the union of rows either annotator assigned to that category (diagonal / (A + B − diagonal)).

| Category | Annotator A count | Annotator B count | Rows both agreed | Category agreement rate |
| --- | --- | --- | --- | --- |
| Bank account or service | 28 | 29 | 28 | 96.6% |
| Consumer loan | 24 | 23 | 23 | 95.8% |
| Credit card | 23 | 22 | 21 | 87.5%* |
| Credit reporting | 38 | 38 | 37 | 94.9% |
| Debt collection | 14 | 16 | 14 | 87.5%* |
| Money transfer or service | 24 | 23 | 23 | 95.8% |
| Mortgage | 24 | 24 | 24 | 100% |

\* Credit card and Debt collection show the lowest agreement rate. Credit card is touched by 3 of the 5 disagreements (rows 8384, 8590, 8762) and Debt collection by 2 (rows 8384, 8699) — see the disagreement summary below.

## Annotator confusion matrix (A rows vs B columns)

Off-diagonal cells are the 5 disagreements; every other cell on a row/column pair is 0.

| A \ B | Bank account | Consumer loan | Credit card | Credit reporting | Debt collection | Money transfer | Mortgage |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Bank account or service | 28 | 0 | 0 | 0 | 0 | 0 | 0 |
| Consumer loan | 0 | 23 | 0 | 1 | 0 | 0 | 0 |
| Credit card | 1 | 0 | 21 | 0 | 1 | 0 | 0 |
| Credit reporting | 0 | 0 | 0 | 37 | 1 | 0 | 0 |
| Debt collection | 0 | 0 | 0 | 0 | 14 | 0 | 0 |
| Money transfer or service | 0 | 0 | 1 | 0 | 0 | 23 | 0 |
| Mortgage | 0 | 0 | 0 | 0 | 0 | 0 | 24 |

## Disagreement summary

| Row | Annotator A | Annotator B | Category pair | Final label | Revealed a protocol gap? |
| --- | --- | --- | --- | --- | --- |
| 8158 | Consumer loan | Credit reporting | Consumer loan / Credit reporting | Consumer loan | No — resolved directly under existing Rule 4 |
| 8384 | Credit card | Debt collection | Credit card / Debt collection | Credit card | No — resolved directly under existing Rule 5 |
| 8590 | Money transfer or service | Credit card | Money transfer / Credit card | Money transfer or service | **Yes** — protocol had no rule for this pair; added Rule 9 |
| 8699 | Credit reporting | Debt collection | Credit reporting / Debt collection | Credit reporting | **Yes** — protocol had no rule for this pair; added Rule 10 |
| 8762 | Credit card | Bank account or service | Credit card / Bank account | Credit card | **Yes** — protocol had no rule for this pair; added Rule 11 |

Full rationale for each resolution is in `disagreement_resolutions.csv`. The three protocol gaps are closed by the dated revisions in the "Revision log" section of `labelling_protocol.md` (Rules 9–11).

## Reproducing this result

```bash
python3 -c "
import csv
from collections import Counter, defaultdict

def load(f):
    with open(f, encoding='utf-8') as fh:
        return {row['row']: row['human_label'] for row in csv.DictReader(fh)}

a = load('labelling/annotator_A.csv')
b = load('labelling/annotator_B.csv')
n = len(a)
po = sum(1 for k in a if a[k] == b[k]) / n
labels = sorted(set(a.values()) | set(b.values()))
ca, cb = Counter(a.values()), Counter(b.values())
pe = sum((ca[l] / n) * (cb[l] / n) for l in labels)
kappa = (po - pe) / (1 - pe)
print(f'n={n} po={po:.4f} pe={pe:.4f} kappa={kappa:.4f} disagreements={sum(1 for k in a if a[k] != b[k])}')

conf = defaultdict(lambda: defaultdict(int))
for k in a:
    conf[a[k]][b[k]] += 1
print('confusion matrix (rows=A, cols=B):')
print(','.join(['A_label'] + labels))
for l in labels:
    print(','.join([l] + [str(conf[l][m]) for m in labels]))
"
```
