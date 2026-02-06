#!/usr/bin/env python3
"""
CLI verification for GeminiFileClient.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gemini_file_client import GeminiFileClient


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    print("=" * 60)
    print("Gemini File Client Verification")
    print("=" * 60)

    client = GeminiFileClient()

    test_cases = [
        ("Say hello", "Simple greeting"),
        ("Count to 3", "Simple counting"),
        ("What is 2+2?", "Simple math"),
        ("Reply with one word: blue", "Short response"),
    ]

    results = []

    for i, (prompt, description) in enumerate(test_cases, 1):
        print(f"\n[Test {i}/{len(test_cases)}] {description}")
        print(f"Prompt: {prompt}")
        print("-" * 60)

        for run in range(1, 4):
            print(f"  Run {run}... ", end="", flush=True)

            response = client.send_prompt(prompt, timeout=180)

            result = {
                "test": i,
                "run": run,
                "description": description,
                "prompt": prompt,
                "success": response.success,
                "elapsed": response.elapsed_seconds,
                "response_len": len(response.response_text),
                "response": response.response_text[:200],
                "output_file": response.output_file,
                "error": response.error,
            }
            results.append(result)

            if response.success:
                print(f"OK {response.elapsed_seconds:.2f}s | {len(response.response_text)} chars")
                if run == 1:
                    print("\n--- Response Preview ---")
                    print(response.response_text[:300])
                    print("..." if len(response.response_text) > 300 else "")
                    print("-" * 60)
            else:
                print(f"FAIL {response.error}")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    success_count = sum(1 for r in results if r["success"])
    total_count = len(results)
    avg_time = (
        sum(r["elapsed"] for r in results if r["success"]) / max(success_count, 1)
    )

    print(f"Success Rate: {success_count}/{total_count} ({100*success_count/total_count:.1f}%)")
    print(f"Average Time: {avg_time:.2f}s")

    if success_count == total_count:
        print("\nALL TESTS PASSED")
        return 0

    print(f"\n{total_count - success_count} TESTS FAILED")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
