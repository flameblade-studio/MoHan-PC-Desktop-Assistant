### 未發布：表情取樣診斷

- 表情取樣持續執行完整仲裁與八小時加速壓測，至少涵蓋擷取時間的 90% 與原有 16 輪，記錄完成輪數；保留阻塞讀取、原生與 opcode 證據、全部目標及既有品質門檻。快速 CPU 的高讀取錯誤仍需 CI 驗證。
- 新增時間預算與斷言失敗傳遞的防退化測試，並記錄十次本機對照；非阻塞讀取競爭仍待上游修復。

### 未发布：表情采样诊断

- 表情采样持续执行完整仲裁与八小时加速压测，至少覆盖采集时间的 90% 与原有 16 轮，记录完成轮数；保留阻塞读取、原生与 opcode 证据、全部目标及现有质量门槛。快速 CPU 的高读取错误仍需 CI 验证。
- 新增时间预算与断言失败传递的防退化测试，并记录十次本机对照；非阻塞读取竞争仍待上游修复。

### Unreleased: Expression sampling diagnostics

- Repeat complete arbitration and accelerated eight-hour soaks for at least 90% of the capture duration and the original 16 passes, recording completed passes. Preserve blocking reads, native and opcode evidence, all targets and existing quality gates. High read errors on fast CPUs still require CI validation.
- Add regression tests for the wall-time budget and assertion propagation, and record ten local comparisons. Concurrent nonblocking reads still require an upstream fix.

### 未リリース：表情サンプリングの診断

- 完全な仲裁と八時間の加速負荷試験を、収集時間の 90% 以上かつ従来の 16 回以上繰り返し、完了回数を記録します。ブロッキング読み取り、ネイティブと opcode の証拠、全ターゲット、既存の品質条件を維持します。高速 CPU の読み取りエラーは CI 検証が必要です。
- 時間予算とアサーション失敗の伝播を回帰試験し、ローカルで十回の比較を記録します。非ブロッキング読み取りの競合は上流での修正が必要です。
