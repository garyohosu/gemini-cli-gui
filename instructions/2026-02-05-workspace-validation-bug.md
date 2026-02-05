# Bug Report: Workspace Validation Error (HTTP 400)

**Date**: 2026-02-05  
**Reporter**: User  
**Severity**: High  
**Status**: Identified

## Problem Description

When using the Gemini CLI GUI Wrapper application, users encounter an **HTTP Error 400: Bad Request** when trying to send a message after selecting a workspace.

### Error Log
```
[10:26:51] [SYS] Gemini サーバーを起動しています...
[10:27:10] [SYS] ワークスペースを設定しました: C:/temp
[10:27:22] [SYS] サーバー準備完了
[10:27:32] [YOU] こんにちは
[10:27:32] [ERR] エラー: HTTP Error 400: Bad Request
```

## Root Cause Analysis

The issue is in `server/gemini_server.js`, specifically in the `resolveWorkingDir()` function (lines 23-38).

### Current Implementation

```javascript
const WORKSPACE_ROOT = path.resolve(process.env.GEMINI_WORKSPACE_ROOT || process.cwd());

function resolveWorkingDir(requestedDir) {
  const resolved = path.resolve(requestedDir || WORKSPACE_ROOT);
  const rel = path.relative(WORKSPACE_ROOT, resolved);
  const isInside =
    rel && !rel.startsWith('..') && !path.isAbsolute(rel);

  if (!isInside && resolved !== WORKSPACE_ROOT) {
    return null;  // Returns null → 400 Bad Request
  }

  if (!fs.existsSync(resolved) || !fs.statSync(resolved).isDirectory()) {
    return null;
  }

  return resolved;
}
```

### Why It Fails

1. **Server starts** without `GEMINI_WORKSPACE_ROOT` environment variable set
2. `WORKSPACE_ROOT` defaults to `process.cwd()` (e.g., `C:/Users/user/gemini-cli-gui`)
3. **User selects workspace** via GUI: `C:/temp`
4. GUI sends POST to `/prompt/start` with `workingDir: "C:/temp"`
5. `resolveWorkingDir("C:/temp")` checks if `C:/temp` is inside `C:/Users/user/gemini-cli-gui`
6. **Check fails** → returns `null`
7. Server responds with **400 Bad Request** (line 175-177)

### Code Path

```javascript
// In startPrompt() function (line 173-178)
const cwd = resolveWorkingDir(workingDir);
if (!cwd) {
  res.writeHead(400, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ error: 'Invalid workingDir' }));
  return;
}
```

## Impact

- **Severity**: High - Application is completely unusable
- **Affected Users**: All users who select a workspace different from server's `process.cwd()`
- **Workaround**: None (unless user manually sets `GEMINI_WORKSPACE_ROOT` env var before starting)

## Expected Behavior

The application should allow users to freely select any valid workspace directory through the GUI, regardless of where the server was started.

## Proposed Solutions

### Option A: Remove Workspace Root Restriction (Recommended for GUI app)

Since this is a GUI application where users explicitly select workspaces via folder dialog:

```javascript
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

**Pros**: 
- Simple and direct
- Matches user expectations for GUI application
- Users already have OS-level folder selection dialog

**Cons**: 
- Less restrictive (but security is already delegated to OS folder picker)

### Option B: Dynamic Workspace Root Update

Allow GUI to update `WORKSPACE_ROOT` when workspace is selected:

```javascript
let WORKSPACE_ROOT = path.resolve(process.env.GEMINI_WORKSPACE_ROOT || process.cwd());

// Add new endpoint POST /workspace/set
if (req.url === '/workspace/set' && req.method === 'POST') {
  const body = await parseBody(req);
  const { workspaceRoot } = body;
  
  const resolved = path.resolve(workspaceRoot);
  if (fs.existsSync(resolved) && fs.statSync(resolved).isDirectory()) {
    WORKSPACE_ROOT = resolved;
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ success: true, workspaceRoot: WORKSPACE_ROOT }));
    return;
  }
  
  res.writeHead(400, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ error: 'Invalid workspace path' }));
  return;
}
```

Then update `app.py` to call this endpoint when workspace is selected.

**Pros**: 
- Maintains security concept of "workspace root"
- More explicit workspace management

**Cons**: 
- More complex
- Requires changes to both frontend and backend

### Option C: Accept Workspace Root via Environment Variable in GUI

Update `app.py` to pass `GEMINI_WORKSPACE_ROOT` when starting server:

```python
def _start_server(self) -> None:
    # ... existing code ...
    env = os.environ.copy()
    if self._workspace_root:
        env['GEMINI_WORKSPACE_ROOT'] = str(self._workspace_root)
    
    self._server_process = subprocess.Popen(
        ["node", "server/gemini_server.js"],
        env=env,
        # ...
    )
```

**Pros**: 
- Maintains workspace root security model
- Uses existing environment variable mechanism

**Cons**: 
- Requires server restart when workspace changes
- More complex UX (need to handle server lifecycle)

## Recommendation

**Option A** is recommended for this GUI application because:
1. Users already interact with OS-level folder selection dialog
2. Workspace security is handled at OS permission level
3. Simpler implementation with fewer edge cases
4. Matches user mental model for desktop applications

## Related Files

- `server/gemini_server.js` - Server-side validation logic
- `app.py` - GUI application main file
- `core/workspace_sandbox.py` - Workspace security implementation (separate from server)

## Testing Checklist

- [ ] Start application without `GEMINI_WORKSPACE_ROOT` env var
- [ ] Select workspace via GUI (different from app directory)
- [ ] Send a message and verify it processes successfully
- [ ] Verify workspace sandbox still prevents out-of-workspace operations
- [ ] Test with workspace on different drive (e.g., `D:/projects`)
- [ ] Test with workspace containing spaces in path
- [ ] Test with relative paths
- [ ] Test with invalid/nonexistent paths

## Notes

- The `WorkspaceSandbox` class in `core/workspace_sandbox.py` already handles workspace security on the Python side
- The server-side validation in `gemini_server.js` appears to be redundant for GUI use case
- For CLI/API use cases, workspace root restrictions make sense, but for GUI apps, the OS folder picker provides sufficient security boundary
