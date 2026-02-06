# Clean Response Extraction Fix - Test Results

**Date**: 2026-02-05
**Issue**: #22
**Tested by**: Local Codex

## Root Cause (Observed)
- Raw TTY output mostly contains UI/spinner/banners.
- In this environment, prompts appear to be waiting for auth; no actual model response text is present in the raw output.
- As a result, the previous `_clean_response()` could only extract UI artifacts (ASCII art banner).

## Solution Implemented
- Replaced `_clean_response()` in `core/gemini_runner.py` with a state-machine approach that:
  - Searches for the echoed prompt.
  - Skips UI/banner lines via `_is_ui_line()`.
  - Collects response lines until the next prompt.
  - Falls back to a looser cleanup if state machine finds nothing.
- Added debug logging to trace extraction steps and line decisions.

## Test Results

### Verification Script (interactive)
Command:
```
"Say hello`nCount to 3`nこんにちは`n`n" | py scripts\verify_gemini_tty.py --interactive --raw-log result\2026-02-05_clean-response-fix_raw.txt --clean-log result\2026-02-05_clean-response-fix_clean.txt
```

Results:
- "Say hello": elapsed_ms=3112, clean_len=0 (no response text)
- "Count to 3": elapsed_ms=95470, clean_len=640 (ASCII art banner)
- "こんにちは": elapsed_ms=2108, clean_len=0 (no response text)

### Debug Output
- `result/2026-02-05_clean-response-fix_debug.txt`
- Shows that the state machine could not locate a non-UI response after prompt; fallback still returns banner in some cases.

### Raw Output Inspection
- `result/2026-02-05_clean-response-fix_raw.txt` contains repeated "Waiting for auth..." UI.
- No clear model response lines found after ANSI stripping.

### GUI Test
Command:
```
py app.py --log-mode none
```
Result:
- Timed out in this environment (non-interactive). App process was terminated.

## Performance
- Initial prompt in interactive session: ~3s (no response text)
- Second prompt showed long delay (~95s), likely due to auth wait or UI refresh.

## Conclusion
- ✅ Extraction logic updated with state machine + fallback + debug logging.
- ❌ Unable to validate real response extraction due to missing response text (auth/UI-only output in this environment).

## Next Step
- Re-test on an authenticated local session where Gemini CLI returns actual content.
- If responses still fail, adjust `_is_ui_line()` and prompt detection with real samples.
