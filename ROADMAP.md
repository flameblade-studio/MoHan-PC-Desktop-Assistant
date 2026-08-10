# 墨寒開發路線圖／墨寒开发路线图／MoHan Roadmap／墨寒ロードマップ

## 繁體中文

本路線圖用來說明方向，不代表交付期限。安全、隱私、資料相容性及避免舊功能退步，永遠優先於功能數量。

### 穩定基礎

- 使用 Python 與 PySide6 建置的 Windows 10/11 桌面夥伴。
- 台灣繁體中文文字對話、標準轉錄及 Realtime 語音。
- 表情仲裁、眨眼、AIUEO 嘴型、視線與動態效果。
- 任務、靈感、可編輯長期記憶、計時器與提醒。
- 權限閘控工具、本機 SQLite 資料、DPAPI 機密儲存及可攜式設定檔轉移。
- Google Gmail、Calendar 及 Drive 流程已在維護者的真實環境完成驗證。
- 受保護的 main 工作流程、Windows CI、安全政策、公開發行稽核及自動化回歸測試套件。

### 公開預覽整合

- Microsoft Outlook、OneDrive 及 Calendar：已有實作；仍待真實租用戶端對端驗證。
- GitHub 助理工具：已有實作；仍待真實儲存庫端對端驗證。
- Home Assistant：已有權限邊界與連接器基礎；仍待真實伺服器及實體裝置驗證。

上述整合一律維持自願啟用；在取得可重現的真實環境驗證證據前，不得宣稱已完成完整驗證。

### 近期品質目標

- 擴充真實裝置與真實帳號的整合測試涵蓋率。
- 改善無障礙、首次使用說明的清晰度、診斷及復原路徑。
- 持續改善動畫與語音同步品質，同時不得破壞可決定重現的待機、語音結束及表情規則。
- 改善貢獻者文件，並在證據顯示維護阻力時隔離更多功能邊界。
- 待永續資金足以負擔可信任的 Windows 憑證時加入程式碼簽章。

### 歡迎協作方向

- 不包含機密或私人資料且可重現的錯誤報告。
- 無障礙及台灣繁體中文使用者體驗改善。
- Windows 封裝、音訊裝置及多螢幕相容性。
- 具備明確權限、確認及復原能力的安全連接器介接器。
- 能降低維護風險的測試與文件。

開始實作大型變更前，請先提出 Feature Request。安全問題必須遵照 [SECURITY.md](SECURITY.md)，不得公開張貼漏洞、金鑰或私人資料。

## 简体中文

本路线图用于说明方向，不代表交付期限。安全、隐私、数据兼容性及避免旧功能退步，永远优先于功能数量。

### 稳定基础

- 使用 Python 与 PySide6 构建的 Windows 10/11 桌面伙伴。
- 台湾繁体中文文字对话、标准转录及 Realtime 语音。
- 表情仲裁、眨眼、AIUEO 嘴型、视线与动态效果。
- 任务、灵感、可编辑长期记忆、计时器与提醒。
- 权限门控工具、本地 SQLite 数据、DPAPI 机密存储及可移植配置文件转移。
- Google Gmail、Calendar 及 Drive 流程已在维护者的真实环境完成验证。
- 受保护的 main 工作流、Windows CI、安全策略、公开发行审计及自动化回归测试套件。

### 公开预览集成

- Microsoft Outlook、OneDrive 及 Calendar：已有实现；仍待真实租户端到端验证。
- GitHub 助理工具：已有实现；仍待真实仓库端到端验证。
- Home Assistant：已有权限边界与连接器基础；仍待真实服务器及物理设备验证。

上述集成一律保持自愿启用；在取得可重现的真实环境验证证据前，不得宣称已完成完整验证。

### 近期质量目标

- 扩充真实设备与真实账号的集成测试覆盖率。
- 改善无障碍、首次使用说明的清晰度、诊断及恢复路径。
- 持续改善动画与语音同步质量，同时不得破坏可确定重现的待机、语音结束及表情规则。
- 改善贡献者文档，并在证据显示维护阻力时隔离更多功能边界。
- 待可持续资金足以负担可信任的 Windows 证书时加入代码签名。

### 欢迎协作方向

- 不包含机密或私人数据且可重现的错误报告。
- 无障碍及台湾繁体中文用户体验改善。
- Windows 封装、音频设备及多显示器兼容性。
- 具备明确权限、确认及回滚能力的安全连接器适配器。
- 能降低维护风险的测试与文档。

开始实现大型变更前，请先提出 Feature Request。安全问题必须遵照 [SECURITY.md](SECURITY.md)，不得公开发布漏洞、密钥或私人数据。

## English

This roadmap communicates direction, not deadlines. Safety, privacy, data compatibility, and regression protection always take priority over feature count.

### Stable foundations

- Windows 10/11 desktop companion built with Python and PySide6.
- Taiwan Traditional Chinese text chat, standard transcription, and Realtime voice.
- Expression arbitration, blink, AIUEO visemes, gaze, and motion effects.
- Tasks, ideas, editable long-term memory, timers, and reminders.
- Permission-gated tools, local SQLite data, DPAPI secret storage, and portable profile transfer.
- Google Gmail, Calendar, and Drive flows validated in the maintainer's real environment.
- Protected-main workflow, Windows CI, security policy, public-release audit, and automated regression suite.

### Public-preview integrations

- Microsoft Outlook, OneDrive, and Calendar: implementation exists; real-tenant end-to-end validation remains pending.
- GitHub assistant tools: implementation exists; real-repository end-to-end validation remains pending.
- Home Assistant: permission boundaries and connector foundations exist; real-server and physical-device validation remains pending.

These integrations must remain opt-in and must not be presented as fully validated until reproducible real-environment evidence is available.

### Near-term quality goals

- Expand real-device and real-account integration test coverage.
- Improve accessibility, onboarding clarity, diagnostics, and recovery paths.
- Continue animation and voice-sync quality work without breaking deterministic idle, speech-completion, and expression rules.
- Improve contributor documentation and isolate more feature boundaries where evidence shows maintenance friction.
- Add code signing when sustainable funding makes a trusted Windows certificate practical.

### Contribution priorities

- Reproducible bug reports that contain no secrets or private data.
- Accessibility and Taiwan Traditional Chinese UX improvements.
- Windows packaging, audio-device, and multi-display compatibility.
- Safe connector adapters with explicit permissions, confirmation, and rollback.
- Tests and documentation that reduce maintenance risk.

Please open a Feature Request before implementing a large change. Security findings must follow [SECURITY.md](SECURITY.md) and must not be posted publicly with vulnerabilities, keys, or private data.

## 日本語

本ロードマップは方向性を示すものであり、納期を示すものではありません。安全性、プライバシー、データ互換性、回帰防止を、機能数より常に優先します。

### 安定した基盤

- Python と PySide6 で構築した Windows 10/11 デスクトップコンパニオン。
- 台湾繁体字中国語のテキストチャット、標準文字起こし、Realtime 音声。
- 表情調停、まばたき、AIUEO ビセーム、視線、モーション効果。
- タスク、アイデア、編集可能な長期記憶、タイマー、リマインダー。
- 権限ゲート付きツール、ローカル SQLite データ、DPAPI 機密ストレージ、ポータブルプロファイル転送。
- Google Gmail、Calendar、Drive のフローは、保守担当者の実環境で検証済みです。
- 保護された main ワークフロー、Windows CI、セキュリティポリシー、公開リリース監査、自動回帰テストスイート。

### 公開 Preview 統合

- Microsoft Outlook、OneDrive、Calendar：実装済みですが、実テナントでのエンドツーエンド検証は未完了です。
- GitHub アシスタントツール：実装済みですが、実リポジトリでのエンドツーエンド検証は未完了です。
- Home Assistant：権限境界とコネクター基盤は実装済みですが、実サーバーおよび物理デバイスでの検証は未完了です。

これらの統合はすべてオプトインを維持し、再現可能な実環境の検証証拠が得られるまで、完全に検証済みと表示してはいけません。

### 短期的な品質目標

- 実デバイスおよび実アカウントの統合テスト範囲を拡大します。
- アクセシビリティ、オンボーディングの明確さ、診断、復旧経路を改善します。
- 決定論的な待機、音声終了、表情規則を壊さずに、アニメーションと音声同期の品質改善を継続します。
- コントリビューター向け文書を改善し、保守上の摩擦を証拠が示す箇所では、機能境界をさらに分離します。
- 信頼できる Windows 証明書を持続可能な資金で取得できる段階で、コード署名を追加します。

### コントリビューションの優先事項

- 機密情報や個人データを含まない、再現可能なバグ報告。
- アクセシビリティおよび台湾繁体字中国語 UX の改善。
- Windows パッケージ、オーディオデバイス、マルチディスプレイの互換性。
- 明示的な権限、確認、ロールバックを備えた安全なコネクターアダプター。
- 保守リスクを低減するテストと文書。

大規模な変更を実装する前に Feature Request を提出してください。セキュリティ上の問題は [SECURITY.md](SECURITY.md) に従い、脆弱性、キー、個人データを公開投稿してはいけません。
