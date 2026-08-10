# 墨寒桌面助理 v2.1.0 RC1／墨寒桌面助手 v2.1.0 RC1／MoHan Desktop Assistant v2.1.0 RC1／墨寒デスクトップアシスタント v2.1.0 RC1

## 繁體中文

> 預發行候選版

### 本版重點

- 完整遷移至 Python 3.14，並保留未來評估 Python 3.15 lazy imports 的清楚升級邊界。
- 首次啟動、主要操作介面與互動式 EXE 安裝程式支援繁體中文、簡體中文、英文、日文；MSI 維持繁中基底，另附 en-US、zh-CN、ja-JP 轉換檔。
- 文字對話預設改為 `gpt-5.6-luna`，移除新使用者介面中的舊 mini 選項；既有設定會安全遷移，不覆蓋其他自訂模型。
- 建立可插拔語音供應器架構，加入預設關閉的 Azure Speech 女性聲線預覽。沒有金鑰、離線或雲端失敗時，仍優先回到 Windows 本機女性語音。
- 改善長期記憶的本機向量檢索、語義摘要、安全剪枝與可還原封存；受保護記憶不會因容量自動移除。
- 新增預設關閉的安全背景工作者，可在冷卻、去重、勿擾與權限限制下提供軟體狀態或 IDE 診斷提示。
- 重構 Realtime／非 Realtime 音訊緩衝，降低輸入與播放延遲，禁止靜默遺失中間語音。
- 修正姿勢切換偶發抖動、殘影與舊動畫回呼競速，同時保留眨眼、嘴型、表情仲裁、逐圖錨點、視線、視差與物理動態。
- 首次設定與主視窗改為明亮、高對比、大字級介面；加入古風科技主視覺、墨寒安裝圖與一致的墨寒半身程式圖示。
- 語音轉錄提示詞改為依四種介面語言與個人設定產生的中性預設，不再向所有使用者預填炎劍工作室專有詞；既有自訂提示詞完整保留。
- 修正首次設定欄位標題的垂直對齊及托腮待機姿勢說話時嘴角過度上揚，並更新 README 與官網的最新版實機圖。
- 延後非必要啟動工作並改善啟動流程，在不犧牲資料、安全檢查與原有功能的前提下降低等待時間。

### 下載與相容性

- Windows 10/11 x64。
- 可選免安裝 ZIP、每位使用者 EXE 安裝程式或 MSI。
- 沒有 OpenAI API 金鑰仍可使用本機資料功能、離線回覆與 Windows 本機語音；完整雲端 AI、OpenAI 語音與 Realtime 需要使用者自己的 API 金鑰與額度。
- Microsoft、GitHub、Home Assistant 與 Azure Speech 仍包含尚待更多真實帳號／設備驗證的預覽整合，請勿一開始就使用重要帳號、正式儲存庫或高風險設備。

### 驗證

- Python 3.14.6：`ALL_56_TESTS_OK`
- Windows CI、公開內容稽核、封裝自我測試、事件迴圈測試：通過
- EXE／MSI 靜默安裝、自我測試與移除：通過
- SHA-256、CycloneDX SBOM、更新清單與 Artifact Attestation：已產生
- Gitleaks 完整 Git 歷史掃描：未發現金鑰洩漏

### 相關 Pull Request

- [#14 穩定 Windows CI 介面測試](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/14)
- [#15 本地化安裝程式並加速啟動](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/15)
- [#17 修正語音時的眼部疊影](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/17)
- [#18 墨寒遷移至 Python 3.14](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/18)
- [#19 降低 Realtime 音訊延遲](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/19)
- [#20 消除姿勢切換抖動與殘影](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/20)
- [#21 本機語意記憶檢索與安全剪枝](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/21)
- [#22 安全背景管理器與工作執行緒](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/22)
- [#23 可插拔語音供應器](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/23)
- [#24 Azure Speech 預覽與日文基本可用性](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/24)
- [#25 文字聊天預設使用 GPT-5.6 Luna](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/25)
- [#26 四語安裝程式與明亮易讀介面](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/26)

**完整變更：** [v2.0.14-rc.3...v2.1.0-rc.1](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/compare/v2.0.14-rc.3...v2.1.0-rc.1)

## 简体中文

> 预发布候选版

### 本版重点

- 完整迁移到 Python 3.14，并为未来评估 Python 3.15 lazy imports 保留清晰的升级边界。
- 首次启动、主要操作界面及交互式 EXE 安装程序支持繁体中文、简体中文、英文、日文；MSI 保持繁中基础，并附 en-US、zh-CN、ja-JP 转换文件。
- 文字聊天默认改用 `gpt-5.6-luna`，新用户界面移除旧 mini 选项；现有设置会安全迁移，不覆盖其他自定义模型。
- 建立可插拔语音供应器架构，并加入默认关闭的 Azure Speech 女性声线预览。缺少密钥、离线或云端失败时，仍优先回退到 Windows 本地女性语音。
- 改进长期记忆的本地向量检索、语义摘要、安全剪枝及可恢复封存；受保护记忆不会因容量自动移除。
- 新增默认关闭的安全后台工作线程，可在冷却、去重、勿扰和权限限制下提供软件状态或 IDE 诊断提示。
- 重构 Realtime／非 Realtime 音频缓冲，降低输入与播放延迟，并禁止静默丢失中间语音。
- 修复姿势切换偶发抖动、残影与旧动画回调竞速，同时保留眨眼、嘴型、表情仲裁、逐图锚点、视线、视差及物理动态。
- 首次设置和主窗口改为明亮、高对比、大字号界面，并加入古风科技主视觉、墨寒安装图片与统一的墨寒半身程序图标。
- 语音转录提示词改为按四种界面语言与个人设置生成的中性默认值，不再为所有用户预填炎剑工作室专用词；现有自定义提示词完整保留。
- 修复首次设置字段标题的垂直对齐及托腮待机姿势说话时嘴角过度上扬，并更新 README 与官网的最新版实机图。
- 延后非必要启动工作并优化启动流程，在不牺牲数据、安全检查及现有功能的前提下降低等待时间。

### 下载与兼容性

- Windows 10/11 x64。
- 可选择免安装 ZIP、每用户 EXE 安装程序或 MSI。
- 没有 OpenAI API 密钥时仍可使用本地数据功能、离线回复与 Windows 本地语音；完整云端 AI、OpenAI 语音与 Realtime 需要用户自己的 API 密钥与额度。
- Microsoft、GitHub、Home Assistant 与 Azure Speech 仍包含需要更多真实账号／设备验证的预览集成，请勿一开始就用于重要账号、正式仓库或高风险设备。

### 验证

- Python 3.14.6：`ALL_56_TESTS_OK`
- Windows CI、公开内容审计、打包自测、事件循环测试：通过
- EXE／MSI 静默安装、自测与卸载：通过
- SHA-256、CycloneDX SBOM、更新清单与 Artifact Attestation：已生成
- Gitleaks 完整 Git 历史扫描：未发现密钥泄漏

### 相关 Pull Request

- [#14 稳定 Windows CI 界面测试](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/14)
- [#15 本地化安装程序并加速启动](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/15)
- [#17 修复语音时的眼部叠影](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/17)
- [#18 墨寒迁移至 Python 3.14](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/18)
- [#19 降低 Realtime 音频延迟](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/19)
- [#20 消除姿势切换抖动与残影](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/20)
- [#21 本机语义记忆检索与安全剪枝](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/21)
- [#22 安全后台管理器与工作线程](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/22)
- [#23 可插拔语音供应器](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/23)
- [#24 Azure Speech 预览与日文基本可用性](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/24)
- [#25 文字聊天默认使用 GPT-5.6 Luna](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/25)
- [#26 四语安装程序与明亮易读界面](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/26)

**完整变更：** [v2.0.14-rc.3...v2.1.0-rc.1](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/compare/v2.0.14-rc.3...v2.1.0-rc.1)

## English

> Pre-release candidate

### Highlights

- Fully migrated source, Windows CI, and release packaging to Python 3.14, with an explicit boundary for a future Python 3.15 lazy-import evaluation.
- Added Traditional Chinese, Simplified Chinese, English, and Japanese to first run, primary workflows, and the interactive EXE installer. The MSI keeps its Traditional Chinese base and ships en-US, zh-CN, and ja-JP transforms.
- Made `gpt-5.6-luna` the text-chat default and removed the old mini choice from the new-user UI. Existing settings migrate safely without overwriting other custom models.
- Introduced a pluggable speech-provider boundary and an opt-in Azure Speech female-voice preview. Windows female local speech remains the first fallback when credentials are missing, the device is offline, or a cloud provider fails.
- Improved fully local vector retrieval, semantic summarization, safe pruning, and restorable archives for long-term memory. Protected memories are never removed merely to meet a capacity target.
- Added opt-in, read-only background workers for application-state and IDE diagnostic notices, with cooldowns, deduplication, Do Not Disturb rules, and existing permission boundaries.
- Reworked Realtime and non-Realtime audio buffering to reduce capture/playback delay without silently dropping words.
- Fixed intermittent pose-transition jitter, ghosting, and stale animation callbacks while preserving blinking, visemes, expression arbitration, per-image anchors, gaze, parallax, and physics.
- Redesigned first run and the main window with a bright, high-contrast, larger-type theme, an ink-and-technology hero, MoHan installer art, and consistent MoHan half-body application icons.
- Replaced the author-specific transcription default with neutral prompts generated from the selected UI language and user profile while preserving all existing custom prompts.
- Corrected first-run label alignment and the over-wide smile while the chin-rest pose speaks, then refreshed the latest README and website screenshots.
- Deferred non-essential startup work and streamlined initialization without skipping data integrity, safety checks, or existing behavior.

### Downloads and compatibility

- Windows 10/11 x64.
- Choose the no-install portable ZIP, per-user EXE installer, or MSI package.
- Local data features, offline replies, and Windows local speech work without an OpenAI API key. Full cloud AI, OpenAI speech, and Realtime require a user-owned API key and API credits.
- Microsoft, GitHub, Home Assistant, and Azure Speech still include preview integrations awaiting broader real-account or real-device validation. Do not begin with critical accounts, production repositories, or high-risk devices.

### Verification

- Python 3.14.6: `ALL_56_TESTS_OK`
- Windows CI, public-content audit, packaged self-test, and event-loop smoke test: passed
- Silent EXE/MSI install, self-test, and uninstall: passed
- SHA-256 catalog, CycloneDX SBOM, update manifest, and artifact attestations: generated
- Full-history Gitleaks scan: no leaked secrets found

### Related pull requests

- [#14 Stabilize Windows CI UI tests](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/14)
- [#15 Localize installer and accelerate startup](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/15)
- [#17 Fix speech eye-overlay artifacts](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/17)
- [#18 Migrate MoHan to Python 3.14](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/18)
- [#19 Reduce Realtime audio latency](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/19)
- [#20 Eliminate pose-transition jitter and ghosting](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/20)
- [#21 Local semantic-memory retrieval and safe pruning](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/21)
- [#22 Safe background manager and workers](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/22)
- [#23 Pluggable speech providers](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/23)
- [#24 Azure Speech preview and baseline Japanese usability](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/24)
- [#25 Default text chat to GPT-5.6 Luna](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/25)
- [#26 Four-language installer and bright readable UI](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/26)

**Full changelog:** [v2.0.14-rc.3...v2.1.0-rc.1](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/compare/v2.0.14-rc.3...v2.1.0-rc.1)

## 日本語

> プレリリース候補版

### 主な変更

- ソースコード、Windows CI、配布物を Python 3.14 へ完全移行し、将来の Python 3.15 lazy imports 評価に備えた明確な境界を残しました。
- 初回設定、主要操作、対話型 EXE インストーラーを繁体字中国語、簡体字中国語、英語、日本語へ対応させました。MSI は繁体字中国語を基準とし、en-US、zh-CN、ja-JP 変換ファイルを同梱します。
- 文字会話の既定モデルを `gpt-5.6-luna` へ変更し、新規利用者向け画面から旧 mini を削除しました。他の独自モデル設定は上書きしません。
- 交換可能な音声供給元の境界と、既定では無効の Azure Speech 女性音声プレビューを追加しました。キー不足、オフライン、クラウド障害時は Windows 本機女性音声を最初に利用します。
- 長期記憶のローカルベクトル検索、意味要約、安全な整理、復元可能な保管を改善しました。保護された記憶は容量調整だけを理由に削除しません。
- アプリ状態と IDE 診断を読み取り専用で知らせる、任意の背景ワーカーを追加しました。待機時間、重複防止、集中モード、既存の権限制限を守ります。
- Realtime／非 Realtime の音声バッファーを再構成し、言葉を無断で欠落させずに入力・再生遅延を減らしました。
- 姿勢切り替え時の断続的な揺れ、残像、古いアニメーション処理の競合を修正し、まばたき、口形、表情調停、画像ごとの基準点、視線、視差、物理動作を維持しました。
- 初回設定と本体画面を明るく高コントラストな大きめ文字へ刷新し、古風と技術を融合した主画像、墨寒のインストール画像、統一した墨寒半身アイコンを追加しました。
- 音声文字起こしの既定文を、選択した画面言語と利用者設定から作る中立的な内容へ変更しました。既存の独自文は上書きしません。
- 初回設定の項目名の縦位置と、頬杖姿勢で話す際の過度に広い笑顔を修正し、README と公式サイトの実機画像を最新版へ更新しました。
- データ整合性、安全確認、既存動作を省略せず、不要な初期処理を遅延させて起動待ちを短縮しました。

### ダウンロードと互換性

- Windows 10/11 x64。
- インストール不要の ZIP、利用者単位の EXE インストーラー、MSI から選べます。
- OpenAI API キーがなくても、ローカルデータ、オフライン応答、Windows 本機音声を利用できます。完全なクラウド AI、OpenAI 音声、Realtime には利用者自身の API キーと API 利用枠が必要です。
- Microsoft、GitHub、Home Assistant、Azure Speech には、実アカウント／実機での追加検証が必要なプレビュー連携が含まれます。重要なアカウント、本番リポジトリ、高リスク機器から使い始めないでください。

### 検証

- Python 3.14.6：`ALL_56_TESTS_OK`
- Windows CI、公開内容監査、配布物自己検査、イベントループ検査：成功
- EXE／MSI の無人インストール、自己検査、アンインストール：成功
- SHA-256 一覧、CycloneDX SBOM、更新情報、Artifact Attestation：生成済み
- Gitleaks による Git 全履歴検査：機密情報の漏えいなし

### 関連 Pull Request

- [#14 Windows CI の UI テストを安定化](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/14)
- [#15 インストーラーを多言語化し起動を高速化](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/15)
- [#17 音声再生時の目の重なりを修正](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/17)
- [#18 墨寒を Python 3.14 へ移行](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/18)
- [#19 Realtime 音声遅延を削減](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/19)
- [#20 姿勢切替時の揺れと残像を解消](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/20)
- [#21 ローカル意味記憶検索と安全な剪定](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/21)
- [#22 安全なバックグラウンド管理とワーカー](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/22)
- [#23 交換可能な音声プロバイダー](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/23)
- [#24 Azure Speech プレビューと日本語の基本機能](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/24)
- [#25 テキストチャットの既定を GPT-5.6 Luna に変更](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/25)
- [#26 四言語インストーラーと明るく読みやすい UI](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pull/26)

**完全な変更履歴：** [v2.0.14-rc.3...v2.1.0-rc.1](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/compare/v2.0.14-rc.3...v2.1.0-rc.1)
