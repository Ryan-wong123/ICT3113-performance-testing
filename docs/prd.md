# Step 1 Golden Test Set PRD

## Objective

Create a frozen, reproducible golden test set of 150–200 Team 8 complaint tickets for later classification-accuracy measurement. The completed set contains 175 tickets.

## Scope and constraints

- Use only rows 8000–8999 from `ict3113_tickets.csv`.
- Treat `source_label` as noisy sampling metadata, never as the final label, and do not show it to annotators.
- Define the seven permitted categories in a written protocol before annotation.
- Two team members label every ticket independently, without conferring; preserve both sheets, the agreement statistic, and every disagreement resolution.
- Freeze and commit the final set before candidate model benchmarking.
- Do not send candidate or final golden-set narratives to candidate models before that freeze.

## Required evidence

| Evidence | Location |
| --- | --- |
| Full course dataset | `labelling/ict3113_tickets.csv` |
| Team scope extract | `labelling/team8_rows_8000_8999.csv` |
| Protocol | `labelling/labelling_protocol.md` |
| Independent annotator sheets | `labelling/annotator_A.csv`, `labelling/annotator_B.csv` |
| Agreement statistic | `labelling/agreement_results.md` |
| Reviewed disagreements | `labelling/disagreement_resolutions.csv` |
| Frozen final set | `labelling/golden_test_set.csv` |

## Method

Labelling is fully manual: two team members each independently label all 175 tickets, following the written protocol, without conferring and without seeing `source_label`.

## Acceptance criteria

- The final set has 150–200 unique rows, all in the Team 8 range (8000–8999).
- Each final label is one of the required seven categories.
- Both annotator sheets contain the same 175 rows.
- Cohen's kappa between the two annotators is calculated and reported as inter-human agreement.
- Each disagreement between the two annotators has a resolution with a rationale.
- Every row in `golden_test_set.csv` matches the two annotators' agreed label, or the recorded resolution where they disagreed.
