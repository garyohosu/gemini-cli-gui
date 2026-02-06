# URGENT: Git Pull Required

**For**: Local Codex  
**Date**: 2026-02-05

## Problem

You're looking for `instructions/2026-02-05_EXECUTE_THIS.md` but it's not in your local directory.

**Reason**: The file is on remote branch `fix/clean-response-extraction` but you haven't pulled it yet.

## Solution

Run these commands:

```bash
git fetch origin
git checkout fix/clean-response-extraction
git pull
```

## Verification

After pulling, verify the file exists:

```bash
Test-Path instructions\2026-02-05_EXECUTE_THIS.md
# Should return: True

# Or list all instruction files:
ls instructions\2026-02-05*.md
```

## Then Execute

Once you see the file, execute it:

```bash
# Read the instructions
cat instructions\2026-02-05_EXECUTE_THIS.md

# Or open in editor
code instructions\2026-02-05_EXECUTE_THIS.md
```

Follow the 8 steps in that file.

## Quick Check - What Branch Are You On?

```bash
git branch --show-current
```

**Expected**: `fix/clean-response-extraction`  
**If different**: Run the git commands above

---

**TL;DR**: Run `git pull`, then look for the file again.
