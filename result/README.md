# Results - Test and Implementation Outcomes

このフォルダには、実装とテストの結果が格納されます。

## ユーザー向け - 結果の確認方法

```bash
# 最新の結果を取得
git pull

# 結果ファイル一覧
ls result/2026-02-05_*.md

# 最新の結果を確認
cat result/2026-02-05_*.md
# または
code result/
```

## ファイル命名規則

```
result/YYYY-MM-DD_task-name.md
```

例：
- `result/2026-02-05_tty-cli-verification.md` - CLI検証結果
- `result/2026-02-05_clean-response-fix.md` - 応答抽出修正結果

## 結果ファイルの構造

各結果ファイルには以下を含めてください：

```markdown
# [タスク名] - Test Results

**Date**: YYYY-MM-DD
**Issue**: #XX
**Tested by**: Local Codex / GenSpark

## Summary
簡潔な概要（1-2文）

## Root Cause / Problem
何が問題だったか

## Solution Implemented
何を実装したか

## Test Results

### Test 1: [テスト名]
- Input: ...
- Expected: ...
- Actual: ...
- Result: ✅ PASS / ❌ FAIL

### Test 2: [テスト名]
...

## Performance
- Metric 1: X seconds
- Metric 2: Y MB
...

## Conclusion
- [ ] All tests passed
- [ ] Ready for production
- [ ] Issues found: [describe]

## Next Steps
（必要に応じて）
```

## 既存の結果ファイル

### 2026-02-05_tty-cli-verification.md

**内容**: pywinptyを使ったCLI検証
**結果**:
- ✅ Speed: 2.1秒（2回目以降）
- ✅ Data capture: 33KB受信
- ❌ Extraction: 応答が抽出できていない

**次のアクション**: 応答抽出ロジック修正（Issue #22）

## 期待される次の結果

### 2026-02-05_clean-response-fix.md

**待機中** - Local Codexが実装・テスト後に作成

**期待内容**:
- 修正内容の説明
- テスト結果（複数プロンプト）
- パフォーマンス確認
- GUIでの動作確認

## ログファイル

詳細なログは `.txt` ファイルに保存可能：

```
result/2026-02-05_tty-raw.txt      - 生のPTY出力
result/2026-02-05_tty-clean.txt    - クリーニング後の出力
result/2026-02-05_debug.log        - デバッグログ
```

## レビュープロセス

1. **Local Codex**: 結果ファイル作成 → コミット → プッシュ
2. **User**: `git pull` → `result/` フォルダ確認
3. **User → GenSpark**: 結果を共有（必要に応じて）
4. **GenSpark**: レビュー → Issue/PRにコメント
