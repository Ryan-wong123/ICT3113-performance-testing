# Team 8 Golden-Set Labelling Protocol

## Status and purpose

This protocol governs independent human labelling of the 175 narratives that make up the Team 8 golden test set (final labels in `labelling/golden_test_set.csv`, drawn from `labelling/team8_rows_8000_8999.csv`). Its purpose is to create a reliable golden test set for Assignment 1 accuracy evaluation. The raw `source_label` is a sampling aid only and is not accuracy ground truth, and it is not shown to annotators.

Labelling is fully manual: two team members each label every ticket independently, following this protocol and without conferring. The frozen set must be committed before any candidate Ollama benchmark begins.

## Scope and process

- Two named annotators (Annotator A and Annotator B) each label all 175 tickets independently, without conferring or seeing the other annotator's sheet, recording results in `labelling/annotator_A.csv` and `labelling/annotator_B.csv`.
- Use only the narrative, this protocol, and the seven category names below. Do not view `source_label` while labelling.
- Assign exactly one category to every narrative. There is no `Other` or multi-label outcome.
- Use the exact category spelling shown in this document and the annotation template.
- Complete both independent sheets before any disagreement discussion occurs.
- After both sheets are complete, calculate Cohen's kappa between the two annotators and record it in `labelling/agreement_results.md` as inter-human agreement.
- Discuss and resolve every row where the two sheets disagree; record each resolution, with rationale, in `labelling/disagreement_resolutions.csv`. The final label for every ticket (agreed or resolved) is compiled into `labelling/golden_test_set.csv`.

## Category definitions

| Category | Use when the primary complaint concerns | Do not use when the primary complaint concerns |
| --- | --- | --- |
| Credit reporting | A credit report, credit score, credit inquiry, reporting agency, or inaccurate reporting of account information. | A collection action, loan servicing, or card/account problem where reporting is merely a consequence. |
| Debt collection | A collector's efforts or conduct in collecting an alleged debt, including contact, validation, threats, harassment, or collection records. | The underlying loan, mortgage, card, or bank-account product when no collection activity is the main issue. |
| Mortgage | A home-secured loan or its servicing, payment, escrow, modification, foreclosure, or home-loan account. | A non-home consumer loan or a general credit-report issue. |
| Credit card | A credit-card account, card transaction, credit limit, card interest or fee, card payment, or card issuer's service. | A debit/checking account, bank transfer, or non-card consumer loan. |
| Bank account or service | A deposit/checking/savings account or its bank service, including account access, ATM/debit-account use, deposits, withdrawals, overdrafts, or bank-account fees. | A credit-card account, money-transfer service, mortgage, or non-home consumer loan. |
| Consumer loan | A non-mortgage, non-credit-card credit product, such as an auto, personal, student, instalment, payday, or title loan. | A home loan, credit-card account, debt-collector conduct, or credit reporting issue. |
| Money transfer or service | Sending, receiving, or transferring money through a remittance, transfer, payment, money order, or comparable transfer service. | A problem whose main product is a bank account or credit card rather than the transfer itself. |

## Decision rules for difficult narratives

1. **Primary issue rule.** Choose the category for the product or activity most central to the customer's complaint and requested remedy.
2. **Multiple products.** If several products are mentioned, label the product directly involved in the disputed event. If still tied, use the earliest product that caused the stated harm and record the uncertainty for later resolution.
3. **Multiple issues in one product.** Use the product category once; do not create a label for every issue.
4. **Credit reporting versus another product.** Use `Credit reporting` when the stated error or requested correction is about a credit report, score, inquiry, or reporting. Otherwise use the underlying product category.
5. **Debt collection versus another product.** Use `Debt collection` when the complaint is about collection conduct. Use the underlying product category when the complaint is about the account itself without collection conduct being central.
6. **Bank account versus money transfer.** Use `Money transfer or service` when the disputed service is the transfer of funds. Use `Bank account or service` when the account, debit access, deposit, withdrawal, overdraft, or bank service is central.
7. **Insufficient information.** Do not leave a ticket unlabelled. Choose the single category best supported by the narrative, retaining a private note for later discussion if uncertain.
8. **No external evidence.** Do not research the company, infer missing facts, use source labels, or use model output. Classify only from the narrative.
9. **Money transfer versus credit card.** *(Added 2026-09-26, Rule revision 1.)* Use `Money transfer or service` when the disputed event is the transfer itself (a missing, delayed, misdirected, or failed transfer), even if the funds move to, from, or through a credit-card account. Use `Credit card` only when the disputed issue is the card account, transaction, limit, fee, or interest, and the transfer mechanism itself is not the complaint.
10. **Credit reporting versus debt collection.** *(Added 2026-09-26, Rule revision 2.)* Use `Credit reporting` when the complaint's central issue and requested remedy concern the accuracy of a credit report, score, or entry — including entries placed there by a debt collector. Use `Debt collection` when the central issue is the collector's conduct (contact, validation, threats, harassment), even if that conduct also produced a reporting consequence.
11. **Credit card versus bank account or service.** *(Added 2026-09-26, Rule revision 3.)* Use `Credit card` when the disputed charge, payment, limit, or fee is on a credit-card account, and a bank account is only the funding source for that payment. Use `Bank account or service` when the account itself — access, deposits, withdrawals, or overdraft — is the central issue.

## Annotation and resolution records

Each independent sheet contains only `row,human_label`. Annotators may retain private uncertainty notes until they submit their completed sheet, but must not share those notes during independent labelling.

After both sheets are complete, the team calculates Cohen's kappa, discusses only the disagreeing rows, and records every resolution in `disagreement_resolutions.csv` (columns: `row,annotator_a_label,annotator_b_label,final_label,rationale`). A disagreement that reveals an unclear rule requires a dated protocol revision below.

## Revision log

All 5 disagreements from the independent labelling round were reviewed. Two were resolved directly under the protocol as already written and required no change:

- **Row 8158** (Consumer loan vs Credit reporting) — resolved under existing Rule 4.
- **Row 8384** (Credit card vs Debt collection) — resolved under existing Rule 5.

Three revealed a gap — the protocol had no explicit rule for that category pair — and a new rule was added the same day to close it:

- **2026-09-26 — Rule revision 1 (added Rule 9).** Row 8590 (Money transfer or service vs Credit card) exposed a missing rule for transfers that move through a credit-card account. Added Rule 9 to resolve it: the transfer act itself governs, not the account it touches.
- **2026-09-26 — Rule revision 2 (added Rule 10).** Row 8699 (Credit reporting vs Debt collection) exposed a missing rule for reporting entries caused by a debt collector. Added Rule 10: use the requested remedy (reporting correction vs collector conduct) to decide.
- **2026-09-26 — Rule revision 3 (added Rule 11).** Row 8762 (Credit card vs Bank account or service) exposed a missing rule analogous to Rule 6, but for credit cards rather than money transfers. Added Rule 11: a bank account that is only the funding source for a card payment does not make the ticket a bank-account complaint.

Full rationale for each of the 5 resolutions is in `disagreement_resolutions.csv`; the per-category breakdown and confusion matrix are in `agreement_results.md`.