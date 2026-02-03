# SendKeys Focus Fix (2026-02-03)

## File
`scripts/gui_smoke_sendkeys.vbs`

## Improvements
- Activate window by PID (python.exe + app.py in command line)
- Fallback to title activation with retries

## Run
```bat
cscript //nologo scripts\gui_smoke_sendkeys.vbs
```

## Customize
- `workspacePath`, `promptText`
- `TAB_TO_FOLDER_BTN`, `TAB_TO_INPUT`
