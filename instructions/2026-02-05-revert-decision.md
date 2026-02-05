# Decision: Revert to Node.js Server Approach

**Date**: 2026-02-05  
**Decision by**: Claude Code (local)  
**Status**: Recommended

## Context

After implementing persistent Gemini CLI using pywinpty (PR #17, commits 00f842e, 006f8fe), user testing revealed:

✅ **Performance**: Excellent (2s after warm-up)  
❌ **Output**: ANSI escape sequences - unreadable (Issue #19)

Claude Code analysis:
> pywinptyでgemini CLIの出力を取得できていません。geminiはNode.jsアプリケーションなので、cmd.exe経由では複雑な問題があります。

## The Problem with pywinpty Approach

### Technical Issues
1. **Gemini CLI is a Node.js application**
   - Not a native command-line tool
   - Runs Node.js → spawns another process internally
   - Complex process tree: Python → pywinpty → cmd.exe → Node.js → Gemini CLI

2. **Output Capture Complexity**
   - pywinpty captures raw TTY output
   - ANSI escape sequences everywhere
   - Spinner animations, progress bars, ASCII art
   - Difficult to parse reliably

3. **Architecture Mismatch**
   - pywinpty designed for native terminal apps
   - Gemini CLI is a wrapped Node.js app
   - Impedance mismatch causes issues

## Claude Code's Insight

> 2回目以降の応答は既にキャッシュ/ウォームアップの効果でNode.jsサーバーも速くなっているはずです。

**This is likely correct!** The original Node.js server approach may already benefit from:
- Node.js JIT compilation warm-up
- Module caching
- Network connection reuse
- API token caching

## Recommendation: Revert to Node.js Server

### Reasons
1. **Simplicity**: Proven architecture, already working
2. **Reliability**: Clean JSON output, no ANSI parsing needed
3. **Performance**: May already have warm-up benefits
4. **Maintainability**: Simpler to debug and extend

### Original Architecture (Proven)
```
GUI (Python) → HTTP POST → Node.js Server → subprocess → Gemini CLI → JSON output
```

**Benefits**:
- Clean JSON responses
- HTTP error handling
- Request/response IDs
- Cancel support
- No ANSI issues

### What to Revert
- Remove `core/gemini_runner.py`
- Restore original `app.py` (use GeminiClient with HTTP)
- Keep `server/gemini_server.js` improvements (workspace validation fix)

## Performance Expectations

### Baseline (M0 verification)
- Call 1: 29.17s
- Call 2: 31.76s
- Call 3: 33.27s

### Expected after Revert
- 1st call: ~30s (acceptable)
- 2nd+ calls: Potentially faster due to warm-up (need to measure)

If warm-up doesn't help significantly, **~30s is still acceptable** for an initial release. Better than:
- 98s (before pywinpty)
- Unreadable output (pywinpty with ANSI)

## Alternative if Performance Still Issue

If Node.js server is still too slow after revert, consider:

### Option: Keep Node.js Server Warm
Instead of persistent Gemini CLI process, keep Node.js server with:
- Process pooling
- Connection keep-alive
- Gemini CLI session reuse (if CLI supports it)

This is **much simpler** than pywinpty approach.

## Testing Plan After Revert

1. Revert pywinpty commits
2. Test 1st request: expect ~30s
3. Test 2nd request immediately after: measure time
4. Test 3rd request: measure time
5. Document warm-up effect if any

## Acceptance Criteria

After revert, system should:
- ✅ Display clean, readable responses
- ✅ Complete requests in reasonable time (~30-60s)
- ✅ Handle errors gracefully
- ✅ Support all existing features (cancel, workspace, etc.)

## User Impact

**Short term**: 
- Responses readable again
- Slight performance regression (2s → 30s)
- But still better than original 98s

**Long term**:
- More reliable foundation
- Easier to optimize incrementally
- Better user experience overall

## Decision

**Recommendation**: ✅ **Revert to Node.js server approach**

Reasons:
1. Proven architecture
2. Clean output
3. Simpler maintenance
4. Acceptable performance (~30s)
5. Can optimize later if needed

The pywinpty experiment showed that dramatic speed improvements are possible, but the complexity cost is too high. Better to have a slower but reliable system than a fast but broken one.

## Implementation Steps

1. Create new branch: `revert/pywinpty-approach`
2. Revert commits 00f842e and 006f8fe
3. Test thoroughly
4. Update documentation
5. Merge to main
6. Close Issue #19 as "won't fix - reverted approach"
7. Update Issue #17 with new performance baseline

## Conclusion

Sometimes the simple solution is the right solution. The Node.js server approach may not be the fastest, but it's:
- **Reliable**
- **Maintainable**  
- **Good enough**

We can always optimize later if needed, but we need a working foundation first.

---

**Status**: Awaiting user confirmation to proceed with revert.
