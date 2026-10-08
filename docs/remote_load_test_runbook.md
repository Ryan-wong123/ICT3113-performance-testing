# Step 5: Runbook for a genuinely separate-machine load test

**Status: completed on 4 October 2026.** This runbook produced the final `_remote.jtl` separate-machine measurements. **Machine A** runs the service and Ollama; **Machine B** runs JMeter only.

## On Machine A (this machine) — one-time setup

1. **Allow inbound port 8000 through Windows Firewall.** This is a security-setting change, so please run it yourself (as Administrator), not something I'll do automatically:
   ```powershell
   New-NetFirewallRule -DisplayName "Ticket Triage 8000" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
   ```
2. **Confirm Machine A's current address** (used by the completed run): `192.168.68.57`. Because DHCP can change it, re-check with `ipconfig` before any reproduction.
3. Keep `docker compose up -d` running for whichever candidate model is under test (I'll drive model switching from here, same as before — just tell me which model you're about to test on Machine B and I'll switch it).
4. From another device on the same LAN (or ask me to check), confirm reachability once firewall is set:
   ```powershell
   Invoke-WebRequest http://192.168.68.57:8000/health
   ```
   Should return `{"status":"ok",...}`. If it times out, the firewall rule above didn't take, or your router isolates devices from each other (some routers have "AP/client isolation" — check router settings if this fails).

## On Machine B (the second PC) — one-time setup

1. **Install Java** (JMeter needs it) — if not already present:
   ```powershell
   winget install --id Microsoft.OpenJDK.21 --accept-package-agreements --accept-source-agreements
   ```
2. **Install JMeter** (download the pinned binary from Apache's archive, verify SHA-512, no installer). `curl.exe` is used because `Invoke-WebRequest` aborted the TLS transport on the completed Machine B:
   ```powershell
   $zip = "$env:TEMP\apache-jmeter-5.6.3.zip"
   $checksum = "$env:TEMP\apache-jmeter-5.6.3.zip.sha512"
   curl.exe -L --retry 3 -o $zip "https://archive.apache.org/dist/jmeter/binaries/apache-jmeter-5.6.3.zip"
   curl.exe -L --retry 3 -o $checksum "https://archive.apache.org/dist/jmeter/binaries/apache-jmeter-5.6.3.zip.sha512"
   $expected = (Get-Content $checksum -Raw).Split()[0].ToLower()
   $actual = (Get-FileHash $zip -Algorithm SHA512).Hash.ToLower()
   if ($expected -ne $actual) { throw "Checksum mismatch - do not use this file" } else { Write-Host "Checksum OK" }
   Expand-Archive -Path $zip -DestinationPath "$env:LOCALAPPDATA\Programs\Apache"
   ```
3. **Get the repo** (gives you the `.jmx`, the narrative CSV, and everywhere results should go):
   ```powershell
   git clone https://github.com/Ryan-wong123/performance-testing-Ollama.git
   cd performance-testing-Ollama
   git checkout step-5-testing
   ```
4. **Verify you can reach Machine A:**
   ```powershell
   Invoke-WebRequest http://192.168.68.57:8000/health
   ```

## Running the tests (repeat this section per candidate model)

Coordination step: **tell me which model you're about to test**, and I'll run this on Machine A before you start each model's block:
```bash
docker compose down; rm -f runtime/tickets.db; OLLAMA_MODEL=<tag> docker compose up -d
```
I'll also send one warm-up request so the first timed sample isn't cold-start-polluted, and confirm `/health` reports the right model.

Once I confirm the model is loaded and warm, run this on Machine B (PowerShell), substituting `<model_label>` (e.g. `llama3.2_1b`), `<rate>`, `<duration>`, and `<run>`:

```powershell
cd performance-testing-Ollama
$jmeter = "$env:LOCALAPPDATA\Programs\Apache\apache-jmeter-5.6.3\bin\jmeter.bat"
$out = "jmeter\results\<model_label>_rate<rate>_run<run>_remote"
& $jmeter -n `
  -t jmeter\test_plans\ticket_triage_load_test.jmx `
  -l "$out.jtl" `
  -j "$out.jmeter.log" `
  "-JtargetThroughputPerMin=<rate>" `
  "-JdurationSec=<duration>" `
  "-Jthreads=50" `
  "-JnarrativesCsv=jmeter\test_plans\load_test_narratives.csv" `
  "-Jhost=192.168.68.57" `
  "-Jport=8000"
```

Use the exact same rates/durations as the original co-located matrix, so the two datasets are directly comparable — see `docs/load_test_results.md` for each model's rates:

| Model | Low test rate | High test rate | Duration |
| --- | --- | --- | --- |
| `llama3.2:1b` | 7/min | 22/min | 120s |
| `llama3.2:3b` | 3.5/min | 11/min | 120s |
| `qwen2.5:7b` | 1.5/min | 5/min | 90s |

Run each rate **3 times** (`run` = 1, 2, 3), i.e. 6 runs per model, 18 total — matching the original matrix. Note the `_remote` suffix in the output filename, so these don't overwrite the original co-located `.jtl` files; both datasets stay in the repo for comparison.

These low/high rates were chosen from latency measured on the older i7 environment. They must not be described as below/above the capacity of the faster final i9 Machine A; the separate 40/min and 60/min probes establish that machine's measured boundary.

### Stress test (one model, boundary probes)

Once the regular matrix is done for `llama3.2:1b`, run the 40/min stress probe from Machine B:
```powershell
& $jmeter -n `
  -t jmeter\test_plans\ticket_triage_load_test.jmx `
  -l "jmeter\results\llama3.2_1b_stress_remote.jtl" `
  -j "jmeter\results\llama3.2_1b_stress_remote.jmeter.log" `
  "-JtargetThroughputPerMin=40" `
  "-JdurationSec=180" `
  "-Jthreads=200" `
  "-JnarrativesCsv=jmeter\test_plans\load_test_narratives.csv" `
  "-Jhost=192.168.68.57" `
  "-Jport=8000"
```

On the completed environment, 40/min remained sustainable, so the test was extended without overwriting it:

```powershell
& $jmeter -n `
  -t jmeter\test_plans\ticket_triage_load_test.jmx `
  -l "jmeter\results\llama3.2_1b_stress60_remote.jtl" `
  -j "jmeter\results\llama3.2_1b_stress60_remote.jmeter.log" `
  "-JtargetThroughputPerMin=60" `
  "-JdurationSec=180" `
  "-Jthreads=200" `
  "-JnarrativesCsv=jmeter\test_plans\load_test_narratives.csv" `
  "-Jhost=192.168.68.57" `
  "-Jport=8000"
```

The initial 60/min probe established an overloaded side of the boundary. Two additional repeats at each rate were then retained as `llama3.2_1b_stress40_run2_remote.jtl`, `...run3...`, `llama3.2_1b_stress60_run2_remote.jtl`, and `...run3...`. The repetitions showed that 40/min is consistently stable while 60/min is variable and not repeatably sustainable; see `docs/load_test_results.md` for the per-run and across-run analysis.

## Bringing results back

Easiest: push directly from Machine B, since it's the same GitHub repo:
```powershell
git add jmeter/results/*_remote.jtl
git commit -m "Add separate-machine load/stress test results"
git push origin step-5-testing
```
The completed results were returned as an archive and imported without overwriting the older files. The old/new difference must **not** be described as a direct measurement of co-location bias because Machine A's CPU and Ollama version also changed; see `docs/test_environment.md`.

If you'd rather not push from Machine B, copy the `*_remote.jtl` and `*_remote.jmeter.log` files back to this machine any way you like (shared folder, USB, etc.) and drop them in `jmeter/results/` here instead — tell me when they're in place and I'll take it from there.
