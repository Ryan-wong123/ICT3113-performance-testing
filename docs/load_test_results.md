# Step 5: Load and Stress Test Results

## Status and scope

The final load evidence is the separate-machine dataset collected on 4 October 2026:

- **Machine A:** Ticket Triage Docker container plus native, CPU-only Ollama.
- **Machine B:** Apache JMeter 5.6.3 and Java 21 only.
- **Traffic path:** Machine B to `http://192.168.68.57:8000`.
- **Pacing:** JMeter core `PreciseThroughputTimer`, an open-loop Poisson arrival process.
- **Matrix:** 3 models × 2 rates × 3 repeats = 18 runs.
- **Stress:** `llama3.2:1b` at 40/min and 60/min for 180 seconds of arrivals, three repeats at each rate.

Every value below is computed from a kept `jmeter/results/*_remote.jtl` file with `scripts/summarize_jtl.py`'s nearest-rank percentile method. Throughput uses the longer of the configured arrival window and the interval from the first sample start to the final sample completion; this prevents sparse runs from being overstated and includes time spent draining queued work after arrivals stop. The older files without `_remote` are retained as co-located pipeline-validation evidence, but they are not the final load measurements.

The realistic Step 3 peak is only 7.278311 tickets/hour (0.1213/min). A short test at that rate would contain too few samples to calculate useful percentiles, so the matrix deliberately uses accelerated rates. Each model's lower tested rate is still at least 12 times the realistic peak.

## Pooled results across the three repeats

Pooled percentiles combine all three raw JTL files for the named configuration. Offered/observed arrivals are `total samples / total configured arrival-window duration`. All regular runs completed within their configured windows, so completed throughput equals that arrival rate; successful throughput excludes failed samples. Poisson pacing explains small count variation at the lowest rates.

| Model | Target rate | n | Completed / successful throughput | Errors | Mean | p50 | p95 | p99 | Max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `llama3.2:1b` | 7/min | 42 | 7.00 / 6.67 per min | 2 (4.76%) | 962ms | 872ms | 2,067ms | 2,112ms | 2,112ms |
| `llama3.2:1b` | 22/min | 132 | 22.00 / 21.17 per min | 5 (3.79%) | 715ms | 501ms | 1,868ms | 2,747ms | 2,785ms |
| `llama3.2:3b` | 3.5/min | 22 | 3.67 / 3.67 per min | 0 | 1,405ms | 1,190ms | 2,498ms | 2,854ms | 2,854ms |
| `llama3.2:3b` | 11/min | 66 | 11.00 / 11.00 per min | 0 | 1,298ms | 1,041ms | 3,059ms | 4,031ms | 4,031ms |
| `qwen2.5:7b` | 1.5/min | 9 | 2.00 / 2.00 per min | 0 | 3,049ms | 3,052ms | 4,840ms | 4,840ms | 4,840ms |
| `qwen2.5:7b` | 5/min | 24 | 5.33 / 5.33 per min | 0 | 3,443ms | 2,116ms | 6,404ms | 9,196ms | 9,196ms |

The seven normal-matrix errors all came from `llama3.2:1b` returning text outside the seven-category output contract; the service correctly returned HTTP 502. They are model-output errors, not JMeter or network errors. The larger models produced no matrix errors.

## Per-run results

### `llama3.2:1b`

| Rate | Run | n | Errors | p50 | p95 | p99 | Raw evidence |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 7/min | 1 | 14 | 1 | 909ms | 1,727ms | 1,727ms | `llama3.2_1b_rate7_run1_remote.jtl` |
| 7/min | 2 | 14 | 1 | 772ms | 1,773ms | 1,773ms | `llama3.2_1b_rate7_run2_remote.jtl` |
| 7/min | 3 | 14 | 0 | 802ms | 2,112ms | 2,112ms | `llama3.2_1b_rate7_run3_remote.jtl` |
| 22/min | 1 | 44 | 0 | 639ms | 1,959ms | 2,747ms | `llama3.2_1b_rate22_run1_remote.jtl` |
| 22/min | 2 | 44 | 3 | 444ms | 1,541ms | 1,806ms | `llama3.2_1b_rate22_run2_remote.jtl` |
| 22/min | 3 | 44 | 2 | 477ms | 1,961ms | 2,785ms | `llama3.2_1b_rate22_run3_remote.jtl` |

### `llama3.2:3b`

| Rate | Run | n | Errors | p50 | p95 | p99 | Raw evidence |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 3.5/min | 1 | 8 | 0 | 1,032ms | 2,437ms | 2,437ms | `llama3.2_3b_rate3.5_run1_remote.jtl` |
| 3.5/min | 2 | 7 | 0 | 1,190ms | 2,854ms | 2,854ms | `llama3.2_3b_rate3.5_run2_remote.jtl` |
| 3.5/min | 3 | 7 | 0 | 1,522ms | 2,498ms | 2,498ms | `llama3.2_3b_rate3.5_run3_remote.jtl` |
| 11/min | 1 | 22 | 0 | 1,159ms | 3,159ms | 4,031ms | `llama3.2_3b_rate11_run1_remote.jtl` |
| 11/min | 2 | 22 | 0 | 999ms | 2,987ms | 3,622ms | `llama3.2_3b_rate11_run2_remote.jtl` |
| 11/min | 3 | 22 | 0 | 776ms | 2,226ms | 2,618ms | `llama3.2_3b_rate11_run3_remote.jtl` |

### `qwen2.5:7b`

| Rate | Run | n | Errors | p50 | p95 | p99 | Raw evidence |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1.5/min | 1 | 3 | 0 | 4,111ms | 4,840ms | 4,840ms | `qwen2.5_7b_rate1.5_run1_remote.jtl` |
| 1.5/min | 2 | 3 | 0 | 1,789ms | 4,738ms | 4,738ms | `qwen2.5_7b_rate1.5_run2_remote.jtl` |
| 1.5/min | 3 | 3 | 0 | 3,052ms | 4,187ms | 4,187ms | `qwen2.5_7b_rate1.5_run3_remote.jtl` |
| 5/min | 1 | 8 | 0 | 1,738ms | 4,737ms | 4,737ms | `qwen2.5_7b_rate5_run1_remote.jtl` |
| 5/min | 2 | 8 | 0 | 2,010ms | 6,404ms | 6,404ms | `qwen2.5_7b_rate5_run2_remote.jtl` |
| 5/min | 3 | 8 | 0 | 4,278ms | 9,196ms | 9,196ms | `qwen2.5_7b_rate5_run3_remote.jtl` |

At 1.5/min, each Qwen run has only three samples. Those individual p95/p99 values are maxima rather than stable tail estimates. The three-run pool is still only nine samples, so its tail must be treated as indicative. This limitation is stated rather than concealed.

## Mean and spread across the three repeats

The assignment asks for both the mean and the spread across repeated runs. Each cell below is the arithmetic mean of the three run-level statistics followed by the observed minimum–maximum range. This is intentionally separate from the pooled table above: pooling describes all samples together, whereas this table shows repeatability between runs.

| Model and rate | Run mean latency | p50 mean (range) | p95 mean (range) | p99 mean (range) |
| --- | ---: | ---: | ---: | ---: |
| `llama3.2:1b`, 7/min | 962ms (886–1,092) | 828ms (772–909) | 1,871ms (1,727–2,112) | 1,871ms (1,727–2,112) |
| `llama3.2:1b`, 22/min | 715ms (603–853) | 520ms (444–639) | 1,820ms (1,541–1,961) | 2,446ms (1,806–2,785) |
| `llama3.2:3b`, 3.5/min | 1,405ms (1,386–1,431) | 1,248ms (1,032–1,522) | 2,596ms (2,437–2,854) | 2,596ms (2,437–2,854) |
| `llama3.2:3b`, 11/min | 1,298ms (960–1,515) | 978ms (776–1,159) | 2,791ms (2,226–3,159) | 3,424ms (2,618–4,031) |
| `qwen2.5:7b`, 1.5/min | 3,049ms (2,752–3,495) | 2,984ms (1,789–4,111) | 4,588ms (4,187–4,840) | 4,588ms (4,187–4,840) |
| `qwen2.5:7b`, 5/min | 3,443ms (2,251–4,418) | 2,675ms (1,738–4,278) | 6,779ms (4,737–9,196) | 6,779ms (4,737–9,196) |

| Model and rate | Completed throughput mean (range) | Successful throughput mean (range) | Error-rate mean (range) |
| --- | ---: | ---: | ---: |
| `llama3.2:1b`, 7/min | 7.00/min (7.00–7.00) | 6.67/min (6.50–7.00) | 4.76% (0.00–7.14) |
| `llama3.2:1b`, 22/min | 22.00/min (22.00–22.00) | 21.17/min (20.50–22.00) | 3.79% (0.00–6.82) |
| `llama3.2:3b`, 3.5/min | 3.67/min (3.50–4.00) | 3.67/min (3.50–4.00) | 0.00% (0.00–0.00) |
| `llama3.2:3b`, 11/min | 11.00/min (11.00–11.00) | 11.00/min (11.00–11.00) | 0.00% (0.00–0.00) |
| `qwen2.5:7b`, 1.5/min | 2.00/min (2.00–2.00) | 2.00/min (2.00–2.00) | 0.00% (0.00–0.00) |
| `qwen2.5:7b`, 5/min | 5.33/min (5.33–5.33) | 5.33/min (5.33–5.33) | 0.00% (0.00–0.00) |

The two rates were selected before the final remote rerun from latency measured on the older i7 accuracy-test environment. They are therefore low/high **test rates**, not demonstrated below/above-capacity points for the faster i9 Machine A. Only the dedicated 40/min and 60/min probes establish a capacity bracket on Machine A.

## Stress boundary for `llama3.2:1b`

The offered/observed arrival rate is the number of JMeter samples divided by the configured three-minute arrival window. Completed and successful throughput use the longer of that window and first-sample-to-final-completion time. This distinction matters when queued work continues after arrivals stop. Successful throughput additionally excludes failed samples. The first 40/min and 60/min files retain their original names; the additional files are explicitly numbered `run2` and `run3`.

| Rate | Run | n | Errors | Mean | p50 | p95 | p99 | Max | Offered / completed / successful rate | Raw evidence |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 40/min | 1 | 120 | 4 (3.33%) | 1,379ms | 1,273ms | 2,736ms | 3,743ms | 3,762ms | 40.00 / 40.00 / 38.67 per min | `llama3.2_1b_stress_remote.jtl` |
| 40/min | 2 | 121 | 1 (0.83%) | 2,036ms | 1,839ms | 4,131ms | 5,334ms | 5,451ms | 40.33 / 40.33 / 40.00 per min | `llama3.2_1b_stress40_run2_remote.jtl` |
| 40/min | 3 | 120 | 1 (0.83%) | 1,295ms | 996ms | 3,154ms | 3,890ms | 4,485ms | 40.00 / 40.00 / 39.67 per min | `llama3.2_1b_stress40_run3_remote.jtl` |
| 60/min | 1 | 181 | 154 (85.08%) | 6,277ms | 5,001ms | 5,003ms | 7,024ms | 300,044ms | 60.33 / 30.25 / 4.51 per min | `llama3.2_1b_stress60_remote.jtl` |
| 60/min | 2 | 180 | 3 (1.67%) | 6,372ms | 1,102ms | 66,816ms | 69,622ms | 69,815ms | 60.00 / 44.31 / 43.57 per min | `llama3.2_1b_stress60_run2_remote.jtl` |
| 60/min | 3 | 180 | 4 (2.22%) | 982ms | 768ms | 2,609ms | 3,095ms | 3,757ms | 60.00 / 60.00 / 58.67 per min | `llama3.2_1b_stress60_run3_remote.jtl` |

### Stress mean and spread across repeats

As in the regular matrix, each cell is the arithmetic mean of the three run-level statistic followed by its observed minimum–maximum range.

| Rate | Run mean latency | p50 mean (range) | p95 mean (range) | p99 mean (range) | Error-rate mean (range) |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 40/min | 1,570ms (1,295–2,036) | 1,369ms (996–1,839) | 3,340ms (2,736–4,131) | 4,322ms (3,743–5,334) | 1.66% (0.83–3.33) |
| 60/min | 4,544ms (982–6,372) | 2,290ms (768–5,001) | 24,809ms (2,609–66,816) | 26,580ms (3,095–69,622) | 29.66% (1.67–85.08) |

| Rate | Completed throughput mean (range) | Successful throughput mean (range) |
| ---: | ---: | ---: |
| 40/min | 40.11/min (40.00–40.33) | 39.44/min (38.67–40.00) |
| 60/min | 44.85/min (30.25–60.00) | 35.58/min (4.51–58.67) |

For completeness, pooling all samples at each stress rate gives:

| Rate | n | Errors | Mean | p50 | p95 | p99 | Max |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 40/min | 361 | 6 (1.66%) | 1,571ms | 1,384ms | 3,435ms | 4,899ms | 5,451ms |
| 60/min | 541 | 161 (29.76%) | 4,547ms | 1,538ms | 5,003ms | 69,359ms | 300,044ms |

The pooled 60/min p95 of about five seconds is misleading on its own: 152 failures in run 1 were clipped at the configured five-second connect timeout, while run 2's successful but queued requests produced a 66.8-second p95. The across-run table exposes that instability instead of averaging it away.

All three 40/min runs were stable for their full windows: p95 remained 2.736–4.131 seconds, successful throughput remained 38.67–40.00/min, and all six errors were output-contract HTTP 502s rather than overload/network failures.

At 60/min, behaviour was not repeatably sustainable:

- **Run 1 collapsed:** 152 connect timeouts, one 300-second response timeout, one output-contract 502, and only 27 successful JMeter samples. Successful throughput fell to 4.51/min over the full 358.98-second completion span. From 60 seconds onward every new sample failed.
- **Run 2 developed a late queue:** the final 30-second arrival bucket had mean latency 27.7 seconds, p95 69.6 seconds, and maximum 69.8 seconds. The error rate stayed low, but queued drain time reduced completed throughput to 44.31/min against 60/min offered traffic.
- **Run 3 remained stable:** p95 was 2.609 seconds with four output-contract 502s. This shows 60/min is a state- and burst-sensitive boundary region, not a rate that fails identically every time.

The defensible conclusion is therefore:

- **Largest tested consistently sustainable rate:** 40/min (three of three stable repeats).
- **First tested unreliable rate:** 60/min (two of three repeats showed collapse or severe queue growth).
- **Measured reliability boundary:** between 40 and 60 tickets/minute on this Machine A and test setup.

The evidence does not justify an exact maximum. Tests at 45/50/55 per minute, preferably with longer windows, would be required to narrow the transition.

## Bottleneck diagnosis

The bottleneck remains CPU-only Ollama inference serialised behind the service's single classification lock. At 40/min, all three repeats drained traffic consistently. At 60/min, variation in Poisson bursts and model-generation time sometimes creates a queue faster than the single locked inference path can drain it. Run 2 shows this directly through sharply increasing final-bucket latency; run 1 shows the next failure stage, where the request/socket backlog fills and clients hit connection and response timeouts. Run 3 happened not to accumulate that queue, which is why 60/min must be described as unreliable rather than universally failing. The container remained healthy after each run; this is overload sensitivity, not a crash.

The baseline intentionally has no cache, batching, queue limit, load shedding, or background workers. Those omissions explain why overload becomes long waits and connection failures rather than controlled HTTP 429/503 responses; they must not be “fixed” in Assignment 1.

## Requirement reconciliation

### R1 — p95 `POST /tickets` below 10 seconds at peak

All three candidates pass in the new load-test environment. Their pooled p95 at the lower accelerated rates is 2.067s, 2.498s, and 4.840s respectively, even though those rates are 58×, 29×, and 12× the realistic peak of 7.278311/hour. The Qwen conclusion has the small-sample caveat above.

### R2 — at least 8 tickets/hour sustained

All three candidates pass. The lowest successful pooled throughput was Qwen's 2.00/min (120/hour), fifteen times the requirement, with zero errors. Even the lowest successful regular-matrix throughput, `llama3.2:1b` at 6.67/min, remains far above R2.

### R3 — at least 85% overall accuracy and no category below 70%

All three candidates still fail, based on the frozen accuracy evidence in `analysis/accuracy/*.json`: 28.0% (`llama3.2:1b`), 32.0% (`llama3.2:3b`), and 78.9% (`qwen2.5:7b`). See `docs/accuracy_results.md` for per-category results.

| Requirement | `llama3.2:1b` | `llama3.2:3b` | `qwen2.5:7b` |
| --- | --- | --- | --- |
| R1 — p95 < 10s | **PASS** (2.067s) | **PASS** (2.498s) | **PASS** (4.840s; n=9 caveat) |
| R2 — ≥8/hour | **PASS** | **PASS** | **PASS** |
| R3 — accuracy threshold | **FAIL** (28.0%) | **FAIL** (32.0%) | **FAIL** (78.9%) |

**No candidate meets all three requirements.** The failure is accuracy, not performance, in the final separate-machine environment.

## Comparison with the older co-located dataset

The old non-remote JTL files remain in `jmeter/results/`. Applying the same pooled nearest-rank method gives:

| Configuration | Old co-located p95 | New separate-machine p95 |
| --- | ---: | ---: |
| `llama3.2:1b`, 7/min | 15,896ms | 2,067ms |
| `llama3.2:1b`, 22/min | 37,341ms | 1,868ms |
| `llama3.2:3b`, 3.5/min | 45,896ms | 2,498ms |
| `llama3.2:3b`, 11/min | 42,054ms | 3,059ms |
| `qwen2.5:7b`, 1.5/min | 62,569ms | 4,840ms |
| `qwen2.5:7b`, 5/min | 92,277ms | 6,404ms |

This is **not** a controlled measurement of co-location bias. The system-under-test hardware also changed from the older Intel i7-9750H machine to the current Intel i9-14900HX Machine A, and Ollama changed from 0.34.4 to 0.35.1. The direction is consistent with removing resource competition and using a much faster CPU, but the contribution of each change cannot be isolated. The old claim that 40/min caused unbounded growth applies only to the old environment and is superseded for the final environment.

## Raw-evidence reconciliation

The 24 remote JTL files contain exactly 1,197 samples:

| JMeter outcome | Count |
| --- | ---: |
| Successful response | 1,023 |
| HTTP 502 response | 21 |
| TCP connect timeout before reaching the service | 152 |
| Response/read timeout after reaching the service | 1 |
| **Total JTL samples** | **1,197** |

The service log reconciliation is exact:

- The repository already contained 946 historical `POST /tickets` entries.
- Of the 1,197 remote JMeter samples, 1,045 reached the FastAPI service and therefore appear in `logs/requests.jsonl`: 1,023 JMeter successes, 21 HTTP 502s, and the one read-timeout request that eventually completed server-side with 201 after JMeter stopped waiting.
- The 152 TCP connect timeouts never reached FastAPI and correctly have no service-log entry.
- Six untimed manual model-warm-up requests were logged separately, including the warm-up before the repeated stress block.
- `946 + 1,045 + 6 = 1,997`, exactly matching the current `POST /tickets` count in `logs/requests.jsonl`.

No reported result depends on an unreconciled request, and `predictions/prediction_record.md` remains unchanged.
