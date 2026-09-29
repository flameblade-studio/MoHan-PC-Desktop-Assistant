# Pyright 警告棘輪／Pyright 警告棘轮／Pyright warning ratchet／Pyright 警告ラチェット

## 繁體中文

品質閘門以 `tools/pyright_baseline.json` 記錄 basic 模式各檔案的警告數。任何檔案增加警告都會失敗；警告減少時會提示執行 `python tools/quality_gate.py --update-baseline`。更新指令只接受各檔案維持或降低，不能提高基準。

品質閘門會把臨時 Pyright 專案綁定到執行中的 Python 環境，確保分析器實際載入 CI 安裝的 typed wheel。目前 Python 3.15 相容版 PySide6 含 60 個 `.pyi`；basic 模式從此環境修正前的 0 個錯誤、208 個警告降為 0 個錯誤、49 個警告。standard 模式評估為 19 個錯誤，分布為 `reportPossiblyUnboundVariable` 9 個、`reportIncompatibleMethodOverride` 10 個；本輪維持 basic，未切換模式。

## 简体中文

质量闸门使用 `tools/pyright_baseline.json` 记录 basic 模式下各文件的警告数。任何文件增加警告都会失败；警告减少时会提示运行 `python tools/quality_gate.py --update-baseline`。更新命令只接受各文件保持或降低，不能提高基准。

质量闸门会把临时 Pyright 项目绑定到运行中的 Python 环境，确保分析器实际加载 CI 安装的 typed wheel。当前 Python 3.15 兼容版 PySide6 包含 60 个 `.pyi`；basic 模式从此环境修正前的 0 个错误、208 个警告降为 0 个错误、49 个警告。standard 模式评估为 19 个错误，其中 `reportPossiblyUnboundVariable` 9 个、`reportIncompatibleMethodOverride` 10 个；本轮保持 basic，未切换模式。

## English

The quality gate records each file's basic-mode warning count in `tools/pyright_baseline.json`. Any per-file increase fails the gate. A decrease prompts `python tools/quality_gate.py --update-baseline`, which accepts only unchanged or lower per-file counts and cannot raise the baseline.

The quality gate binds its temporary Pyright project to the active Python environment so the analyzer loads the typed wheels installed by CI. The Python 3.15 compatibility build of PySide6 contains 60 `.pyi` files; the basic result fell from 0 errors and 208 warnings before these environment-aware fixes to 0 errors and 49 warnings. A standard-mode feasibility run reports 19 errors: 9 `reportPossiblyUnboundVariable` and 10 `reportIncompatibleMethodOverride`. This change keeps basic mode and does not switch modes.

## 日本語

品質ゲートは basic モードのファイル別警告数を `tools/pyright_baseline.json` に記録します。ファイル単位で警告が増えると失敗します。警告が減ると `python tools/quality_gate.py --update-baseline` の実行を案内し、この更新は各ファイルの維持または減少だけを受け入れ、基準を増やせません。

品質ゲートは一時 Pyright プロジェクトを実行中の Python 環境へ結び付け、CI がインストールした typed wheel を解析器が実際に読み込むようにします。Python 3.15 互換版 PySide6 には 60 個の `.pyi` があり、basic の結果はこの環境で修正する前のエラー 0 件・警告 208 件から、エラー 0 件・警告 49 件へ減少しました。standard モードの評価はエラー 19 件で、内訳は `reportPossiblyUnboundVariable` 9 件と `reportIncompatibleMethodOverride` 10 件です。今回は basic モードを維持し、切り替えません。
