# 分層全身語義稽核證據／分层全身语义稽核证据／Layered Full-Body Semantic Audit Evidence／レイヤー全身セマンティック監査証拠

## 繁體中文

本目錄保存 `tools/audit_layered_full_body_semantics.py` 對
`assets/pose-atlas/v4-layered/`（24 視角 × 25 層）的語義稽核輸出
`layered-full-body-semantic-audit.json`。

- 報告 schema：`mohan.layered-full-body-semantic-audit.v1`
- 退出碼契約：
  - `0`：全部語義檢查通過。
  - `1`：一項以上檔案級語義檢查失敗。
  - `2`：稽核設定或執行本身失敗（fail closed）。

`build.ps1` 會在 PyInstaller 等昂貴封裝步驟之前先執行本稽核；
退出碼非 `0` 即中止封裝。

## 简体中文

本目录保存 `tools/audit_layered_full_body_semantics.py` 对
`assets/pose-atlas/v4-layered/`（24 视角 × 25 层）的语义稽核输出
`layered-full-body-semantic-audit.json`。

- 报告 schema：`mohan.layered-full-body-semantic-audit.v1`
- 退出码契约：
  - `0`：全部语义检查通过。
  - `1`：一项以上文件级语义检查失败。
  - `2`：稽核配置或执行本身失败（fail closed）。

`build.ps1` 会在 PyInstaller 等昂贵封装步骤之前先执行本稽核；
退出码非 `0` 即中止封装。

## English

This directory stores `layered-full-body-semantic-audit.json`, the output of
`tools/audit_layered_full_body_semantics.py` over
`assets/pose-atlas/v4-layered/` (24 views × 25 layers).

- Report schema: `mohan.layered-full-body-semantic-audit.v1`
- Exit-code contract:
  - `0`: all semantic checks passed.
  - `1`: one or more file-level semantic checks failed.
  - `2`: audit configuration or execution failed closed.

`build.ps1` runs this audit before expensive packaging steps such as
PyInstaller; any non-`0` exit aborts packaging.

## 日本語

本ディレクトリは `tools/audit_layered_full_body_semantics.py` による
`assets/pose-atlas/v4-layered/`（24 視点 × 25 層）のセマンティック監査出力
`layered-full-body-semantic-audit.json` を保存する。

- レポート schema：`mohan.layered-full-body-semantic-audit.v1`
- 終了コード契約：
  - `0`：全セマンティック検査合格。
  - `1`：1 件以上のファイルレベル検査が失敗。
  - `2`：監査設定または実行自体が失敗（fail closed）。

`build.ps1` は PyInstaller などの高コストなパッケージング前に本監査を実行し、
終了コードが `0` 以外なら中止する。
