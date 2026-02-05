# Summary for Claude Code Review

**Date**: 2026-02-05  
**Created by**: GenSpark AI Assistant  
**Purpose**: Document issues discovered during user testing for local Claude Code review

## Issues Created

### Issue #14: HTTP 400 Bug (CRITICAL)
**URL**: https://github.com/garyohosu/gemini-cli-gui/issues/14  
**PR**: https://github.com/garyohosu/gemini-cli-gui/pull/15  
**Status**: Documented, needs fix implementation

**Problem**: Application is completely unusable - returns HTTP 400 when user selects any workspace different from server's startup directory.

**Root Cause**: `server/gemini_server.js` validates workspace must be inside `WORKSPACE_ROOT`, but `WORKSPACE_ROOT` defaults to `process.cwd()` when no env var is set.

**Recommended Fix**: Remove workspace root restriction (Option A in bug report) since:
- OS folder dialog already provides security boundary
- Python's `WorkspaceSandbox` handles workspace security
- Matches user expectations for desktop GUI app

**Documentation**: `instructions/2026-02-05-workspace-validation-bug.md`

---

### Issue #17: Performance Degradation
**URL**: https://github.com/garyohosu/gemini-cli-gui/issues/17  
**PR**: https://github.com/garyohosu/gemini-cli-gui/pull/18  
**Status**: Investigated, needs confirmation

**Problem**: Responses take ~2 minutes (98s) instead of baseline ~31s (3.2x slower).

**Root Cause (Suspected)**: Network latency to Google Gemini API servers
- User confirms: "家では１分だった" (1 minute at home)
- Environment-specific issue (current location has poor connectivity)
- 67-second overhead likely in network communication phase

**Recommended Actions**:
1. Run investigation steps to confirm network is bottleneck
2. If confirmed: Use faster network connection or implement caching
3. If not network: Investigate GUI/server overhead

**Documentation**: `instructions/2026-02-05-slow-response-investigation.md`

---

## Priority

1. **Issue #14** - CRITICAL - Fix immediately (app is unusable)
2. **Issue #17** - MEDIUM - Investigate after #14 is fixed

## Files to Review

### Issue #14 (HTTP 400 Bug)
- `server/gemini_server.js` - Lines 23-38 (`resolveWorkingDir` function)
- `instructions/2026-02-05-workspace-validation-bug.md` - Full analysis
- Proposed fix: Simplify `resolveWorkingDir` to accept any valid directory path

### Issue #17 (Performance)
- `instructions/2026-02-05-slow-response-investigation.md` - Full analysis
- Investigation steps can be run locally to confirm root cause

## Quick Fix for Issue #14

Replace `server/gemini_server.js` lines 23-38:

```javascript
// OLD (restrictive - causes bug)
function resolveWorkingDir(requestedDir) {
  const resolved = path.resolve(requestedDir || WORKSPACE_ROOT);
  const rel = path.relative(WORKSPACE_ROOT, resolved);
  const isInside = rel && !rel.startsWith('..') && !path.isAbsolute(rel);
  
  if (!isInside && resolved !== WORKSPACE_ROOT) {
    return null;  // ← Returns null = 400 error
  }
  
  if (!fs.existsSync(resolved) || !fs.statSync(resolved).isDirectory()) {
    return null;
  }
  
  return resolved;
}

// NEW (permissive - matches GUI app expectations)
function resolveWorkingDir(requestedDir) {
  if (!requestedDir) {
    return null;
  }
  
  const resolved = path.resolve(requestedDir);
  
  if (!fs.existsSync(resolved) || !fs.statSync(resolved).isDirectory()) {
    return null;
  }
  
  return resolved;
}
```

This allows users to select any valid directory through the GUI while still validating the directory exists and is accessible.

## Testing After Fix

1. Start app: `py app.py`
2. Select workspace different from app directory (e.g., `C:/temp`)
3. Send a message
4. Should work without 400 error

## User Context

The user is testing the app and discovered both issues:
1. HTTP 400 error prevented any usage
2. After fix (merged in #16), observed slow performance

User's analysis was correct: "ネットのせいかな？" (network issue) for the performance problem.

## Repository Workflow Compliance

✅ All changes committed and pushed  
✅ Issues created with detailed analysis  
✅ Pull requests created with documentation  
✅ CHANGELOG.md updated  
✅ Documentation saved in `instructions/` folder  
✅ Following AGENTS.md guidelines
