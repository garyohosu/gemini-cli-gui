param(
    [string]$Prompt,
    [string]$OutputFile = "C:\temp\gemini_output.txt",
    [int]$TimeoutSeconds = 180,
    [string]$WorkspaceDir = ""
)

$outDir = Split-Path -Parent $OutputFile
if (-not (Test-Path $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}

if (Test-Path $OutputFile) {
    Remove-Item $OutputFile -Force
}

# Build command with workspace if specified
$command = "gemini -p `"$Prompt`" -y"
if ($WorkspaceDir -and (Test-Path $WorkspaceDir)) {
    $command += " -d `"$WorkspaceDir`""
}
$command += " > `"$OutputFile`" 2>&1"

# Change to workspace directory before running
$originalDir = Get-Location
if ($WorkspaceDir -and (Test-Path $WorkspaceDir)) {
    Set-Location $WorkspaceDir
}

$proc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", $command -WindowStyle Hidden -PassThru -WorkingDirectory $(if ($WorkspaceDir) { $WorkspaceDir } else { $originalDir })

$proc | Wait-Process -Timeout $TimeoutSeconds

# Restore original directory
if ($WorkspaceDir -and (Test-Path $WorkspaceDir)) {
    Set-Location $originalDir
}

if (Test-Path $OutputFile) {
    Get-Content $OutputFile -Raw
} else {
    Write-Error "Output file not found: $OutputFile"
    exit 1
}
