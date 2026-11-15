<#
.SYNOPSIS
  Machine A: prepare, pause for JMeter on Machine B, then record ONE Assignment 2 speed run.

.DESCRIPTION
  Run from the repository root after .\scripts\a2_start_service.ps1 -Config <same config>.
  Before the run:
    1. checks /health matches the configuration;
    2. restarts native Windows Ollama (clears its prompt cache; no model loaded);
    3. records Ollama version, model IDs and OLLAMA_* settings, and stops if a model ID changed;
    4. sends the three fixed warm-up tickets one at a time (timings discarded);
       for the cascade, also loads the large model directly so both models are resident;
    5. checks `ollama ps` lists the expected model(s) at 100% CPU;
    6. records GET /stats total and the service-log line count.
  It then waits while you start JMeter on Machine B. When JMeter has exited, press Enter:
    7. records GET /stats again, the log line count and `ollama ps`;
    8. writes analysis/a2/speed/runs/<config>_run<n>.json and the run's log segment
       analysis/a2/speed/logs/<config>_run<n>.jsonl.

.EXAMPLE
  .\scripts\a2_speed_run.ps1 -Config cascade_a -Run 1
#>
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("qwen2.5_7b", "cascade_a", "cascade_b")]
    [string]$Config,
    [Parameter(Mandatory = $true)]
    [ValidateRange(1, 3)]
    [int]$Run,
    [string]$ServiceUrl = "http://localhost:8000",
    [string]$OllamaUrl = "http://localhost:11434",
    [string]$OllamaApp = "$env:LOCALAPPDATA\Programs\Ollama\ollama app.exe",
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

$tag = "${Config}_run$Run"
$runDir = "analysis/a2/speed/runs"
$logDir = "analysis/a2/speed/logs"
$envDir = "analysis/a2/speed/environment"
New-Item -ItemType Directory -Force -Path $runDir, $logDir, $envDir | Out-Null
$runFile = "$runDir/$tag.json"
if (Test-Path $runFile) { throw "$runFile already exists. Never overwrite a run; use the next run number or ask the team." }

# Frozen model IDs (docs/candidate_models.md, docs/test_environment.md).
$expectedIds = @{ "llama3.2:1b" = "baf6a787fdff"; "llama3.2:3b" = "a80c4f17acd5"; "qwen2.5:7b" = "845dbda0ea48" }
$isCascade = $Config -like "cascade_*"
$expectedResident = if ($isCascade) { @("llama3.2:1b", "qwen2.5:7b") } else { @("qwen2.5:7b") }
$requestLog = "logs/requests.jsonl"

function Get-Utc { (Get-Date).ToUniversalTime().ToString("o") }
function Write-Utf8NoBom([string]$path, [string]$text) {
    $full = Join-Path (Get-Location) $path
    [System.IO.File]::WriteAllText($full, $text, (New-Object System.Text.UTF8Encoding $false))
}
function Get-StatsTotal {
    $stats = Invoke-RestMethod -Uri "$ServiceUrl/stats" -TimeoutSec 30
    $total = 0
    foreach ($p in $stats.categories.PSObject.Properties) { $total += [int]$p.Value }
    return $total
}
function Get-LogLineCount {
    if (-not (Test-Path $requestLog)) { return 0 }
    return [System.IO.File]::ReadAllLines((Resolve-Path $requestLog)).Length
}
function Get-OllamaPs { (& ollama ps | Out-String) }
function Test-Resident([string]$psText) {
    foreach ($model in $expectedResident) {
        $line = ($psText -split "`n") | Where-Object { $_ -match ("^" + [regex]::Escape($model) + "\s") }
        if (-not $line) { return "missing $model" }
        if ($line -notmatch "100% CPU") { return "$model is not 100% CPU" }
    }
    return ""
}
function Send-Ticket([int]$row, [string]$narrative) {
    $body = @{ narrative = $narrative; ticket_row = $row } | ConvertTo-Json -Compress
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($body)
    $watch = [System.Diagnostics.Stopwatch]::StartNew()
    $result = Invoke-RestMethod -Method Post -Uri "$ServiceUrl/tickets" -Body $bytes `
        -ContentType "application/json; charset=utf-8" -TimeoutSec 600
    $watch.Stop()
    return @{ row = $row; seconds = [math]::Round($watch.Elapsed.TotalSeconds, 3); category = $result.category }
}

# 1. Configuration check.
$health = Invoke-RestMethod -Uri "$ServiceUrl/health" -TimeoutSec 10
$expectMode = if ($isCascade) { "on" } else { "off" }
if ($health.cascade_mode -ne $expectMode) { throw "Service cascade_mode=$($health.cascade_mode); run a2_start_service.ps1 -Config $Config first." }
if ($isCascade) {
    $letter = $Config.Substring($Config.Length - 1).ToUpper()
    if ($health.rule_setting -ne $letter) { throw "Service rule_setting=$($health.rule_setting), expected $letter." }
} elseif ($health.model -ne "qwen2.5:7b") { throw "Service model=$($health.model), expected qwen2.5:7b." }

# 2. Restart native Ollama.
Write-Host "Restarting Ollama ..."
Get-Process -Name "ollama app", "ollama" -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 3
if (-not (Test-Path $OllamaApp)) { throw "Ollama app not found at $OllamaApp; pass -OllamaApp <path>." }
Start-Process -FilePath $OllamaApp
$version = $null
for ($i = 0; $i -lt 90 -and $null -eq $version; $i++) {
    try { $version = (Invoke-RestMethod -Uri "$OllamaUrl/api/version" -TimeoutSec 2).version } catch { Start-Sleep -Seconds 1 }
}
if ($null -eq $version) { throw "Ollama did not come back within 90 s." }
$restartedAt = Get-Utc
$psAfterRestart = Get-OllamaPs

# 3. Environment snapshot and model-ID check.
$ollamaList = (& ollama list | Out-String)
$ollamaEnv = (Get-ChildItem Env: | Where-Object { $_.Name -like "OLLAMA_*" -and $_.Name -notin @("OLLAMA_MODEL", "OLLAMA_SMALL_MODEL", "OLLAMA_LARGE_MODEL", "OLLAMA_BASE_URL", "OLLAMA_TIMEOUT_SECONDS") } |
    ForEach-Object { "$($_.Name)=$($_.Value)" }) -join "`n"
$userEnv = ([Environment]::GetEnvironmentVariables("User").GetEnumerator() | Where-Object { $_.Key -like "OLLAMA_*" } |
    ForEach-Object { "$($_.Key)=$($_.Value)" }) -join "`n"
foreach ($model in $expectedIds.Keys) {
    $line = ($ollamaList -split "`n") | Where-Object { $_ -match ("^" + [regex]::Escape($model) + "\s") }
    if (-not $line -or $line -notmatch $expectedIds[$model]) { throw "Model ID for $model changed or missing. Stop and report it." }
}
$snapshot = @(
    "captured_utc: $(Get-Utc)", "config: $Config", "run: $Run", "ollama_version: $version",
    "--- ollama list", $ollamaList, "--- OLLAMA_* (process)", $ollamaEnv, "--- OLLAMA_* (user)", $userEnv,
    "--- ollama ps after restart", $psAfterRestart, "--- docker", (& docker version --format "{{.Server.Version}}" | Out-String),
    "--- git", (& git rev-parse HEAD | Out-String)
)
Write-Utf8NoBom "$envDir/$tag.txt" ($snapshot -join "`n")

# 4. Warm-up (timings discarded).
$rows = Import-Csv -Encoding UTF8 "analysis/a2/speed_test_rows.csv"
$warmups = @($rows | Where-Object { $_.role -eq "warmup" })
if ($warmups.Count -ne 3) { throw "Expected 3 warm-up rows in analysis/a2/speed_test_rows.csv." }
$warmupLog = @()
foreach ($w in $warmups) {
    $r = Send-Ticket ([int]$w.row) $w.narrative
    Write-Host ("warm-up row {0}: {1} s (discarded)" -f $r.row, $r.seconds)
    $warmupLog += $r
}
if ($isCascade) {
    # The brief allows sending one warm-up directly to the large model. Same options as the service (num_gpu 0).
    $payload = @{ model = "qwen2.5:7b"; prompt = $warmups[0].narrative; stream = $false; options = @{ num_gpu = 0 } } | ConvertTo-Json -Compress
    Invoke-RestMethod -Method Post -Uri "$OllamaUrl/api/generate" -Body ([System.Text.Encoding]::UTF8.GetBytes($payload)) `
        -ContentType "application/json; charset=utf-8" -TimeoutSec 600 | Out-Null
    Write-Host "Large model loaded directly for the cascade warm-up."
}
$warmedAt = Get-Utc

# 5. Residency check.
$psBefore = Get-OllamaPs
Write-Host $psBefore
$problem = Test-Resident $psBefore
if ($problem) { throw "ollama ps check failed: $problem. Do not start JMeter." }

# 6. Counters before.
$statsBefore = Get-StatsTotal
$linesBefore = Get-LogLineCount
$readyAt = Get-Utc

Write-Host ""
Write-Host "READY at $readyAt (UTC). Start JMeter on Machine B NOW (within 4 minutes, before Ollama's 5-minute keep-alive):" -ForegroundColor Green
Write-Host "  .\scripts\a2_jmeter_run.ps1 -Config $Config -Run $Run -HostA <this machine's IP>" -ForegroundColor Green
Write-Host "Do not use Machine A while it runs (about 11 minutes including the 6-minute pause)."
[void](Read-Host "When JMeter on Machine B has printed 'end of run' and exited, press Enter here")

# 7. Counters after.
$statsAfter = Get-StatsTotal
$linesAfter = Get-LogLineCount
$psAfter = Get-OllamaPs
$finishedAt = Get-Utc
$afterProblem = Test-Resident $psAfter

# 8. Log segment and run record.
$segment = "$logDir/$tag.jsonl"
& $Python scripts/extract_a2_log_segment.py --log $requestLog --after-line $linesBefore --through-line $linesAfter --output $segment
if ($LASTEXITCODE -ne 0) { throw "Log extraction failed." }

$record = [ordered]@{
    config = $Config; run = $Run; machine = "Machine A"
    ollama_version = $version
    ollama_restarted_utc = $restartedAt; warmup_finished_utc = $warmedAt; ready_utc = $readyAt; recorded_after_utc = $finishedAt
    warmup_discarded = $warmupLog
    ollama_ps_before = $psBefore.Trim(); ollama_ps_after = $psAfter.Trim()
    models_still_resident_after = ($afterProblem -eq ""); residency_note_after = $afterProblem
    stats_total_before = $statsBefore; stats_total_after = $statsAfter; stored_during_run = $statsAfter - $statsBefore
    log_lines_before = $linesBefore; log_lines_after = $linesAfter; log_segment = $segment
    jtl = "jmeter/results/a2_$tag.jtl"
    environment_snapshot = "$envDir/$tag.txt"
}
Write-Utf8NoBom $runFile ($record | ConvertTo-Json -Depth 5)
Write-Host "Wrote $runFile and $segment. Stored during run: $($statsAfter - $statsBefore)." -ForegroundColor Green
if ($afterProblem) { Write-Warning "After the run: $afterProblem. A model was unloaded during the run; report this, do not hide it." }
