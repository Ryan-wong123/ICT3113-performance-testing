# Step 5: Accuracy Results

Every golden-set ticket (175 rows, `labelling/golden_test_set.csv`) was sent through the real `POST /tickets` endpoint of the running Docker container — never bypassed — once per candidate model. Raw per-ticket results, per-category accuracy, and confusion matrices are in `analysis/accuracy/<model>.json`; this document summarises and interprets them.

## Overall and per-category accuracy

| Model | Overall accuracy | R3 overall (≥85%) | Weakest category | Weakest accuracy | R3 per-category (≥70%) |
| --- | --- | --- | --- | --- | --- |
| `llama3.2:1b` | 28.00% (49/175) | **FAIL** | `Credit card` | 0.00% (0/23) | **FAIL** |
| `llama3.2:3b` | 32.00% (56/175) | **FAIL** | `Mortgage` | 4.17% (1/24) | **FAIL** |
| `qwen2.5:7b` | 78.86% (138/175) | **FAIL** | `Consumer loan` | 58.33% (14/24) | **FAIL** |

**No candidate meets requirement R3.** All three fail the 85% overall bar; `qwen2.5:7b` is the closest by a wide margin (nearly 47 points above the two smaller models) but still falls 6.14 points short overall, and its `Consumer loan` category falls short of the 70% per-category floor by 11.67 points.

## Per-category accuracy, full breakdown

| Category | Golden-set support | `llama3.2:1b` | `llama3.2:3b` | `qwen2.5:7b` |
| --- | --- | --- | --- | --- |
| Bank account or service | 28 | 35.71% | 89.29% | 89.29% |
| Consumer loan | 24 | 45.83% | 50.00% | 58.33% |
| Credit card | 23 | **0.00%** | 4.35% | 73.91% |
| Credit reporting | 38 | 42.11% | 26.32% | 94.74% |
| Debt collection | 14 | 7.14% | 28.57% | 78.57% |
| Money transfer or service | 24 | 20.83% | 12.50% | 75.00% |
| Mortgage | 24 | 25.00% | **4.17%** | 70.83% |

## Confusion matrix highlights

**`llama3.2:1b`** never once predicted `Credit card` for any ticket, including the 23 tickets that were actually `Credit card` — it substituted `Credit reporting` (12 times) or `Consumer loan` (5 times) instead. It also produced 5 tickets whose output didn't match any of the seven categories at all (502 errors — e.g. the model replied `'Account Recovery'`, `'Identity Theft'`, or `'- Debt collection'` instead of an exact category string), confirming the strict-output-contract failure path from `categories.parse_category` genuinely fires against a real model, not just in theory.

**`llama3.2:3b`** shows a single dominant confusion pattern: `Bank account or service` acts as a de facto default answer. It is correct on 25/28 of its own true category, but also absorbs the majority of wrong guesses from every other category: 18/23 `Credit card` tickets, 17/38 `Credit reporting` tickets, 16/24 `Money transfer or service` tickets, and 10/24 `Mortgage` tickets were all mislabelled as `Bank account or service`.

**`qwen2.5:7b`** shows no dominant-default pattern — errors are spread across plausible near-neighbour categories (e.g. `Consumer loan` mistaken for `Credit reporting` or `Debt collection`; `Mortgage` mistaken for `Bank account or service`), consistent with genuine boundary-case difficulty rather than a systemic bias, and produced zero output-format errors across all 175 tickets.

## An important, unplanned finding: response non-determinism

Predictions/expectations going into this step assumed each candidate's accuracy would be a fixed, well-defined number. During testing, **the same exact prompt and narrative, replayed twice against the same model, produced two different valid-format answers** (row 8037, `llama3.2:3b`: once "Consumer loan", once "Bank account or service" on a separate replay — see the investigation in this step's session log). This is not a bug: `src/app/ollama_client.py` never sets a `temperature` or `seed` on the Ollama request, so Ollama's default sampling temperature (~0.8) means every call is genuinely non-deterministic.

**This matters for how these numbers should be read:** the accuracy figures above are each from a single run per model (as the brief requires — "send every golden-set ticket through `POST /tickets` for each candidate model," not repeated runs), but given demonstrated non-determinism, a repeat run of the same model against the same golden set would likely **not** reproduce the exact same accuracy percentage, though the broad ordering (qwen2.5:7b ≫ llama3.2:3b ≈ llama3.2:1b) is expected to be robust to this variance given how large the gaps are. This is a genuine, reportable characteristic of the unoptimised baseline, not a measurement error — an optimised version (Assignment 2) might reasonably pin `temperature`/`seed` for reproducible classification.

## Why the actual results diverge so sharply from Step 4's predictions

Step 4 predicted 72% / 83% / 90% overall accuracy for `llama3.2:1b` / `llama3.2:3b` / `qwen2.5:7b` respectively, based on a handful of ad-hoc Step 2 smoke-test tickets (4 tickets, all correct) — not a rigorous measurement. The actual results (28% / 32% / 79%) are dramatically lower for the two smaller models. The most likely explanation, based on the confusion-matrix evidence above: **the baseline's classification prompt (`src/app/categories.py`'s `category_prompt()`) is a bare list of seven category names with a one-line instruction and no few-shot examples** — apparently sufficient for `qwen2.5:7b` to perform reasonably, but insufficient for the two smaller models, which each collapsed toward a small number of default/attractor categories rather than genuinely discriminating between all seven. This was not visible in Step 2's tiny informal sample, and is exactly the kind of finding rigorous testing (as opposed to spot-checking) is supposed to surface. Per the brief, this is not something to fix now — the baseline is frozen — but it is a central, honest finding for Step 6.

## Reconciliation with service logs

All 525 accuracy-test requests (175 golden-set tickets × 3 candidates) are contained in the 946-entry historical `POST /tickets` block that existed before the final remote rerun. After all remote traffic and six warm-ups, the current log contains 1,997 `POST /tickets` entries. See the exact reconciliation in `docs/load_test_results.md`.
