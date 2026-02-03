# Verify Reparse Points Result (2026-02-03)

Command: `scripts\verify_reparse_points.ps1`

Workspace: C:\Users\garyo\AppData\Local\Temp\gemini-sandbox-eg43rdpt.cyc\workspace
Outside: C:\Users\garyo\AppData\Local\Temp\gemini-sandbox-eg43rdpt.cyc\outside

Symlink created: C:\Users\garyo\AppData\Local\Temp\gemini-sandbox-eg43rdpt.cyc\workspace\link_outside -> C:\Users\garyo\AppData\Local\Temp\gemini-sandbox-eg43rdpt.cyc\outside
Junction created: C:\Users\garyo\AppData\Local\Temp\gemini-sandbox-eg43rdpt.cyc\workspace\junction_outside -> C:\Users\garyo\AppData\Local\Temp\gemini-sandbox-eg43rdpt.cyc\outside

Python verification output:
```json
{
  "symlink": "DENY: Path escapes workspace: C:\\Users\\garyo\\AppData\\Local\\Temp\\gemini-sandbox-eg43rdpt.cyc\\outside\\secret.txt",
  "junction": "DENY: Path escapes workspace: C:\\Users\\garyo\\AppData\\Local\\Temp\\gemini-sandbox-eg43rdpt.cyc\\outside\\secret.txt"
}
```

Saved: C:\project\gemini-cli-gui\result\verify_reparse_points_20260203-205202.md
