# M0 技術検証結果

実施日: 2026-02-03

## M0-1: Gemini CLI 基本動作確認

### インストール状況
- [x] Gemini CLI インストール済み
- バージョン: 0.26.0
- パス: `C:\Users\garyo\AppData\Roaming\npm\gemini.cmd`

### 主要オプション
```
-p, --prompt          非インタラクティブモード
-y, --yolo            自動承認モード（全操作を自動承認）
-o, --output-format   出力形式（text / json / stream-json）
--approval-mode       承認モード（default / auto_edit / yolo / plan）
```

### 無料枠の制限

| 認証方法 | RPM (分あたり) | RPD (日あたり) |
|---------|---------------|----------------|
| **Googleアカウント（推奨）** | 60 | 1,000 |
| Gemini APIキー | 10 | 250 |

**注意:**
- 2025年12月にGoogleが無料枠を50-80%削減
- Gemini 2.5 Proは10-15プロンプト後にFlashモデルに自動切り替え
- 429エラー時は自動リトライ（バックオフ付き）
- `gemini-3-flash-preview` モデルで容量制限が発生する場合あり

参考: https://geminicli.com/docs/quota-and-pricing/

## M0-2: subprocess 連携

### 単発テスト
```bash
gemini -p "Say hello in one word" -o json
```
**結果**: 成功（初回約3.5秒）

### 連続呼び出しテスト
```python
for i in range(3):
    subprocess.run(['gemini', '-p', 'Say yes', '-o', 'json'], ...)
```

| 呼び出し | 実行時間 |
|---------|---------|
| Call 1 | 29.17秒 |
| Call 2 | 31.76秒 |
| Call 3 | 33.27秒 |

**結論**: 連続呼び出しは問題なし。約30秒/回で安定。

### JSON出力フォーマット
```json
{
  "session_id": "c88f0bb1-0bd1-4749-8c99-2a37ed946e74",
  "response": "Hello",
  "stats": {
    "models": { ... },
    "tools": { ... },
    "files": { ... }
  }
}
```

### ストリーミング出力フォーマット（stream-json）
```json
{"type":"init","timestamp":"...","session_id":"...","model":"auto-gemini-3"}
{"type":"message","timestamp":"...","role":"user","content":"..."}
{"type":"message","timestamp":"...","role":"assistant","content":"..."}
```

NDJSON（JSON Lines）形式で、1行ずつパース可能。

## M0-3: 出力フォーマット調査

### 結論
- `-o json` で機械可読な出力が得られる
- `response` フィールドにAIの回答
- `stats` フィールドにトークン使用量等の統計
- ストリーミングはNDJSON形式でリアルタイム処理可能

## 比較: Electron版 vs Python版

| 項目 | Electron版 | Python版（想定） |
|------|-----------|-----------------|
| コマンド実行時間 | 約90秒 | 約3.5秒 |
| 出力形式 | 不明 | JSON/NDJSON |
| パース | 困難 | 容易 |

**結論**: Electron版の90秒問題は解決。Python + subprocess で実装可能。

## CodexGUI との互換性

CodexGUI の `codex_wrapper.py` と同様のアプローチが使用可能:

```python
# 同期実行
cmd = ["gemini", "-p", prompt, "-o", "json"]
result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

# ストリーミング実行
cmd = ["gemini", "-p", prompt, "-o", "stream-json"]
process = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)
for line in process.stdout:
    data = json.loads(line)
    # 処理
```

## 次のステップ

- [x] M0-1: Gemini CLI 基本動作確認
- [x] M0-2: subprocess 連携（基本テスト）
- [x] M0-3: 出力フォーマット調査
- [ ] M0-4: WorkspaceSandbox（パス検証）

## 参考

- CodexGUI リポジトリ: https://github.com/garyohosu/CodexGUI
- Gemini CLI ヘルプ: `gemini --help`
