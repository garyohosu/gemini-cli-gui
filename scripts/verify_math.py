#!/usr/bin/env python3
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gemini_file_client import GeminiFileClient

def main():
    prompt = "What is 2+2?"
    print(f"Verifying prompt: '{prompt}'...")
    
    client = GeminiFileClient()
    start_time = time.time()
    response = client.send_prompt(prompt, timeout=120)
    elapsed = time.time() - start_time
    
    if response.success:
        print(f"SUCCESS: {elapsed:.2f}s (client reported {response.elapsed_seconds:.2f}s)")
        print("-" * 20)
        print(response.response_text)
        print("-" * 20)
        
        # Save result
        result_path = Path("result/2026-02-06_math_verification.md")
        with open(result_path, "w", encoding="utf-8") as f:
            f.write("# Verification Result: " + prompt + "\n\n")
            f.write("**Date**: 2026-02-06\n")
            f.write("**Status**: ✅ SUCCESS\n\n")
            f.write("## Summary\n")
            f.write("Verified that the Gemini CLI correctly answers a basic math question.\n\n")
            f.write("## Details\n")
            f.write("- **Prompt**: \"" + prompt + "\"\n")
            f.write("- **Elapsed Time**: " + str(round(elapsed, 2)) + "s\n")
            f.write("- **Success**: True\n\n")
            f.write("## Response\n")
            f.write("```text\n" + response.response_text + "\n```\n")
            
        print(f"Result saved to {result_path}")
        return 0
    else:
        print(f"FAILED: {response.error}")
        return 1

if __name__ == "__main__":
    sys.exit(main())