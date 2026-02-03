# WorkspaceSandbox Verification (2026-02-03)

## Command
`python scripts\verify_workspace_sandbox.py`

## Output
```json
{
  "ok_relative": "C:\\Users\\garyo\\AppData\\Local\\Temp\\tmp9lczsgwx\\dir\\file.txt",
  "ok_absolute": "C:\\Users\\garyo\\AppData\\Local\\Temp\\tmp9lczsgwx\\dir\\file2.txt",
  "fail_traversal": "Path escapes workspace: C:\\Users\\garyo\\AppData\\Local\\Temp\\outside.txt",
  "fail_unc": "UNC/long paths are not allowed: \\\\server\\share\\file.txt",
  "fail_long_path": "UNC/long paths are not allowed: \\\\?\\C:\\temp\\file.txt",
  "fail_other_drive": "Cross-drive absolute paths are not allowed: Z:\\tmp\\file.txt"
}
```
