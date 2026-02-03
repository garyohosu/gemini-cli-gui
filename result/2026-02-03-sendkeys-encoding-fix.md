# SendKeys Script Encoding Fix (2026-02-03)

- Rewrote `scripts/gui_smoke_sendkeys.vbs` as UTF-8 without BOM and ASCII-only strings to avoid VBScript invalid character errors.
