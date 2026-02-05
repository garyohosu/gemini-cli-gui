# Task Steps (2026-02-05)

1. `git pull`
2. `git checkout fix/clean-response-extraction`
3. Read `instructions/2026-02-05_USE_FILE_OUTPUT.md`
4. Implement:
   - `scripts/run_gemini_to_file.ps1`
   - `core/gemini_file_client.py`
   - `scripts/verify_file_client.py`
5. Run CLI verification: `py scripts\verify_file_client.py`
6. Document results: `result/2026-02-05_file_output_verification.md`
7. If all tests pass, integrate into GUI (`app.py`)
8. Commit and push
