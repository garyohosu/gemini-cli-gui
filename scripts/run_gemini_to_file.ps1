param(
    [string]$Prompt,
    [string]$OutputFile = "C:\temp\gemini_output.txt",
    [int]$TimeoutSeconds = 180
)

$outDir = Split-Path -Parent $OutputFile
if (-not (Test-Path $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}

if (Test-Path $OutputFile) {
    Remove-Item $OutputFile -Force
}

$command = "gemini -p `"$Prompt`" -y > `"$OutputFile`" 2>&1"
$proc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", $command -WindowStyle Hidden -PassThru

$proc | Wait-Process -Timeout $TimeoutSeconds

if (Test-Path $OutputFile) {
    Get-Content $OutputFile -Raw
} else {
    Write-Error "Output file not found: $OutputFile"
    exit 1
}
