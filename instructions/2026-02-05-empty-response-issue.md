# Issue: Empty Response from Gemini CLI

**Date**: 2026-02-05  
**Reported by**: User testing  
**Current Branch**: Unknown (reverted from pywinpty)  
**Severity**: Critical - No responses displayed

## Problem Description

After reverting from pywinpty approach back to Node.js server approach, the GUI receives responses but they are **empty**.

### Observed Behavior

```
[13:31:57] [YOU] こんにちは
[13:31:57] [SYS] Gemini が応答中です... (requestId=1de54b19-cad7-4313-a319-01a8eb30e422)
[13:32:03] [SYS] { "requestId": "35b56dfd-b9e1-4047-ba4a-8cff662e4009", "success": true, "response": { "response": "" }, "elapsed": 5580 }
```

**Key observations**:
1. ✅ Server responds quickly (~6 seconds)
2. ✅ Request completes successfully (`"success": true`)
3. ❌ Response is empty (`"response": ""`)
4. ❌ User receives no actual content

### Test Results

| Request | Response Time | Content | Status |
|---------|--------------|---------|--------|
| "こんにちは" | 6s | Empty | ❌ FAIL |
| "ファイル一覧を下さい" | Interrupted | - | ❌ FAIL |
| "こんにちは" (retry) | 6s | Empty | ❌ FAIL |

## Root Cause Analysis

### Hypothesis 1: Gemini CLI Output Not Captured

The Node.js server is spawning Gemini CLI but not capturing its stdout correctly.

**Evidence**:
- Response structure exists but content is empty
- No error messages
- Quick response time suggests CLI isn't actually running

### Hypothesis 2: JSON Parsing Issue

The server is looking for JSON output but Gemini CLI is outputting something else.

**Possible causes**:
- Missing `-o json` flag
- CLI outputting interactive mode content
- Output buffering issues

### Hypothesis 3: Working Directory Issue

Similar to Issue #14, workspace validation might be blocking execution.

**Check**:
- Is `resolveWorkingDir()` still enforcing restrictions?
- Was the fix in PR #16 reverted?

## Investigation Steps

### Step 1: Test Gemini CLI Directly

```bash
# Test if Gemini CLI works at all
cd C:/temp
gemini -p "こんにちは" -o json

# Expected: JSON with response content
# If this fails, Gemini CLI itself has issues
```

### Step 2: Test Server Endpoint Directly

```bash
# Start server
cd C:/PROJECT/gemini-cli-gui
node server/gemini_server.js

# In another terminal:
curl -X POST http://localhost:9876/prompt/start \
  -H "Content-Type: application/json" \
  -d "{\"prompt\":\"こんにちは\",\"workingDir\":\"C:/temp\",\"timeoutMs\":60000}"

# Check response:
# - Is requestId returned?
# - Poll /prompt/result?requestId={id}
# - Does result contain actual response text?
```

### Step 3: Check Server Logs

```bash
# Run server with debug output
cd C:/PROJECT/gemini-cli-gui
node server/gemini_server.js

# Look for:
# - "Received prompt: ..." message
# - Gemini CLI spawn command
# - stdout/stderr output
# - JSON parsing attempts
```

### Step 4: Review Recent Changes

```bash
git log --oneline -10
git diff HEAD~5..HEAD server/gemini_server.js
```

Look for:
- Changes to subprocess spawning
- Output capture logic
- JSON parsing
- Response formatting

## Code to Review

### `server/gemini_server.js`

Lines to check:
- `startPrompt()` function - How CLI is spawned
- `child.stdout.on('data')` - Output capture
- JSON parsing logic
- Response payload construction

### Expected Flow

```javascript
// Should be something like:
const child = spawn('gemini', ['-p', prompt, '-o', 'json', '-y'], {
  cwd: workingDir,
  shell: true
});

let stdout = '';
child.stdout.on('data', data => {
  stdout += data;
});

child.on('close', code => {
  const response = JSON.parse(stdout); // ← Is this working?
  // ...
});
```

## Quick Fix Checklist

- [ ] Verify `-o json` flag is passed to Gemini CLI
- [ ] Verify stdout is being captured (not just stderr)
- [ ] Check if output is being buffered and needs flushing
- [ ] Verify JSON.parse isn't failing silently
- [ ] Check if workspace validation is blocking execution
- [ ] Test Gemini CLI standalone to confirm it works

## Testing Requirements for Fix

**Before presenting to user, AI must test**:

1. ✅ Direct CLI test: `gemini -p "test" -o json` returns content
2. ✅ Server endpoint test: curl returns non-empty response
3. ✅ GUI test: py app.py shows actual response text
4. ✅ Multiple prompts: Test 3 different prompts
5. ✅ Error cases: Test with invalid workspace, timeout

**Document results in**: `result/2026-02-05-empty-response-fix.md`

## User Expectation

> "後GUIで試す前にCLIで自分で単体で動作確認してねと伝えて。人間を働かせるなと強くAgents.mdに書いておいて。"

**Translation**: "Please test CLI standalone before GUI testing. Tell them not to make humans do the work. Write this strongly in AGENTS.md."

**AI must**: Test thoroughly before asking user to verify.

## Related Issues

- Issue #14: HTTP 400 workspace validation (fixed)
- Issue #17: Performance (2min → pywinpty 2s → reverted → now 6s)
- Issue #19: ANSI sequences (pywinpty approach)

## Current Status

- ❌ Broken: Empty responses
- ⚠️ Needs: Proper testing by AI agent
- 📝 Action: AI must debug and test before user tries again

## Notes for AI Agent

**DO NOT**:
- ❌ Ask user to test without testing yourself first
- ❌ Make code changes blindly
- ❌ Assume it works without verification

**DO**:
- ✅ Test CLI standalone
- ✅ Test server endpoints
- ✅ Test GUI integration
- ✅ Document test results
- ✅ Only then present working solution to user

**Remember**: "人間を働かせるな" - Don't make humans do your work.
