# Step 5: Test Playbook

Prerequisites for all three test types: Docker running, `docker compose up --build` from the repo root, a local Ollama instance (`ollama serve`) reachable at `http://localhost:11434` with the target candidate model already pulled (`ollama pull <tag>`).

## 1. Accuracy test playbook

**Objective:** measure overall and per-category classification accuracy of one candidate model against the frozen 175-ticket golden test set, and produce a confusion matrix.

**Steps:**
1. Set the container to the candidate model and restart with a clean database:
   ```bash
   docker compose down
   rm -f runtime/tickets.db
   OLLAMA_MODEL=<candidate tag, e.g. llama3.2:3b> docker compose up -d
   ```
2. Confirm the correct model is loaded: `curl http://localhost:8000/health` — check the `model` field.
3. (Recommended, avoids cold-start polluting the first measurement) send one throwaway warm-up request: `curl -X POST http://localhost:8000/tickets -H "Content-Type: application/json" -d '{"narrative":"warm up"}'`. Then stop the container, delete `runtime/tickets.db`, and recreate it with the same `OLLAMA_MODEL`; a plain `docker compose restart` does **not** clear a bind-mounted database or append-only log. Keep the warm-up log entry and account for it separately.
4. Run the scorer, which sends all 175 golden-set tickets through the real `POST /tickets` endpoint, one at a time:
   ```bash
   python3 scripts/run_accuracy_test.py --model-label <candidate tag>
   ```
5. Result: `analysis/accuracy/<candidate_tag_with_underscores>.json` — overall accuracy, per-category accuracy, confusion matrix, and warm-latency percentiles (used for R1).
6. Repeat steps 1–5 for each candidate model.

**Expected duration:** ~4 minutes (`llama3.2:1b`) to ~35+ minutes (`qwen2.5:7b`) per model, dominated by Ollama inference time, not the script itself.

## 2. Load test playbook (open-loop, per model, per rate)

**Objective:** measure p50/p95/p99 latency, completed and successful throughput, and error rate at a controlled open-loop arrival rate, three repeats per configuration.

**Steps:**
1. Set the container to the candidate model (as in the accuracy playbook, steps 1–3).
2. Determine the model's approximate sequential capacity: `60 / mean_single_request_latency_seconds` (from that model's accuracy-test JSON, `warm_latency_seconds.mean_s`) gives requests/minute.
3. Choose two rates to test: below capacity (~50% of the computed capacity) and above capacity (~150%).
4. Run 3 repeats at each rate from separate Machine B, targeting Machine A's reachable IP. The exact PowerShell command and completed rate matrix are in `docs/remote_load_test_runbook.md`.
5. Keep outputs with the `_remote` suffix so they cannot overwrite the historical co-located files.
6. Summarise a run: `python3 scripts/summarize_jtl.py jmeter/results/<file>.jtl --arrival-window-seconds <90-or-120>` — prints and optionally saves p50/p95/p99, completed and successful throughput, offered arrival rate, and error rate/codes. Supplying the configured window prevents sparse low-rate runs from overstating throughput; queued drain time beyond that window is still counted.
7. Repeat for every candidate model and both rates (6 runs per model, 18 total for 3 candidates).

The older same-machine wrapper remains useful for a local smoke test only:

```bash
for run in 1 2 3; do
  bash scripts/run_jmeter_test.sh <model_label> <rate_per_min> <duration_sec> $run
done
```

**Design notes for reproducers:** the JMeter plan (`jmeter/test_plans/ticket_triage_load_test.jmx`) uses the core `PreciseThroughputTimer` (a Poisson-arrival open-loop timer, standard in JMeter 5.x — no plugin needed) inside a Thread Group with 50 threads (enough headroom that the timer, not thread availability, governs pacing at these rates) and a `JSR223PreProcessor` (Groovy) that builds the JSON request body via `JsonOutput.toJson(...)`, which safely escapes narratives containing quotes or newlines. Narratives are drawn from `jmeter/test_plans/load_test_narratives.csv` — the 825 Team 8 rows **not** in the golden set, kept separate so load-test traffic never touches the frozen accuracy-evaluation data.

## 3. Stress test playbook (find the limit)

**Objective:** determine the arrival rate beyond which latency grows without bound for at least one candidate model.

**Steps:**
1. Pick a model already characterised by the load test (its approximate capacity is known).
2. Set the container to that model, with a clean database, following an explicit warm-up call (see accuracy playbook step 3) so the very first sample isn't cold-start-polluted.
3. Run a longer JMeter invocation directly from Machine B (not through the same-machine wrapper) with an increased thread pool. Preserve every probe and raise the rate without overwriting earlier evidence until a rate shows saturation or loss of repeatability. This team tested 40/min and 60/min, with three repeats at each rate:
   ```bash
   jmeter -n -t jmeter/test_plans/ticket_triage_load_test.jmx \
     -l jmeter/results/<model_label>_stress.jtl \
     -JtargetThroughputPerMin=<rate> -JdurationSec=<duration, this team used 180> \
     -Jthreads=200 -JnarrativesCsv=jmeter/test_plans/load_test_narratives.csv \
     -Jhost=<Machine A IP> -Jport=8000
   ```
4. Summarise with `python3 scripts/summarize_jtl.py <file> --arrival-window-seconds 180`. Genuine saturation may appear as unbounded latency, completed throughput below offered arrivals, rising connection/response timeouts, or a combination. Do not call a rate “the maximum” unless the kept evidence brackets or demonstrates the limit.
5. Report each repeat, the pooled samples, and the arithmetic mean plus minimum–maximum spread across repeats. The retained dataset has three 40/min and three 60/min runs. Preserve their variance: 40/min was consistently stable, whereas 60/min collapsed once, developed severe tail latency once, and remained stable once.

## Notes for anyone reproducing these results

- **Every run's raw `.jtl` file is kept in `jmeter/results/`** — do not trust a number in `docs/load_test_results.md` or `docs/accuracy_results.md` that doesn't trace to a file there or in `analysis/accuracy/`.
- **Reset `runtime/tickets.db` between model switches** (`rm -f runtime/tickets.db` before `docker compose up`) — otherwise `GET /stats` mixes tickets from different candidate models, though this does not affect the `.jtl`/accuracy-JSON evidence itself, which is self-contained per run.
- **Final load/stress evidence uses separate machines.** Files ending `_remote.jtl` are the final dataset. Files without `_remote` are the older co-located pipeline-validation dataset and must not be mixed into final pooled percentiles.

---

# Assignment 2 Playbook (planned)

Not yet executed. Cascade switch (default off, see `docs/task.md` "When to turn the cascade switch on"): off for steps 1–6 and for all single-model work; **on only for steps 7 and the cascade speed runs in step 9**, and confirm it before each such run. Follow the order below; commit the items marked **(commit first)** before running anything later in the list.

1. **Split the golden set (commit first).** Odd rows = tuning, even rows = test; write `analysis/a2/golden_split.csv`.
2. **Memory check.** Start the service with Ollama; load the large and small model; run a few tickets through each; run `ollama ps` in the Ollama container and confirm both are listed and stay listed. Save the output. If they do not both stay loaded, try a smaller pair; if none fits, stop and report that a cascade is not feasible.
3. **Record the environment.** Versions, digests, Ollama settings (see `docs/test_environment.md`, Assignment 2 section).
4. **Single-model test-set accuracy.** For the top model and each other model, send every even-row ticket through `POST /tickets`; score overall, per-category (with counts) and a confusion matrix into `analysis/a2/accuracy/<config>.json`. Derive the limits in `docs/a2_accuracy_limits.md` from the top model.
5. **Design the rule on the tuning set only.** Pick the approach and two settings; write `docs/a2_escalation_rule.md`.
6. **Predictions (commit first).** Commit `predictions/a2_prediction_record.md` and `docs/a2_escalation_rule.md` before any cascade benchmark.
7. **Cascade accuracy.** Test-set run at both settings, with escalated count, and accuracy of escalated vs non-escalated tickets.
8. **Pick the speed-test parameters.** Restart Ollama and warm up; send three different typical-length tickets one at a time to the top model; S = the middle time. Rate = one ticket per 2×S seconds. Run length = S minutes (minimum 5). Same for every configuration. Choose and commit the fixed ordered workload rows (outside the golden set, some typical and some long) in `analysis/a2/speed_test_rows.csv`.
9. **Each speed run (three per configuration).**
   1. Restart the Ollama container; check `GET /health` or `ollama ps`.
   2. Send the same three fixed warm-up tickets one at a time; discard timings. For the cascade, make sure both models are loaded (warm-up tickets that the rule escalates, or one sent directly to the large model); confirm both in `ollama ps`.
   3. Call `GET /stats` and note the total.
   4. Run JMeter (open-loop; Open Model Thread Group or `PreciseThroughputTimer`) on the separate machine at the chosen rate and length. HTTP response timeout = max(10×S s, 5 min); the trailing pause is longer than the timeout by at least one minute (for S = 6, `rate(5/min) random_arrivals(6 min) pause(6 min)` with a 5-minute timeout).
   5. Call `GET /stats` again; the increase is the number of requests completed and stored.
   6. Keep the raw `.jtl` as `jmeter/results/a2_<config>_run<n>.jtl` and the segment of the service log for the run.
10. **Report per run:** sent, completed, errored, unfinished; p50 (mean and spread across the three runs); p95 pooled over the three runs (state the sample count); throughput; error rate; cascade escalation fraction from the service log. No p99. Compare the test rate with the client's peak from `analysis/workload_model.json`. Do not reuse Assignment 1 speed figures.
11. **Reconcile and recommend.** Every figure must trace to a `.jtl`, log or JSON in the repository; compare the recommendation, predictions and outcomes in `docs/a2_results.md`.
