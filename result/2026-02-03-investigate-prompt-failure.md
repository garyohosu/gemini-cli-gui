# Investigation Result (2026-02-03)

## Cause
- `/prompt` was failing because the Gemini CLI received **both** `-p` and **positional prompt tokens**. This happens when `spawn` runs with `shell: true` and the prompt contains spaces, causing the prompt to be split into multiple arguments. The CLI then interprets extra tokens as positional prompts, resulting in:
  - `Cannot use both a positional prompt and the --prompt (-p) flag together`

## Evidence
- Stderr from `/prompt`:
  - `Cannot use both a positional prompt and the --prompt (-p) flag together`

## Fix Applied
- Quote the prompt argument on Windows when using `shell: true` so the prompt remains a single argument.
- `server/gemini_server.js` now wraps the prompt in quotes and escapes double-quotes.

## Follow-up
- Re-run with a longer prompt timeout to verify success (outside this environment, 30s+ may be needed).
