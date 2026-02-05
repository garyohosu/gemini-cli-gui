## Repository Instructions

- Read this file before making changes.
- If you make any change to the repository (code or docs), append a brief entry to `CHANGELOG.md`.
- Keep entries concise and dated (YYYY-MM-DD).
- Save task instructions as Markdown files in the `instructions` folder.
- Output execution results as Markdown files in the `result` folder.
- Append any additional rules to this file as they arise.
- `instructions/` and `result/` are used to share information between chat AI and CLI agents via GitHub.
- Read `handoff.md` before continuing work on this repository.

## MANDATORY: CLI Verification First

**Rule**: AI agents MUST verify with CLI apps BEFORE GUI integration.

### Why CLI First?

1. **Measurable**: 動作時間を正確に計測できる
2. **Observable**: 表示内容を直接確認できる
3. **Repeatable**: 何度でも自動テスト可能
4. **Debuggable**: ログ出力で問題を特定しやすい
5. **Fast feedback**: GUI起動不要で高速検証

### Required Steps

1. **Create CLI verification app** (`scripts/verify_*.py`)
2. **Run it yourself** - Don't ask user to test
3. **Measure performance** - Elapsed time, memory, etc.
4. **Verify output** - Check displayed content is correct
5. **Test multiple scenarios** - Positive, edge, error cases
6. **Document results** (`result/2026-02-05_*.md`)
7. **Only then integrate with GUI**
8. **Ask user for final verification** - Not for debugging

### 人間を働かせるな

- ❌ Don't make users do your testing
- ❌ Don't ask users to debug output
- ❌ Don't integrate untested code
- ✅ Test everything with CLI first
- ✅ Verify performance yourself
- ✅ Document all test results
- ✅ Present working solution to user

**Reference**: `instructions/2026-02-05_CLI_VERIFICATION_FIRST.md` for detailed workflow
