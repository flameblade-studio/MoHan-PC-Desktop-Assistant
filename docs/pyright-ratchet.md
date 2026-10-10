# Pyright 警告棘輪／Pyright 警告棘轮／Pyright warning ratchet／Pyright 警告ラチェット

## 繁體中文

品質閘門以 `tools/pyright_baseline.json` 記錄 basic 模式各檔案的警告數。任何檔案增加警告都會失敗；警告減少時會提示執行 `python tools/quality_gate.py --update-baseline`。更新指令只接受各檔案維持或降低，不能提高基準。

品質閘門會把臨時 Pyright 專案綁定到執行中的 Python 環境，確保分析器實際載入 CI 安裝的官方 PySide6 6.12.0 typed wheel。現行 basic 模式基準為 0 個錯誤、51 個警告；先前 standard 模式評估為 19 個錯誤，分布為 `reportPossiblyUnboundVariable` 9 個、`reportIncompatibleMethodOverride` 10 個。本輪維持 basic，並由雲端 CI 判定新版 wheel 是否維持棘輪。

## 简体中文

质量闸门使用 `tools/pyright_baseline.json` 记录 basic 模式下各文件的警告数。任何文件增加警告都会失败；警告减少时会提示运行 `python tools/quality_gate.py --update-baseline`。更新命令只接受各文件保持或降低，不能提高基准。

质量闸门会把临时 Pyright 项目绑定到运行中的 Python 环境，确保分析器实际加载 CI 安装的官方 PySide6 6.12.0 typed wheel。当前 basic 模式基准为 0 个错误、51 个警告；先前 standard 模式评估为 19 个错误，其中 `reportPossiblyUnboundVariable` 9 个、`reportIncompatibleMethodOverride` 10 个。本轮保持 basic，并由云端 CI 判断新版 wheel 是否保持棘轮。

## English

The quality gate records each file's basic-mode warning count in `tools/pyright_baseline.json`. Any per-file increase fails the gate. A decrease prompts `python tools/quality_gate.py --update-baseline`, which accepts only unchanged or lower per-file counts and cannot raise the baseline.

The quality gate binds its temporary Pyright project to the active Python environment so the analyzer loads the official PySide6 6.12.0 typed wheels installed by CI. The current basic-mode baseline is 0 errors and 51 warnings; the earlier standard-mode feasibility result was 19 errors: 9 `reportPossiblyUnboundVariable` and 10 `reportIncompatibleMethodOverride`. This change keeps basic mode, and cloud CI determines whether the new wheel preserves the ratchet.

## 日本語

品質ゲートは basic モードのファイル別警告数を `tools/pyright_baseline.json` に記録します。ファイル単位で警告が増えると失敗します。警告が減ると `python tools/quality_gate.py --update-baseline` の実行を案内し、この更新は各ファイルの維持または減少だけを受け入れ、基準を増やせません。

品質ゲートは一時 Pyright プロジェクトを実行中の Python 環境へ結び付け、CI が導入した公式 PySide6 6.12.0 typed wheel を解析器が実際に読み込むようにします。現在の basic モード基準はエラー 0 件・警告 51 件で、以前の standard モード評価はエラー 19 件、内訳は `reportPossiblyUnboundVariable` 9 件と `reportIncompatibleMethodOverride` 10 件です。今回は basic モードを維持し、新しい wheel がラチェットを保つかはクラウド CI で判定します。
