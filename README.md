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

**開発初期段階（技術検証中）**

Gemini CLI との連携方法を検証しています。過去の試行で課題があったため、慎重に進めています。

## Requirements (end users)
- Windows 10/11 (64-bit)
- [Node.js](https://nodejs.org/) (v18+)
- [Gemini CLI](https://github.com/google-gemini/gemini-cli) (`npm install -g @anthropic-ai/gemini-cli`)
- Google アカウント（Gemini の認証用）
- インターネット接続

## Usage
1. GitHub Releases から exe をダウンロード
2. アプリを起動
3. ワークスペースフォルダを選択
4. チャットで依頼を入力
5. プレビューを確認して承認

## Development

### Prerequisites
- Python 3.11+
- Git

### Setup
```bash
git clone https://github.com/garyohosu/gemini-cli-gui.git
cd gemini-cli-gui
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt  # TODO: 作成予定
```

### Tech Stack
- GUI: PySide6
- Build: PyInstaller

## Documentation
- [spec.md](spec.md) - 技術仕様・セキュリティ要件

## License
MIT License (予定)
