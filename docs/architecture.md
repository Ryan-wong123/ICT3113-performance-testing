# Step 1 Golden Test Set Architecture

## Overview

This branch has no running service. It is a file-based evidence package for constructing the Assignment 1 golden test set through fully manual labelling.

```text
labelling/ict3113_tickets.csv (full course dataset)
        |
        v
labelling/team8_rows_8000_8999.csv (Team 8 rows 8000-8999)
        |
        v
labelling/labelling_protocol.md (categories + decision rules, written first)
        |
        v
Two independent human annotators
        |-------------------------------> labelling/annotator_A.csv
        |-------------------------------> labelling/annotator_B.csv
        v
labelling/agreement_results.md (Cohen's kappa, inter-human)
        |
        v
labelling/disagreement_resolutions.csv (reviewed final labels + rationale)
        |
        v
labelling/golden_test_set.csv (row, narrative, final_label)
```

## Components

| Component | Responsibility |
| --- | --- |
| `labelling/ict3113_tickets.csv` | Supplied course dataset. |
| `labelling/team8_rows_8000_8999.csv` | Team 8's 1,000-row scope (rows 8000–8999). |
| `labelling/labelling_protocol.md` | Category definitions and decision rules for ambiguous narratives, written before labelling started. |
| `labelling/annotator_A.csv`, `labelling/annotator_B.csv` | Two independent human label sheets (`row,human_label`) over the same 175 tickets. |
| `labelling/agreement_results.md` | Observed agreement and Cohen's kappa between the two annotators. |
| `labelling/disagreement_resolutions.csv` | Human-reviewed final decisions and rationales for every row where the annotators disagreed. |
| `labelling/golden_test_set.csv` | Final `row,narrative,final_label` file: agreed label where the annotators matched, resolved label otherwise. |

## Data flow and integrity

`source_label` in `team8_rows_8000_8999.csv` is a sampling/audit aid only; annotators do not see it while labelling and it is never used as ground truth. Every row in `golden_test_set.csv` reconciles with either (a) an identical label from both annotator sheets, or (b) a recorded resolution in `disagreement_resolutions.csv`.

## Boundary

The Step 1 branch deliberately excludes the Docker service, Ollama integration, load testing, prediction, benchmark, and analysis artefacts. Those belong to subsequent assignment steps.
