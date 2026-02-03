# Handoff Document - gemini-cli-gui

作成日: 2026-02-03

## プロジェクト概要

**目的**: 無料・GUI重視のGemini CLI GUIラッパー（Windows向け）
- 課金嫌い・CLI嫌いなユーザー向け
- Claude Coworkのようなツールを無料で提供

**リポジトリ**: https://github.com/garyohosu/gemini-cli-gui

## 完了した作業

### 1. ドキュメント作成
- `README.md` - プロジェクト概要、セットアップ手順
- `spec.md` - 技術仕様書（MVP〜v1）
- `docs/M0_verification.md` - 技術検証結果

### 2. M0 技術検証（大部分完了）

#### M0-1: Gemini CLI 基本動作確認 ✅
- Gemini CLI v0.26.0 インストール済み
- 主要オプション確認:
  - `-p, --prompt` - 非インタラクティブモード
  - `-y, --yolo` - 自動承認モード
  - `-o json` / `-o stream-json` - 構造化出力

#### M0-2: subprocess 連携 ✅
- Python subprocess.run で呼び出し可能
- 実行時間: 約30秒/回（安定）
- 連続呼び出し: 3回連続で問題なし

#### M0-3: 出力フォーマット ✅
- `-o json` で構造化JSONレスポンス取得可能
- `-o stream-json` でNDJSON形式（ストリーミング）
- パースは容易（CodexGUIと同様のアプローチ可能）

#### M0-4: WorkspaceSandbox ❌ 未着手

### 3. レート制限調査 ✅

| 認証方法 | RPM | RPD |
|---------|-----|-----|
| Googleアカウント | 60 | 1,000 |
| Gemini APIキー | 10 | 250 |

- 2025年12月に無料枠50-80%削減
- 429エラー時は自動リトライあり

### 4. 速度改善の検討

#### 問題
- 毎回のgemini CLI呼び出しに約30秒かかる
- Node.js起動だけで約7秒のオーバーヘッド

#### 試した方法
1. **stdin入力** - 動作するが毎回プロセス起動
2. **pywinpty (疑似TTY)** - 出力取得できず
3. **Node.jsサーバー常駐** - gemini-cli-coreロード成功（4秒）だが内部API呼び出しが複雑

#### 結論
- 現時点では30秒/回を許容してsubprocess方式で実装が現実的
- server/gemini_server.js にNode.jsサーバーの雛形あり（未完成）

## 参考リポジトリ

**CodexGUI**: https://github.com/garyohosu/CodexGUI
- 同じユーザーが作成したCodex CLI用GUI
- `core/codex_wrapper.py` が参考になる
- PySide6 + subprocess方式

## ファイル構成

```
gemini-cli-gui/
├── README.md
├── spec.md
├── docs/
│   └── M0_verification.md
└── server/
    └── gemini_server.js  # Node.js常駐サーバー（実験中・未完成）
```

## 次のステップ（推奨）

### Option A: MVP実装を開始（推奨）
1. CodexGUIの`codex_wrapper.py`をベースに`gemini_wrapper.py`作成
2. 基本的なPySide6 GUIを作成
3. 30秒/回の速度を許容して動くものを作る

### Option B: 速度改善を継続
1. gemini-cli-coreの`GeminiClient`/`GeminiChat`の使い方を調査
2. 内部APIを直接呼び出す方法を探る
3. または、Gemini APIを直接Pythonから呼ぶ（要APIキー）

## 重要な発見

1. **Electron版で90秒かかった問題は解決** - Python subprocess では30秒程度
2. **JSON出力が使える** - `-o json`オプションでパースしやすい
3. **gemini-cli-coreは直接使えるがセットアップが複雑**
4. **CodexGUIと同じアーキテクチャで実装可能**

## 環境情報

- OS: Windows 10/11
- Python: 3.12
- Node.js: 22.x
- Gemini CLI: 0.26.0
- 必要パッケージ: PySide6, pywinpty (オプション)

## コマンドメモ

```bash
# Gemini CLI テスト
gemini -p "Say hello" -o json

# 実行時間計測
python -c "
import subprocess, time
start = time.time()
subprocess.run(['gemini', '-p', 'test', '-o', 'json'], shell=True)
print(f'{time.time()-start:.2f}s')
"

# セッション一覧
gemini --list-sessions
```

## 注意事項

- ユーザーはGoogle AI Plus課金ユーザーだが、ツールは無課金ユーザー向け
- APIキーを要求しない設計にする
- Node.jsプロセスが残る場合は `taskkill /F /IM node.exe` で停止

## 2026-02-03 Update (Codex CLI)
- `AGENTS.md` updated with repository rules:
  - Append changes to `CHANGELOG.md`
  - Save instructions in `instructions/` and results in `result/`
  - Append new rules to `AGENTS.md`
  - `instructions/` and `result/` are for chat AI / CLI sharing
- Added `CHANGELOG.md`
- Added `CLAUDE.md` and `GEMINI.md` (read `AGENTS.md`)
- Created `instructions/` and `result/` folders
- Updated `server/gemini_server.js`:
  - Restrict `workingDir` to `GEMINI_WORKSPACE_ROOT` (reject out-of-root/nonexistent with 400)
  - Force `-y` (`-yolo`) on `/prompt`
- Added `scripts/measure_server.ps1` to measure startup + /health + /prompt
- Runtime measurement blocked by policy in this environment (single `node -v` works)

## Next Actions
1. Run `scripts/measure_server.ps1` locally and share timings
2. Switch `/prompt` to use `gemini-cli-core` API (remove subprocess)
3. Relax hardcoded core path via env or discovery
