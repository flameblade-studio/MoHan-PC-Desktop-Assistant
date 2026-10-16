### 素體啟動降級診斷／素体启动降级诊断／Body startup fallback diagnostics／素体起動時のフォールバック診断

- 將既有半身畫面快照移至獨立模組，保持繪製行為並下修核心模組行數上限。／将既有半身画面快照移至独立模块，保持绘制行为并下调核心模块行数上限。／Move the existing half-body snapshot into a dedicated module, preserving rendering behavior and lowering the core module line-count limit.／既存の半身スナップショットを専用モジュールへ移し、描画動作を維持してコアモジュールの行数上限を引き下げます。

- 自適應素體需要復原時保留既有半身畫面，並記錄只含安全摘要的診斷事件；原始例外文字、路徑與秘密維持在事件之外。錯誤事件僅由啟動異常路徑產生。／自适应素体需要恢复时保留现有半身画面，并记录只含安全摘要的诊断事件；原始异常文本、路径和秘密维持在事件之外。错误事件仅由启动异常路径产生。／When adaptive body startup requires recovery, retain the existing half-body fallback and record a sanitized diagnostic event with raw exception text, paths, and secrets kept outside the event. Error events are emitted only on the startup-error path.／適応型素体の起動に復旧が必要な場合は既存の半身表示を維持し、安全な要約だけを診断イベントに記録します。例外の生テキスト、パス、秘密情報はイベントの外に保ち、エラーイベントは起動エラーの経路だけで記録します。
