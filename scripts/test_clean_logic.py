
import sys
from pathlib import Path
import re
import logging
import io

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from core.gemini_runner import GeminiRunner

def test_clean():
    log_stream = io.StringIO()
    logging.basicConfig(level=logging.DEBUG, stream=log_stream, format='%(message)s')
    
    runner = GeminiRunner(working_dir=Path("."))
    
    # Try multiple raw files
    raw_files = [
        "result/2026-02-05_pyte_fix_raw.txt",
        "result/2026-02-05_clean-response-fix_raw.txt"
    ]
    
    for filename in raw_files:
        raw_path = ROOT_DIR / filename
        if not raw_path.exists():
            print(f"File not found: {raw_path}")
            continue

        print(f"\n=== Testing File: {filename} ===")
        with open(raw_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        
        parts = content.split("--- prompt ")
        for part in parts:
            if not part.strip():
                continue
            
            lines = part.split("\n")
            idx_str = lines[0].strip(" -")
            raw_content = "\n".join(lines[1:])
            
            # Search for what prompt it might be
            prompt = "Say hello in one word."
            if "こんにちは" in raw_content or "縺薙ｓ縺ｫ縺｡縺ｯ" in raw_content:
                prompt = "こんにちは"
            elif "Count to 3" in raw_content:
                prompt = "Count to 3"
            elif "List files" in raw_content:
                prompt = "List files"
                
            print(f"\n--- Prompt {idx_str}: '{prompt}' ---")
            log_stream.truncate(0)
            log_stream.seek(0)
            
            cleaned = runner._clean_response(raw_content, prompt)
            print(f"Cleaned output (len={len(cleaned)}):\n{cleaned}")
            # print("Logs:", log_stream.getvalue()) # Uncomment for debugging

if __name__ == "__main__":
    test_clean()
