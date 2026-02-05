## Repository Instructions

- Read this file before making changes.
- If you make any change to the repository (code or docs), append a brief entry to `CHANGELOG.md`.
- Keep entries concise and dated (YYYY-MM-DD).
- Save task instructions as Markdown files in the `instructions` folder.
- Output execution results as Markdown files in the `result` folder.
- Append any additional rules to this file as they arise.
- `instructions/` and `result/` are used to share information between chat AI and CLI agents via GitHub.
- Read `handoff.md` before continuing work on this repository.

## Multi-Agent Collaboration Rules (Added 2026-02-05)

### Agent Roles

This repository is worked on by TWO agents:

1. **GenSpark AI (Remote)** - Linux-based virtual environment
   - Documentation and analysis
   - Architecture design
   - Code review
   - Issue creation and PR management
   - **CANNOT**: Run Windows-specific tools (Gemini CLI, pywinpty, GUI)

2. **Local Codex CLI (Windows)** - User's local Windows machine
   - Windows-specific testing
   - Gemini CLI integration testing
   - GUI application testing
   - Windows environment debugging
   - **CANNOT**: Access during user's offline time

### Collaboration Protocol

#### Communication via GitHub ONLY

**MANDATORY**: All inter-agent communication through Issues and Pull Requests.

```
GenSpark AI creates Issue/PR
       ↓
GitHub (central coordination)
       ↓
Local Codex reads Issue/PR
       ↓
Local Codex implements/tests
       ↓
Local Codex updates PR with results
       ↓
GenSpark AI reviews
```

#### Direct Code Commits = CONFLICT RISK

**DO NOT**:
- ❌ GenSpark: Directly commit code changes to main
- ❌ GenSpark: Make changes that need Windows testing without PR
- ❌ Local Codex: Commit without creating PR
- ❌ Both: Work on same files simultaneously

**DO**:
- ✅ GenSpark: Create Issues for problems
- ✅ GenSpark: Create PRs with proposed solutions (docs/analysis)
- ✅ Local Codex: Create PRs for Windows-tested implementations
- ✅ Both: Comment on Issues/PRs for coordination
- ✅ Both: Merge only after review and approval

#### Issue Creation Guidelines

**GenSpark AI** creates issues for:
- Bugs discovered during analysis
- Feature requests from user
- Architecture improvements needed
- Documentation gaps

**Local Codex** creates issues for:
- Windows-specific bugs found during testing
- Environment-specific problems
- Test failures that need investigation

**Issue Template**:
```markdown
## Problem
Clear description of the issue

## Environment
- Agent: GenSpark AI / Local Codex
- OS: Linux / Windows
- Tested: Yes/No

## Steps to Reproduce
1. ...
2. ...

## Expected vs Actual
Expected: ...
Actual: ...

## Proposed Solution
(If known)

## Assignment
@local-codex / @genspark-ai
```

#### Pull Request Guidelines

**Before Creating PR**:
1. Create branch: `type/description` (e.g., `fix/empty-response`)
2. Make changes
3. **TEST THOROUGHLY** (mandatory)
4. Document test results in `result/` folder
5. Commit with clear message
6. Push to remote
7. Create PR

**PR Template**:
```markdown
## Summary
Brief description of changes

## Testing Done
- [ ] CLI standalone tested
- [ ] Server endpoint tested
- [ ] GUI tested (if applicable)
- [ ] Test results documented in result/

## Environment
- Tested on: Windows / Linux
- Agent: GenSpark AI / Local Codex

## Review Needed
What should reviewer check?

## Related Issue
Fixes #X
```

### Responsibility Matrix

| Task | GenSpark AI | Local Codex |
|------|-------------|-------------|
| Windows testing | ❌ Cannot | ✅ Must do |
| Gemini CLI testing | ❌ Cannot | ✅ Must do |
| GUI testing | ❌ Cannot | ✅ Must do |
| pywinpty testing | ❌ Cannot | ✅ Must do |
| Documentation | ✅ Primary | ✅ Can assist |
| Issue creation | ✅ Yes | ✅ Yes |
| PR creation | ✅ Yes | ✅ Yes |
| Architecture design | ✅ Primary | ✅ Can review |
| Code review | ✅ Yes | ✅ Yes |
| Linux testing | ✅ Can do | ❌ Cannot |

### Current Division of Work

**GenSpark AI (This Agent)**:
- ✅ Create issues for bugs/features
- ✅ Create documentation PRs
- ✅ Analyze problems and propose solutions
- ✅ Review Local Codex's PRs
- ✅ Update AGENTS.md, CHANGELOG.md
- ❌ **CANNOT test Gemini CLI** (not installed in Linux sandbox)
- ❌ **CANNOT run GUI** (no Windows environment)
- ❌ **CANNOT install pywinpty** (Windows-only)

**Local Codex (Windows Agent)**:
- ✅ Test Gemini CLI integration
- ✅ Run GUI application and test all features
- ✅ Test pywinpty-based solutions
- ✅ Create PRs with tested implementations
- ✅ Document Windows-specific test results
- ⚠️ **May be offline** when user is not at computer

### Conflict Prevention

#### Scenario 1: GenSpark proposes fix, Local Codex implements

1. **GenSpark**: Create Issue with detailed analysis
2. **GenSpark**: Create PR with proposed code (mark as "needs Windows testing")
3. **Local Codex**: Read Issue/PR
4. **Local Codex**: Checkout PR branch
5. **Local Codex**: Test on Windows
6. **Local Codex**: If works: Approve PR + add test results
7. **Local Codex**: If fails: Comment on PR with findings + propose fix
8. **Either**: Merge after both approve

#### Scenario 2: Local Codex implements feature

1. **Local Codex**: Create Issue describing what will be implemented
2. **Local Codex**: Create branch and implement
3. **Local Codex**: Test thoroughly on Windows
4. **Local Codex**: Document test results in `result/`
5. **Local Codex**: Create PR
6. **GenSpark**: Review code and documentation
7. **GenSpark**: Approve or request changes
8. **Local Codex**: Merge after approval

#### Scenario 3: Conflict detected

If both agents have uncommitted changes:
1. **Stop immediately**
2. **Create Issue**: "Merge conflict detected"
3. **Coordinate via Issue comments**
4. **Agree on who commits first**
5. **Second agent rebases and resolves conflicts**

### Example Workflow: Fixing Empty Response Bug

```
User reports: "Empty responses"
       ↓
GenSpark creates Issue #X: "Empty Response Bug"
       ↓
GenSpark analyzes code, adds investigation steps to Issue
       ↓
GenSpark creates draft PR with proposed fix (NOT TESTED)
       ↓
Local Codex reads Issue #X and PR
       ↓
Local Codex tests Gemini CLI: `gemini -p "test" -o json`
       ↓
Local Codex finds root cause, updates PR with actual fix
       ↓
Local Codex tests: CLI → Server → GUI (all pass)
       ↓
Local Codex documents results in result/2026-02-05-fix-empty-response.md
       ↓
Local Codex updates PR: "Tested and working on Windows"
       ↓
GenSpark reviews code + test results
       ↓
GenSpark approves PR
       ↓
Local Codex merges PR
       ↓
Issue #X closed
```

## Summary

**Key Points**:
1. 🌐 GenSpark = Linux/Documentation, Codex = Windows/Testing
2. 📝 All coordination via Issues and PRs
3. 🚫 No direct commits without PR
4. ✅ Always test before merging
5. 📋 Document test results in `result/`

**Golden Rule**: When in doubt, create an Issue first.

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
