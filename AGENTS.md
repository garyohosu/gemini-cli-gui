## Repository Instructions

- Read this file before making changes.
- If you make any change to the repository (code or docs), append a brief entry to `CHANGELOG.md`.
- Keep entries concise and dated (YYYY-MM-DD).
- Save task instructions as Markdown files in the `instructions` folder.
- Output execution results as Markdown files in the `result` folder.
- Append any additional rules to this file as they arise.
- `instructions/` and `result/` are used to share information between chat AI and CLI agents via GitHub.
- Read `handoff.md` before continuing work on this repository.

## Critical Development Rules (Added 2026-02-05)

### MANDATORY: Test Before User Interaction

**NEVER ask users to test your code. YOU must test it first.**

#### Testing Requirements for All Code Changes

1. **CLI/Server Changes**: Test standalone before GUI integration
   ```bash
   # Example for Gemini server:
   cd /path/to/project
   node server/gemini_server.js &
   curl -X POST http://localhost:9876/prompt/start \
     -H "Content-Type: application/json" \
     -d '{"prompt":"こんにちは","workingDir":"C:/temp"}'
   # Verify response has actual content, not empty string
   ```

2. **Python Changes**: Test with unit tests or standalone scripts
   ```bash
   python -m pytest tests/
   # OR
   python core/your_module.py  # If has __main__ block
   ```

3. **GUI Changes**: Run the app yourself and verify:
   ```bash
   py app.py
   # Test all modified features
   # Screenshot or log the results
   ```

#### What to Test

- ✅ **Positive cases**: Normal inputs work correctly
- ✅ **Edge cases**: Empty input, special characters, long text
- ✅ **Error cases**: Invalid input, timeout, network errors
- ✅ **Performance**: Measure actual response times
- ✅ **Output quality**: Verify content is readable and complete

#### Documentation of Test Results

Save test results in `result/YYYY-MM-DD-test-{feature}.md`:
```markdown
# Test Results: Feature Name

Date: YYYY-MM-DD
Tested by: AI Agent Name

## Test Cases
1. Test case 1: PASS/FAIL
   - Input: ...
   - Expected: ...
   - Actual: ...
   
2. Test case 2: PASS/FAIL
   ...

## Conclusion
All tests passed. Ready for user testing.
OR
Tests failed. Need to fix X, Y, Z.
```

### User's Role

**Users are product owners, not QA testers.**

- Users provide requirements and feedback
- Users do final acceptance testing (after AI testing)
- Users should NEVER be the first to discover bugs

### Violation Consequences

If you ask users to test without testing yourself:
1. User will be frustrated (wasted time)
2. Trust in AI assistance decreases
3. Development velocity slows down

**"人間を働かせるな" - Don't make humans do your work.**

### Exception: User Feedback

After YOU have tested and confirmed it works:
- ✅ "I've tested this and it works. Could you verify it meets your needs?"
- ❌ "Please test this and let me know if it works."

## Summary

**Test first, then present. Not the other way around.**
