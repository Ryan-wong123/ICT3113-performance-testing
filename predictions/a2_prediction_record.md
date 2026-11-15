# Assignment 2 Prediction Record — Frozen Before Testing

**Frozen:** 15 November 2026, before the first Assignment 2 accuracy or speed benchmark. This file must never be edited after its first commit. Differences between these predictions and the measurements belong in `docs/a2_results.md` and the final deck.

## Evidence and method used

The predictions use only evidence that already existed before Assignment 2 testing:

- Assignment 1 predictions for the 90 odd-row tuning tickets;
- Assignment 1 tuning-subset warm medians: approximately 3.38 s for `llama3.2:1b`, 6.69 s for `llama3.2:3b`, and 17.29 s for `qwen2.5:7b`;
- the tuning-only category-rule simulations documented in `docs/a2_escalation_rule.md`;
- the Machine A memory check showing both cascade models resident together.

The Assignment 1 latency anchors came from the older i7/Ollama 0.34.4 environment, whereas Assignment 2 uses the i9/Ollama 0.35.1 environment. The numerical latency predictions are therefore deliberately falsifiable estimates, not claims that the old timing will repeat.

## Predicted fastest qualifying configuration

**Prediction:** unchanged `qwen2.5:7b` alone will be the fastest configuration that satisfies both the overall and every per-category accuracy limit.

`llama3.2:1b` and `llama3.2:3b` are expected to be faster but to fail the accuracy limits. Both cascades are expected to retain Qwen-like accuracy, but their high predicted escalation fractions mean they pay the small-model latency on almost every ticket and then usually pay the Qwen latency as well.

## Exact cascade predictions

| Configuration | Predicted escalation | Predicted test accuracy | Predicted warm median latency | Basis |
| --- | ---: | ---: | ---: | --- |
| Setting A | 90% | 78% | 19.0 s | Tuning simulation 81/90 escalated and 70/90 correct; latency estimate `3.38 + 0.90 × 17.29 = 18.94 s`. |
| Setting B | 81% | 76% | 17.4 s | Tuning simulation 73/90 escalated and 68/90 correct; latency estimate `3.38 + (73/90) × 17.29 = 17.40 s`. |

The latency approximation ignores queueing and assumes the small and large calls resemble their Assignment 1 warm medians. The formal speed runs, not these estimates, decide the recommendation.

## Predicted category losses

When a small-model answer is accepted, the largest accuracy losses relative to Qwen are predicted for:

1. `Credit reporting`; and
2. `Money transfer or service`.

In the tuning-only Setting B simulation, each lost one correct ticket relative to Qwen, while Mortgage gained one. The prediction is uncertain because the category samples and the number of accepted small-model predictions are small. Setting A is expected to have smaller category losses than Setting B because it does not accept `Bank account or service` predictions.

## Conditions for judging the prediction

- Accuracy and pass/fail use only the 85 even-row test tickets through the real `POST /tickets` endpoint.
- Speed uses the common Assignment 2 open-loop rate/workload and three runs per configuration from a separate JMeter machine.
- The fastest qualifying configuration must pass both the overall limit and every per-category limit.
- A prediction is not repaired after seeing a result; it is marked right, partly right or wrong with evidence.
