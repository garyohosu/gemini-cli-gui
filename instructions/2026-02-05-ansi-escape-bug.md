# Bug Report: ANSI Escape Sequences in GeminiRunner Output

**Date**: 2026-02-05  
**Reporter**: User testing  
**Severity**: High - Response content not visible  
**Status**: Identified

## Problem Description

After implementing the persistent Gemini CLI process using `pywinpty` (`core/gemini_runner.py`), the GUI displays raw ANSI escape sequences and terminal formatting instead of clean text responses.

### Observed Output

```
[12:25:44] [SYS] [?u]11;?\[>q[>4;?m[c[?2004h]0;◇ Ready (temp)  
███ █████████ ██████████ ██████ ██████ █████ ██████ █████ █████
░░░███ ███░░░░░███░░███░░░░░█░░██████ ██████ ░░███ ░░██████ ░░███ ░░███
[2K[1A[2K[1A[2K[1A[2K[1A[2K[1A[2K[G
⠋ Waiting for auth... (Press ESC or CTRL+C to cancel)
...
```

**Expected**: Clean text like "こんにちは！何かお手伝いできることはありますか？"

### Test Results

| Request | Response Time | Output Quality |
|---------|---------------|----------------|
| 1st: "こんにちは" | 92s | ❌ ANSI sequences only |
| 2nd: "ファイル一覧" | 2s ⚡ | ❌ ANSI sequences only |
| 3rd: "test1.txt表示" | 2s ⚡ | ❌ ANSI sequences only |

**Performance**: ✅ Excellent (2s after initial warm-up)  
**Output Parsing**: ❌ Broken (ANSI sequences not stripped)

## Root Cause Analysis

### Why This Happens

`pywinpty` creates a pseudo-TTY (terminal) to communicate with Gemini CLI. The CLI detects it's running in a terminal and:

1. Enables color output (ANSI color codes)
2. Displays interactive UI elements (spinners, progress bars)
3. Sends cursor control sequences (clear screen, move cursor)
4. Shows ASCII art banner
5. Enables bracketed paste mode and other terminal features

All of these are captured as raw output by `GeminiRunner`.

### Code Location

`core/gemini_runner.py` - Lines where output is captured:

```python
def _read_loop(self) -> None:
    """Background thread that reads from PTY."""
    while self._running:
        try:
            chunk = self._pty.read(timeout=0.1)  # ← Reads raw TTY output
            if chunk:
                with self._lock:
                    self._buffer += chunk  # ← Includes ALL ANSI codes
        except Exception:
            pass
```

### ANSI Escape Sequences Found

The output contains:

1. **Cursor control**:
   - `[2K` - Clear line
   - `[1A` - Move cursor up
   - `[?25l` / `[?25h` - Hide/show cursor

2. **Color codes**:
   - `[>q` - Set cursor style
   - `[?u]` - Unknown terminal query

3. **Bracketed paste mode**:
   - `[?2004h` - Enable bracketed paste

4. **UI elements**:
   - Spinner characters: ⠋⠙⠹⠸⠼⠴⠦⠧⠇
   - Box drawing: ╭─╮│╰─╯
   - Progress bars

5. **Window title**:
   - `]0;◇ Ready (temp) `

## Impact

- **Severity**: High - Users cannot read responses
- **Functionality**: Core feature (viewing AI responses) is broken
- **Performance**: Excellent (side effect of fix)
- **User Experience**: Completely unusable in current state

## Proposed Solutions

### Solution A: Strip ANSI Escape Sequences (Recommended)

Use regex to remove ANSI codes from output before displaying:

```python
import re

def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text."""
    # Remove ANSI escape codes
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    text = ansi_escape.sub('', text)
    
    # Remove OSC sequences (window title, etc.)
    osc_escape = re.compile(r'\x1B\][^\x07]*\x07')
    text = osc_escape.sub('', text)
    
    # Remove other control characters
    text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)
    
    return text
```

Apply in `GeminiRunner.send_prompt()` or when displaying in GUI.

**Pros**:
- Simple to implement
- Preserves all functionality
- Standard approach for terminal output parsing

**Cons**:
- May need refinement for edge cases

### Solution B: Force Non-Interactive Mode

Try to disable TTY features by setting environment variables:

```python
import os

os.environ['TERM'] = 'dumb'  # Disable advanced terminal features
os.environ['NO_COLOR'] = '1'  # Disable color output
os.environ['GEMINI_NO_INTERACTIVE'] = '1'  # If supported
```

**Pros**:
- Prevents ANSI codes at source

**Cons**:
- May not work (Gemini CLI might not respect these)
- Less control over output

### Solution C: Parse JSON Output Mode

If Gemini CLI supports JSON output in interactive mode:

```python
# Try to use JSON output in persistent mode
self._pty.write('--output-format json\r\n')
```

Then parse JSON responses instead of raw text.

**Pros**:
- Structured output
- No parsing needed

**Cons**:
- May not be supported in interactive mode
- More complex implementation

### Solution D: Hybrid Approach (Use -o json flag)

Switch back to subprocess mode with `-o json` but keep process warm using a pool:

```python
# Keep a pool of ready processes
process_pool = []

def get_ready_process():
    if not process_pool:
        # Spawn new process with -o json
        proc = subprocess.Popen(['gemini', '-o', 'json', ...])
    return process_pool.pop()
```

**Pros**:
- Clean JSON output
- No ANSI parsing needed

**Cons**:
- Loses speed benefit of persistent mode
- More complex process management

## Recommended Solution

**Solution A** is recommended because:

1. **Simple**: Single regex function
2. **Effective**: Standard approach for terminal output
3. **Fast**: Preserves 2-second response time
4. **Maintainable**: Well-understood pattern

## Implementation Plan

### Step 1: Add ANSI stripping function

In `core/gemini_runner.py`:

```python
import re

def strip_ansi_codes(text: str) -> str:
    """Remove ANSI escape sequences and control characters."""
    # ANSI escape sequences
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    text = ansi_escape.sub('', text)
    
    # OSC sequences (operating system commands)
    osc_escape = re.compile(r'\x1B\].*?(?:\x07|\x1B\\)')
    text = osc_escape.sub('', text)
    
    # CSI sequences (control sequence introducer)
    csi_escape = re.compile(r'\x1B\[.*?[@-~]')
    text = csi_escape.sub('', text)
    
    # Other control characters (except newline, tab)
    control_chars = re.compile(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F-\x9F]')
    text = control_chars.sub('', text)
    
    return text
```

### Step 2: Apply stripping in send_prompt

```python
def send_prompt(self, prompt: str, timeout_sec: float = 180.0) -> GeminiResponse:
    # ... existing code ...
    
    # Strip ANSI codes from response
    raw_response = self._extract_response()
    clean_response = strip_ansi_codes(raw_response)
    
    return GeminiResponse(
        text=clean_response,  # ← Use cleaned text
        elapsed_ms=elapsed_ms,
        success=True
    )
```

### Step 3: Test with various prompts

```
Test 1: Simple greeting
Test 2: File operations
Test 3: Multi-line responses
Test 4: Code blocks
Test 5: Japanese text
```

## Testing Checklist

- [ ] Simple text responses display correctly
- [ ] File listings are readable
- [ ] Multi-line responses preserved
- [ ] Code blocks formatted properly
- [ ] Japanese/Unicode text intact
- [ ] No leftover ANSI artifacts
- [ ] Performance still ~2 seconds (not regressed)
- [ ] Box drawing and emoji removed

## Alternative: Immediate Workaround

While implementing the fix, users can try:

1. **Check logs**: ANSI codes might be stripped in logs
2. **Use different terminal**: Some terminals auto-strip
3. **Manual parsing**: Copy output and manually remove codes

## Performance Note

✅ **Side Benefit Confirmed**: Persistent mode achieved **50x speed improvement**!

- Before: ~98 seconds per request
- After (2nd+ request): **~2 seconds** ⚡

This is a massive win once the ANSI stripping is implemented.

## Related Files

- `core/gemini_runner.py` - Main implementation
- `app.py` - GUI integration
- Regex patterns: Standard ANSI escape code removal

## References

- ANSI escape codes: https://en.wikipedia.org/wiki/ANSI_escape_code
- Regex patterns: https://stackoverflow.com/questions/14693701/how-can-i-remove-the-ansi-escape-sequences-from-a-string-in-python
- Terminal control sequences: https://invisible-island.net/xterm/ctlseqs/ctlseqs.html

## User Impact

Once fixed:
- ✅ 50x faster responses (2s vs 98s)
- ✅ Clean, readable output
- ✅ All functionality working
- ✅ Ready for v0.2.0 release
