# Step 5: Test Environment

## Final separate-machine load-test environment

The final load and stress results were collected on 4 October 2026 with the system under test and load generator on physically separate Windows machines.

| Role | Hardware | OS | Software |
| --- | --- | --- | --- |
| **Machine A — Ticket Triage Service** | ASUS TUF Gaming F16 FX607JIR; Intel Core i9-14900HX, 24 cores / 32 logical processors; 16,774,344,704 bytes RAM (~15.62 GiB) | Windows 11 Pro 10.0.26200, build 26200 | Docker Desktop 4.79.0; Docker client/engine 29.5.3; Python 3.12, FastAPI and uvicorn inside the container |
| **Machine A — Ollama backend** | Same physical machine; CPU-only confirmed for every candidate by `ollama ps` reporting `100% CPU` | Same | Native Ollama 0.35.1; reached from the container through `host.docker.internal:11434` |
| **Machine B — JMeter generator** | Acer Nitro AN515-54; Intel Core i7-9750H @ 2.60GHz, 6 cores / 12 logical processors; 15.85 GiB RAM | Windows 11 Home 10.0.22631, build 22631 | Apache JMeter 5.6.3; Microsoft OpenJDK 21.0.12.101 |

Machine B ran JMeter only. It did not run Docker, Ollama, the service, or a candidate model, so load generation did not steal CPU or RAM from Machine A.

## Network

- Machine A service address: `192.168.68.57:8000`.
- Machine B source address shown during the connectivity check: `10.59.54.128`.
- `Test-NetConnection 192.168.68.57 -Port 8000` returned `TcpTestSucceeded: True` before testing.
- `GET /health` from Machine B returned `status=ok`, the intended model tag, and `classification_mode=synchronous_sequential`.
- Windows Firewall on Machine A explicitly allowed inbound TCP 8000 on the private profile.

The different private subnets show that the path was routed rather than loopback. Exact switch/router/VPN topology and round-trip time were not captured, so network latency cannot be separated from service latency. At normal rates, however, the sub-second-to-low-second model-dependent spread dominates any ordinary LAN routing delay.

## Candidate identity and CPU-only verification

Each locally pulled model ID matched the first 12 hexadecimal characters of the manifest digest frozen in `docs/candidate_models.md`:

| Candidate | Local ID | Frozen manifest digest prefix | Processor |
| --- | --- | --- | --- |
| `llama3.2:1b` | `baf6a787fdff` | `baf6a787fdff` | `100% CPU` |
| `llama3.2:3b` | `a80c4f17acd5` | `a80c4f17acd5` | `100% CPU` |
| `qwen2.5:7b` | `845dbda0ea48` | `845dbda0ea48` | `100% CPU` |

Before the first timed block for each model, one untimed request loaded the model into memory. The container was then recreated with an empty SQLite database while the Ollama model remained warm. `/health` and `/stats` confirmed the correct tag and zero stored tickets before timed traffic.

## JMeter configuration

- JMeter 5.6.3, non-GUI mode.
- Core `PreciseThroughputTimer`; no third-party pacing plugin.
- Open-loop Poisson arrivals, never closed-loop.
- 50 threads for the regular matrix; 200 for stress.
- HTTP connect timeout: 5,000ms.
- HTTP response timeout: 300,000ms.
- Narratives: `jmeter/test_plans/load_test_narratives.csv`, the 825 Team 8 rows outside the golden set.
- Three repeats per regular model/rate configuration and three repeats at each reported stress rate.
- Raw results: `jmeter/results/*_remote.jtl`.

## Older co-located environment

The repository also retains the earlier non-remote JTL files, collected with JMeter, the service, and Ollama co-located on what is now Machine B: the Acer Nitro AN515-54 with its i7-9750H and 15.85 GiB RAM, then using Ollama 0.34.4. Those files validate the test pipeline but do not satisfy the brief's separate-machine rule and are not the final load evidence.

The old and new datasets are not a controlled A/B test of co-location. In addition to moving JMeter away, Machine A changed from an i7-9750H to an i9-14900HX and Ollama changed from 0.34.4 to 0.35.1. The much lower new latency cannot be attributed to any one of those changes.

## Accuracy-test environment boundary

The frozen accuracy JSON files were produced before this remote load rerun on the older environment. Accuracy traffic still used the real `POST /tickets` endpoint and is unaffected by the separate-machine requirement. Candidate tags/digests and service code are unchanged, so those files remain the recorded accuracy evidence. Nevertheless, the Ollama runtime and host CPU differ from the final load environment, and the service does not pin temperature or seed; exact accuracy percentages are therefore measurements of that recorded run, not guaranteed reproduction values on Machine A.

## Limitations

- **Short accelerated windows:** the regular matrix used 90–120-second windows and stress used 180-second windows. This keeps the exercise practical but produces small samples at low rates, especially Qwen's nine pooled samples at 1.5/min.
- **Realistic rate not directly replayed:** 7.278311 tickets/hour would require a multi-hour run for meaningful percentiles. Every lower matrix rate is intentionally much higher.
- **Laptop system under test:** power and thermal behaviour may differ from a server, although the i9-14900HX sustained all normal runs without observed collapse.
- **Windows and Docker Desktop:** the service runs through Docker Desktop rather than native Linux.
- **Single instance:** one service container and one Ollama instance, with no load balancer or horizontal scaling, matching the Assignment 1 baseline scope.
- **Network topology not characterised:** the routed path worked reliably at normal load, but RTT and intermediate equipment were not recorded.

These limits are disclosed rather than used to adjust requirements or discard unfavourable results.

## Scaling to the client's deployment

The measured capacity values apply to this exact single-instance, CPU-only i9-14900HX configuration. They must not be scaled linearly by core count: Ollama inference performance also depends on CPU architecture, memory bandwidth, model quantisation, runtime version, operating-system/container overhead, and sustained thermal behaviour. A target commodity CPU server should therefore be qualified by repeating this repository's playbook on that server rather than multiplying the laptop result by a nominal hardware ratio.

For planning, the tested machine has substantial performance headroom over the modelled peak of 7.278311 tickets/hour: every candidate sustained at least 120 successful tickets/hour in the regular matrix. That comparison supports capacity feasibility for one similar host, not a universal server-sizing promise. Additional hardware can improve capacity but cannot correct the measured accuracy failures; accuracy must be addressed separately when making the Step 6 recommendation.

---

# Assignment 2 Test Environment

Status: **memory and accuracy complete; speed parameters fixed on 15 November 2026.** Speed runs have not started.

Assignment 2 retains the Assignment 1 machines and hardware. Machine A runs the service and native CPU-only Ollama; Machine B will run JMeter separately during the speed tests.

| Item | Assignment 2 value |
| --- | --- |
| Machine A | ASUS TUF Gaming F16 FX607JIR; Intel Core i9-14900HX; 24 cores / 32 logical processors; approximately 15.62 GiB physical RAM |
| Machine B | Acer Nitro AN515-54; Intel Core i7-9750H; 6 cores / 12 logical processors; 15.85 GiB RAM; used only for JMeter |
| Docker | Engine 29.5.3; Compose v5.1.4 |
| Docker allocation | 32 logical CPUs; 8,121,454,592 bytes, approximately 7.56 GiB |
| Ollama | Native Windows Ollama 0.35.1 on Machine A |
| Models | `llama3.2:1b` ID `baf6a787fdff`; `llama3.2:3b` ID `a80c4f17acd5`; `qwen2.5:7b` ID `845dbda0ea48`; all match the frozen digest prefixes |
| Inference settings checked | `num_gpu: 0`; runtime context 4096; `ollama ps` reported `100% CPU` |
| Assignment 2 branch at memory check | `assignment-2`, commit `6be6f8e` |

## Cascade memory-feasibility check

Both possible small/large pairs were loaded on Machine A using CPU-only requests with a ten-minute keep-alive.

| Candidate pair | Result | Resident sizes | Processor | Context |
| --- | --- | --- | --- | --- |
| `llama3.2:3b` + `qwen2.5:7b` | PASS — both remained resident simultaneously | 2.6 GB + 5.1 GB | 100% CPU for both | 4096 |
| `llama3.2:1b` + `qwen2.5:7b` | PASS — both remained resident simultaneously | 1.5 GB + 5.1 GB | 100% CPU for both | 4096 |

Therefore, both Assignment 1 small models are technically feasible cascade partners for `qwen2.5:7b`. This memory check does not select the final pair; selection will use tuning-set accuracy and expected escalation cost.

The prompts used here were only model-loading checks. They are not accuracy or benchmark evidence and did not use the golden test set.

Raw environment evidence:

- `analysis/a2/environment/machine_a.txt`
- `analysis/a2/environment/docker_environment.txt`
- `analysis/a2/environment/ollama_version.txt`
- `analysis/a2/environment/ollama_models.txt`
- `analysis/a2/environment/memory_qwen7b_llama1b.txt`
- `analysis/a2/environment/memory_qwen7b_llama3b.txt`

Ollama inference options were held constant for all measured configurations: the service explicitly sends `num_gpu: 0`; `num_ctx`, `num_thread` and server parallelism are not overridden and therefore use the same Ollama 0.35.1 defaults throughout. Runtime `ollama ps` showed context 4096 and 100% CPU. The absence of an explicit effective thread/parallel count is a test-environment limitation; those defaults must not be changed for the remaining speed runs.

Known mismatch to resolve: the Assignment 1 accuracy JSONs were produced on the i7 / Ollama 0.34.4 environment, while the final load results are from the i9 / Ollama 0.35.1 Machine A. The Assignment 2 brief permits reusing Assignment 1 single-model accuracy only if the digest, prompt, Ollama version and machine are unchanged, so the default is to re-run test-set accuracy on the final Machine A. The service does not currently pin `temperature` or `seed`; any change to inference options must be recorded and held constant across configurations.

## Assignment 2 speed parameters

After restarting native Ollama, Machine A ran the three committed warm-up rows through Qwen with the cascade off. `ollama ps` reported Qwen at 100% CPU, context 4096. The three typical timing tickets were then sent one at a time through `POST /tickets`:

| Row | Characters | Elapsed |
| ---: | ---: | ---: |
| 8685 | 779 | 2.404 s |
| 8242 | 780 | 2.979 s |
| 8345 | 778 | 2.666 s |

The middle value is **S = 2.666 seconds**. Therefore every configuration uses:

- one arrival every **5.332 seconds** (`2 × S`), equivalent to **11.253 tickets/minute**;
- a **5-minute** arrival window (the brief's minimum exceeds S minutes);
- a **300-second** HTTP response timeout (`max(10 × S, 300 s)`);
- a **360-second** trailing pause, one minute longer than the timeout.

The offered POST rate is 92.77 times the client's modelled peak submission rate (11.253 vs 0.121305/min). For context it is 77.31 times the workload model's combined peak submission-plus-search rate (0.145566/min). Raw timing evidence is `analysis/a2/timing/qwen_s.json`; rows and narratives are fixed in `analysis/a2/speed_test_rows.csv`.
