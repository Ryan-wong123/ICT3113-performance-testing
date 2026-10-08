# Step 4: Prediction Record

**This record is frozen at commit time and must not be revised after the first benchmark run** (Step 5), per the assignment brief. It is written before any of the three candidate models has been pulled, run against the golden set, or load-tested. Every number below is a specific, falsifiable prediction — being wrong is expected and acceptable; being vague is not.

## Hardware this prediction is made for

Intel Core i7-9750H (6 cores / 12 threads @ 2.60 GHz base), 15.9 GB RAM, Windows 11 Home, Docker Desktop, Ollama 0.34.4, CPU-only inference (`num_gpu: 0`) despite this machine also having an NVIDIA GTX 1660 Ti (confirmed unused via `ollama ps` showing `100% CPU` in Step 2). If Step 5's benchmarking runs on different hardware, these latency predictions (not the accuracy predictions, which are hardware-independent) should be treated as void and re-derived — this is noted explicitly so a hardware change can't later be used to explain away a wrong latency prediction.

## 1. Where the bottleneck will be, and why

**Prediction: the bottleneck under any load will be Ollama's CPU-bound token-generation time itself, serialized behind `OllamaClassifier`'s single lock — not FastAPI, SQLite, or logging.**

Evidence this prediction is based on (from Step 2's actual observed logs, `logs/requests.jsonl`):
- `GET /search`: 16.5ms, 22.3ms
- `GET /stats`: 29.2ms
- `POST /tickets` (warm, `llama3.2:3b`): 2,697.7ms, 2,704.1ms, 2,978.2ms — roughly **100–200× slower** than the database operations above.

Because every classification call acquires the same lock before touching Ollama, end-to-end sustained throughput is capped at `1 / mean_inference_latency` requests/second regardless of how many concurrent HTTP requests arrive — the FastAPI layer and SQLite are three orders of magnitude too fast to be the limiting factor at any of these candidates' expected latencies. This is predicted to bind hardest for `qwen2.5:7b` (the largest, slowest candidate — see below), and is expected to be the reason (if any) that R1 (p95 `POST /tickets` < 10s) fails for that candidate specifically.

## 2. Per-candidate accuracy and latency predictions

| Model | Predicted overall accuracy (golden set, 175 tickets) | Predicted warm single-request latency | Predicted cold-start latency (first request, model load into RAM) |
| --- | --- | --- | --- |
| `llama3.2:1b` | **72%** — predicted to fail R3's 85% overall floor | **≈1.3s** | **≈42s** |
| `llama3.2:3b` | **83%** — predicted to narrowly miss R3's 85% overall floor | **≈2.8s** (already observed: mean 2.79s across 3 warm requests in Step 2) | **≈67s** (already observed: 66.77s in Step 2) |
| `qwen2.5:7b` | **90%** — predicted to clear R3's 85% overall floor | **≈8s** — predicted to be closest to, or possibly exceed, R1's 10s p95 threshold | **≈150s (2.5 min)** |

**Method for the latency predictions on `llama3.2:1b` and `qwen2.5:7b`** (disclosed so the prediction can be judged, not just trusted): scaled from `llama3.2:3b`'s *already-observed* warm latency (2.79s) by each model's weights-file-size ratio to 3b (`llama3.2:1b` is 0.654× the size of `llama3.2:3b`; `qwen2.5:7b` is 2.319× — see `docs/candidate_models.md` for exact byte counts), then adjusted qualitatively: predicted `1b` latency is pulled *below* the naive linear scaling (1.83s) because smaller models typically have fewer layers and smaller hidden dimensions, compounding beyond a pure weights-size ratio; predicted `7b` latency is pushed *above* the naive linear scaling (6.47s) because larger CPU inference is often memory-bandwidth-bound rather than purely compute-bound, which tends to scale worse than linearly with size. Cold-start predictions use the same size ratios applied directly to the observed 66.77s cold start for `3b`, since cold start is dominated by reading weights off disk rather than compute. **This scaling method itself is a real prediction and can be wrong** — Step 5 should report the actual ratios observed and compare.

**Method for the accuracy predictions:** `llama3.2:3b` is predicted closest to its own Step 2 behaviour (4/4 ad-hoc test narratives during development were classified correctly and in valid output format — not a rigorous accuracy measurement, since those 4 tickets were not drawn from the golden set, but the only empirical signal available for any candidate before Step 5). `llama3.2:1b` is predicted lower on the reasoning that smaller instruction-tuned models are more likely to violate the service's strict output-format contract (`categories.parse_category` requires an *exact* category match — see `src/app/categories.py`) on ambiguous tickets, in addition to genuinely misclassifying more of them. `qwen2.5:7b` is predicted higher on the general expectation that larger, more capable models produce more reliable structured output and finer-grained disambiguation between similar categories.

## 3. Categories predicted to be hardest, and why

**Predicted hardest: `Debt collection` and `Credit card`, for all three candidates.**

This prediction is not a guess — it is derived directly from Step 1's actual annotator disagreement evidence (`labelling/disagreement_resolutions.csv`, `labelling/agreement_results.md`), not from general reasoning about the categories:

- Of the 175 golden-set tickets, exactly 5 disagreements occurred between the two independent human annotators. **`Credit card` was one side of 3 of those 5 disagreements** (rows 8384 vs `Debt collection`, 8590 vs `Money transfer or service`, 8762 vs `Bank account or service`). **`Debt collection` was one side of 2 of the 5** (rows 8384, 8699 vs `Credit reporting`).
- Three of the five disagreements (8590, 8699, 8762) required the labelling protocol itself to be extended with a new rule (Rules 9–11 in `labelling/labelling_protocol.md`) because no existing rule resolved that category pair — meaning trained humans, following a written protocol, only reached agreement on these specific pairs after the protocol was patched mid-project.
- `Debt collection` is also the smallest golden-set category (14 of 175 tickets — see `labelling/agreement_results.md`'s per-category support table), so any model error on it moves the per-category accuracy figure further per mistake than an equivalent error on a larger category like `Credit reporting` (38 tickets).

**Predicted per-category weak point specifically at risk of failing R3's 70% per-category floor: `Debt collection`**, for all three candidates, for the reasons above. `Credit card` is predicted to be the second-weakest category but is predicted to stay above the 70% floor for `llama3.2:3b` and `qwen2.5:7b` (only failing it for `llama3.2:1b`).

## Predictions this record commits to (summary table, for direct comparison against Step 5's actual results)

| Claim | Falsifiable by |
| --- | --- |
| Bottleneck is Ollama CPU inference time, not the app/DB/logging | Step 5's stress test and per-component timing |
| `llama3.2:1b` overall accuracy ≈72%, fails R3 | Step 5's accuracy test |
| `llama3.2:3b` overall accuracy ≈83%, narrowly fails R3 | Step 5's accuracy test |
| `qwen2.5:7b` overall accuracy ≈90%, passes R3 | Step 5's accuracy test |
| `llama3.2:1b` warm latency ≈1.3s, cold ≈42s | Step 5's latency measurements |
| `llama3.2:3b` warm latency ≈2.8s, cold ≈67s (already observed) | Step 5's latency measurements |
| `qwen2.5:7b` warm latency ≈8s (closest to/over the R1 10s p95 limit), cold ≈150s | Step 5's latency measurements |
| `Debt collection` is the hardest category for all 3 models, likely below the 70% per-category floor | Step 5's confusion matrices |
| `Credit card` is the second-hardest category, above 70% except for `llama3.2:1b` | Step 5's confusion matrices |
