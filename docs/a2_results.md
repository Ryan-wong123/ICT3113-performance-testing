# Assignment 2 — Results and Recommendation

**Status (16 November 2026): recommendation approved; deck checked against this document.** Every figure below comes from a committed file (see "Where each figure comes from"); nothing is typed in from memory. The recommendation in Section 8 was approved on 16 November 2026 on the instruction of a team member, after the 8-slide deck `Group08_A2.pptx` was checked against this document and the raw files. Before submission the deck still needs the items in Section 11. The frozen files `docs/a2_escalation_rule.md` and `predictions/a2_prediction_record.md` are quoted, not edited.

## 1. Summary

- **Limits** (top model `qwen2.5:7b`, 66/85 = 77.65% on the 85 even-row test tickets): overall limit **67.65%**; per-category limits **29.44%–85.00%**.
- **Passing both limits:** `qwen2.5:7b` alone and **cascade A**. Cascade B fails one category by one ticket (Money transfer or service 7/13 = 53.85% vs a 54.23% limit). `llama3.2:3b` (28.24%) and `llama3.2:1b` (25.88%) fail the overall limit and most categories.
- **Speed** (11.253 tickets/min, 5-minute window, three runs each): mean p50 `qwen2.5:7b` **7.52 s**, cascade A **38.83 s**, cascade B **23.94 s**. The cascade queued at this rate (utilisation 1.04–1.27 for A), so these p50 values partly reflect run length; the service time per ticket points the same way (Section 4.3).
- **The cascade did not help.** Both settings escalated about 84–94% of tickets in the accuracy test (87–92% under load), above the ~67% break-even implied by the measured model speeds (Section 6), so almost every ticket paid the small-model cost and then the large-model cost.
- **Recommendation (approved):** deploy `qwen2.5:7b` alone. No tested configuration is both faster than it and within the accuracy limits.

## 2. What was tested

| Item | Value |
| --- | --- |
| Top model (reference) | `qwen2.5:7b`, ID `845dbda0ea48` |
| Other single models | `llama3.2:3b` (`a80c4f17acd5`), `llama3.2:1b` (`baf6a787fdff`) |
| Cascade pair | small `llama3.2:1b`, large `qwen2.5:7b`; both resident together, CPU-only (`docs/test_environment.md`) |
| Cascade rule | Category-based on the small model's parsed category (`docs/a2_escalation_rule.md`). **Setting A** accepts Money transfer or service and Mortgage and escalates the other five. **Setting B** also accepts Bank account or service and escalates four. |
| Split | Odd `row` value = tuning (90), even = test (85); `analysis/a2/golden_split.csv` |
| Service code | Frozen at commit `3752b350984145462dbfc724c2a6d9969f324dd5`; `src/app` is unchanged since |
| Machines | Service + native Ollama 0.35.1 on Machine A (i9-14900HX, ~15.62 GiB RAM); JMeter 5.6.3 on separate Machine B (i7-9750H); details in `docs/test_environment.md` |
| Speed parameters | S = 2.666 s (middle of 2.404, 2.979, 2.666 s; rows 8685, 8242, 8345) → one arrival every 5.332 s = 11.253/min; 5-minute window (S minutes would be 2.67 min, below the 5-minute minimum); 300 s response timeout; 360 s trailing pause; seed 8; 70-row ordered workload, 56 arrivals per run |

The Assignment 1 baseline is unchanged: with the cascade switch off the service behaves as in Assignment 1, and Assignment 1 evidence is identical to `main`.

## 3. Accuracy results (85 test tickets, through `POST /tickets`, once per configuration)

### 3.1 Overall

| Configuration | Correct / 85 | Accuracy | Invalid-category responses (counted wrong) | Overall limit 67.65% |
| --- | ---: | ---: | ---: | --- |
| `qwen2.5:7b` alone | 66 / 85 | 77.65% | 1 | **Pass** |
| Cascade A | 69 / 85 | 81.18% | 1 | **Pass** |
| Cascade B | 67 / 85 | 78.82% | 1 | Pass overall, **fails a category** |
| `llama3.2:3b` alone | 24 / 85 | 28.24% | 0 | Fail |
| `llama3.2:1b` alone | 22 / 85 | 25.88% | 1 | Fail |

### 3.2 Per category (correct / n, accuracy; ✗ = below the per-category limit)

| Category (n) | Limit | `qwen2.5:7b` | Cascade A | Cascade B | `llama3.2:3b` | `llama3.2:1b` |
| --- | ---: | --- | --- | --- | --- | --- |
| Bank account or service (13) | 69.62% | 11/13 = 84.6% | 12/13 = 92.3% | 13/13 = 100.0% | 10/13 = 76.9% | 4/13 = 30.8% ✗ |
| Consumer loan (14) | 56.43% | 10/14 = 71.4% | 11/14 = 78.6% | 10/14 = 71.4% | 4/14 = 28.6% ✗ | 6/14 = 42.9% ✗ |
| Credit card (12) | 68.33% | 10/12 = 83.3% | 10/12 = 83.3% | 10/12 = 83.3% | 0/12 = 0.0% ✗ | 0/12 = 0.0% ✗ |
| Credit reporting (15) | 85.00% | 15/15 = 100.0% | 14/15 = 93.3% | 13/15 = 86.7% | 4/15 = 26.7% ✗ | 8/15 = 53.3% ✗ |
| Debt collection (9) | 29.44% | 4/9 = 44.4% | 5/9 = 55.6% | 6/9 = 66.7% | 3/9 = 33.3% | 0/9 = 0.0% ✗ |
| Money transfer or service (13) | 54.23% | 9/13 = 69.2% | 9/13 = 69.2% | 7/13 = 53.8% ✗ | 3/13 = 23.1% ✗ | 3/13 = 23.1% ✗ |
| Mortgage (9) | 62.78% | 7/9 = 77.8% | 8/9 = 88.9% | 8/9 = 88.9% | 0/9 = 0.0% ✗ | 1/9 = 11.1% ✗ |

**Small numbers.** Every test category has 9–15 tickets, so one ticket moves a category by 6.7–11.1 points. Debt collection and Mortgage (n = 9) are too small for the per-category limit to be a fair test. Cascade B's only failure is one ticket under the Money transfer limit (53.85% vs 54.23%), which is within what a single ticket or a re-run could change. Accuracy was measured once per configuration with `temperature`/`seed` unpinned (Assignment 1 found identical prompts can give different valid answers), so exact percentages are measurements of this run, not guaranteed reproductions. Both small models scored 0/12 on Credit card.

### 3.3 Cascade escalation (from the service log, successful decisions only)

| | Escalated | Not escalated | Accuracy of escalated | Accuracy of not escalated | Failed request (no decision) |
| --- | --- | --- | --- | --- | --- |
| Cascade A | 79 / 84 = 94.05% | 5 / 84 | 64/79 = 81.01% | 5/5 = 100% | 1 (counted wrong) |
| Cascade B | 71 / 84 = 84.52% | 13 / 84 | 59/71 = 83.10% | 8/13 = 61.54% | 1 (counted wrong) |

For B, 5 of the 13 accepted small-model answers were wrong (38%): the rule let wrong answers through, which is where its Money transfer and Credit reporting losses came from. All five were the 1B model predicting "Bank account or service" (the true labels were Money transfer or service ×3, Credit card ×1, Credit reporting ×1); on the test set that prediction was right only 3 of 8 times, against 4 of 8 on the tuning set. Confusion matrices for every configuration are in `analysis/a2/accuracy/*.json`.

## 4. Speed results (three open-loop runs per configuration, 56 arrivals each)

Single models that fail accuracy (`llama3.2:3b`, `llama3.2:1b`) were not speed-tested, per the brief. Cascade B was speed-tested although it fails the accuracy limits and is marked as not passing. Latency is computed from successful requests only; no p99 is reported.

### 4.1 Per run

| Configuration / run | Sent | Completed | Successful | Errored | Unfinished | p50 | Completed throughput | Error rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `qwen2.5:7b` run 1 | 56 | 56 | 52 | 4 | 0 | 6.36 s | 672 /h | 7.14% |
| `qwen2.5:7b` run 2 | 56 | 56 | 56 | 0 | 0 | 6.92 s | 586 /h | 0% |
| `qwen2.5:7b` run 3 | 56 | 56 | 56 | 0 | 0 | 9.29 s | 672 /h | 0% |
| Cascade A run 1 | 56 | 56 | 56 | 0 | 0 | 34.13 s | 607 /h | 0% |
| Cascade A run 2 | 56 | 56 | 56 | 0 | 0 | 57.41 s | 528 /h | 0% |
| Cascade A run 3 | 56 | 56 | 56 | 0 | 0 | 24.97 s | 647 /h | 0% |
| Cascade B run 1 | 56 | 56 | 56 | 0 | 0 | 18.21 s | 672 /h | 0% |
| Cascade B run 2 | 56 | 56 | 56 | 0 | 0 | 22.77 s | 660 /h | 0% |
| Cascade B run 3 | 56 | 56 | 56 | 0 | 0 | 30.85 s | 653 /h | 0% |

All four Qwen run 1 errors were connection timeouts that never reached the service (the service log holds 52 tickets for that run). Completed throughput divides by the longer of the 300 s window and the time to the last completion, so queue drain is included; the offered load was about 672 /h.

### 4.2 Across runs

| Configuration | p50 per run | Mean p50 | Spread (max − min) | Pooled p95 | Pooled samples | Mean completed throughput | Escalation under load |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `qwen2.5:7b` | 6.36 / 6.92 / 9.29 s | **7.52 s** | 2.93 s | 26.57 s | 164 | 643 /h | n/a |
| Cascade A | 34.13 / 57.41 / 24.97 s | **38.83 s** | 32.44 s | 128.78 s | 168 | 594 /h | 154/168 = 91.67% |
| Cascade B (not passing accuracy) | 18.21 / 22.77 / 30.85 s | **23.94 s** | 12.65 s | 66.47 s | 168 | 662 /h | 146/168 = 86.90% |

The pooled p95 is computed over all successful requests from the three runs (164, 168, 168), as the brief asks. The brief says a single run of about 30 requests is too small for a stable p95; these runs had 56, so each run is larger than that, but the spread across runs is still large, so treat the p95 figures as indicative.

Escalation under load differs from the accuracy-test fraction by about 2.4 points in each direction (A: 91.67% vs 94.05%; B: 86.90% vs 84.52%). The two tests use different tickets (a 70-row workload alternating near-p50 and near-p95 lengths vs the 85 test tickets), so no large gap needs explaining.

### 4.3 Queueing: how to read these p50 values

The brief wants an arrival rate the top model can keep up with, so that the latency settles and describes the configuration. Here the rate did not leave the top model idle half the time. The three timing tickets were all about 780 characters, but the workload mixes typical and long tickets, so the mean service time was longer than S.

| Configuration | Mean service time per run | Utilisation per run (service time ÷ offered gap of 5.357 s) |
| --- | --- | --- |
| `qwen2.5:7b` | 3.92 / 5.34 / 4.50 s | 0.73 / 1.00 / 0.84 |
| Cascade A | 5.93 / 6.82 / 5.55 s | 1.11 / 1.27 / 1.04 |
| Cascade B | 5.30 / 5.44 / 5.51 s | 0.99 / 1.02 / 1.03 |

At utilisation near or above 1 a queue grows through the arrival window, so the cascade p50 values (especially cascade A) depend partly on the 5-minute run length and not only on the configuration. That is why this section reports service time and utilisation as well. The direction of the result does not depend on the queue: per-ticket service time is higher for cascade A (5.55–6.82 s) than for Qwen (3.92–5.34 s) and no lower for cascade B (5.30–5.51 s), and cascade A could not keep up at the offered rate while Qwen alone nearly could. Source: `analysis/a2/speed/service_times.json`.

### 4.4 Client load

The test rate of 11.253 submissions/min is **92.77×** the client's modelled peak submission rate (0.121305/min, `analysis/workload_model.json`) and 77.31× the combined peak submission-and-search rate (0.145566/min). The rate is above the client's peak, so Qwen alone answering 52–56 of the 56 requests per run (the four failures were connection timeouts that never reached the service) shows it can handle the client's modelled load many times over on this machine. Cascade A's queueing at this rate does not mean it would queue at the client's real peak. It means it cannot sustain this accelerated rate.

## 5. Accuracy against latency (data for the trade-off chart)

Overall limit line: **67.65%**.

| Configuration | Test accuracy | Passes both limits | Mean p50 under load | Pooled p95 | Supplementary: mean latency, sequential accuracy run |
| --- | ---: | --- | ---: | ---: | ---: |
| `qwen2.5:7b` | 77.65% | Yes | 7.52 s | 26.57 s | 3.14 s |
| Cascade A | 81.18% | Yes | 38.83 s | 128.78 s | 3.93 s |
| Cascade B | 78.82% | No (Money transfer, one ticket) | 23.94 s | 66.47 s | 3.09 s |
| `llama3.2:3b` | 28.24% | No | not speed-tested | not speed-tested | 1.45 s |
| `llama3.2:1b` | 25.88% | No | not speed-tested | not speed-tested | 1.03 s |

The last column is the mean request latency during the sequential accuracy runs (one request at a time, no queue; `analysis/a2/accuracy/*.json`, `latency_seconds`). It is supplementary context and not speed-test evidence. It shows the same ordering without a queue: the 1B and 3B models are fastest and inaccurate, cascade A is slower than Qwen alone (p50 3.74 s vs 2.95 s), and cascade B is about level with Qwen on the mean (3.09 s vs 3.14 s, p50 1.93 s vs 2.95 s) while failing a category. Cascade B's accuracy run includes one 71.5 s request that raises its mean.

## 6. Why the cascade did not beat the top model

A cascade's mean latency is about the small-model latency plus the escalation fraction times the large-model latency. Using the sequential accuracy-run means on the same test tickets (small `llama3.2:1b` 1.027 s, large `qwen2.5:7b` 3.138 s), it is faster than the large model alone only when the escalation fraction is below `1 − 1.027 / 3.138 ≈ 67%`. The deck (slide 7) uses the speed-test workload instead, which alternates about 780-character and about 1,760-character tickets: `llama3.2:1b` sequential p50 0.965 s and `qwen2.5:7b` mean service time 4.59 s (the mean of 3.92, 5.34 and 4.50 s from `analysis/a2/speed/service_times.json`). On that basis the cascade costs about `0.965 + 0.917 × 4.59 ≈ 5.2 s` per ticket against 4.59 s for Qwen alone, and the break-even is about 79%. The two bases differ because the longer speed-test tickets cost Qwen proportionally more than the 1B model. Both are derived arithmetic, not separate measurements, and the deck's basis mixes a sequential median with an under-load mean. Either way the break-even (67–79%) is well below the measured escalation (84–94%), so the conclusion does not depend on the basis.

Both settings are well above that: 94.05% (A) and 84.52% (B) in the accuracy test, 91.67% and 86.90% under load. The `llama3.2:1b` model is rarely confident enough in the categories that matter, so almost every ticket pays for both models. Applying the formula to the measured fractions gives about 3.98 s for A (measured mean 3.93 s) and 3.68 s for B (measured mean 3.09 s), against 3.14 s for Qwen alone. Setting B accepts more small-model answers and escalates less, which cut its latency, but it lost accuracy: its accepted answers were 61.54% correct, and it dropped below the Money transfer limit.

This is a result for this pair and this rule only. The escalation lists were chosen from Assignment 1 evidence (below), and only the category-based rule with `llama3.2:1b` was tested. The `llama3.2:3b` pair, a length rule, an agreement rule and a confidence rule were not run, so this does not show that no cascade could beat Qwen.

## 7. Predictions against outcomes

Predictions are quoted from `predictions/a2_prediction_record.md` (frozen before testing). Verdicts are the team's to confirm.

| Prediction | Outcome | Verdict and why |
| --- | --- | --- |
| `qwen2.5:7b` alone is the fastest configuration that satisfies both limits | Qwen alone and cascade A qualify; Qwen's mean p50 is 7.52 s vs 38.83 s | **Right.** The reasoning (high escalation means small cost plus large cost) held. |
| `llama3.2:1b` and `llama3.2:3b` are faster but fail accuracy | They fail (25.88%, 28.24%); sequential mean 1.03 s and 1.45 s vs 3.14 s | **Right** on both parts; neither was speed-tested because they fail accuracy. |
| Cascade A: 90% escalation | 94.05% (accuracy run), 91.67% (under load) | **Close.** Within about 4 points. The tuning estimate came from Assignment 1 records. |
| Cascade A: 78% accuracy | 81.18% | **Partly right.** Passes as predicted, 3.2 points higher, within the noise of 85 tickets. |
| Cascade A: 19.0 s median latency | 38.83 s mean p50 under load; 3.74 s sequential p50 | **Wrong.** The estimate used Assignment 1 warm medians from the older i7 (3.38 s small, 17.29 s large), but Machine A runs Qwen in about 3 s. In the speed test the cascade queued (utilisation 1.04–1.27), which the formula ignores. |
| Cascade B: 81% escalation | 84.52% (accuracy run), 86.90% (under load) | **Close.** 3–6 points under the actual. |
| Cascade B: 76% accuracy | 78.82% overall, fails Money transfer by one ticket | **Partly right.** Overall above the prediction, but it did not qualify. |
| Cascade B: 17.4 s median latency | 23.94 s mean p50 under load; 1.93 s sequential p50 | **Wrong** for the same reasons as A. |
| Largest category losses are Credit reporting and Money transfer or service | B: Credit reporting −2 (13/15 vs 15/15) and Money transfer −2 (7/13 vs 9/13) relative to Qwen; A: Credit reporting −1, Money transfer 0 | **Right.** These are the largest losses in both settings, and A's losses are smaller than B's, as predicted. |
| Setting A would lose less accuracy than B | A fails nothing; B fails Money transfer | **Right.** |

## 8. Recommendation (approved 16 November 2026)

**Deploy `qwen2.5:7b` alone.**

1. It passes both accuracy limits (77.65% overall; no category below its limit).
2. It is the fastest configuration that does. The only other configuration that passes both limits, cascade A, was slower on every measure: mean p50 38.83 s vs 7.52 s, pooled p95 128.78 s vs 26.57 s, per-ticket service time 5.55–6.82 s vs 3.92–5.34 s, and sequential p50 3.74 s vs 2.95 s.
3. No tested configuration is faster than the top model within the limits, so there is no speed gain to claim and no accuracy given up (0 points overall, 0 in every category). Cascade A scored 3.5 points higher overall but at about five times the p50 latency.
4. Cascade B fails the Money transfer limit and is no faster on the mean (3.09 s vs 3.14 s sequential). `llama3.2:3b` and `llama3.2:1b` fail the overall limit and most categories.

**What the attempt cost:** the cascade needs both models resident (1.5 GB + 5.1 GB) and extra service logic, and gave no speed benefit for this pair and rule.

**Conditions on this recommendation:** it holds for this test set, the category-based rule with `llama3.2:1b`, one machine and one arrival rate. A different rule, such as a length or agreement rule, or a different pair, was not tested.

## 9. What these results do not show

- **Sample sizes.** 85 test tickets, categories of 9–15 tickets, 56 requests per speed run (164–168 pooled). One accuracy run per configuration with unpinned `temperature`/`seed`. The same model on the same tickets did give different answers: for the 79 tickets cascade A sent to Qwen, Qwen alone answered 4 differently (64 correct in the cascade vs 62 correct alone on those same tickets); for cascade B's 71 escalated tickets, 4 differed (59 vs 57). The deck's slide 7 wording compares 81.0% with Qwen's 77.6% on all 85 tickets, which is a different set; the same-ticket comparison above is the supported one.
- **The test set is not new data.** All models also ran on the full golden set in Assignment 1; the test set gives a fair comparison on the same tickets with the cascade rule not tuned on them.
- **The rule was designed from Assignment 1 evidence, not fresh tuning runs.** The escalation lists were chosen using Assignment 1 predictions (older i7, Ollama 0.34.4) restricted to the 90 tuning tickets, so there is no `analysis/a2/tuning/` directory. The rule document reports the resulting tuning estimates (A: 81/90 escalated, 70/90 correct; B: 73/90, 68/90), and I recomputed those from the Assignment 1 records and they match. Debt collection has only 5 tuning tickets. This reading, and the row-value reading of "odd/even rows", should be confirmed with the lecturer.
- **Queueing in the speed tests.** The rate was set from S as the brief specifies, but S came from three short tickets, so the cascades ran at or above capacity and their p50 values partly reflect run length (Section 4.3).
- **Long single requests.** One Qwen request in run 2 (row 8772, 70.5 s service), one cascade A request in run 2 (row 8568, 76.0 s), and one cascade B request in the accuracy run (71.5 s) were far above the rest (all other speed-run requests took 9.7 s or less). Their cause was not captured. They are included, not removed, and they affect p95 and the affected runs' p50.
- **Network path.** JMeter on Machine B reached Machine A through USB tethering to a phone on Wi-Fi, as in Assignment 1. Four Qwen run 1 requests failed with connection timeouts that never reached the service. This adds latency and some errors common to all configurations.
- **One machine, one arrival rate, one run length.** A laptop on Windows with Docker Desktop. The rate is 92.8× the client's modelled peak, so these results compare configurations at an accelerated rate and do not predict real-world latency at the client's true load. Do not scale the numbers by core count.
- **Residency checks.** `ollama ps` before each cascade run listed both models. The after-run records show models unloaded because the check ran after the 6-minute drain, past Ollama's default 5-minute keep-alive, so they are not a during-run check.
- **Excluded run.** The first Qwen JMeter run (`jmeter/results/a2_qwen2.5_7b_run0_invalid_no_warmup.jtl`) began before the restart and warm-up, so it is retained but not used.
- **Pair coverage.** Only `llama3.2:1b` + `qwen2.5:7b` was run as a cascade. The memory check passed for `llama3.2:3b` + `qwen2.5:7b` too, but that pair was not tested.

## 10. Where each figure comes from

| Figure | Source |
| --- | --- |
| Split and counts | `analysis/a2/golden_split.csv` (`python3 scripts/split_golden_set.py --check`) |
| Limits, per-category table | `docs/a2_accuracy_limits.md`, `analysis/a2/accuracy/qwen2.5_7b.json` |
| Accuracy, per-category, escalation, sequential latency | `analysis/a2/accuracy/{qwen2.5_7b,llama3.2_3b,llama3.2_1b,cascade_A,cascade_B}.json` |
| S, rate, timeout, pause | `analysis/a2/timing/qwen_s.json`, `jmeter/test_plans/a2_ticket_triage_speed_test.jmx` |
| Per-run speed, p50, pooled p95, throughput, escalation under load | `analysis/a2/speed/{qwen2.5_7b,cascade_a,cascade_b}.json` from `jmeter/results/a2_<config>_run<n>.jtl` and `analysis/a2/speed/logs/` |
| Service time, utilisation, long requests | `analysis/a2/speed/service_times.json` |
| Run records, environment snapshots | `analysis/a2/speed/runs/`, `analysis/a2/speed/environment/` |
| Client peak | `analysis/workload_model.json` |
| Frozen rule and predictions | `docs/a2_escalation_rule.md`, `predictions/a2_prediction_record.md` |

Re-derive and check:

```bash
python3 scripts/split_golden_set.py --check
python3 -m unittest tests.test_split_golden_set tests.test_a2_cascade tests.test_a2_accuracy tests.test_a2_speed tests.test_build_a2_speed_rows tests.test_a2_service_times -v
for c in qwen2.5_7b cascade_a cascade_b; do L=""; [ $c != qwen2.5_7b ] && L="--service-log analysis/a2/speed/logs/${c}_run1.jsonl --service-log analysis/a2/speed/logs/${c}_run2.jsonl --service-log analysis/a2/speed/logs/${c}_run3.jsonl"; python3 scripts/summarize_a2_speed.py --jtl jmeter/results/a2_${c}_run1.jtl --jtl jmeter/results/a2_${c}_run2.jtl --jtl jmeter/results/a2_${c}_run3.jtl $L --expected-sent 56 --arrival-window-seconds 300 --output analysis/a2/speed/$c.json; done
python3 scripts/a2_service_times.py
git diff --exit-code analysis/a2/speed
git diff --exit-code 3752b350984145462dbfc724c2a6d9969f324dd5 -- src/app
```

## 11. Open items for the team

1. ~~Review and approve the recommendation in Section 8.~~ Done 16 November 2026.
2. Confirm with the lecturer: the row-value reading of "odd/even rows", and using Assignment 1 records for rule design.
3. Decide whether to look for the cause of the three 70–76 s requests (for example the Ollama server log) before submission.
4. Decide whether to add a supplementary lower-rate speed run to show the cascade without queueing. It is not required by the brief; if run, report it separately and do not replace the committed runs.
5. The 8-slide deck (`Group08_A2.pptx`) is built and its figures match this document and the raw files. Before submission:
   - Replace the placeholder `[Team to confirm: name the tools and versions used.]` in the slide 8 AI declaration with the actual tools and versions.
   - Slide 5's bar chart labels its groups `1`, `2`, `3`; they are `qwen2.5:7b`, cascade A and cascade B. Label them.
   - Slide 7 says Qwen answered A's escalated tickets "81.0% right vs 77.6% when run alone", which compares different ticket sets. The same-ticket figures are 64/79 vs 62/79 (4 answers differed).
   - Slide 6's "Overall limit 67.65%" label is clipped at the right edge and the `llama3.2:1b / 3b` label overlaps its points.
   - Slide 1's repository link shows square brackets around the URL.
   - Slide 7 states the break-even as about 79%; Section 6 explains why this differs from the 67% on the accuracy-run basis.
