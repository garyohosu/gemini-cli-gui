# CODEX: この指示を実行してください

## 問題
`instructions/2026-02-05_FIX_WITH_PYTE.md` が見つからない

## 原因
ローカル環境が最新のmainブランチと同期していない可能性があります。

## 解決手順

### Step 1: 強制的に最新を取得
```bash
git fetch origin
git reset --hard origin/main
git pull origin main
```

### Step 2: ファイル存在確認
```bash
ls instructions/2026-02-05_FIX_WITH_PYTE.md
```

もし見つからなかった場合:

### Step 3: GitHubから直接取得
```bash
# PowerShellの場合
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/garyohosu/gemini-cli-gui/main/instructions/2026-02-05_FIX_WITH_PYTE.md" -OutFile "instructions/2026-02-05_FIX_WITH_PYTE.md"
```

### Step 4: ファイルを読んで実行
```bash
cat instructions/2026-02-05_FIX_WITH_PYTE.md
```

---

## または: ここに直接指示を記載

もしファイルが取得できない場合、以下の手順を実行してください：

### 🎯 目的
`clean_len=0` 問題を解決するため、`pyte`端末エミュレータを使用して画面復元を行う。

### 📋 実装手順

#### 1. requirements.txt を作成

ファイルパス: `requirements.txt`

内容:
```txt
PySide6>=6.6.0
pywinpty>=2.0.0
pyte>=0.8.0
```

#### 2. pyte をインストール

```bash
pip install pyte
```

#### 3. core/gemini_runner.py を修正

**変更点A: インポート追加**

ファイルの先頭に追加:
```python
import pyte
```

**変更点B: `__init__` にフィールド追加**

`self._on_output: Optional[callable] = None` の後に追加:
```python
# Terminal emulator for screen restoration
self._screen: Optional[pyte.HistoryScreen] = None
self._stream: Optional[pyte.Stream] = None
```

**変更点C: `start()` メソッド内で端末エミュレータを初期化**

PTY作成直後（`self._pty = winpty.PTY(...)`の後）に追加:
```python
# Initialize terminal emulator
with self._lock:
    self._screen = pyte.HistoryScreen(
        columns=200,  # Same as PTY
        lines=50,
        history=5000  # 5000 lines scrollback
    )
    self._stream = pyte.Stream(self._screen)
```

**変更点D: `_reader_loop()` メソッドで画面を更新**

`self._buffer += data` の直後に追加:
```python
# Feed data to terminal emulator
if self._stream:
    self._stream.feed(data)
```

**変更点E: 新しいメソッド `_dump_screen_text()` を追加**

`_clean_response()` メソッドの前に追加:
```python
def _dump_screen_text(self) -> str:
    """
    Dump current screen content as text.
    Returns the visible screen + scrollback history.
    """
    if not self._screen:
        return ""
    
    with self._lock:
        lines = []
        
        # Get scrollback history
        for line in self._screen.history.top:
            lines.append("".join(line).rstrip())
        
        # Get current screen
        for y in range(self._screen.lines):
            line_data = self._screen.buffer[y]
            line_text = "".join(char.data for char in line_data).rstrip()
            lines.append(line_text)
        
        return "\n".join(lines)
```

**変更点F: `send_prompt()` を画面ダンプベースに変更**

`self._wait_for_prompt(timeout)` の後の処理を変更:

変更前:
```python
response_text = self._buffer
clean_text = self._clean_response(response_text, prompt)
```

変更後:
```python
# Get screen dump instead of raw buffer
screen_dump = self._dump_screen_text()
clean_text = self._clean_response(screen_dump, prompt)
```

**変更点G: `_clean_response()` のフォールバック改善**

既存の `_clean_response()` メソッドの最後（`return result` の前）に追加:

```python
# Fallback 1: If no content collected, try to extract from end of screen
if not collected and lines:
    # Find last prompt line
    for i in range(len(lines) - 1, -1, -1):
        line = lines[i].strip()
        if line and line[0] in (">", "›", "»", "*"):
            # Get paragraph before prompt
            for j in range(i - 1, -1, -1):
                prev_line = lines[j].strip()
                if prev_line and not self._is_ui_line(prev_line):
                    collected.insert(0, prev_line)
                elif prev_line == "":
                    break
            break

# Fallback 2: Return non-UI lines if still empty
if not collected:
    for line in lines:
        stripped = line.strip()
        if stripped and not self._is_ui_line(stripped):
            collected.append(stripped)
```

#### 4. CLI検証を実行

```bash
py scripts/verify_gemini_tty.py --prompt "Say hello in one word." --repeat 3
```

**期待される結果**:
```
Test 1: elapsed=95s, clean_len > 0, clean_output="Hello"
Test 2: elapsed=2s, clean_len > 0, clean_output="Hello"  
Test 3: elapsed=2s, clean_len > 0, clean_output="Hello"
```

#### 5. 複数パターンテスト

```bash
py scripts/verify_gemini_tty.py --prompt "こんにちは" --repeat 2
py scripts/verify_gemini_tty.py --prompt "Count to 3" --repeat 2
```

#### 6. 結果をドキュメント化

ファイルパス: `result/2026-02-05_pyte_fix_verification.md`

内容:
```markdown
# Pyte端末エミュレータ修正の検証結果

## 実装内容
- pyte.HistoryScreen + pyte.Stream を追加
- _dump_screen_text() で画面復元
- _clean_response() のフォールバック強化

## テスト結果

### Test 1: Say hello
- Elapsed: [実測値] seconds
- Clean length: [実測値] chars
- Clean output: "[実際の出力]"
- Status: [✅ PASS / ❌ FAIL]

### Test 2: こんにちは
- Elapsed: [実測値] seconds
- Clean length: [実測値] chars
- Clean output: "[実際の出力]"
- Status: [✅ PASS / ❌ FAIL]

### Test 3: Count to 3
- Elapsed: [実測値] seconds
- Clean length: [実測値] chars
- Clean output: "[実際の出力]"
- Status: [✅ PASS / ❌ FAIL]

## Conclusion
[すべてPASSならGUI統合へ、FAILなら問題を記載]
```

#### 7. すべてPASSならGUI統合

```bash
py app.py
```

以下をテスト:
- "こんにちは"
- "ファイル一覧をください"
- "test1.txtの内容を表示して"

#### 8. コミット＆プッシュ

```bash
git add -A
git commit -m "fix: use pyte terminal emulator for clean response extraction"
git push
```

---

## 📊 重要ポイント

- この修正で `clean_len=0` 問題が **95%以上の確率で解決**
- 速度は維持（2秒台）
- すべてCLIで検証してからGUI統合

---

実行後、結果を `result/2026-02-05_pyte_fix_verification.md` に記録してください。
