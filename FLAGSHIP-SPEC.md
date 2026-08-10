# 墨寒旗艦 2.0 規格／墨寒旗舰 2.0 规格／MoHan Flagship 2.0 Specification／墨寒フラッグシップ 2.0 仕様

## 繁體中文

### 執行管線

`輸入 → 意圖 → 結構化計畫 → 本機政策 → 預覽／確認 → 工具執行 → 結果驗證 → 稽核／復原資訊`

AI 只產生提案；權限由本機應用程式掌管。

### 支援介面

- Windows 白名單網站、資料夾、應用程式及可復原的檔案操作。
- 使用者建立的工作流程與排程。
- Home Assistant 本機控制與健康狀態。
- Google、Microsoft 及 GitHub OAuth 連接器基礎。
- 私人網路行動裝置狀態與命令頁面。
- 應用程式視窗截圖及白名單中的唯讀遠端檔案。
- 本機攝影機存在偵測。
- 分級、可到期、可匯出的本機記憶。

### 四項遠端與智慧家庭邊界

1. 行動裝置遠端：自願啟用、配對裝置 token、狀態與命令，且可撤銷。
2. 智慧家庭：Home Assistant OS 維持獨立於 Windows PC。
3. 攝影機：預設關閉、狀態可見、只在本機處理，且不得靜默錄影。
4. 遠端畫面／檔案：只限應用程式視窗及明確的資料夾白名單。

### 驗收門檻

- 全部 v1.21.9 原始碼回歸測試皆通過。
- 新增的安全、規劃器契約、遠端驗證、注入、白名單、資料庫、工作流程、Home Assistant、備份與生命週期測試皆通過。
- Realtime、轉錄、TTS、嘴型同步、動畫、物理效果、表情選擇、拖曳行為、提醒、任務時序及遷移不得退步。
- 封裝後執行檔必須通過自我測試及重複的乾淨設定檔 smoke test。
- 既有設定檔遷移必須保留身分、模型、語音、記憶、對話、工作紀錄、提醒、動畫及個人設定。
- 遠端、攝影機、雲端及 Home Assistant 元件必須可分別停用；離線桌面核心仍須持續運作。

## 简体中文

### 执行管线

`输入 → 意图 → 结构化计划 → 本地策略 → 预览／确认 → 工具执行 → 结果验证 → 审计／撤销信息`

AI 只生成提案；权限由本地应用程序掌管。

### 支持界面

- Windows 白名单网站、文件夹、应用程序及可恢复的文件操作。
- 用户创建的工作流与计划任务。
- Home Assistant 本地控制与健康状态。
- Google、Microsoft 及 GitHub OAuth 连接器基础。
- 专用网络移动设备状态与命令页面。
- 应用程序窗口截图及白名单中的只读远程文件。
- 本地摄像头存在检测。
- 分级、可过期、可导出的本地记忆。

### 四项远程与智能家居边界

1. 移动设备远程控制：自愿启用、配对设备 token、状态与命令，且可撤销。
2. 智能家居：Home Assistant OS 保持独立于 Windows PC。
3. 摄像头：默认关闭、状态可见、只在本地处理，且不得静默录制。
4. 远程画面／文件：只限应用程序窗口及明确的文件夹白名单。

### 验收门槛

- 全部 v1.21.9 源代码回归测试均通过。
- 新增的安全、规划器契约、远程身份验证、注入、白名单、数据库、工作流、Home Assistant、备份与生命周期测试均通过。
- Realtime、转录、TTS、嘴型同步、动画、物理效果、表情选择、拖动行为、提醒、任务时序及迁移不得退步。
- 封装后可执行文件必须通过自检及重复的干净配置文件 smoke test。
- 现有配置文件迁移必须保留身份、模型、语音、记忆、对话、工作记录、提醒、动画及个人设置。
- 远程、摄像头、云端及 Home Assistant 组件必须可分别禁用；离线桌面核心仍须持续工作。

## English

### Execution pipeline

`input → intent → structured plan → local policy → preview/confirmation → tool execution → result verification → audit/undo information`

The AI produces proposals only; the local application owns authority.

### Supported surfaces

- Windows allowlisted websites, folders, applications, and recoverable file work.
- User-created workflows and schedules.
- Home Assistant local control and health status.
- Google, Microsoft, and GitHub OAuth connector foundations.
- Private-network mobile status and command page.
- App-window screenshots and allowlisted read-only remote files.
- Local camera presence detection.
- Tiered, expiring, exportable local memory.

### Four remote and smart-home boundaries

1. Mobile remote: opt-in, paired-device tokens, status and commands, and revocable.
2. Smart home: Home Assistant OS remains independent from the Windows PC.
3. Camera: off by default, visible, local-only, and no silent recording.
4. Remote screen/files: app window only and explicit folder allowlists.

### Acceptance gates

- All v1.21.9 source regression tests pass.
- New safety, planner-contract, remote-auth, injection, whitelist, database, workflow, Home Assistant, backup, and lifecycle tests pass.
- No regression in Realtime, transcription, TTS, lip sync, animation, physics, expression selection, drag behavior, reminders, task timing, or migration.
- The packaged executable passes self-test and repeated clean-profile smoke tests.
- Existing profile migration preserves identity, models, voices, memories, conversations, work records, reminders, animation, and personal configuration.
- Remote, camera, cloud, and Home Assistant components remain separately disableable; the offline desktop core continues to work.

## 日本語

### 実行パイプライン

`入力 → 意図 → 構造化計画 → ローカルポリシー → プレビュー／確認 → ツール実行 → 結果検証 → 監査／取り消し情報`

AI は提案だけを生成し、権限はローカルアプリケーションが保持します。

### 対応インターフェース

- Windows で許可リストに登録した Web サイト、フォルダー、アプリケーション、および復元可能なファイル操作。
- ユーザーが作成したワークフローとスケジュール。
- Home Assistant のローカル制御と稼働状態。
- Google、Microsoft、GitHub OAuth コネクターの基盤。
- プライベートネットワーク内のモバイル状態およびコマンドページ。
- アプリウィンドウのスクリーンショット、および許可リストに登録した読み取り専用リモートファイル。
- ローカルカメラによる在席検出。
- 階層化、有効期限付き、エクスポート可能なローカルメモリ。

### リモートおよびスマートホームの四つの境界

1. モバイルリモート：オプトイン、ペアリング済み端末の token、状態とコマンドを使用し、取り消し可能とします。
2. スマートホーム：Home Assistant OS は Windows PC から独立した状態を維持します。
3. カメラ：既定で無効、状態を可視化、ローカル処理限定とし、無断録画を禁止します。
4. リモート画面／ファイル：アプリウィンドウと、明示的なフォルダー許可リストだけに限定します。

### 受け入れゲート

- v1.21.9 の全ソース回帰テストが合格します。
- 新しい安全性、プランナー契約、リモート認証、注入、許可リスト、データベース、ワークフロー、Home Assistant、バックアップ、ライフサイクルの各テストが合格します。
- Realtime、文字起こし、TTS、リップシンク、アニメーション、物理効果、表情選択、ドラッグ動作、リマインダー、タスクのタイミング、移行に回帰がありません。
- パッケージ化した実行ファイルが、自己テストと反復するクリーンプロファイル smoke test に合格します。
- 既存プロファイルの移行で、アイデンティティ、モデル、音声、記憶、会話、作業記録、リマインダー、アニメーション、個人設定を維持します。
- リモート、カメラ、クラウド、Home Assistant の各コンポーネントを個別に無効化でき、オフラインデスクトップコアは継続して動作します。
