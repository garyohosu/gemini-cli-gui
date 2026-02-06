# Gemini CLI + subprocess + stream-json 実装ガイド

## 🎯 目的

pywinpty/pyteアプローチを廃止し、**subprocess + stream-json**で確実な出力取得を実現。

## 📚 参考実装

実際に動いているプロダクション実装：
- GitHub: https://github.com/centminmod/gemini-cli-mcp-server
- 2,500+テストケース、FastMCP使用
- Claude CodeからGemini CLIを呼び出し

---

## 🔧 実装手順

### Step 1: 新しい`core/gemini_subprocess_client.py`を作成

```python
"""
Gemini CLI Subprocess Client

subprocess.run で Gemini CLI を実行し、-o stream-json で確実な出力取得。
pywinpty/pyteは使用しない。
"""

import subprocess
import json
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

@dataclass
class GeminiResponse:
    """Gemini CLI response data"""
    text: str
    elapsed_ms: int
    success: bool
    error: Optional[str] = None


class GeminiSubprocessClient:
    """
    Gemini CLI client using subprocess.run with stream-json output.
    
    Advantages over pywinpty:
    - No PTY/ANSI issues
    - JSON output is easily parseable
    - No terminal emulation needed
    - Works reliably on Windows
    """
    
    def __init__(self, working_dir: Path, yolo_mode: bool = True):
        """
        Initialize client.
        
        Args:
            working_dir: Workspace directory for Gemini CLI
            yolo_mode: Enable YOLO mode (auto-approve operations)
        """
        self.working_dir = working_dir
        self.yolo_mode = yolo_mode
    
    def send_prompt(
        self, 
        prompt: str, 
        model: str = "gemini-2.5-flash",
        timeout: float = 180.0
    ) -> GeminiResponse:
        """
        Send prompt to Gemini CLI and get response.
        
        Args:
            prompt: User prompt
            model: Gemini model to use
            timeout: Timeout in seconds
            
        Returns:
            GeminiResponse with text and metadata
        """
        start_ms = time.time() * 1000
        
        # Build command
        command = [
            "gemini",
            "--prompt", prompt,
            "--model", model,
            "-o", "stream-json"  # NDJSON output
        ]
        
        if self.yolo_mode:
            command.append("-y")
        
        try:
            # Execute Gemini CLI
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                cwd=str(self.working_dir),
                timeout=timeout,
                encoding='utf-8',
                errors='replace'
            )
            
            # Parse NDJSON output
            response_text = self._parse_ndjson(result.stdout)
            
            elapsed_ms = int(time.time() * 1000 - start_ms)
            
            if result.returncode != 0:
                # Error occurred
                error_msg = result.stderr or "Unknown error"
                return GeminiResponse(
                    text="",
                    elapsed_ms=elapsed_ms,
                    success=False,
                    error=error_msg
                )
            
            return GeminiResponse(
                text=response_text,
                elapsed_ms=elapsed_ms,
                success=True
            )
            
        except subprocess.TimeoutExpired:
            elapsed_ms = int(time.time() * 1000 - start_ms)
            return GeminiResponse(
                text="",
                elapsed_ms=elapsed_ms,
                success=False,
                error="Request timeout"
            )
        except Exception as e:
            elapsed_ms = int(time.time() * 1000 - start_ms)
            return GeminiResponse(
                text="",
                elapsed_ms=elapsed_ms,
                success=False,
                error=str(e)
            )
    
    def _parse_ndjson(self, stdout: str) -> str:
        """
        Parse NDJSON (Newline Delimited JSON) output from Gemini CLI.
        
        Expected format:
        {"type":"text","text":"Hello"}
        {"type":"text","text":" world"}
        {"type":"text","text":"!"}
        
        Args:
            stdout: Raw stdout from Gemini CLI
            
        Returns:
            Concatenated text from all text chunks
        """
        response_text = ""
        
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            
            try:
                data = json.loads(line)
                
                # Extract text chunks
                if data.get("type") == "text":
                    response_text += data.get("text", "")
                
            except json.JSONDecodeError:
                # Skip invalid JSON lines
                continue
        
        return response_text.strip()


# Example usage
if __name__ == "__main__":
    # Test client
    workspace = Path("C:/temp")
    client = GeminiSubprocessClient(workspace, yolo_mode=True)
    
    print("Testing Gemini CLI subprocess client...")
    
    # Test 1: Simple prompt
    print("\nTest 1: Say hello")
    response = client.send_prompt("Say hello in one word.")
    print(f"Response: {response.text}")
    print(f"Elapsed: {response.elapsed_ms}ms")
    print(f"Success: {response.success}")
    
    # Test 2: Japanese
    print("\nTest 2: Japanese")
    response = client.send_prompt("こんにちは")
    print(f"Response: {response.text}")
    print(f"Elapsed: {response.elapsed_ms}ms")
    
    # Test 3: Count
    print("\nTest 3: Count to 3")
    response = client.send_prompt("Count to 3")
    print(f"Response: {response.text}")
    print(f"Elapsed: {response.elapsed_ms}ms")
```

---

### Step 2: CLI検証アプリを作成

`scripts/verify_subprocess_client.py`:

```python
#!/usr/bin/env python3
"""
Verify Gemini Subprocess Client

Test the new subprocess-based client before GUI integration.
"""

import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gemini_subprocess_client import GeminiSubprocessClient

def main():
    print("=== Gemini Subprocess Client Verification ===\n")
    
    # Workspace
    workspace = Path("C:/temp")
    if not workspace.exists():
        print(f"Error: {workspace} does not exist")
        return 1
    
    print(f"Workspace: {workspace}\n")
    
    # Test prompts
    test_cases = [
        ("Say hello in one word.", "Hello"),
        ("こんにちは", "Japanese greeting response"),
        ("Count to 3", "1, 2, 3"),
        ("List files in current directory", "File listing")
    ]
    
    # Initialize client
    client = GeminiSubprocessClient(workspace, yolo_mode=True)
    
    # Run tests
    results = []
    for i, (prompt, expected) in enumerate(test_cases, 1):
        print(f"--- Test {i}/{len(test_cases)} ---")
        print(f"Prompt: {prompt}")
        print(f"Expected: {expected}")
        
        start = time.time()
        response = client.send_prompt(prompt, timeout=180.0)
        elapsed = time.time() - start
        
        print(f"✓ Elapsed: {elapsed:.1f}s")
        print(f"✓ Success: {response.success}")
        print(f"✓ Text length: {len(response.text)} chars")
        
        if response.success:
            print(f"✓ Response preview:")
            print("-" * 40)
            print(response.text[:200] + ("..." if len(response.text) > 200 else ""))
            print("-" * 40)
            status = "✅ PASS"
        else:
            print(f"✗ Error: {response.error}")
            status = "❌ FAIL"
        
        results.append({
            "test": i,
            "prompt": prompt,
            "success": response.success,
            "elapsed": elapsed,
            "text_len": len(response.text),
            "status": status
        })
        
        print()
    
    # Summary
    print("=== Test Summary ===")
    passed = sum(1 for r in results if r["success"])
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    for r in results:
        print(f"Test {r['test']}: {r['status']} ({r['elapsed']:.1f}s, {r['text_len']} chars)")
    
    # Save results
    result_file = Path("result/2026-02-05_subprocess_verification.md")
    result_file.parent.mkdir(exist_ok=True)
    
    with open(result_file, "w", encoding="utf-8") as f:
        f.write("# Gemini Subprocess Client Verification Results\n\n")
        f.write(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"## Summary\n\n")
        f.write(f"- Total Tests: {total}\n")
        f.write(f"- Passed: {passed}\n")
        f.write(f"- Failed: {total - passed}\n\n")
        f.write("## Test Results\n\n")
        
        for r in results:
            f.write(f"### Test {r['test']}: {r['status']}\n")
            f.write(f"- Prompt: {r['prompt']}\n")
            f.write(f"- Elapsed: {r['elapsed']:.1f}s\n")
            f.write(f"- Text Length: {r['text_len']} chars\n\n")
        
        if passed == total:
            f.write("## Conclusion\n\n")
            f.write("✅ All tests passed. Ready for GUI integration.\n")
        else:
            f.write("## Conclusion\n\n")
            f.write("❌ Some tests failed. Review errors before GUI integration.\n")
    
    print(f"\nResults saved to: {result_file}")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
```

---

### Step 3: 実行して検証

```bash
# 検証アプリ実行
py scripts/verify_subprocess_client.py
```

**期待される結果**:
```
Test 1: ✅ PASS (30s, 50 chars) - "Hello"
Test 2: ✅ PASS (25s, 120 chars) - "こんにちは！..."
Test 3: ✅ PASS (28s, 20 chars) - "1\n2\n3"
Test 4: ✅ PASS (32s, 300 chars) - "File listing..."
```

---

### Step 4: すべてPASSならGUI統合

`app.py`を更新：

```python
# 変更前
from core.gemini_runner import GeminiRunner

# 変更後
from core.gemini_subprocess_client import GeminiSubprocessClient as GeminiRunner
```

---

## 🎯 重要なポイント

### 1. pywinpty/pyteは完全に廃止

- `requirements.txt`から削除
- `core/gemini_runner.py`は使用しない
- `pyte`関連のコードもすべて削除

### 2. 速度について

- **初回**: 30秒程度（Gemini CLI起動）
- **2回目以降**: 30秒程度（subprocess.runは毎回新規実行）

**注意**: subprocessアプローチは**プロセスを常駐させない**ため、pywinptyの「2秒」は実現できません。

ただし：
- ✅ 確実に動作する
- ✅ 30秒は許容範囲（実用可能）
- ✅ 出力抽出が確実
- ✅ 保守が容易

### 3. もし常駐が必要なら

将来的に高速化が必要な場合：
- Node.jsサーバー方式（`server/gemini_server.js`）を改善
- または、Gemini CLI自体のセッション管理機能を調査

---

## 📋 検証チェックリスト

- [ ] `core/gemini_subprocess_client.py` 作成
- [ ] `scripts/verify_subprocess_client.py` 作成
- [ ] CLI検証実行（すべてPASS）
- [ ] 結果ドキュメント化（`result/2026-02-05_subprocess_verification.md`）
- [ ] `app.py` 統合
- [ ] GUIテスト（3回連続）
- [ ] pywinpty/pyte関連ファイル削除
- [ ] `requirements.txt` 更新（pywinpty, pyte削除）

---

## 🎉 成功基準

1. ✅ CLI検証で全テストPASS
2. ✅ 応答が読める（clean text）
3. ✅ 30秒前後で応答
4. ✅ 連続実行で安定動作
5. ✅ GUIで正常表示

---

## 📊 パフォーマンス比較

| 方式 | 初回 | 2回目以降 | 出力品質 | 実装難易度 |
|------|------|----------|---------|-----------|
| pywinpty + pyte | 90秒 | 2秒 ✨ | ❌ ガーベジ | 😱 超高 |
| subprocess + json | 30秒 | 30秒 | ✅ クリーン | 😊 低 |

**結論**: subprocess方式が実用的。
