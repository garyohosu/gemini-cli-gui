# Git Conflict Resolution Guide for Codex

## 自動判断ルール

### CHANGELOG.md の競合が発生した場合

**常に Option 2 を選択してください**: 変更をコミットしてから checkout

理由:
- CHANGELOG.md は作業履歴なので、変更を保存すべき
- stash は一時退避で後で面倒
- 変更を記録してからブランチ切り替えが最も安全

### 実行コマンド

```bash
git add CHANGELOG.md
git commit -m "docs: update CHANGELOG with local changes"
git checkout fix/clean-response-extraction
git pull
```

### その他のファイルで競合した場合

1. **ドキュメント系** (*.md, docs/*): コミットして checkout
2. **コード系** (*.py, *.js): コミットして checkout
3. **設定系** (.gitignore, *.json): コミットして checkout

**基本方針**: 迷ったら常に Option 2 (コミット → checkout)

---

## 自動化スクリプト

```bash
# このコマンドを実行すれば自動的に解決します
git add -A
git commit -m "docs: auto-commit before branch switch"
git checkout fix/clean-response-extraction
git pull
```

---

**結論**: git checkout で競合が発生したら、迷わず上記のコマンドを実行してください。
