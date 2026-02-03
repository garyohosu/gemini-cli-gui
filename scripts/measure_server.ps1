param(
  [int]$HealthTimeoutSec = 20,
  [int]$PromptTimeoutSec = 60,
  [int]$ShutdownTimeoutSec = 5,
  [string]$ResultDir = ''
)

$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir '..')
$workspace = $repoRoot
$env:GEMINI_WORKSPACE_ROOT = $workspace.Path

if (-not $ResultDir) {
  $ResultDir = Join-Path $repoRoot 'result'
}
if (-not (Test-Path $ResultDir)) {
  New-Item -ItemType Directory -Path $ResultDir | Out-Null
}
$timestamp = (Get-Date).ToString('yyyyMMdd-HHmmss')
$resultPath = Join-Path $ResultDir "measure_server_${timestamp}.md"
$log = New-Object System.Collections.Generic.List[string]
$log.Add("# Measure Server Result ($((Get-Date).ToString('yyyy-MM-dd')))") | Out-Null
$log.Add('') | Out-Null
$log.Add('Command: `scripts\measure_server.ps1`') | Out-Null
$log.Add('') | Out-Null

$proc = $null
try {
  $sw = [System.Diagnostics.Stopwatch]::StartNew()
  $proc = Start-Process -FilePath node -ArgumentList @('server/gemini_server.js') -WorkingDirectory $workspace.Path -WindowStyle Hidden -PassThru
  $log.Add("SERVER_PID $($proc.Id)") | Out-Null
  Write-Output "SERVER_PID $($proc.Id)"

  $health = $null
  $deadline = (Get-Date).AddSeconds($HealthTimeoutSec)
  while ((Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 500
    try {
      $health = Invoke-WebRequest -Uri 'http://127.0.0.1:9876/health' -UseBasicParsing -TimeoutSec 1
      if ($health.StatusCode -eq 200) { break }
    } catch { }
  }
  $sw.Stop()
  $elapsedMs = $sw.ElapsedMilliseconds

  if ($health -and $health.StatusCode -eq 200) {
    $log.Add("HEALTH_OK in ${elapsedMs}ms") | Out-Null
    $log.Add($health.Content) | Out-Null
    Write-Output "HEALTH_OK in ${elapsedMs}ms"
    Write-Output $health.Content
  } else {
    $log.Add("HEALTH_FAIL after ${elapsedMs}ms") | Out-Null
    Write-Output "HEALTH_FAIL after ${elapsedMs}ms"
  }

  if ($health -and $health.StatusCode -eq 200) {
    $sw2 = [System.Diagnostics.Stopwatch]::StartNew()
    $payload = @{ prompt = 'Say hello in one word'; workingDir = $workspace.Path } | ConvertTo-Json
    try {
      $resp = Invoke-WebRequest -Uri 'http://127.0.0.1:9876/prompt' -Method Post -Body $payload -ContentType 'application/json' -UseBasicParsing -TimeoutSec $PromptTimeoutSec
      $sw2.Stop()
      $promptElapsed = $sw2.ElapsedMilliseconds
      $log.Add("PROMPT_OK in ${promptElapsed}ms") | Out-Null
      $log.Add($resp.Content) | Out-Null
      Write-Output "PROMPT_OK in ${promptElapsed}ms"
      Write-Output $resp.Content
    } catch {
      $sw2.Stop()
      $promptElapsed = $sw2.ElapsedMilliseconds
      $log.Add("PROMPT_FAIL in ${promptElapsed}ms") | Out-Null
      $log.Add($_.Exception.Message) | Out-Null
      Write-Output "PROMPT_FAIL in ${promptElapsed}ms"
      Write-Output $_.Exception.Message
    }
  }
} finally {
  if ($proc -and !$proc.HasExited) {
    try {
      Stop-Process -Id $proc.Id -Force
      Wait-Process -Id $proc.Id -Timeout $ShutdownTimeoutSec -ErrorAction SilentlyContinue
    } catch { }
  }
}

$log.Add('') | Out-Null
$log.Add("Saved: $resultPath") | Out-Null
$log | Set-Content -Path $resultPath
