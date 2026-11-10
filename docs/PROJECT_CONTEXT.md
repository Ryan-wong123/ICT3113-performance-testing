# ICT3113 Assignment 1 — Project Context

## 1. Project Objective

The team is acting as a performance-testing / engineering consultancy for a financial services client.

The client receives complaint tickets and currently has humans manually read and route them. The goal is to build and evaluate a local AI-based ticket triage system that automatically classifies each complaint into one of seven categories.

The central project question is:

> Given CPU-only hardware and no public model APIs, which local Ollama model should the client deploy, and what level of service quality can the team realistically promise?

This is **not primarily an AI model-development project**. The work is to:

1. build a simple baseline system
2. define measurable performance and accuracy requirements
3. create a manually-labelled golden test set
4. benchmark several CPU-only Ollama models
5. conduct load, accuracy, and stress tests
6. identify bottlenecks
7. compare actual results with predictions
8. make a final client recommendation.

## 2. Team 8 Dataset Scope

The course dataset is `ict3113_tickets.csv`.

Team 8 must use only **rows 8000 to 8999 inclusive** (1,000 tickets).

All labelling and all test traffic must come from these rows.

### CSV columns

- `row`
- `source_label`
- `narrative`

### Seven categories

1. Credit reporting
2. Debt collection
3. Mortgage
4. Credit card
5. Bank account or service
6. Consumer loan
7. Money transfer or service

### Important constraint

The existing `source_label` is **not trusted ground truth**. It is noisy and must not be used as the final benchmark truth. Build a separate manually-labelled golden test set.

## 3. Golden Test Set

The team must create a golden test set of **150–200 tickets** from Team 8's rows.

Recommended size: **175 tickets**.

A practical sampling approach is about **25 tickets per source-label category** to improve coverage, while still independently assigning final human labels from the narrative.

### Required process

1. **Write the labelling protocol before labelling.** Define each category and rules for ambiguous, multi-product, multi-issue, insufficient-information, or overlapping cases.
2. **At least two team members independently label every selected ticket.** Do not split the tickets between annotators.
3. **Calculate an inter-annotator agreement statistic.** Cohen's Kappa is suitable for two annotators.
4. **Resolve every disagreement.** Record the final label, reasoning, and any protocol revision caused by the disagreement.
5. **Freeze the golden set before benchmarking.** Commit it to GitHub before the first model benchmark run and do not change labels after seeing model outputs.

Suggested files:

```text
labelling/
  team8_rows_8000_8999.csv
  golden_test_set.csv
  labelling_protocol.md
  annotator_A.csv
  annotator_B.csv
  disagreement_resolutions.csv
  agreement_results.md
```

### Critical rule for Codex

**Do not run candidate Ollama models on the golden-set tickets before the human labelling process is complete, frozen, and committed.**

The frozen set was built by fully manual labelling: two team members independently labelled all 175 tickets, without conferring, per `labelling/labelling_protocol.md`.The freeze-before-benchmark rule remains unchanged.

## 4. System Under Test

The System Under Test consists of:

1. Ticket Triage Service
2. Ollama model backend
3. Ticket storage
4. Logging / instrumentation

The service must run in Docker.

### Required API endpoints

#### POST `/tickets`

Accept one ticket narrative, call Ollama synchronously, classify it into exactly one of the seven categories, store the ticket and result, then return the category.

#### GET `/search`

Return stored tickets matching a text query.

#### GET `/stats`

Return counts of stored tickets grouped by assigned category.

## 5. Baseline Constraints

Assignment 1 requires an intentionally straightforward baseline:

- synchronous classification
- sequential model calls
- no caching
- no request queue
- no batching
- no background workers
- no pre-optimisation

Do not optimise the service yet. Optimisation belongs to Assignment 2.

## 6. Ollama / Model Constraints

- No public model APIs.
- All inference must use local Ollama.
- CPU-only inference.
- No GPU benchmarking.
- Select **3–5 candidate models**.
- Span at least **two parameter-size classes**.
- Record each candidate's exact Ollama tag and digest.
- Also record parameter size, licence, and why it was selected.

The candidate set should expose a clear speed-versus-accuracy trade-off.

## 7. Workload Model

Quantitatively model a plausible financial-services complaint workload.

Estimate:

- ticket volume per relevant period;
- average arrival rate;
- peak arrival rate;
- non-peak arrival rate;
- search frequency;
- peak versus non-peak periods;
- ticket-length distribution.

Use public sources wherever possible. If a figure is estimated, label it clearly and explain how it was estimated.

Ticket-length distribution can be calculated directly from Team 8's 1,000 narratives. Useful statistics include mean, min, max, p50, p95, p99, word count, and character count.

## 8. Performance and Accuracy Requirements

The team must define measurable requirements for:

1. response time;
2. throughput;
3. classification accuracy.

Each requirement must be testable.

### Response-time requirement

Specify the percentile, threshold, and load condition.

Example structure only:

```text
Under a peak arrival rate of X requests/minute,
p95 POST /tickets latency must remain below Y seconds.
```

### Throughput requirement

Example structure:

```text
The service must sustain at least X ticket classifications/hour under peak expected load.
```

### Accuracy requirement

Include both:

- overall accuracy;
- per-category accuracy.

Actual values must be justified from the workload model, usability, capacity, and misrouting impact.

## 9. Prediction Record

Before benchmarking, commit a prediction record that is specific enough to be proven wrong.

Required predictions:

- expected bottleneck and why;
- expected accuracy for each candidate model;
- expected single-request latency for each candidate model on the team's hardware;
- categories expected to be hardest to classify and why.

Do not revise the prediction record after the first benchmark.

Suggested file:

```text
predictions/prediction_record.md
```

## 10. Instrumentation and Logging

Every request handled by the service must be logged. Every number shown in the final presentation must reconcile with either service logs or raw JMeter `.jtl` files.

The exact fields the implementation logs are an engineering decision, not part of this brief — see `docs/architecture.md` (Step 2 Baseline Service Architecture, `request_logging.py`) for the current field list.

## 11. Test Environment

Document the machines running:

- service;
- Ollama;
- load generator.

Record CPU, RAM, OS, software versions, network connection, and factors that may affect representativeness.

### Important constraint

The **JMeter load generator must run on a separate machine from the System Under Test**.

Do not use co-hosted JMeter results as final evidence.

## 12. Accuracy Testing

For every candidate model:

1. send every frozen golden-set ticket through `POST /tickets`;
2. capture the model's returned category;
3. compare it with the golden label.

Report:

- overall accuracy;
- per-category accuracy;
- confusion matrix.

Accuracy testing should go through the actual service endpoint, not bypass the service.

## 13. JMeter Load Testing

JMeter acts as the client's complaint intake.

It should read Team 8 narratives and send them through `POST /tickets` one at a time.

Do **not** bulk-import the CSV into the service.

### Open-loop requirement

Traffic must be open-loop at controlled arrival rates.

Use either:

- Open Model Thread Group; or
- Precise Throughput Timer.

Do not rely on closed-loop traffic to support throughput or latency claims.

### Required metrics

At every tested arrival rate report:

- p50 latency;
- p95 latency;
- p99 latency;
- achieved throughput;
- error rate.

### Three runs

Every reported configuration must be run **three times**. Report the mean and spread across runs.

Keep every raw `.jtl` file in the repository.

## 14. Stress Test

Design and execute at least one stress test for at least one candidate model.

A suitable objective is:

> Determine the maximum sustainable ticket arrival rate before latency grows without bound, throughput stops scaling, or errors begin increasing.

The stress-test procedure must be reproducible and documented in the test playbook.

## 15. Bottleneck Diagnosis

After load and stress tests, diagnose what limits the baseline.

Possible evidence may include:

- CPU utilisation
- Ollama inference time
- memory pressure
- request handling time
- storage
- network behaviour
- serialization or locking

Do not merely say a larger model is slower. Explain which component is limiting performance and support it with evidence.

## 16. Compare Predictions With Results

After testing, compare the frozen prediction record with actual measurements.

Use a structure such as:

| Prediction | Actual | Explanation |
|---|---|---|
| Model A accuracy = X | Actual = Y | Why different |
| Model A latency = X | Actual = Y | Why different |
| Category Z hardest | Actual category = Q | Why |

Being wrong is acceptable. Vague predictions are not.

## 17. Final Recommendation

The final recommendation must follow from:

- workload model
- stated requirements
- accuracy results
- latency results
- throughput results
- stress-test results
- bottleneck analysis

Do not automatically choose the fastest, largest, or most accurate model.

It is acceptable to conclude that **no candidate meets all requirements**, as long as that finding is supported by measurements.

## 18. Final Submission

Main submission: **PowerPoint, maximum 12 slides**.

### Slide structure

1. Cover Page — group number, names, IDs, project title, GitHub link
2. Service Architecture — triage service, Ollama, storage, load generator, endpoints, synchronous baseline
3. Workload Model — ticket volume, search rate, peak/non-peak, ticket lengths, citations
4. Performance and Accuracy Requirements — latency, throughput, accuracy, justifications
5. Candidate Models — 3–5 models, tags, digests, size classes, justification
6. Golden Test Set — protocol, revisions, agreement statistic, disagreement examples
7. Test Environment — hardware/software, separate JMeter machine, assumptions/limitations
8. Test Playbook — step-by-step accuracy, load, and stress procedures
9. Load and Stress Test Results — p50/p95/p99, throughput, error, stress limit, bottleneck
10. Accuracy Results — overall accuracy, per-category accuracy, confusion-matrix highlights
11. Predictions, Recommendation and Defence — predicted vs actual, final recommendation, unmet requirements
12. References and Acknowledgements — CFPB, Ollama, model licences, workload sources

## 19. Supporting Files

Submission/supporting material should include:

- golden test set
- prediction record
- labelling protocol
- protocol revisions
- independent annotator sheets
- agreement statistic

Repository should retain:

- service source code
- Docker files
- model pins/configuration
- service logs
- JMeter `.jtl` files
- test scripts
- golden set
- prediction record

## 20. Suggested Repository Structure

```text
performance-testing-1/
│
├── README.md
├── PROJECT_CONTEXT.md
├── docker-compose.yml
│
├── src/
│   ├── app/
│   ├── routes/
│   ├── storage/
│   ├── ollama/
│   └── logging/
│
├── data/
│   ├── ict3113_tickets.csv
│   ├── team8_rows_8000_8999.csv
│   └── golden_test_set.csv
│
├── labelling/
│   ├── labelling_protocol.md
│   ├── annotator_A.csv
│   ├── annotator_B.csv
│   ├── disagreement_resolutions.csv
│   └── agreement_results.md
│
├── predictions/
│   └── prediction_record.md
│
├── jmeter/
│   ├── test_plans/
│   └── results/
│
├── logs/
│
├── analysis/
│   ├── accuracy/
│   ├── confusion_matrix/
│   ├── latency/
│   └── throughput/
│
├── docs/
│   ├── workload_model.md
│   ├── requirements.md
│   └── test_playbook.md
│
└── slides/
```

## 22. Non-Negotiable Assignment Rules

1. Team 8 uses rows `8000–8999`.
2. Golden set must contain 150–200 tickets.
3. At least two annotators independently label every golden ticket, without conferring.
4. Golden set is frozen before first model benchmark.
5. Raw source labels are noisy and are not the final truth.
6. Use 3–5 local Ollama candidates.
7. Span at least two model size classes.
8. CPU-only inference.
9. No public model API.
10. Baseline remains synchronous and unoptimised.
11. JMeter runs on a separate machine.
12. Load traffic is open-loop.
13. Three runs per reported configuration.
14. Report p50, p95, p99, throughput, and error rate.
15. Accuracy is reported overall and per category.
16. Include confusion matrices.
17. Perform at least one stress test.
18. Diagnose the bottleneck.
19. Every reported number must reconcile with logs or `.jtl` files.
20. Final recommendation must follow from the team's own requirements and measurements.

## 23. Current Team Decisions

Decisions already made in the ChatGPT discussion:

- Team number: **8**
- Dataset scope: **rows 8000–8999**
- Recommended golden-set size: **175 tickets**
- Recommended balanced starting sample: approximately **25 tickets per source category**
- Golden set must be manually labelled independently
- Original `source_label` should ideally not be shown to annotators if it could bias them
- Build the baseline before optimisation
- Treat the project as a reproducible performance-engineering experiment, not an LLM-training project
- Golden set labelling is fully manual: two team members independently label every ticket, without conferring, and the reported kappa is inter-human agreement.

These decisions can still be changed by the team unless the assignment brief itself imposes the rule.

## 24. Overall Workflow

```text
Team 8 CSV (rows 8000–8999)
        │
        ├───────────────┬───────────────────┐
        │               │                   │
        ▼               ▼                   ▼
Golden-set work    Workload research    Baseline build
150–200 tickets         │                   │
        │               │                   │
2 independent labels    │                   │
        │               │                   │
Resolve disagreements   │                   │
        │               │                   │
Freeze golden set       │                   │
        │               ▼                   │
        │        Define requirements         │
        │               │                   │
        └───────────────┬┴───────────────────┘
                        ▼
               Select Ollama models
                        │
                        ▼
                Write predictions
                        │
                        ▼
                Commit before tests
                        │
            ┌───────────┴────────────┐
            │                        │
            ▼                        ▼
     Accuracy testing          JMeter load testing
            │                        │
            │                 3 runs/configuration
            │                        │
            ▼                        ▼
 Overall/per-category      p50/p95/p99/throughput/error
 accuracy + confusion               │
 matrices                           ▼
                               Stress test
                                     │
                                     ▼
                               Find limit
                                     │
                                     ▼
                           Diagnose bottleneck
                                     │
                  ┌──────────────────┘
                  ▼
         Compare against requirements
                  │
                  ▼
        Compare predictions to actual
                  │
                  ▼
        Recommend model to the client
```

## 25. Core Principle

Assignment 1 is not about making the baseline as fast as possible.

It is about producing a **carefully measured, reproducible baseline** that lets the team answer:

> On the client's constrained CPU-only infrastructure, which local model gives the most acceptable balance between classification quality and service performance, and what service level can the team defend with evidence?

That baseline becomes the foundation for Assignment 2 optimisation.

---

# Assignment 2 Brief

## 26. Assignment 2 — Performance Optimisation: Fast Triage Within an Accuracy Floor

Sections 1–25 above describe Assignment 1 and remain valid history; they are not rewritten.

### Question

Assignment 1 showed that Ollama inference accounts for almost all request latency and that no single candidate met every Assignment 1 requirement. The client now accepts lower accuracy within a defined limit, with speed as the primary concern. Can the Assignment 1 models be arranged so the system is faster without giving up more accuracy than the client accepts? Inference stays CPU-only, with no hosted model API, on the same machine, CPU and RAM as Assignment 1.

### Configurations tested

1. **Top model alone (required):** the most accurate Assignment 1 model (`qwen2.5:7b`, 138/175 = 78.86% on the full golden set), unchanged. Its accuracy sets the limit; its latency is the one to beat.
2. **Each other Assignment 1 model alone (required):** `llama3.2:3b` and `llama3.2:1b`. A smaller model may already pass; check, do not assume.
3. **One cascade at two settings (team design):** a smaller model classifies first; a rule accepts its answer or passes the ticket to a larger model, whose answer is final.
4. **Hard constraint:** both cascade models must be resident together on the Assignment 1 machine with no extra RAM or CPU (`ollama ps` lists both). If no pair fits, report that a cascade is not feasible, show the evidence, and recommend a single model.

Approximate cascade latency ignoring queueing: small-model latency + escalation fraction × large-model latency. A single mid-sized model is an acceptable recommendation, and so is concluding the cascade did not help. A cascade must still be built, accuracy-tested and speed-tested even if a single model is recommended.

### Fixed from Assignment 1

- Candidate models (same Ollama tags and digests); no new models.
- Classification prompt and the seven categories (same prompt for every model and configuration).
- Golden test set and labels (frozen in Assignment 1).
- Endpoints `POST /tickets`, `GET /search`, `GET /stats` and their behaviour.
- CPU-only Ollama on hardware the team controls.
- Test method: open-loop Apache JMeter, three runs per configuration, raw `.jtl` files and service logs retained in the repository.
- Test machine, including CPU count and the RAM given to Docker and Ollama. If machines must change, report and explain.

### May change

- The `POST /tickets` implementation (call one model, apply a rule, call a second model where required).
- The escalation rule and what it depends on (second prompt for a confidence word, second small model, ticket-length check); it may add a model call but the classification prompt is unchanged.
- The pairing of models in the cascade, provided both are Assignment 1 candidates.

### Not permitted

- Caching classification results for previously seen tickets.
- Changing Ollama inference settings (thread count, parallelism, context length) between configurations; record them once and hold them constant.
- Fine-tuning, additional classifiers, retrieval, or any component not part of the Assignment 1 system.

### Step 1 — Accuracy limits

- Split the golden set by row number: odd rows = tuning set, even rows = test set (about 90 tickets). Commit the split before anything else.
- Tune the escalation rule on the tuning set only. Every accuracy number reported uses the test set only.
- **Overall limit:** top model's test-set accuracy − 10 percentage points (not the full-golden-set figure).
- **Per-category limit:** for each of the seven categories, no configuration may score more than 15 points below the top model's accuracy on that category, on the test set. The Assignment 1 70%-per-category requirement does not apply.
- Show counts (right/wrong) beside every percentage; say when a category is too small for a fair per-category test.

### Step 2 — Cascade design

- Pick one approach for the decision signal, justify it, and hold it fixed. Suggested methods: category-based (reliable categories judged from the small model on the tuning set only), agreement (two small calls disagree → escalate), self-reported HIGH/LOW confidence (a separate call counts toward cascade time), ticket length (only if length predicts errors in the Assignment 1 data). Other rules are allowed.
- Document the rule so another team could implement it from the description.
- Test exactly two settings of the rule, chosen on the tuning set and reported on the test set.
- Implemented within `POST /tickets`: one ticket in, one category out, and the caller cannot tell which model answered. The service log records, per ticket, which model produced the final classification and whether escalation occurred.
- Memory check first: load both models, run a few tickets through each, confirm `ollama ps` lists both; if they do not both stay loaded, try a smaller pair.

### Step 3 — Predictions (commit before any testing; never revised)

- Which configuration is expected to be the fastest that satisfies the accuracy limits, with reasons.
- For the cascade at each setting: expected escalation fraction, accuracy and median latency.
- Which categories are expected to lose the most accuracy when the small model's answer is accepted.
- Marks reward specificity and the later analysis of where predictions were wrong, not correctness.

### Step 4 — Test and measure

**Accuracy test.** Every test-set ticket through `POST /tickets`, once per configuration. Report overall accuracy (count and percentage), per-category accuracy checked against the per-category limit, and a confusion matrix. For the cascade also report the number escalated and the accuracy of escalated and non-escalated tickets separately. Tuning-set results may be shown but only test-set results decide pass/fail. Single-model Assignment 1 prediction records may be reused (score only test-set rows, say so) only if digest, prompt, Ollama version and machine are unchanged.

**Speed test.** Run after the accuracy test: every configuration that passes both limits, plus the cascade at both settings, plus the top model. Single models that fail accuracy need no speed test. If the cascade fails the limits, still report its speed, marked as not passing accuracy.

- *Arrival rate from the top model's speed:* restart Ollama, warm up, send three different typical-length tickets one at a time to the top model, take the middle time S (seconds). Send one ticket every 2×S seconds. Do not send the same ticket three times (Ollama caches prompts).
- *Run length:* S minutes, minimum 5 (about 30 tickets).
- *Same rate and run length for every configuration;* write S, the rate, the run length, the three timings and the three ticket row numbers in the report.
- *Compare with the client's peak rate* from the Assignment 1 workload model; say whether the test rate is above (shows the system can handle the client's load) or below (compares configurations only) on the limitations slide.
- *Three runs per configuration.* Use one fixed ordered set of tickets from rows outside the golden set, including typical and long tickets; commit the row numbers.
- *Before the first run* record software versions, model digests and Ollama settings; check they are unchanged before each configuration.
- *Each run:* restart the Ollama container and check it is up; send three fixed warm-up tickets (timings discarded; same three every time); for the cascade warm up both models and confirm both in `ollama ps`; note `GET /stats` total; run JMeter (Open Model Thread Group or `PreciseThroughputTimer`) at the chosen rate and length; HTTP response timeout 10×S seconds and at least 5 minutes; trailing pause longer than the timeout by at least one minute (e.g. `rate(5/min) random_arrivals(6 min) pause(6 min)` for S = 6); note `GET /stats` again — the increase is the number of requests completed and stored.
- *Report per run:* requests sent, completed, errored, unfinished; p50 (mean and spread across runs); p95 pooled across the three runs (about 90 requests, state the number); achieved throughput and error rate; for the cascade the escalation fraction from service logs (explain any large gap from the accuracy-test figure). No p99. Do not reuse Assignment 1 speed figures.
- *Test environment:* describe the machines as in Assignment 1 (or refer to that description if unchanged). The load generator runs on a separate machine from the service.

### Step 5 — Recommendation

Recommend one configuration that satisfies both accuracy limits on the test set and is the fastest of those that do, by the team's own measurements at the chosen rate. State how much faster it is than the top model and how much accuracy it gives up overall and by category. If the cascade was not the fastest qualifying configuration, say so and explain with the measured escalation fraction and latencies. If nothing but the top model satisfies the limits, recommend it and describe what was attempted and what it cost.

### Deliverables

One PowerPoint of at most 8 slides, named `GroupNum_A2.pptx` (e.g. `Group08_A2.pptx`),with supporting files: the prediction record, the written escalation rule, and the list of speed-test row numbers. The prediction record and escalation rule must be committed before the first Assignment 2 benchmark run. Raw `.jtl` files and service logs for every reported run are retained in the repository.

| Slide | Content |
| --- | --- |
| 1. Cover | Group, names, IDs, repository link. Top model and its Assignment 1 accuracy. Overall and per-category limits. |
| 2. Cascade design | Diagram. Escalation rule in full. Settings tested. Why this rule. |
| 3. Test environment and method | Machines (or refer to Assignment 1). Arrival rate and why. Workload tickets. Warm-up and drain procedure. Any change from Assignment 1. |
| 4. Accuracy results | Overall and per-category accuracy for every configuration, with counts. Which pass the limits. Escalation fraction; accuracy of escalated vs non-escalated tickets. |
| 5. Speed results | p50 per run with spread, pooled p95, throughput and error rate for every speed-tested configuration. Escalation fraction under load. |
| 6. Trade-off | One chart: accuracy vs latency, one point per configuration and setting, overall limit drawn as a line. Short interpretation. |
| 7. Predictions, recommendation, defence | Predictions vs outcomes and why they differed. Recommended configuration, speed gain, accuracy cost. If the cascade lost, why. |
| 8. Limitations, references, AI declaration | What the results do not show (sample size, one machine, one arrival rate, seen tickets). References. Model licences. AI use. |

Every figure on slides 4–7 must be traceable to a log or `.jtl` file in the repository.

### Assessment (20%)

Design (Step 2) 6%: cascade inside the existing service, rule reproducible, two settings tested, memory check reported, logs show which model answered each ticket. Measurement (Steps 1, 3, 4) 7%: limits from the test set, predictions committed before testing, accuracy for every configuration, three-run open-loop speed tests for every qualifying configuration and the cascade, escalation fraction from logs, all figures reconcile with raw data. Recommendation (Step 5) 7%: fastest qualifying configuration from own measurements, trade-off shown, predictions compared with outcomes, clear statement if the cascade did not help, limitations stated.


### How Assignment 2 relates to the Assignment 1 baseline (team decision)

- The Assignment 1 baseline is preserved: branch `main` holds the Assignment 1 evidence; Assignment 2 is added on branch `assignment-2`.
- The cascade is added behind an off-by-default switch so that, with it off, the service behaves exactly as the Assignment 1 baseline. Assignment 1 requirements (R1–R3), predictions, accuracy JSONs and results are not edited.
- Assignment 2 limits, rule, predictions and results live in new `a2_*` files and `analysis/a2/`.
- Differences from Assignment 1 reporting: Assignment 2 reports p50 per run and pooled p95 and no p99 (runs of about 30 requests are too small); the Assignment 1 requirement of p99 and 70% per category is unchanged history.
