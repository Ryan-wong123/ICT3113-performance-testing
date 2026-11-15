<#
.SYNOPSIS
  Machine B: run ONE Assignment 2 JMeter speed run against Machine A.

.DESCRIPTION
  Run from the repository root on Machine B, only after Machine A's
  .\scripts\a2_speed_run.ps1 has printed READY. Uses the committed plan defaults
  (11.253/min random arrivals for 5 min, seed 8, 300 s timeout, 360 s pause) and the
  committed ordered workload; nothing about the schedule is overridden.

.EXAMPLE
  .\scripts\a2_jmeter_run.ps1 -Config qwen2.5_7b -Run 1 -HostA 192.168.1.23
#>
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("qwen2.5_7b", "cascade_a", "cascade_b")]
    [string]$Config,
    [Parameter(Mandatory = $true)]
    [ValidateRange(1, 3)]
    [int]$Run,
    [Parameter(Mandatory = $true)]
    [string]$HostA,
    [int]$Port = 8000,
    [string]$JMeter = ""
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

if (-not $JMeter) {
    $onPath = Get-Command jmeter.bat -ErrorAction SilentlyContinue
    if ($onPath) { $JMeter = $onPath.Source }
    elseif ($env:JMETER_HOME) { $JMeter = Join-Path $env:JMETER_HOME "bin\jmeter.bat" }
    else { $JMeter = "C:\Users\ryan\AppData\Local\Programs\Apache\apache-jmeter-5.6.3\bin\jmeter.bat" }
}
if (-not (Test-Path $JMeter)) { throw "jmeter.bat not found at $JMeter; pass -JMeter <path>." }

$tag = "a2_${Config}_run$Run"
$jtl = "jmeter\results\$tag.jtl"
$jlog = "jmeter\results\$tag.jmeter.log"
if (Test-Path $jtl) { throw "$jtl already exists. Never overwrite a run." }

# Check Machine A is reachable and configured for this configuration.
$health = Invoke-RestMethod -Uri "http://${HostA}:$Port/health" -TimeoutSec 10
$expectMode = if ($Config -like "cascade_*") { "on" } else { "off" }
if ($health.cascade_mode -ne $expectMode) { throw "Machine A reports cascade_mode=$($health.cascade_mode); expected $expectMode for $Config." }
if ($expectMode -eq "on") {
    $letter = $Config.Substring($Config.Length - 1).ToUpper()
    if ($health.rule_setting -ne $letter) { throw "Machine A reports rule_setting=$($health.rule_setting); expected $letter." }
}
Write-Host "Machine A OK: $($health | ConvertTo-Json -Compress)"

$workload = @(Import-Csv -Encoding UTF8 "jmeter\test_plans\a2_speed_narratives.csv")
Write-Host "Workload rows available: $($workload.Count) (must exceed the arrivals in one run, about 56)."

$started = (Get-Date).ToUniversalTime().ToString("o")
& $JMeter -n `
    -t "jmeter\test_plans\a2_ticket_triage_speed_test.jmx" `
    -l $jtl `
    -j $jlog `
    "-Jhost=$HostA" `
    "-Jport=$Port"
$exitCode = $LASTEXITCODE
$ended = (Get-Date).ToUniversalTime().ToString("o")

if (-not (Test-Path $jtl)) { throw "JMeter did not write $jtl (exit code $exitCode)." }
$samples = @(Import-Csv $jtl)
$ok = @($samples | Where-Object { $_.success -eq "true" }).Count
$codes = $samples | Group-Object responseCode | ForEach-Object { "$($_.Name)=$($_.Count)" }
Write-Host ""
Write-Host "Run $tag  started $started  ended $ended (UTC)  JMeter exit code $exitCode"
Write-Host "Samples in JTL: $($samples.Count)  successful: $ok  response codes: $($codes -join ', ')"
if ($samples.Count -gt $workload.Count) {
    Write-Warning "More samples than distinct workload rows: some tickets were sent twice. Report this."
}
Write-Host "Now press Enter on Machine A. Then commit $jtl and $jlog from this machine (see docs/test_playbook.md)."
