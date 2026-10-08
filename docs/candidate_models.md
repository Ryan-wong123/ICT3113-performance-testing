# Step 4: Candidate Models

## Selection

Three candidate models, spanning two parameter-size classes, were selected as runnable CPU-only on the team's original development hardware (Intel Core i7-9750H, 6 cores / 12 threads, 15.9 GB RAM — see `predictions/prediction_record.md`). Step 5 subsequently used that Acer machine for JMeter and a separate i9-14900HX Machine A for the service/Ollama load tests; the final environment is recorded in `docs/test_environment.md`.

| Model | Ollama tag | Size class | Manifest digest | Model weights size | Licence |
| --- | --- | --- | --- | --- | --- |
| Llama 3.2 1B | `llama3.2:1b` | Small (~1B params) | `sha256:baf6a787fdffd633537aa2eb51cfd54cb93ff08e28040095462bb63daf552878` | 1,321,082,688 bytes (~1.23 GiB) | Llama 3.2 Community License + Acceptable Use Policy |
| Llama 3.2 3B | `llama3.2:3b` | Small (~3B params) | `sha256:a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72` | 2,019,377,376 bytes (~1.88 GiB) | Llama 3.2 Community License + Acceptable Use Policy |
| Qwen2.5 7B | `qwen2.5:7b` | Large (~7B params) | `sha256:845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e` | 4,683,073,952 bytes (~4.36 GiB) | Apache License 2.0 |

## How the digests and licences were obtained

Every digest above is the **manifest digest**: `sha256` of the exact bytes returned by the Ollama registry's manifest endpoint for that tag (`GET https://registry.ollama.ai/v2/library/<name>/manifests/<tag>`, `Accept: application/vnd.docker.distribution.manifest.v2+json`). This is the same digest Ollama itself computes — verified directly: the `llama3.2:3b` digest above was cross-checked against `ollama list`'s local ID (`a80c4f17acd5`) on this team's machine after Step 2, and the first 12 hex characters matched exactly.

Licence text for each family was fetched from the actual licence blobs referenced in each manifest (not assumed from memory):
- `llama3.2` (both 1b and 3b — same family licence): the manifest's licence layer blobs resolve to Meta's **"LLAMA 3.2 COMMUNITY LICENSE AGREEMENT"** plus a separate **"Llama 3.2 Acceptable Use Policy"** document — a custom, non-OSI licence with usage restrictions (e.g. a separate licence is required from Meta if the licensee has more than 700 million monthly active users), not a fully permissive open-source licence.
- `qwen2.5:7b`: the manifest's licence layer blob resolves to the standard **Apache License, Version 2.0** — permissive.

These were not pulled (downloaded) to this machine to obtain this information — only the small manifest and licence-text blobs were fetched, per the team's decision to defer the multi-gigabyte model downloads to Step 5.

## Justification for the candidate set

- **Two size classes, one family held constant to isolate the size variable.** `llama3.2:1b` and `llama3.2:3b` are the same model family and licence at two parameter counts, so any accuracy/latency difference between them is attributable to model size rather than architecture or training data. `qwen2.5:7b` is a different family and roughly 2–4× the parameter count of `llama3.2:3b`, and Apache-2.0 licensed rather than Meta's custom licence — this is deliberate: it tests whether an architecturally different, larger, more permissively-licensed model changes the accuracy/latency trade-off, not just whether "bigger is better" within one family.
- **The trade-off is expected to be visible, not avoided.** Per the brief: "Smaller models are faster on CPU and wrong more often; larger models are more accurate, slower, and sustain less throughput." The ~3.6× weights-size gap between `llama3.2:1b` (1.23 GiB) and `qwen2.5:7b` (4.36 GiB) is expected to translate into a comparable latency gap on CPU-only inference (see `predictions/prediction_record.md` for the specific numbers this predicts, made before any of these three models is benchmarked on the golden set).
- **All three are practical for this team's hardware.** `llama3.2:3b` was already run successfully, CPU-only, on this exact machine in Step 2 (verified: `ollama ps` reported `100% CPU`, warm single-request latency ≈2.8s — see below). `llama3.2:1b`'s smaller footprint should comfortably fit within the 15.9 GB RAM available even for CPU-only inference; `qwen2.5:7b`'s ~4.36 GiB of weights is the upper bound this team is prepared to run without a GPU, chosen deliberately to be large enough to show the trade-off without being infeasible on this hardware.
- **Only 3, not 4–5, candidates.** The team decided 3 is sufficient to demonstrate the required trade-off (2 size classes, both directions of the family/architecture comparison) while keeping Step 5's benchmarking matrix (3 models × JMeter load/stress runs × golden-set accuracy runs, 3 repeats each) tractable on a single CPU-only development machine.

## Step 5 verification

All three models were pulled and run in Step 5. Each local model ID matched the first 12 hexadecimal characters of the frozen manifest digest above, and `ollama ps` reported `100% CPU` for every candidate. The final load generator and system under test ran on separate machines; see `docs/test_environment.md` for hardware, software, network path, and limitations.
