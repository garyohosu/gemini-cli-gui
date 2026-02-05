# CLI検証優先ルール - 実装前に必ずCLIで確認

## 🎯 目的

GUIに統合する前に、**CLIアプリで動作・速度・出力を完全に検証する**

## 📋 必須ルール

### ❌ やってはいけないこと

- GUIに直接統合してユーザーに確認を求める
- 「動くはず」で実装を終わらせる
- 目視確認なしでコードを書く

### ✅ 必ずやること

1. **CLIアプリを作成** (`scripts/verify_*.py`)
2. **自分で実行して確認**
3. **動作時間を計測**
4. **出力内容を目視確認**
5. **結果をドキュメント化** (`result/2026-02-05_*.md`)
6. **すべて OK なら GUI 統合**
7. **最終確認をユーザーに依頼**

---

## 🔧 実装フロー

```
Step 1: CLI検証アプリ作成
  ↓
  scripts/verify_clean_response.py を作成
  - core/gemini_runner.py を import
  - 3つのテストプロンプトを実行
  - elapsed_ms を計測
  - raw/clean 出力を記録
  
Step 2: 自分で実行
  ↓
  py scripts/verify_clean_response.py --prompt "Say hello" --repeat 3
  - 1回目: 初期化時間 (90-120秒)
  - 2回目: キャッシュ後 (2-5秒) ← ここが重要！
  - 3回目: 安定性確認
  
Step 3: 出力確認
  ↓
  - raw 出力: ANSI/UI要素が含まれている？
  - clean 出力: 純粋な回答だけ抽出できている？
  - clean_len > 0: 空レスポンス問題が解決している？
  
Step 4: 複数パターンテスト
  ↓
  - 英語: "Say hello"
  - 日本語: "こんにちは"
  - 複雑: "Count to 10 and explain"
  - ファイル操作: "List files in current directory"
  
Step 5: 結果ドキュメント化
  ↓
  result/2026-02-05_cli_verification_complete.md に記録:
  
  ## Test Results
  
  ### Test 1: Say hello
  - Elapsed: 2.1 seconds
  - Raw length: 1836 chars
  - Clean length: 5 chars
  - Clean output: "Hello"
  - ✅ PASS
  
  ### Test 2: こんにちは
  - Elapsed: 2.3 seconds
  - Raw length: 2145 chars
  - Clean length: 42 chars
  - Clean output: "こんにちは！何かお手伝いできることはありますか？"
  - ✅ PASS
  
  (以下同様)
  
  ## Performance Summary
  - 1st call: 98 seconds (initialization)
  - 2nd call: 2.1 seconds (50x faster)
  - 3rd call: 2.3 seconds (stable)
  
  ## Conclusion
  - ✅ Speed: 2秒台で安定
  - ✅ Output: クリーンな抽出成功
  - ✅ Stability: 連続実行で問題なし
  - ✅ Ready for GUI integration
  
Step 6: GUI統合
  ↓
  app.py を更新:
  - from core.gemini_runner import GeminiRunner
  - GeminiClient を GeminiRunner に置き換え
  - エラーハンドリング追加
  
Step 7: GUI動作確認
  ↓
  py app.py
  - ワークスペース選択: C:/temp
  - テスト1: "こんにちは"
  - テスト2: "ファイル一覧"
  - テスト3: "test1.txt の内容"
  
Step 8: 最終確認依頼
  ↓
  result/2026-02-05_final_verification_request.md
  
  ## ユーザー確認依頼
  
  CLI検証で以下を確認しました：
  - ✅ 2秒台の高速応答
  - ✅ クリーンな出力抽出
  - ✅ 連続実行で安定動作
  
  GUIに統合完了しました。
  
  **最終確認をお願いします**:
  1. git pull
  2. py app.py
  3. 以下をテスト:
     - "こんにちは"
     - "ファイル一覧"
     - "test1.txtの内容"
  
  期待される結果:
  - 各リクエスト約2秒で応答
  - UI要素なしのクリーンな出力
  - 3回連続で安定動作
```

---

## 📝 CLI検証アプリのテンプレート

```python
#!/usr/bin/env python3
"""
Gemini CLI Response Extraction Verification

目的: core/gemini_runner.py の _clean_response() が正しく動作するか検証
"""

import sys
import time
from pathlib import Path
from core.gemini_runner import GeminiRunner

def main():
    print("=== Gemini CLI Response Extraction Verification ===\n")
    
    # 作業ディレクトリ
    workspace = Path("C:/temp")
    if not workspace.exists():
        print(f"Error: {workspace} does not exist")
        return 1
    
    # テストプロンプト
    test_prompts = [
        "Say hello in one word.",
        "こんにちは と日本語で返事してください",
        "Count to 3."
    ]
    
    # GeminiRunner初期化
    print(f"Starting Gemini CLI in: {workspace}\n")
    runner = GeminiRunner(working_dir=workspace, yolo_mode=True)
    
    try:
        runner.start()
        print("✅ Gemini CLI started\n")
        
        # 各プロンプトをテスト
        for i, prompt in enumerate(test_prompts, 1):
            print(f"--- Test {i}/{len(test_prompts)} ---")
            print(f"Prompt: {prompt}")
            
            start = time.time()
            response = runner.send_prompt(prompt, timeout=180.0)
            elapsed = time.time() - start
            
            if response.success:
                print(f"✅ Success")
                print(f"⏱️  Elapsed: {elapsed:.1f} seconds")
                print(f"📊 Raw length: {len(response.text)} chars")
                
                # クリーン出力を表示
                clean = response.text.strip()
                print(f"📝 Clean output ({len(clean)} chars):")
                print("-" * 40)
                print(clean)
                print("-" * 40)
                
                if len(clean) == 0:
                    print("❌ WARNING: Empty clean output!")
                
            else:
                print(f"❌ Failed: {response.error}")
            
            print()
        
        print("=== Verification Complete ===")
        
    finally:
        runner.stop()
        print("Gemini CLI stopped")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

---

## 🎯 このファイルの使い方

### Codex への指示例

```
instructions/2026-02-05_CLI_VERIFICATION_FIRST.md を読んで、
以下の手順で作業してください：

1. scripts/verify_clean_response.py を作成（上記テンプレート使用）
2. 実行: py scripts/verify_clean_response.py
3. 出力を確認して result/2026-02-05_cli_verification_complete.md に記録
4. すべて OK なら GUI 統合
5. 最終確認依頼を result/ に記録
```

---

## 💡 重要ポイント

1. **ユーザーはテスターではない**: AIが先に検証する
2. **CLI で確認してから GUI**: 段階的に統合
3. **数値で証明**: 「動くはず」ではなく「2.1秒で動いた」
4. **ドキュメント化**: すべての結果を記録

---

## 📚 参考

- 既存の CLI 検証アプリ: `scripts/verify_gemini_tty.py`
- 検証結果例: `result/2026-02-05_tty-cli-verification.md`
- 実装ガイド: `instructions/2026-02-05_EXECUTE_THIS.md`

---

**結論**: CLIで完全に検証してからGUIに統合。ユーザーには最終確認のみ依頼。
