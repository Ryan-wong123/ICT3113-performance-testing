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

# Assignment 2 Playbook (in progress)

Steps 1–8 are complete; speed runs in step 9 are next. Cascade switch (default off, see `docs/task.md` "When to turn the cascade switch on"): off for single-model work; on only for cascade work, confirmed before each run. Fixed speed parameters are 11.253 arrivals/minute for 5 minutes, a 300-second timeout, and a 360-second trailing pause. Machine B uses `jmeter/test_plans/a2_ticket_triage_speed_test.jmx` and its 70-row projection `jmeter/test_plans/a2_speed_narratives.csv`; the projection is derived in order from the `workload` rows in `analysis/a2/speed_test_rows.csv`.

1. **Split the golden set (commit first).** Odd rows = tuning, even rows = test; write `analysis/a2/golden_split.csv`.
2. **Memory check.** Start the service with Ollama; load the large and small model; run a few tickets through each; run `ollama ps` in the Ollama container and confirm both are listed and stay listed. Save the output. If they do not both stay loaded, try a smaller pair; if none fits, stop and report that a cascade is not feasible.
3. **Record the environment.** Versions, digests, Ollama settings (see `docs/test_environment.md`, Assignment 2 section).
4. **Single-model test-set accuracy.** For the top model and each other model, send every even-row ticket through `POST /tickets`; score overall, per-category (with counts) and a confusion matrix into `analysis/a2/accuracy/<config>.json`. Derive the limits in `docs/a2_accuracy_limits.md` from the top model.
5. **Design the rule on the tuning set only.** Pick the approach and two settings; write `docs/a2_escalation_rule.md`.
6. **Predictions (commit first).** Commit `predictions/a2_prediction_record.md` and `docs/a2_escalation_rule.md` before any cascade benchmark.
7. **Cascade accuracy.** Test-set run at both settings, with escalated count, and accuracy of escalated vs non-escalated tickets.
8. **Pick the speed-test parameters.** Restart Ollama and warm up; send three different typical-length tickets one at a time to the top model; S = the middle time. Rate = one ticket per 2×S seconds. Run length = S minutes (minimum 5). Same for every configuration. Choose and commit the fixed ordered workload rows (outside the golden set, some typical and some long) in `analysis/a2/speed_test_rows.csv`.
9. **Speed runs (three per configuration).** Follow "Speed runs — step by step" below. Configurations: `qwen2.5_7b`, `cascade_a`, `cascade_b` (both small models failed accuracy, so they are not speed-tested).
10. **Report per run:** sent, completed, errored, unfinished; p50 from successful requests (mean and spread across the three runs); p95 pooled over the three runs (state the sample count); throughput; error rate; cascade escalation fraction from the service-log segment. No p99. Compare the test rate with the client's peak from `analysis/workload_model.json`. Do not reuse Assignment 1 speed figures.
11. **Reconcile and recommend.** Every figure must trace to a `.jtl`, log or JSON in the repository; compare the recommendation, predictions and outcomes in `docs/a2_results.md`.

## Speed runs — step by step

Fixed for every run: `rate(11.253/min) random_arrivals(5 min) pause(360 sec)`, seed 8, 300-second HTTP timeout, the 70-row ordered workload. Nothing is overridden on the command line except Machine A's address. One run takes about 13–15 minutes (restart, warm-up, 5-minute arrivals, 6-minute drain), so 9 runs take about 2.5 hours.

### Once, before the first run

| Machine A (i9: service + Ollama) | Machine B (i7: JMeter only) |
| --- | --- |
| `git checkout assignment-2; git pull` | `git checkout assignment-2; git pull` |
| Close every other application; plug in the charger; set Windows power mode to *Best performance*; disable sleep. | Plug in; disable sleep. |
| Find the LAN IP: `ipconfig` (IPv4 of the active adapter). | Check JMeter: `jmeter.bat --version` shows 5.6.3 (or note its full path for `-JMeter`). |
| Allow Machine B in (admin PowerShell, once): `New-NetFirewallRule -DisplayName "A2 triage 8000" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow` | Check reachability: `Invoke-RestMethod http://<machine-a-ip>:8000/health` |
| If scripts are blocked: `Set-ExecutionPolicy -Scope Process Bypass` in each new PowerShell window. | Same execution-policy note. |

Both machines on the same network, both on wired or both on the same Wi-Fi; do not change networks between configurations.

### Per configuration (do `qwen2.5_7b`, then `cascade_a`, then `cascade_b`)

On **Machine A**, from the repository root:

```powershell
.\scripts\a2_start_service.ps1 -Config qwen2.5_7b      # later: cascade_a, then cascade_b
```

It sets every variable explicitly (nothing carries over from the previous configuration), recreates the container, and stops with "Configuration mismatch, do NOT run" unless `/health` **and** the container's escalation list match `docs/a2_escalation_rule.md`.

### Per run (repeat for `-Run 1`, `2`, `3`)

1. **Machine A:** `.\scripts\a2_speed_run.ps1 -Config qwen2.5_7b -Run 1`
   - restarts Ollama (pass `-OllamaApp "<path>\ollama app.exe"` if it is not in the default location), checks the three model IDs, saves `analysis/a2/speed/environment/<config>_run<n>.txt`;
   - sends the three fixed warm-up tickets (timings discarded); for the cascade it also loads `qwen2.5:7b` directly with `num_gpu: 0`;
   - stops unless `ollama ps` lists the expected model(s) at 100% CPU;
   - records `GET /stats` and the log line count, then prints **READY**.
2. **Machine B, within 4 minutes of READY** (Ollama unloads idle models after 5 minutes):
   `.\scripts\a2_jmeter_run.ps1 -Config qwen2.5_7b -Run 1 -HostA <machine-a-ip>`
   It refuses to start if Machine A's `/health` does not match the configuration, then runs the committed plan unchanged and prints sample and success counts. Do not touch either machine for the ~11 minutes it runs.
3. **Machine A:** when Machine B has finished, press **Enter** in the waiting window. The script records `/stats` and the log line count again, re-checks `ollama ps`, and writes `analysis/a2/speed/runs/<config>_run<n>.json` and the log segment `analysis/a2/speed/logs/<config>_run<n>.jsonl`. If it warns that a model was unloaded during the run, keep the run and report it.
4. **Check the run:** `stored_during_run` (Machine A) should equal the successful samples (Machine B). Any gap is unfinished or failed requests: report it, never delete the run. A repeated run is a new run number and both are reported.

### Commit after each configuration (avoid conflicts)

- **Machine B** commits only its JTLs: `git add jmeter/results/a2_<config>_run*.jtl; git commit -m "A2 speed runs: <config> JTLs"; git pull --rebase; git push`. (`*.jmeter.log` files are git-ignored debug output.)
- **Machine A** then pulls and commits only its own evidence: `git pull; git add analysis/a2/speed logs/requests.jsonl; git commit -m "A2 speed runs: <config> service evidence"; git push`.
- Never edit `docs/a2_escalation_rule.md` or `predictions/a2_prediction_record.md`. Never truncate `logs/requests.jsonl`.

### After all nine runs (any machine)

The arrival count is fixed by the seed, so every run should send the same number of requests. Use the largest JTL sample count as `--expected-sent` unless a JMeter log shows otherwise, and state the number in the report.

```bash
python3 scripts/summarize_a2_speed.py \
  --jtl jmeter/results/a2_cascade_a_run1.jtl --jtl jmeter/results/a2_cascade_a_run2.jtl --jtl jmeter/results/a2_cascade_a_run3.jtl \
  --service-log analysis/a2/speed/logs/cascade_a_run1.jsonl --service-log analysis/a2/speed/logs/cascade_a_run2.jsonl --service-log analysis/a2/speed/logs/cascade_a_run3.jsonl \
  --expected-sent <N> --arrival-window-seconds 300 --output analysis/a2/speed/cascade_a.json
```

Repeat for `cascade_b` and for `qwen2.5_7b` (no `--service-log` for the single model). Check `duplicate_ticket_rows` is empty and that each run's `completed` matches `stored_during_run` plus errors.
