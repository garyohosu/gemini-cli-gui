#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gemini_file_client import GeminiFileClient

def main():
    print("Verifying 'Say hello'...")
    client = GeminiFileClient()
    response = client.send_prompt("Say hello", timeout=120)
    
    if response.success:
        print(f"SUCCESS: {response.elapsed_seconds:.2f}s")
        print("-" * 20)
        print(response.response_text)
        print("-" * 20)
        return 0
    else:
        print(f"FAILED: {response.error}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
