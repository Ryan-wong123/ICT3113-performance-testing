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
