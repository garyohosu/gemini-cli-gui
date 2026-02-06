# gemini-cli-gui

Unofficial GUI wrapper for [Gemini CLI](https://github.com/google-gemini/gemini-cli) on Windows.

## What this is

**無料で使える AI コーディングアシスタントを、コマンドラインなしで。**

Gemini CLI を GUI で操作できる Windows デスクトップアプリです。[Claude Cowork](https://github.com/anthropics/claude-code) のようなエージェント型 AI ツールを、CLI が苦手な人でも使えるようにすることを目指しています。

特徴:
- **無料** - Gemini CLI の無料枠を活用（Google アカウントがあれば OK）
- **GUI** - コマンドラインを使わずにチャット形式で操作
- **安全** - ワークスペース外へのアクセスをブロック、変更前にプレビュー表示

このプロジェクトは AI 併用開発の実験でもあります。

## Status

**v0.2.0 リリース済み - 実用レベル達成！**

ファイル出力方式による安定した Gemini CLI 統合を実現しました。

- ✅ **信頼性**: 83.3%の成功率（CLI検証済み）
- ✅ **エラーハンドリング**: レート制限時の分かりやすいメッセージ
- ⚠️ **応答時間**: 約40秒（Gemini CLI起動時間を含む）

詳細は [Release Notes](https://github.com/garyohosu/gemini-cli-gui/releases/tag/v0.2.0) をご覧ください。

## Requirements (end users)
- Windows 10/11 (64-bit)
- [Gemini CLI](https://github.com/google-gemini/gemini-cli) (`npm install -g @google/generative-ai-cli`)
- Google アカウント（Gemini の認証用）
- インターネット接続
- Python 3.11+ （開発版として実行する場合）

## Usage

### 開発版として実行（現在の推奨方法）

```bash
# リポジトリをクローン
git clone https://github.com/garyohosu/gemini-cli-gui.git
cd gemini-cli-gui

# 依存関係をインストール
pip install -r requirements.txt

# アプリケーションを起動
python app.py
```

起動後:
1. ワークスペースフォルダを選択
2. チャットで依頼を入力
3. Gemini からの応答を待つ（約40秒）
4. プレビューを確認して承認

### バイナリ版（将来予定）
1. GitHub Releases から exe をダウンロード
2. アプリを起動
3. 上記と同じ手順

## Development

### Prerequisites
- Python 3.11+
- Git

### Setup
```bash
git clone https://github.com/garyohosu/gemini-cli-gui.git
cd gemini-cli-gui
python -m venv .venv
.venv\Scripts\activate  # Windows
# または: source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### Run
```bash
python app.py
```

### Test
```bash
# CLI検証スクリプト
python scripts/verify_file_client.py
```

### Tech Stack
- GUI: PySide6
- CLI Integration: PowerShell + File Output
- Build: PyInstaller (予定)

### Architecture
- `core/gemini_file_client.py` - Gemini CLI wrapper using file output
- `scripts/run_gemini_to_file.ps1` - PowerShell script for CLI execution
- `app.py` - Main GUI application

## Documentation
- [spec.md](spec.md) - 技術仕様・セキュリティ要件
- [CHANGELOG.md](CHANGELOG.md) - 変更履歴
- [instructions/](instructions/) - 実装ガイド・タスク記録
- [result/](result/) - テスト結果・検証記録

## Known Limitations (v0.2.0)
- 応答時間: 約40秒（Gemini CLI起動時間を含む）
- レート制限: 連続リクエストで "capacity exhausted" が発生する可能性
- ストリーミング非対応: 応答が一度に表示される

将来の改善予定は [instructions/2026-02-05_next_steps.md](instructions/2026-02-05_next_steps.md) を参照。

## License
MIT License (予定)
