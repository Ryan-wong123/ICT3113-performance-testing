# Assignment 2 — Step-by-step handoff prompts (i9 operator)

Use this file to run the remaining Assignment 2 work, one prompt at a time, in a fresh Claude Code session on the final test machine (the i9, "Machine A"). It follows the brief in `docs/PROJECT_CONTEXT.md` Section 26 and the checklist in `docs/task.md`.

## How to use

1. Open Claude Code in a clone of the repo, on branch `assignment-2`.
2. Paste **one** prompt below. Let it finish, then review what it committed.
3. Start a **new session** for the next prompt. State is carried by the repo (committed files, the ticked `docs/task.md`, the code-freeze commit hash), not by the conversation.
4. Do the prompts strictly in order. Do not run two at once, and do not run anything else on the i9 during the speed runs.

## Before you start (once)

- Ollama, Docker and Python 3 installed on the i9; `.env` copied from `.env.example`.
- The three pinned models pulled: `llama3.2:1b`, `llama3.2:3b`, `qwen2.5:7b`.
- A **separate second computer** with Apache JMeter 5.6.3 and a JDK, reachable from the i9 over the network (needed from Prompt 6). It can be the Assignment 1 Machine B (i7) or another machine whose hardware you record.
- Your own git identity configured (`git config user.name` / `user.email`). Commits should be authored by you, with no `Co-Authored-By` trailer.
- The team ready to make three decisions: the escalation rule (Prompt 3 → 4), the predictions (Prompt 4), and the final recommendation (Prompt 7).

## Commit gates (from the brief)

| Gate | When |
| --- | --- |
| Golden-set split committed | Before anything else. **Already done** (commit "Split golden set into Assignment 2 tuning and test sets"). |
| Escalation rule and prediction record committed and pushed | Before the first Assignment 2 benchmark run. Done in Prompt 4. Never edited afterwards. |
| Speed-test row numbers committed | Before the speed runs (Prompt 2). |
| Code freeze (our own rule) | Before the first benchmark; the commit hash is recorded (Prompt 2). After it, change config only, not service code. |

## Rules that apply to every prompt

- Never edit Assignment 1 evidence (`analysis/accuracy/*.json`, `predictions/prediction_record.md`, `docs/requirements.md`, `docs/recommendation.md`) or the golden set.
- Never change Ollama inference settings between configurations; no caching; CPU-only; no hosted model API.
- Tune and design on the **tuning set** (odd `row` values) only. Every reported accuracy number and every pass/fail decision uses the **test set** (even `row` values) only.
- Every figure must reconcile with a raw file in `analysis/a2/`, `jmeter/results/` or the request logs. Never invent a number.
- Never force-push or rewrite history. If a push is rejected, fetch and ask.
- Stop and ask at each "STOP AND ASK". If anything is ambiguous, stop and ask; do not work around it silently.

---

## Prompt 1 — Environment and memory check

**Machine:** i9 only. **Done when:** environment recorded; memory-check result committed.

```text
You are continuing ICT3113 Assignment 2 for Team 8 on the final test machine (the i9, "Machine A"). This session does ONLY the tasks below, then stops.

START: run `git checkout assignment-2 && git pull`. Read CLAUDE.md, then AGENTS.md (follow it exactly, including "Assignment 2 guardrails"), then docs/PROJECT_CONTEXT.md Section 26 and docs/task.md. Commits must be authored by me (check git config) with no Co-Authored-By trailer. Push to assignment-2 after each task; never force-push. Never invent a number.

TASK 0 - Environment. Confirm Ollama, Docker, Python 3 and the three pinned models (llama3.2:1b, llama3.2:3b, qwen2.5:7b) are present. Check each local model ID against the digest in docs/candidate_models.md. Confirm `ollama ps` shows 100% CPU. Record Ollama version, Docker version, hardware, RAM given to Docker, and the Ollama inference settings (threads, parallelism, context length) in the Assignment 2 section of docs/test_environment.md. These settings are recorded once and held constant for every configuration. Ask me which separate machine will run JMeter and what its hardware is, and record that too.

TASK 1 - Memory check (the brief says do this before building anything). For each candidate pair (large = qwen2.5:7b; small = llama3.2:3b, then llama3.2:1b): load both models, run a few tickets through each (use rows OUTSIDE the golden set, from jmeter/test_plans/load_test_narratives.csv), and confirm `ollama ps` lists both and that they stay loaded. Save the `ollama ps` output in docs/test_environment.md and tick the memory-check item in docs/task.md. Commit and push.

If no pair stays resident, STOP AND ASK: the brief says to report that a cascade is not feasible, show the ollama ps evidence, and recommend a single model.

Do not write cascade code or run any golden-set ticket in this session.
```

---

## Prompt 2 — Cascade code, tooling and row lists (ends with the code freeze)

**Machine:** any (run on the i9 so the stub tests and the final code are verified there). **Done when:** code-freeze commit pushed and its hash recorded.

```text
You are continuing ICT3113 Assignment 2 for Team 8 on the i9. This session does ONLY the tasks below, then stops.

START: git checkout assignment-2 && git pull. Read CLAUDE.md, AGENTS.md (follow exactly), docs/PROJECT_CONTEXT.md Section 26, docs/task.md. Prompt 1 should already be done (memory check recorded in docs/test_environment.md); if it is not, stop and tell me. Commits authored by me, no Co-Authored-By. Push after each task; never force-push.

TASK 2 - Cascade implementation (brief Step 2). In src/app/, add the cascade inside POST /tickets behind an off-by-default, environment-driven switch (e.g. CASCADE_ENABLED, OLLAMA_SMALL_MODEL, OLLAMA_LARGE_MODEL, CASCADE_RULE_SETTING; no hardcoded model). With the switch off, behaviour must be exactly the Assignment 1 baseline (single model from OLLAMA_MODEL, synchronous, sequential, no caching/queue/batching/workers, num_gpu 0). The response must not reveal which model answered. The escalation rule is a separate pluggable function/config; thresholds are filled in later, in Prompt 4. Add the logged fields from docs/architecture.md ("Assignment 2 logged fields": cascade_mode, rule_setting, small_model, large_model, small_category, final_model, escalated) and report cascade mode in GET /health. Unit-test against a stub Ollama (no real model). Verify `git diff main -- src/app` contains only the cascade additions. Update docs/prd.md, docs/architecture.md and docs/task.md. Commit and push.

TASK 3a - Tooling. Write the Assignment 2 accuracy runner (test set only, i.e. even `row` values in analysis/a2/golden_split.csv; through the real POST /tickets, never bypassing the service; output analysis/a2/accuracy/<config>.json with overall and per-category accuracy WITH right/wrong counts, a confusion matrix, and for the cascade the escalated count and escalated vs non-escalated accuracy). Also write the speed-run summariser/helpers: per run requests sent, completed, errored, unfinished; p50 per run; mean and spread across runs; p95 pooled across the 3 runs with the sample count; throughput; error rate; escalation fraction from the service log. NO p99. Test against a stub. Commit and push.

TASK 3b - Row lists. Choose about 30 workload rows from jmeter/test_plans/load_test_narratives.csv (rows outside the golden set; a mix of typical lengths near p50 and long near p95, using analysis/ticket_length_statistics.json), plus 3 timing tickets for S and 3 warm-up tickets, all 36 rows different. Commit and push analysis/a2/speed_test_rows.csv.

CODE FREEZE: after the final code commit, state its hash and write it into docs/task.md. From here only configuration may change, not service code.

Do not run any real model on a golden-set ticket in this session.
```

---

## Prompt 3 — Limits and tuning runs (ends with your rule decision)

**Machine:** i9 only. **Done when:** limits committed; tuning outputs committed; you have chosen the rule approach and two settings.

```text
You are continuing ICT3113 Assignment 2 for Team 8 on the i9. This session does ONLY the tasks below, then stops.

START: git checkout assignment-2 && git pull. Read CLAUDE.md, AGENTS.md (follow exactly), docs/PROJECT_CONTEXT.md Section 26, docs/task.md. The code freeze from Prompt 2 must exist (its hash is in docs/task.md); if not, stop and tell me. Commits authored by me, no Co-Authored-By. Push after each task; never force-push. Never invent a number.

TASK 4 - Step 1 limits. With the cascade switch OFF and OLLAMA_MODEL=qwen2.5:7b, run ONLY the test set (even `row` values in analysis/a2/golden_split.csv) through POST /tickets using the Assignment 2 accuracy runner. Save analysis/a2/accuracy/qwen2.5_7b.json. Derive the overall limit (test-set accuracy minus 10 percentage points) and each per-category limit (that category's test accuracy minus 15 points). Fill the table in docs/a2_accuracy_limits.md with right/wrong counts, and mark categories too small for a fair per-category test (Debt collection and Mortgage have only 9 test tickets). Do not reuse Assignment 1 accuracy: it was measured on the older i7 / Ollama 0.34.4. Commit and push.

TASK 5 - Tuning runs. Run ONLY the tuning set (odd `row` values) through the small candidate model(s) (llama3.2:3b and llama3.2:1b, switch off, one at a time) and save the per-ticket outputs under analysis/a2/tuning/. Do NOT run or look at any small model's test-set (even-row) results. Commit and push.

STOP AND ASK. Show me: per-category small-model accuracy on the tuning set (Debt collection has only 5 tuning tickets, so say how weak that is); how ticket length relates to small-model errors; and the escalation options (category-based, length-based, agreement of two small calls, self-reported HIGH/LOW confidence), with their expected cost. Wait for my choice of approach and exactly two settings. Do not write the rule document or predictions in this session.
```

---

## Prompt 4 — Escalation rule and predictions (the commit gate)

**Machine:** any. Do this one together with your team. **Done when:** both files are committed and pushed, with no further benchmark run before this.

```text
You are continuing ICT3113 Assignment 2 for Team 8. This session does ONLY the tasks below. IMPORTANT: no benchmark of any kind may run before the commit in this session is pushed.

START: git checkout assignment-2 && git pull. Read CLAUDE.md, AGENTS.md (follow exactly), docs/PROJECT_CONTEXT.md Section 26, docs/task.md, docs/a2_accuracy_limits.md and the tuning outputs in analysis/a2/tuning/. Commits authored by me, no Co-Authored-By. Never force-push.

The rule and the predictions are the team's responsibility. I will tell you the chosen approach and the two settings; you write them up, you do not choose them.

TASK 6a - Write docs/a2_escalation_rule.md so another team could implement it from the text alone: the decision signal, both settings with their exact thresholds/categories, the small and large model (and a fallback pair so the file never needs editing), what happens on a parse error, and why this rule. Fill the thresholds into the pluggable rule config. This is configuration only: do not change service code after the code freeze, and say so if the rule cannot be expressed without a code change.

TASK 6b - STOP AND ASK me for the predictions, then write them specifically (numbers and named categories) into predictions/a2_prediction_record.md: (1) which configuration will be the fastest that satisfies both limits, with reasons; (2) for the cascade at each setting, the expected escalation fraction, accuracy and median latency; (3) which categories will lose the most accuracy when the small model's answer is accepted. Leave predictions/prediction_record.md (Assignment 1) untouched.

Then commit BOTH files together, push, and show me the pushed commit on GitHub. From now on, never edit docs/a2_escalation_rule.md or predictions/a2_prediction_record.md. Wrong predictions go in the final comparison, not in an edit.
```

---

## Prompt 5 — Accuracy test and speed set-up

**Machine:** i9 only. **Done when:** all test-set accuracy JSONs committed; S, the rate and the run length committed.

```text
You are continuing ICT3113 Assignment 2 for Team 8 on the i9. This session does ONLY the tasks below, then stops.

START: git checkout assignment-2 && git pull. Read CLAUDE.md, AGENTS.md (follow exactly), docs/PROJECT_CONTEXT.md Section 26, docs/task.md. Confirm docs/a2_escalation_rule.md and predictions/a2_prediction_record.md are already committed and pushed; if not, stop. NEVER edit those two files, even if a result looks wrong. Do not change service code (code freeze); change configuration only. Commits authored by me, no Co-Authored-By. Never force-push. Never invent a number.

TASK 7 - Accuracy test (test set only = even `row` values; once per configuration; through POST /tickets). Switch OFF: llama3.2:3b, then llama3.2:1b. Switch ON: the cascade at setting A, then setting B. Before each cascade run confirm GET /health reports cascade on with the intended models and setting, `ollama ps` lists both models, and the first log lines show cascade_mode=on with some escalated=true. Recreate the container for every configuration (see the switch table in docs/task.md). Save each analysis/a2/accuracy/<config>.json. Report overall and per-category accuracy WITH counts against the limits, confusion matrices, and for the cascade the escalated count and escalated vs non-escalated accuracy. State which configurations pass BOTH limits. If a result contradicts a prediction or a configuration fails, say so plainly; do not adjust the limits, code or prediction record. Commit and push.

TASK 8 - Speed set-up. Restart Ollama and do the normal warm-up, then send the 3 timing tickets from analysis/a2/speed_test_rows.csv one at a time to qwen2.5:7b (switch off) and take the middle time as S (seconds). Arrival rate = one ticket every 2xS seconds. Run length = S minutes (minimum 5). The same rate, run length and ordered workload apply to every configuration. Compare the rate with the client's peak in analysis/workload_model.json and say whether it is above or below. Record S, the three timings, the three row numbers, the rate and the run length in docs/test_environment.md. Commit and push.

Do not start any JMeter run in this session.
```

---

## Prompt 6 — Speed runs and speed analysis

**Machine:** i9 + the separate JMeter machine. **Done when:** every `.jtl`, log segment and speed JSON is committed.

```text
You are continuing ICT3113 Assignment 2 for Team 8. The service and Ollama run on the i9; JMeter runs on the SEPARATE machine. This session does ONLY the tasks below, then stops.

START: git checkout assignment-2 && git pull (on both machines). Read CLAUDE.md, AGENTS.md (follow exactly), docs/PROJECT_CONTEXT.md Section 26, docs/task.md, and the speed set-up in docs/test_environment.md. Confirm the rule and prediction files are committed and pushed and must not be edited. Do not change service code. Commits authored by me, no Co-Authored-By. Never force-push. Never invent a number. Do not run anything else on the i9 during a run.

TASK 9 - Speed runs. Copy the existing JMeter plan to a new Assignment 2 plan under jmeter/test_plans/; do not edit the Assignment 1 plan. It must be open-loop (Open Model Thread Group or PreciseThroughputTimer), use the committed rate, run length and ordered workload, set the HTTP response timeout to max(10xS seconds, 5 minutes), and end with a pause at least one minute longer than the timeout (for S = 6: rate(5/min) random_arrivals(6 min) pause(6 min) with a 5-minute timeout).

Do THREE runs of each: qwen2.5:7b alone, every single model that passed the accuracy limits, and the cascade at setting A and at setting B (switch on only for the cascade). For each run:
1. Restart the Ollama container and check it is up (GET /health or `ollama ps`).
2. Check versions, model digests and Ollama settings are unchanged since set-up.
3. Send the 3 fixed warm-up tickets one at a time and discard their timings. For the cascade also make sure the large model is loaded (warm-up tickets the rule will escalate, or one sent directly to it) and confirm BOTH models in `ollama ps` before starting.
4. Note GET /stats total.
5. Run JMeter on the other machine at the rate and run length.
6. Note GET /stats again; the increase is the number of requests completed and stored.
7. Save the raw file as jmeter/results/a2_<config>_run<n>.jtl and keep the service-log segment for the run (record the line numbers or timestamps; do NOT delete or truncate logs/requests.jsonl).
Commit and push the raw outputs after each configuration.

TASK 10 - Speed analysis. For every speed-tested configuration report per run: requests sent, completed, errored and UNFINISHED (never throw unfinished requests away); p50 per run with mean and spread across runs; p95 pooled over the three runs (state the sample count); throughput and error rate; and for the cascade the escalation fraction from the service logs (explain any large gap from the accuracy-test figure). No p99. Do not reuse Assignment 1 speed figures. Save analysis/a2/speed/*.json and check every number reconciles with its .jtl or log. Commit and push.
```

---

## Prompt 7 — Results, recommendation and deck

**Machine:** any. **Done when:** results doc, recommendation and deck draft are committed and you have reviewed them.

```text
You are continuing ICT3113 Assignment 2 for Team 8. This session does ONLY the tasks below.

START: git checkout assignment-2 && git pull. Read CLAUDE.md, AGENTS.md (follow exactly), docs/PROJECT_CONTEXT.md Section 26, docs/task.md, docs/a2_accuracy_limits.md, docs/a2_escalation_rule.md, predictions/a2_prediction_record.md, analysis/a2/ and jmeter/results/a2_*. NEVER edit the rule or the prediction record. Commits authored by me, no Co-Authored-By. Never force-push. Every figure must reconcile with a raw file; never invent a number.

TASK 11 - Results and recommendation (STOP AND ASK before finalising). Write docs/a2_results.md and the recommendation: the single configuration that passes BOTH limits on the test set and is the fastest of those that do, by our own measurements at the chosen rate; how much faster it is than qwen2.5:7b alone; how much accuracy it gives up overall and per category; predictions vs outcomes and why they differed; and, plainly, if the cascade did not beat the best qualifying single model, or if only the top model qualified (then say what was attempted and what it cost, citing the measured escalation fraction and latencies). List the limitations: one machine, one arrival rate, seen tickets, small samples (test categories of 9-15 tickets; pooled p95 from about 90 requests), the JMeter machine's hardware, and any change from Assignment 1. Update docs/prd.md, docs/architecture.md, docs/test_environment.md and docs/task.md (tick completed items, add the Assignment 2 verification commands). Show me the draft recommendation and wait for my approval.

TASK 12 - Deck. Draft Group08_A2.pptx (at most 8 slides) following the slide table in docs/PROJECT_CONTEXT.md Section 26: cover; cascade design; test environment and method; accuracy results; speed results; trade-off chart (accuracy vs latency, one point per configuration and setting, the overall limit as a line); predictions, recommendation and defence; limitations, references, model licences and AI declaration. Every figure on slides 4-7 must trace to a .jtl, log or JSON in the repo. The AI declaration must state what the tools produced and what the team did. I will review and submit it to xSiTe by 2359 on Friday 27 November.
```
