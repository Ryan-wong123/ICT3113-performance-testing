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

Every request handled by the service must be logged.

Useful fields:

```text
timestamp
request_id
endpoint
model
ticket_row_if_available
request_start
request_end
latency
http_status
predicted_category
error
```

Every number shown in the final presentation must reconcile with either service logs or raw JMeter `.jtl` files.

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
