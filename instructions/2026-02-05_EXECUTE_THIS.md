# Task: Implement Response Extraction Fix

**Date**: 2026-02-05  
**For**: Local Codex (Windows)  
**Priority**: HIGH  
**Status**: READY TO EXECUTE

## Quick Answer to Your Question

**Choose Option 2**: 実行したい instructions を具体的に指定

👉 **このファイル（instructions/2026-02-05-fix-clean-response.md）を実行してください**

## Why NOT Option 1 (Revert)

pywinptyのリバートは **不要** です：

- ✅ 2.1秒の高速化は成功している
- ✅ データ取得も成功している
- ❌ 問題は抽出ロジックだけ

**解決策**: リバートではなく、抽出ロジック修正（このタスク）

## Current Status Summary

あなた（Codex）の検証結果から：

```
result/2026-02-05_tty-cli-verification.md:
- Prompt 1: elapsed=104s, raw_len=33082, clean_len=640  ⚠️
- Prompt 2: elapsed=2.1s, raw_len=1836, clean_len=0     ❌
```

**問題**: `_clean_response()` が実際の応答まで削除している

## Your Task (Specific Steps)

### Step 1: Analyze Raw Output (5 min)

```bash
# 既に持っているデータを分析
code result/2026-02-05_tty-raw.txt
```

探すもの:
1. エコーされたプロンプト: `"Say hello in one word."`
2. その直後の行 = 実際の応答（例: `"Hello"`）
3. 応答の終わり（次の `>` や空行）

### Step 2: Add Debug Logging (10 min)

`core/gemini_runner.py` の `_clean_response()` に追加:

```python
import logging

def _clean_response(self, raw: str, sent_prompt: str) -> str:
    """Clean up the response by removing echoed input, prompts, and ANSI codes."""
    
    # ADD THIS DEBUG BLOCK
    logging.basicConfig(level=logging.DEBUG, 
                       format='%(levelname)s: %(message)s')
    logging.debug("=== CLEAN RESPONSE START ===")
    logging.debug(f"Raw length: {len(raw)}")
    logging.debug(f"Sent prompt: {sent_prompt}")
    
    # Existing code
    text = self._strip_ansi_codes(raw)
    logging.debug(f"After ANSI strip: {len(text)} chars")
    logging.debug(f"First 300 chars:\n{text[:300]}")
    
    # ... rest of existing code ...
    
    logging.debug(f"Final result: {result}")
    logging.debug("=== CLEAN RESPONSE END ===")
    
    return result
```

### Step 3: Run Test with Debug (5 min)

```bash
py scripts\verify_gemini_tty.py --prompt "Say hello" --repeat 1 > debug_output.txt 2>&1
```

デバッグログを見て、どこで応答が消えたか確認。

### Step 4: Implement State Machine (15 min)

`_clean_response()` を以下のロジックに置き換え:

```python
def _clean_response(self, raw: str, sent_prompt: str) -> str:
    """Clean up the response by removing echoed input, prompts, and ANSI codes."""
    text = self._strip_ansi_codes(raw)
    lines = text.split("\n")
    
    # State machine
    state = "searching"  # searching → found_prompt → collecting
    response_lines = []
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        if state == "searching":
            # Find echoed prompt
            if sent_prompt.strip() in stripped:
                state = "found_prompt"
                logging.debug(f"Found prompt at line {i}")
                continue
        
        elif state == "found_prompt":
            # Skip empty lines after prompt
            if not stripped:
                continue
            
            # Skip UI patterns
            if self._is_ui_line(stripped):
                logging.debug(f"Skipping UI line: {stripped[:50]}")
                continue
            
            # This is the response start!
            state = "collecting"
            response_lines.append(line.rstrip())
            logging.debug(f"Response starts: {stripped}")
        
        elif state == "collecting":
            # Stop at next prompt
            if stripped in ['>', '›', '»', '*']:
                break
            
            # Skip UI within response
            if self._is_ui_line(stripped):
                continue
            
            response_lines.append(line.rstrip())
    
    result = "\n".join(response_lines).strip()
    result = re.sub(r'\n\n\n+', '\n\n', result)
    
    logging.debug(f"Extracted {len(result)} chars")
    return result
```

### Step 5: Test (10 min)

```bash
# Test 1: Simple
py scripts\verify_gemini_tty.py --prompt "Say hello" --repeat 2

# Test 2: Multi-line
py scripts\verify_gemini_tty.py --prompt "Count to 3" --repeat 1

# Test 3: Japanese
py scripts\verify_gemini_tty.py --prompt "こんにちは" --repeat 1
```

**期待結果**:
- clean_len > 0（ゼロでない）
- 実際の応答テキストが取得できている

### Step 6: Test GUI (5 min)

```bash
py app.py
```

1. ワークスペース選択
2. 「こんにちは」送信
3. 応答が表示されるか確認（2-3秒後）

### Step 7: Document Results (10 min)

`result/2026-02-05_clean-response-fix.md` を作成:

```markdown
# Clean Response Extraction Fix - Test Results

**Date**: 2026-02-05
**Issue**: #22
**Tested by**: Local Codex

## Root Cause
_clean_response() was too aggressive in filtering.
[分析結果を記載]

## Solution
Implemented state machine for extraction.
[変更内容を記載]

## Test Results

### Verification Script
- "Say hello": ✅ PASS - Got "Hello"
- "Count to 3": ✅ PASS - Got "1, 2, 3"
- "こんにちは": ✅ PASS - Got Japanese response

### GUI Test
- ✅ Response displayed in ~2s
- ✅ No UI clutter
- ✅ Clean text only

## Performance
- 2nd+ prompts: ~2s (maintained)

## Conclusion
✅ All tests passed. Ready for production.
```

### Step 8: Commit and Push (2 min)

```bash
git add core/gemini_runner.py
git add result/2026-02-05_clean-response-fix.md
git commit -m "fix: improve response extraction in GeminiRunner

- Implement state machine for response extraction
- Add debug logging for troubleshooting
- Test results documented in result/
- Addresses Issue #22"

git push
```

## Expected Outcome

✅ `verify_gemini_tty.py` shows actual response text  
✅ GUI displays responses correctly  
✅ No more empty responses  
✅ Performance maintained (~2s)

## If You Get Stuck

1. **Can't find response in raw.txt?**
   - Look at lines right after the prompt
   - Try searching for single words like "Hello"

2. **Still getting clean_len=0?**
   - Check debug logs - where does state machine stop?
   - Is `_is_ui_line()` matching too much?

3. **Need help?**
   - Comment on Issue #22 with:
     - Debug log output
     - Specific line numbers from raw.txt
     - What you tried

## Time Estimate

Total: ~60 minutes

## Success Criteria

- [ ] clean_len > 0 in verification script
- [ ] Actual response text extracted
- [ ] GUI shows responses
- [ ] Performance ~2s maintained
- [ ] Results documented in result/

---

**START NOW**: この指示に従って実装してください。

完了したら、ユーザーが `git pull` して `result/2026-02-05_clean-response-fix.md` を確認します。
