param(
  [string]$ResultDir = ''
)

$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir '..')

if (-not $ResultDir) {
  $ResultDir = Join-Path $repoRoot 'result'
}
if (-not (Test-Path $ResultDir)) {
  New-Item -ItemType Directory -Path $ResultDir | Out-Null
}

$timestamp = (Get-Date).ToString('yyyyMMdd-HHmmss')
$resultPath = Join-Path $ResultDir "verify_reparse_points_${timestamp}.md"
$log = New-Object System.Collections.Generic.List[string]

$log.Add("# Verify Reparse Points Result ($((Get-Date).ToString('yyyy-MM-dd')))" ) | Out-Null
$log.Add('') | Out-Null
$log.Add('Command: `scripts\verify_reparse_points.ps1`') | Out-Null
$log.Add('') | Out-Null

$tempRoot = Join-Path $env:TEMP ("gemini-sandbox-" + [System.IO.Path]::GetRandomFileName())
$workspace = Join-Path $tempRoot 'workspace'
$outside = Join-Path $tempRoot 'outside'

try {
  New-Item -ItemType Directory -Path $workspace | Out-Null
  New-Item -ItemType Directory -Path $outside | Out-Null
  $secret = Join-Path $outside 'secret.txt'
  Set-Content -Path $secret -Value 'secret'

  $log.Add("Workspace: $workspace") | Out-Null
  $log.Add("Outside: $outside") | Out-Null
  $log.Add('') | Out-Null

  $symlink = Join-Path $workspace 'link_outside'
  $junction = Join-Path $workspace 'junction_outside'

  $symlinkCreated = $false
  $junctionCreated = $false

  try {
    New-Item -ItemType SymbolicLink -Path $symlink -Target $outside | Out-Null
    $symlinkCreated = $true
    $log.Add("Symlink created: $symlink -> $outside") | Out-Null
  } catch {
    $log.Add("Symlink creation failed: $($_.Exception.Message)") | Out-Null
  }

  try {
    cmd /c "mklink /J `"$junction`" `"$outside`"" | Out-Null
    if (Test-Path $junction) {
      $junctionCreated = $true
      $log.Add("Junction created: $junction -> $outside") | Out-Null
    } else {
      $log.Add('Junction creation failed: mklink did not create the path') | Out-Null
    }
  } catch {
    $log.Add("Junction creation failed: $($_.Exception.Message)") | Out-Null
  }

  $log.Add('') | Out-Null

  $python = @"
import json
import sys
from pathlib import Path

repo_root = Path(r"{REPO_ROOT}")
sys.path.insert(0, str(repo_root))

from core.workspace_sandbox import WorkspaceSandbox, SandboxViolation

workspace = Path(r"{WORKSPACE}")
paths = {
    "symlink": r"{SYMLINK}",
    "junction": r"{JUNCTION}",
}

sandbox = WorkspaceSandbox.create(workspace)
results = {}
for label, base in paths.items():
    if not Path(base).exists():
        results[label] = "not_created"
        continue
    candidate = str(Path(base) / "secret.txt")
    try:
        resolved = sandbox.resolve(candidate)
        results[label] = f"ALLOW: {resolved}"
    except SandboxViolation as exc:
        results[label] = f"DENY: {exc}"

print(json.dumps(results, indent=2))
"@

  $python = $python.Replace('{REPO_ROOT}', $repoRoot.Path)
  $python = $python.Replace('{WORKSPACE}', $workspace)
  $python = $python.Replace('{SYMLINK}', $symlink)
  $python = $python.Replace('{JUNCTION}', $junction)

  $log.Add('Python verification output:') | Out-Null
  $log.Add('```json') | Out-Null
  $pythonOutput = $python | python -
  $pythonOutput | ForEach-Object { $log.Add($_) | Out-Null }
  $log.Add('```') | Out-Null
} finally {
  try {
    if (Test-Path $tempRoot) {
      Remove-Item -Recurse -Force $tempRoot
    }
  } catch { }
}

$log.Add('') | Out-Null
$log.Add("Saved: $resultPath") | Out-Null
$log | Set-Content -Path $resultPath

Write-Output "Saved: $resultPath"
