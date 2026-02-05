# Instructions for Local Codex

このフォルダには、Local Codex（Windows環境）向けの実装タスクが格納されています。

## 使い方

### 1. 最新のタスクを取得

```bash
git pull
```

### 2. タスクファイルを確認

```bash
ls instructions/2026-02-05-*.md
```

最新日付のファイルが最新タスクです。

### 3. タスクを実行

指示されたmdファイルを読んで、そこに書かれた通りに実装・テストしてください。

例：
```bash
# mdファイルを開いて読む
cat instructions/2026-02-05-fix-clean-response.md
# または
code instructions/2026-02-05-fix-clean-response.md

# 指示に従って実装・テスト
# ...

# 結果をresult/フォルダに保存
# 例: result/2026-02-05_clean-response-fix.md
```

### 4. 結果をコミット

```bash
git add result/
git add core/  # 修正したファイル
git commit -m "fix: implement clean response extraction"
git push
```

### 5. ユーザーが結果確認

ユーザーが `git pull` して `result/` フォルダを確認します。

## 現在のアクティブタスク

### Issue #22: Response Extraction Fix

**タスクファイル**: `instructions/2026-02-05-fix-clean-response.md`

**概要**:
- pywinptyで2秒応答は成功 ✅
- ただし応答抽出ロジックに問題あり ❌
- `core/gemini_runner.py::_clean_response()` を修正

**手順**:
1. タスクファイルを読む
2. `result/2026-02-05_tty-raw.txt` を分析
3. `core/gemini_runner.py` を修正
4. `scripts/verify_gemini_tty.py` でテスト
5. `result/2026-02-05_clean-response-fix.md` に結果記録
6. コミット・プッシュ

**期待される成果**:
- `verify_gemini_tty.py` で clean_len > 0
- 実際の応答テキストが抽出される
- GUI で応答が表示される

## ルール

1. **テスト必須** - 実装したら必ずテストして結果を記録
2. **result/に記録** - テスト結果は必ず `result/YYYY-MM-DD_*.md` に保存
3. **CHANGELOG更新** - コード変更時は `CHANGELOG.md` に追記
4. **PRで連携** - 完成したらPR作成またはPR更新

## GenSparkとの分担

| タスク | GenSpark | Local Codex |
|--------|----------|-------------|
| Windows テスト | ❌ 不可 | ✅ 担当 |
| Gemini CLI テスト | ❌ 不可 | ✅ 担当 |
| 実装ガイド作成 | ✅ 担当 | - |
| コードレビュー | ✅ 担当 | - |
| 実装・テスト | - | ✅ 担当 |

## 質問がある場合

Issue #22 にコメントしてください。GenSparkが回答します。
