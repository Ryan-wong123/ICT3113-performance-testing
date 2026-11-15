<#
.SYNOPSIS
  Machine A: (re)create the triage container for ONE Assignment 2 speed configuration.

.DESCRIPTION
  Sets every service variable explicitly (so nothing carries over from an earlier
  configuration in the same PowerShell window), recreates the container, and checks
  that /health and the container's own environment match the frozen rule in
  docs/a2_escalation_rule.md. Run once per configuration, from the repository root.

.EXAMPLE
  .\scripts\a2_start_service.ps1 -Config qwen2.5_7b
  .\scripts\a2_start_service.ps1 -Config cascade_a
  .\scripts\a2_start_service.ps1 -Config cascade_b
#>
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("qwen2.5_7b", "cascade_a", "cascade_b")]
    [string]$Config,
    [string]$ServiceUrl = "http://localhost:8000"
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

# Frozen values from docs/a2_escalation_rule.md. Do not edit.
$settings = @{
    "qwen2.5_7b" = @{
        CASCADE_ENABLED = "false"; OLLAMA_MODEL = "qwen2.5:7b"
        OLLAMA_SMALL_MODEL = ""; OLLAMA_LARGE_MODEL = ""; CASCADE_RULE_SETTING = ""
        CASCADE_RULE_TYPE = "category"; CASCADE_ESCALATE_CATEGORIES = ""; CASCADE_LENGTH_THRESHOLD_CHARS = ""
    }
    "cascade_a" = @{
        CASCADE_ENABLED = "true"; OLLAMA_MODEL = "qwen2.5:7b"
        OLLAMA_SMALL_MODEL = "llama3.2:1b"; OLLAMA_LARGE_MODEL = "qwen2.5:7b"; CASCADE_RULE_SETTING = "A"
        CASCADE_RULE_TYPE = "category"
        CASCADE_ESCALATE_CATEGORIES = "Bank account or service|Consumer loan|Credit card|Credit reporting|Debt collection"
        CASCADE_LENGTH_THRESHOLD_CHARS = ""
    }
    "cascade_b" = @{
        CASCADE_ENABLED = "true"; OLLAMA_MODEL = "qwen2.5:7b"
        OLLAMA_SMALL_MODEL = "llama3.2:1b"; OLLAMA_LARGE_MODEL = "qwen2.5:7b"; CASCADE_RULE_SETTING = "B"
        CASCADE_RULE_TYPE = "category"
        CASCADE_ESCALATE_CATEGORIES = "Consumer loan|Credit card|Credit reporting|Debt collection"
        CASCADE_LENGTH_THRESHOLD_CHARS = ""
    }
}
$wanted = $settings[$Config]

foreach ($name in $wanted.Keys) {
    # Process scope only. An empty value removes the variable, so compose uses its empty default.
    $value = $wanted[$name]
    if ($value -eq "") { $value = $null }
    [Environment]::SetEnvironmentVariable($name, $value, "Process")
}
[Environment]::SetEnvironmentVariable("OLLAMA_BASE_URL", "http://host.docker.internal:11434", "Process")
[Environment]::SetEnvironmentVariable("OLLAMA_TIMEOUT_SECONDS", "300", "Process")

Write-Host "Recreating the service container for $Config ..."
docker compose down
if ($LASTEXITCODE -ne 0) { throw "docker compose down failed" }
docker compose up -d --build --force-recreate
if ($LASTEXITCODE -ne 0) { throw "docker compose up failed" }

$health = $null
for ($i = 0; $i -lt 60 -and $null -eq $health; $i++) {
    try { $health = Invoke-RestMethod -Uri "$ServiceUrl/health" -TimeoutSec 5 } catch { Start-Sleep -Seconds 1 }
}
if ($null -eq $health) { throw "Service did not answer $ServiceUrl/health within 60 s" }

$problems = @()
$expectMode = if ($wanted.CASCADE_ENABLED -eq "true") { "on" } else { "off" }
if ($health.cascade_mode -ne $expectMode) { $problems += "health cascade_mode=$($health.cascade_mode), expected $expectMode" }
if ($expectMode -eq "off" -and $health.model -ne $wanted.OLLAMA_MODEL) { $problems += "health model=$($health.model), expected $($wanted.OLLAMA_MODEL)" }
if ($expectMode -eq "on") {
    if ($health.small_model -ne $wanted.OLLAMA_SMALL_MODEL) { $problems += "small_model=$($health.small_model)" }
    if ($health.large_model -ne $wanted.OLLAMA_LARGE_MODEL) { $problems += "large_model=$($health.large_model)" }
    if ($health.rule_setting -ne $wanted.CASCADE_RULE_SETTING) { $problems += "rule_setting=$($health.rule_setting)" }
}
# /health does not show the escalation list, so read it from inside the container.
$inside = (docker compose exec -T ticket-triage printenv CASCADE_ESCALATE_CATEGORIES 2>$null)
if ($null -eq $inside) { $inside = "" }
$inside = ($inside | Out-String).Trim()
if ($inside -ne $wanted.CASCADE_ESCALATE_CATEGORIES) {
    $problems += "container CASCADE_ESCALATE_CATEGORIES='$inside', expected '$($wanted.CASCADE_ESCALATE_CATEGORIES)'"
}

$health | ConvertTo-Json | Write-Host
Write-Host "Container escalation list: '$inside'"
if ($problems.Count -gt 0) {
    throw ("Configuration mismatch, do NOT run: " + ($problems -join "; "))
}
Write-Host "OK: service is configured for $Config." -ForegroundColor Green
