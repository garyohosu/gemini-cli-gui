param(
  [int]$HealthTimeoutSec = 5,
  [int]$PromptTimeoutSec = 5,
  [int]$CancelAfterSec = 3,
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
$resultPath = Join-Path $ResultDir "verify_long_running_${timestamp}.md"
$log = New-Object System.Collections.Generic.List[string]

$log.Add("# Long-Running Verification Result ($((Get-Date).ToString('yyyy-MM-dd')))") | Out-Null
$log.Add('') | Out-Null
$log.Add('Command: `scripts\verify_long_running.ps1`') | Out-Null
$log.Add('') | Out-Null

$proc = $null
try {
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

  if ($health -and $health.StatusCode -eq 200) {
    $log.Add("HEALTH_OK") | Out-Null
    Write-Output "HEALTH_OK"
  } else {
    $log.Add("HEALTH_FAIL") | Out-Null
    Write-Output "HEALTH_FAIL"
  }

  if ($health -and $health.StatusCode -eq 200) {
    $payloadObj = @{
      prompt = 'Write a very long response with many paragraphs.'
      workingDir = $workspace.Path
      timeoutMs = ($PromptTimeoutSec * 1000)
    }
    $payload = $payloadObj | ConvertTo-Json

    # Timeout test
    $timeoutSw = [System.Diagnostics.Stopwatch]::StartNew()
    try {
      Invoke-WebRequest -Uri 'http://127.0.0.1:9876/prompt' -Method Post -Body $payload -ContentType 'application/json' -UseBasicParsing -TimeoutSec $PromptTimeoutSec | Out-Null
      $timeoutSw.Stop()
      $log.Add("PROMPT_TIMEOUT_TEST: unexpected success in $($timeoutSw.ElapsedMilliseconds)ms") | Out-Null
    } catch {
      $timeoutSw.Stop()
      $log.Add("PROMPT_TIMEOUT_TEST: timeout/error in $($timeoutSw.ElapsedMilliseconds)ms") | Out-Null
      $log.Add($_.Exception.Message) | Out-Null
    }

    # Cancellation test (start async, then cancel by requestId)
    $startResp = Invoke-WebRequest -Uri 'http://127.0.0.1:9876/prompt/start' -Method Post -Body $payload -ContentType 'application/json' -UseBasicParsing -TimeoutSec 10
    $startJson = $startResp.Content | ConvertFrom-Json -ErrorAction SilentlyContinue
    $requestId = $startJson.requestId
    if (-not $requestId) {
      throw "requestId not returned from /prompt/start"
    }

    Start-Sleep -Seconds $CancelAfterSec
    try {
      $cancelPayload = @{ requestId = $requestId } | ConvertTo-Json
      Invoke-WebRequest -Uri 'http://127.0.0.1:9876/cancel' -Method Post -Body $cancelPayload -ContentType 'application/json' -UseBasicParsing | Out-Null
      $log.Add("CANCEL_TEST: sent cancel for requestId $requestId") | Out-Null
    } catch {
      $log.Add("CANCEL_TEST: failed to stop server: $($_.Exception.Message)") | Out-Null
    }

    Start-Sleep -Seconds 1
    try {
      $resultResp = Invoke-WebRequest -Uri "http://127.0.0.1:9876/prompt/result?requestId=$requestId" -UseBasicParsing -TimeoutSec 5
      $log.Add("CANCEL_TEST: result status $($resultResp.StatusCode)") | Out-Null
      $log.Add($resultResp.Content) | Out-Null
    } catch {
      $log.Add("CANCEL_TEST: result fetch failed: $($_.Exception.Message)") | Out-Null
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

Write-Output "Saved: $resultPath"
