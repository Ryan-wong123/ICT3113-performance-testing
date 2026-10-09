# Step 6: Recommendation

Every figure in this document comes from `analysis/step6_analysis.json` (regenerate with `python scripts/build_step6_analysis.py`), from `docs/load_test_results.md` (the final separate-machine `*_remote.jtl` evidence), or from `docs/accuracy_results.md` (`analysis/accuracy/*.json`). Figures that combine a measurement with a Step 3 assumption are labelled **derived estimate**. Figures from post-hoc analysis that was not run through the service are labelled **offline**.

## 1. The recommendation

**Do not deploy any of the three candidates as an automatic ticket router.** None of them meets R3, the accuracy requirement, and the only candidate that comes close is still wrong on about one ticket in five.

| | `llama3.2:1b` | `llama3.2:3b` | `qwen2.5:7b` |
| --- | --- | --- | --- |
| R1: p95 `POST /tickets` < 10s | PASS | PASS | PASS |
| R2: ≥ 8 tickets/hour sustained | PASS | PASS | PASS |
| R3: ≥ 85% overall, no category < 70% | **FAIL** (28.00%) | **FAIL** (32.00%) | **FAIL** (78.86%) |
| Meets all three | No | No | No |

**`qwen2.5:7b` is the only candidate worth carrying forward**, and only behind a human check (Section 5). Neither smaller model is recommended in any role.

### What we can and cannot promise the client

For `qwen2.5:7b` on one instance of the measured Machine A (Intel i9-14900HX, CPU-only, Docker Desktop):

| Service quality | Can we promise it? | Evidence |
| --- | --- | --- |
| p95 `POST /tickets` latency < 10s at the modelled peak | **Yes, on Machine A-class hardware only.** The worst single-run p95 across all six `qwen2.5:7b` runs was 9,196ms, at 5/min (41× the modelled peak). Pooled p95 was 4,840ms at 1.5/min (n=9, small sample) and 6,404ms at 5/min (n=24). | `remote_load_r1_evidence`; `qwen2.5_7b_rate*_remote.jtl` |
| Throughput above the modelled peak of 7.278311 tickets/hour | **Yes.** 5.33 successful tickets/min (320/hour) with zero errors at the higher test rate, 44× the peak. | `docs/load_test_results.md` |
| ≥ 85% overall accuracy | **No.** 78.86% measured (138/175); 95% Wilson interval 72.22–84.25%. Even the top of the interval is below 85%. | `accuracy.qwen2.5:7b` |
| Every category ≥ 70% | **No.** `Consumer loan` measured 58.33% (14/24). With only 24 tickets, the interval (38.83–75.53%) still overlaps 70%, so this per-category failure is measured but not statistically conclusive. | `accuracy.qwen2.5:7b.per_category` |
| The same latency on older or unqualified hardware | **No.** On the original i7-9750H, `qwen2.5:7b`'s single-request p95 was 34.98s, 3.5× the R1 limit. | `latency_vs_prediction` |

## 2. Our position: a misrouted ticket costs more than a slow one

The brief requires us to take a position. Our workload model and measurements settle it:

- **Speed costs almost nothing.** At the modelled peak, a ticket arrives every 8.24 minutes on average (`workload_implications.peak_mean_inter_arrival_minutes`). Every candidate on Machine A answers in seconds, with p95 latencies between 1,868ms and 6,404ms across the pooled configurations. There is no queue to build: Machine A sustained 40/min with `llama3.2:1b` in three out of three stress runs, about 330× the modelled peak.
- **Errors cost a human re-route and a delayed resolution, every time.** **Derived estimate:** at the modelled 87.34 tickets/day, fully automatic routing would misroute about 18.5 tickets/day with `qwen2.5:7b`, 59.4/day with `llama3.2:3b` and 62.9/day with `llama3.2:1b` (`workload_implications.misrouted_per_day_if_fully_automatic`).

At this volume, latency is a solved problem and accuracy is the only requirement that separates the candidates. This is why we do not pick the fastest model: `llama3.2:1b`'s speed buys nothing the client needs, and it misroutes 72% of tickets.

## 3. Defence against each requirement

### R1: response time

All three candidates pass in the final separate-machine environment. Every run's p95 is below 10,000ms (`remote_load_r1_evidence.*.every_run_p95_below_r1`). The lowest tested rates are 12–58× the modelled peak. Higher arrival rates can only add queueing, so passing at those rates implies passing at the peak. That is an argument, not a measurement at the peak rate itself: a multi-hour run at 7.28/hour was not performed (disclosed in `docs/test_environment.md`).

**Condition:** R1 depends on the hardware. On the i7-9750H the Step 4 predictions were written for, single-request p95 was 7.35s (`1b`), 13.99s (`3b`) and 34.98s (`qwen`). Two of the three would fail there. Any client server must be qualified by re-running `docs/test_playbook.md` on it before R1 is promised.

### R2: throughput

All three pass with large margins. The lowest successful pooled throughput in the regular matrix was `qwen2.5:7b`'s 2.00/min (120/hour), 15× the 8/hour floor. The windows were short (90–180s), so "sustained indefinitely" is inferred from the absence of queue growth at much higher rates, not observed over hours.

### R3: accuracy

All three fail. This is not a close call:

| Model | Overall | 95% Wilson interval | Failure clear at 95%? | Weakest category |
| --- | ---: | ---: | --- | --- |
| `llama3.2:1b` | 28.00% | 21.88–35.07% | Yes | `Credit card`, 0.00% (0/23) |
| `llama3.2:3b` | 32.00% | 25.54–39.23% | Yes | `Mortgage`, 4.17% (1/24) |
| `qwen2.5:7b` | 78.86% | 72.22–84.25% | Yes | `Consumer loan`, 58.33% (14/24) |

The intervals cover sampling uncertainty over 175 tickets only. Each model was run once. The baseline never sets `temperature` or `seed`, and Step 5 showed that the same prompt can return different answers on replay, so a second run would give a somewhat different percentage. The 47-point gap between `qwen2.5:7b` and the smaller models is far too large to be explained by that.

## 4. The baseline the client already has: the consumer's own label

The brief says the raw category labels "were selected by consumers at submission time". After the golden set was frozen, we scored those consumer-selected labels against the golden labels. This is the routing quality the client would get from simply trusting the form:

| Router | Accuracy on the 175 golden tickets | Re-weighted to all 1,000 Team 8 rows |
| --- | ---: | ---: |
| Consumer self-label (`source_label`) | **85.14%** (149/175; 79.12–89.65%) | 85.56% |
| `qwen2.5:7b` | 78.86% (138/175) | 78.36% |
| `llama3.2:3b` | 32.00% | 29.39% |
| `llama3.2:1b` | 28.00% | 27.78% |

(`consumer_self_label_baseline`, `stratum_weighted_accuracy`.) The golden set was drawn as 25 tickets per `source_label` stratum. Re-weighting by the real stratum sizes barely changes the result, so the comparison is not an artefact of the sampling.

What this means:

- **No candidate beats the label consumers already provide.** On the same tickets, `qwen2.5:7b` is right on 19 where the self-label is wrong, and wrong on 30 where the self-label is right. That difference is not statistically significant (exact McNemar p = 0.152). So there is no evidence that `qwen2.5:7b` is better than the consumer's own choice, and it may be worse. Both smaller models are significantly worse (p < 0.001).
- **R3's own justification implies a higher bar than the one we wrote.** `docs/requirements.md` set 85% as "materially better than noisy self-reported labels". On our golden set those labels score 85.14%, so a model that only just meets R3 would merely match the self-labels. **We do not change R3 after the fact**: it stays at 85% and every candidate fails it. We record plainly that the requirement was set before we had measured the baseline it was meant to beat. For Assignment 2, that baseline should be the reference point.
- **The models and consumers make different mistakes.** Consumer labels are weakest on `Credit reporting` (65.79%), where `qwen2.5:7b` is strongest (94.74%). `qwen2.5:7b` is weakest on loan-type boundaries (`Consumer loan` 58.33%, `Mortgage` 70.83%), where consumer labels are strong. Section 5 builds on this.

**Assumption:** this assumes the client's intake form captures a consumer-selected product, as the CFPB's does. The client brief does not say whether it does.

## 5. The path we recommend instead: agreement-gated triage (pilot only)

**Offline** analysis of the measured `qwen2.5:7b` outputs (`model_vs_self_label.qwen2.5:7b.agreement_gate`):

- **Proposed rule:** auto-route a ticket only when `qwen2.5:7b`'s answer equals the consumer-selected label. Every other ticket goes to a human router.
- **On the golden set:** the two agreed on 122 of 175 tickets (69.71%). On those, the shared label was correct on 119 (97.54%; 95% interval 93.02–99.16%). The other 53 tickets (30.29%) would go to a person.
- **Derived estimate at the modelled 87.34 tickets/day:** about 60.9 tickets/day auto-routed with about 1.5 misroutes, and 26.5 tickets/day for human routing, instead of the 87.34 humans route today.

This is a **recommendation to pilot**, not a measured deployment, for five reasons:

1. **The rule was found and scored on the same 175 tickets.** It needs a fresh, independently labelled validation sample.
2. **The measurement is fragile.** It rests on one non-deterministic run per model, on the old i7 environment with Ollama 0.34.4. The final load environment runs Ollama 0.35.1, and accuracy was not re-measured there.
3. **It changes the system.** The service would have to accept the consumer label and branch on it. That is a change to the Assignment 1 baseline, so it belongs to Assignment 2, alongside pinning `temperature`/`seed` and testing a richer prompt.
4. **It is not R3.** It is a different operating mode, and it would need its own requirement (accuracy on the auto-routed share, plus the maximum share sent to humans) before any go-live decision.
5. **It assumes the intake form captures the consumer's label** (Section 4).

## 6. Predictions versus outcomes

The prediction record (`predictions/prediction_record.md`) is unchanged. Latency predictions were made for the i7-9750H, so they are compared against the i7 accuracy-run measurements (sequential single requests, Ollama 0.34.4), not against the faster i9 Machine A. The record itself forbids using a hardware change to explain away a miss.

| Prediction (frozen) | Actual | Verdict |
| --- | --- | --- |
| Bottleneck: Ollama CPU inference, serialised behind the classifier lock; not FastAPI, SQLite or logging | Confirmed: latency scales with model and with narrative length; queueing appears only above Machine A's 40/min boundary; SQLite paths take 16–30ms | **Right** |
| The bottleneck makes `qwen2.5:7b` the candidate that fails R1 | i7: `qwen` failed (34.98s p95), but so did `3b` (13.99s). i9 Machine A: nobody fails | **Partly right** |
| `llama3.2:1b` accuracy 72%, fails R3 | 28.00%, fails | Pass/fail right; **off by 44.0 points** |
| `llama3.2:3b` accuracy 83%, narrowly fails R3 | 32.00%, fails badly | Pass/fail right; **off by 51.0 points** |
| `qwen2.5:7b` accuracy 90%, passes R3 | 78.86%, fails | **Wrong**: off by 11.14 points and wrong on pass/fail |
| Small models fail mainly by breaking the output format | Format errors: 5 (`1b`), 2 (`3b`), 0 (`qwen`). Valid-but-wrong answers: 121 and 117 | **Wrong mechanism** |
| Warm latency: `1b` 1.3s, `3b` 2.8s, `qwen` 8s | Mean 3.99s, 8.21s, 19.38s (p50 3.48, 6.72, 18.10s), i.e. 2.4–3.1× slower | **Wrong**, all too optimistic |
| Latency scales by weights size (`1b` ≈ 0.46×, `qwen` ≈ 2.86× of `3b`) | 0.486× and 2.361× | Relative scaling **roughly right**; the "worse than linear" adjustment for `qwen` was wrong (the plain 2.319× weights ratio was closer) |
| Cold start: `1b` 42s, `3b` 67s, `qwen` 150s | First request after each model switch: 13.22s, 23.12s, 77.58s (one observation each) | **Wrong**, too pessimistic |
| `Debt collection` hardest for all three, likely below 70% | Not the hardest for any model: 2nd-weakest for `1b` (7.14%), 5th for `3b` (28.57%), 5th for `qwen` (78.57%, above 70%) | **Wrong** |
| `Credit card` second-hardest; above 70% except for `1b` | Hardest for `1b` (0.00%); 2nd-hardest for `3b` (4.35%, far below 70%); 3rd-weakest for `qwen` (73.91%, above 70%) | **Partly right** |

## 7. Where we were wrong, and why

**Accuracy: we anchored on a sample that wasn't one.**
- The predictions rested on four hand-written Step 2 smoke-test tickets, all classified correctly. Four easy, short examples say almost nothing about 175 real narratives.
- We also predicted the wrong failure mode. We expected small models to break the strict output format. Format errors turned out to be minor; the small models instead collapse onto one or two default answers:
  - `llama3.2:1b` answered `Consumer loan` or `Credit reporting` for 123 of 175 tickets, and never once answered `Credit card`.
  - `llama3.2:3b` answered `Bank account or service` for 98 of 175 (`accuracy.*.predicted_label_totals`).
- That points at the baseline's bare, zero-shot prompt (seven category names and one instruction). The prompt is good enough for a 7B model but not for 1–3B models. We overestimated `qwen2.5:7b` by 11 points for the same reason, because none of the examples were hard.

**Latency: the anchor ticket was much shorter than real tickets.**
- The 2.79s anchor came from Step 2 smoke-test requests, but latency depends on how much text the model has to read. Across the accuracy run, word count and latency have a Spearman rank correlation of 0.944 (`1b`), 0.915 (`3b`) and 0.943 (`qwen`). On the same i7, `3b`'s median was 3.95s for tickets under 100 words and 11.56s for tickets of 200+ words.
- Golden-set narratives average 152.68 words. Step 2's narratives were short:
  - **Evidence:** the documented smoke-test example is "My card was charged twice for the same purchase" (10 words).
  - **Inference:** the Step 2 log records a 2.70s `3b` request tagged `ticket_row` 8020, whose real narrative is 219 words. That latency is impossible for a 219-word ticket on that machine, so the request almost certainly carried a short, hand-written narrative rather than row 8020's text. The log stores only the row number, not the narrative.
- The scaling method itself held up reasonably. The anchor was the error.

**Cold start: we anchored on an outlier.** The 66.77s Step 2 figure was the very first load of `llama3.2:3b` on that machine. The Step 5 first-request times were 2–3× faster. One possible cause is that freshly pulled model files were still in the operating system's file cache, but this is a hypothesis: Ollama's `load_duration` is not logged, and each figure is a single observation.

**Hardest categories: human disagreement does not predict model errors.**
- We derived the category prediction from 5 human disagreements out of 175 tickets. That is very few events, and they reflect genuine ambiguity on boundaries that humans find hard.
- The models fail for different reasons. The small models fail through default-answer collapse. `qwen2.5:7b` fails mostly on loan-type boundaries: 6 of 24 `Consumer loan` tickets went to `Credit reporting`, and 6 of 24 `Mortgage` tickets went to `Consumer loan`.
- `Debt collection`, which we expected to be hardest, is one of `qwen2.5:7b`'s better categories (11/14). Human agreement tells you where the labels are uncertain, not where a model will fail.

**What we got right.** The bottleneck. Every Step 5 measurement points to CPU-bound inference behind the single lock: no other component scales with model size or ticket length, and the 60/min stress collapse is the lock's queue overflowing.

## 8. Conditions and risks attached to this recommendation

- **Hardware qualification is mandatory.** R1 passes on the i9-14900HX and failed for two of three models on the i7-9750H. Do not scale by core count; re-run the playbook on the target server (`docs/test_environment.md`).
- **Accuracy was measured in the older environment.** Accuracy was measured on the i7 with Ollama 0.34.4, once per model, with sampling temperature not pinned. Re-measure on the deployment hardware and runtime before any pilot.
- **Overload behaviour.** The baseline has no backpressure. At 60/min, `llama3.2:1b` either collapsed or queued severely in two of three runs. This is irrelevant at the modelled volume but would matter if real volume were around 300× higher than modelled. `qwen2.5:7b`'s own overload point was not stress-tested; it was measured only up to 5/min.
- **Workload model.** The volume comes from Step 3's assumptions (1% market share and peak multiplier; `docs/workload_model.md`). Our latency and throughput conclusions hold even if real volume is an order of magnitude higher. The misroutes/day estimates scale linearly with volume.
- **"Warm" latency includes the first request.** The accuracy JSON's `warm_latency_seconds` statistics include each run's first post-switch request. That inflates the maximum (e.g. `qwen`'s 77.78s) but has negligible effect on p95.

## Evidence index

| Claim area | Source |
| --- | --- |
| Accuracy, confidence intervals, self-label baseline, agreement gate, latency-vs-prediction, first-request times, R1 evidence | `analysis/step6_analysis.json` ← `scripts/build_step6_analysis.py` |
| Per-ticket accuracy results and confusion matrices | `analysis/accuracy/*.json`, `docs/accuracy_results.md` |
| Load, stress, throughput, bottleneck | `jmeter/results/*_remote.jtl`, `docs/load_test_results.md` |
| Workload volumes | `analysis/workload_model.json`, `docs/workload_model.md` |
| Requirements | `docs/requirements.md` |
| Frozen predictions | `predictions/prediction_record.md` |
| Test environment and limitations | `docs/test_environment.md` |
