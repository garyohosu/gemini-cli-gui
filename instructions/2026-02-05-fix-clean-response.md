# Task: Fix Response Extraction in GeminiRunner

**Date**: 2026-02-05  
**Issue**: #22  
**Branch**: `fix/clean-response-extraction`  
**Assignee**: Local Codex (Windows)

## Executive Summary

✅ **Speed confirmed**: 2.1s (50x improvement)  
✅ **Data captured**: 33KB raw output received  
❌ **Extraction broken**: Actual response removed by `_clean_response()`

**Task**: Fix `core/gemini_runner.py::_clean_response()` to extract actual response while removing UI elements.

## Verification Results (Already Done)

From `result/2026-02-05_tty-cli-verification.md`:

```
Prompt 1: "Say hello in one word."
- elapsed_ms: 104513 (initial startup)
- raw_len: 33082 (data received ✅)
- ansi_esc: 1132 (ANSI codes ✅)
- clean_len: 640 (❌ should be ~5-10 chars)

Prompt 2: Same prompt
- elapsed_ms: 2110 (⚡ fast!)
- raw_len: 1836 (data received ✅)
- ansi_esc: 49 (minimal ANSI)
- clean_len: 0 (❌ response completely removed!)
```

**Analysis**: Current `_clean_response()` removes TOO MUCH.

## Root Cause Analysis

### Current Flow (Problematic)

```python
def _clean_response(self, raw: str, sent_prompt: str) -> str:
    text = self._strip_ansi_codes(raw)  # ✅ Works
    lines = text.split("\n")
    
    # Problem: Too aggressive filtering
    for line in lines:
        if self._is_ui_line(line):  # ❌ Removes actual response too
            continue
```

### What's Happening

1. **Prompt 1**: UI banner + response → removes banner + response
2. **Prompt 2**: No banner, just response → removes everything

### Why?

The skip patterns are TOO BROAD. They match actual response content.

## Required Files to Analyze

**Before coding, examine these**:

1. `result/2026-02-05_tty-raw.txt` - Raw PTY output
2. `result/2026-02-05_tty-clean.txt` - Current cleaned output

### What to Look For

Open `result/2026-02-05_tty-raw.txt` and find:

```
[Search for:]
1. The echoed prompt: "Say hello in one word."
2. The NEXT non-empty line after prompt = actual response
3. Where response ends (next prompt symbol or empty lines)
```

**Example expected structure**:
```
[...UI banner...]
> Say hello in one word.
Hello
> [next prompt]
```

## Implementation Guide

### Step 1: Add Debug Logging

Add to `core/gemini_runner.py`:

```python
import logging

# At top of _clean_response()
def _clean_response(self, raw: str, sent_prompt: str) -> str:
    """Clean up the response by removing echoed input, prompts, and ANSI codes."""
    
    # Debug: log what we're working with
    logging.debug(f"=== CLEAN RESPONSE DEBUG ===")
    logging.debug(f"Raw length: {len(raw)}")
    logging.debug(f"Sent prompt: {sent_prompt}")
    
    # Strip ANSI
    text = self._strip_ansi_codes(raw)
    logging.debug(f"After ANSI strip: {len(text)} chars")
    logging.debug(f"First 500 chars: {text[:500]}")
    
    # ... rest of function ...
    
    logging.debug(f"Final result length: {len(result)}")
    logging.debug(f"Final result: {result}")
    logging.debug(f"=== END DEBUG ===")
    
    return result
```

### Step 2: Improve Extraction Logic

**New algorithm**:

```python
def _clean_response(self, raw: str, sent_prompt: str) -> str:
    """Clean up the response by removing echoed input, prompts, and ANSI codes."""
    
    # Strip ANSI first
    text = self._strip_ansi_codes(raw)
    lines = text.split("\n")
    
    # State machine for extraction
    state = "searching"  # searching -> found_prompt -> collecting -> done
    response_lines = []
    
    for line in lines:
        stripped = line.strip()
        
        if state == "searching":
            # Look for echoed prompt
            if sent_prompt.strip() in stripped:
                state = "found_prompt"
                logging.debug(f"Found prompt at: {stripped[:50]}")
                continue
        
        elif state == "found_prompt":
            # Skip empty lines immediately after prompt
            if not stripped:
                continue
            
            # Skip UI lines
            if self._is_ui_line(stripped):
                continue
            
            # This is the start of actual response!
            state = "collecting"
            response_lines.append(line.rstrip())
            logging.debug(f"Response starts: {stripped[:50]}")
        
        elif state == "collecting":
            # Stop at next prompt symbol
            if stripped in ['>', '›', '»', '*']:
                state = "done"
                break
            
            # Skip UI lines within response
            if self._is_ui_line(stripped):
                continue
            
            # Collect response line
            response_lines.append(line.rstrip())
    
    # Clean up result
    result = "\n".join(response_lines).strip()
    
    # Remove multiple blank lines
    result = re.sub(r'\n\n\n+', '\n\n', result)
    
    return result
```

### Step 3: Review _is_ui_line()

Make sure it doesn't match actual response content:

```python
def _is_ui_line(self, line: str) -> bool:
    """Check if line is UI element (not actual response)."""
    
    # Empty lines are not UI (might be in response)
    if not line.strip():
        return False
    
    ui_patterns = [
        r'^\d+\s+\w+\.md\s+files',  # "2 GEMINI.md files"
        r'YOLO mode',
        r'no sandbox',
        r'ctrl \+ y',
        r'/model',
        r'/docs',
        r'Type your message',
        r'Tips for getting started',
        r'Ready \(',
        # Add more as needed, but BE SPECIFIC
    ]
    
    for pattern in ui_patterns:
        if re.search(pattern, line, re.IGNORECASE):
            return True
    
    return False
```

## Testing Instructions

### Test 1: Run Verification Script

```bash
cd C:/PROJECT/gemini-cli-gui
py scripts\verify_gemini_tty.py --prompt "Say hello in one word." --repeat 2 --debug
```

**Expected output**:
```
Prompt 1:
  elapsed_ms: ~100000
  raw_len: ~33000
  clean_len: 5-10 (just "Hello" or "Hello.")
  
Prompt 2:
  elapsed_ms: ~2000
  raw_len: ~1800
  clean_len: 5-10 (just "Hello" or "Hello.")
```

### Test 2: Multiple Prompts

```bash
py scripts\verify_gemini_tty.py --prompt "Count to 3" --repeat 1
# Expected: "1\n2\n3" or "1, 2, 3"

py scripts\verify_gemini_tty.py --prompt "こんにちは" --repeat 1
# Expected: "こんにちは！..." (actual response in Japanese)

py scripts\verify_gemini_tty.py --prompt "List 3 fruits" --repeat 1
# Expected: "Apple\nBanana\nOrange" or similar
```

### Test 3: GUI Integration

```bash
py app.py
# Test:
# 1. Select workspace
# 2. Send "こんにちは"
# 3. Verify response appears in ~2s (not empty)
# 4. Send "ファイル一覧をください"
# 5. Verify file list appears
```

## Debugging Tips

### If response is still empty:

1. Check debug logs - where did extraction stop?
2. Look at `first 500 chars` log - is prompt there?
3. Look at raw.txt manually - where IS the actual response?
4. Adjust state machine accordingly

### If UI elements remain:

1. Check which pattern matched - add to `_is_ui_line()`
2. Be specific - don't use broad patterns like `.*files.*`

## Documentation Requirements

After fixing and testing, create:

### `result/2026-02-05_clean-response-fix.md`

```markdown
# Clean Response Extraction Fix

**Date**: 2026-02-05  
**Issue**: #22

## Problem
`_clean_response()` was removing actual responses along with UI elements.

## Root Cause
1. Skip patterns too broad
2. No clear state machine for "found prompt" → "start response" → "end response"
3. Second prompt had no UI banner, so entire output was response → completely removed

## Solution Implemented

### Algorithm Change
Implemented state machine:
- searching: Find echoed prompt
- found_prompt: Skip empty/UI lines
- collecting: Collect response until next prompt
- done: Stop

### Code Changes
[Paste diff or describe changes]

## Test Results

### Verification Script Tests
| Prompt | Expected | Actual | Result |
|--------|----------|--------|--------|
| "Say hello" | "Hello" | "Hello" | ✅ PASS |
| "Count to 3" | "1, 2, 3" | "1\n2\n3" | ✅ PASS |
| "こんにちは" | Japanese response | [actual] | ✅ PASS |
| "List fruits" | Fruit list | [actual] | ✅ PASS |

### GUI Tests
| Test | Result | Notes |
|------|--------|-------|
| Simple prompt | ✅ PASS | Response in ~2s |
| File listing | ✅ PASS | List displayed |
| File read | ✅ PASS | Content shown |

### Performance
- First prompt: ~100s (initialization)
- Subsequent: ~2s (50x improvement confirmed ⚡)

## Conclusion
Response extraction now working correctly. Ready for production.
```

## Acceptance Criteria

Before creating PR:

- [ ] `verify_gemini_tty.py` shows clean_len > 0 for all tests
- [ ] Extracted text is actual response (not UI)
- [ ] GUI displays responses correctly
- [ ] No UI elements in displayed responses
- [ ] Performance maintained (~2s for subsequent prompts)
- [ ] Test results documented in `result/`
- [ ] Debug logs cleaned up (or made conditional)

## PR Checklist

When creating PR:

- [ ] Branch: `fix/clean-response-extraction`
- [ ] Title: "fix: Improve response extraction in GeminiRunner (#22)"
- [ ] Description: Link to this instruction file
- [ ] Include test results from `result/2026-02-05_clean-response-fix.md`
- [ ] Update CHANGELOG.md
- [ ] Request review from GenSpark

## Notes

- GenSpark cannot test this (Linux, no Gemini CLI)
- All testing must be done by Local Codex on Windows
- Take time to analyze raw.txt before coding
- Use debug logs liberally
- Test incrementally

## Questions?

If stuck, add comments to Issue #22 with:
- What you tried
- Debug log output
- Specific line from raw.txt that's problematic

GenSpark will analyze and provide guidance via Issue comments.
