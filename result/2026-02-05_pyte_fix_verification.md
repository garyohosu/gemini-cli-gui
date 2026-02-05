# Pyte端末エミュレータ修正の検証結果

## 実装内容
- pyte.HistoryScreen + pyte.Stream を追加
- _dump_screen_text() で画面復元
- _clean_response() をステートマシン＋フォールバックで再実装
- requirements.txt に pyte 追加

## テスト結果

### Test 1: Say hello
Command:
```
py scripts/verify_gemini_tty.py --prompt "Say hello in one word." --repeat 3
```

- Run 1: Elapsed 3.010s, Clean length 0, Clean output "" (❌ FAIL)
- Run 2: Elapsed 97.349s, Clean length 1187, Clean output garbled (❌ FAIL)
- Run 3: Elapsed 2.109s, Clean length 943, Clean output garbled (❌ FAIL)

### Test 2: こんにちは
Command:
```
py scripts/verify_gemini_tty.py --prompt "こんにちは" --repeat 2
```

- Run 1: Elapsed 3.010s, Clean length 0, Clean output "" (❌ FAIL)
- Run 2: Elapsed 1112.217s, Clean length 0, Error "Response timeout" (❌ FAIL)

### Test 3: Count to 3
Command:
```
py scripts/verify_gemini_tty.py --prompt "Count to 3" --repeat 2
```

- Run 1: Elapsed 3.010s, Clean length 0, Clean output "" (❌ FAIL)
- Run 2: Elapsed 104.547s, Clean length 1187, Clean output garbled (❌ FAIL)

### Test 4: List files
Command:
```
py scripts/verify_gemini_tty.py --prompt "List files" --repeat 2
```

- Run 1: Elapsed 3.011s, Clean length 0, Clean output "" (❌ FAIL)
- Run 2: Elapsed 106.325s, Clean length 1187, Clean output garbled (❌ FAIL)

## ログ/出力
- Raw: `result/2026-02-05_pyte_fix_raw.txt`
- Clean: `result/2026-02-05_pyte_fix_clean.txt`

## Conclusion
- 画面復元後も出力は実応答ではなく、文字テーブルのようなガーベジが混入。
- clean_len は増えるが応答テキストは抽出できていない。
- 全テストFAILのためGUI統合は未実施。

## 次の調査ポイント
- pyteのscreen/historyがTTYの描画に一致しているか検証
- Gemini CLIがalternate screenや別バッファを使っている可能性
- 画面ダンプではなくraw→prompt検出の別戦略を検討
