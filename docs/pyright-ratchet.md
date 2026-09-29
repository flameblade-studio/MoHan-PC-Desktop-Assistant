# Pyright 警告棘輪／Pyright 警告棘轮／Pyright warning ratchet／Pyright 警告ラチェット

## 繁體中文

品質閘門以 `tools/pyright_baseline.json` 記錄 basic 模式各檔案的警告數。任何檔案增加警告都會失敗；警告減少時會提示執行 `python tools/quality_gate.py --update-baseline`。更新指令只接受各檔案維持或降低，不能提高基準。

目前 basic 模式為 0 個錯誤、50 個警告。standard 模式評估新增 18 個錯誤，分布為 `reportPossiblyUnboundVariable` 9 個、`reportIncompatibleMethodOverride` 8 個、`reportOverlappingOverload` 1 個；本輪維持 basic，未切換模式。

## 简体中文

质量闸门使用 `tools/pyright_baseline.json` 记录 basic 模式下各文件的警告数。任何文件增加警告都会失败；警告减少时会提示运行 `python tools/quality_gate.py --update-baseline`。更新命令只接受各文件保持或降低，不能提高基准。

当前 basic 模式为 0 个错误、50 个警告。standard 模式评估新增 18 个错误，其中 `reportPossiblyUnboundVariable` 9 个、`reportIncompatibleMethodOverride` 8 个、`reportOverlappingOverload` 1 个；本轮保持 basic，未切换模式。

## English

The quality gate records each file's basic-mode warning count in `tools/pyright_baseline.json`. Any per-file increase fails the gate. A decrease prompts `python tools/quality_gate.py --update-baseline`, which accepts only unchanged or lower per-file counts and cannot raise the baseline.

The current basic result is 0 errors and 50 warnings. A standard-mode feasibility run adds 18 errors: 9 `reportPossiblyUnboundVariable`, 8 `reportIncompatibleMethodOverride`, and 1 `reportOverlappingOverload`. This change keeps basic mode and does not switch modes.

## 日本語

品質ゲートは basic モードのファイル別警告数を `tools/pyright_baseline.json` に記録します。ファイル単位で警告が増えると失敗します。警告が減ると `python tools/quality_gate.py --update-baseline` の実行を案内し、この更新は各ファイルの維持または減少だけを受け入れ、基準を増やせません。

現在の basic 結果はエラー 0 件、警告 50 件です。standard モードの実行可能性評価ではエラーが 18 件増え、内訳は `reportPossiblyUnboundVariable` 9 件、`reportIncompatibleMethodOverride` 8 件、`reportOverlappingOverload` 1 件です。今回は basic モードを維持し、切り替えません。
