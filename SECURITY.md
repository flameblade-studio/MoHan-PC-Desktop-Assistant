# 安全政策／安全政策／Security Policy／セキュリティポリシー

## 繁體中文

### 支援版本

安全修正會套用至目前的公開預覽版及最新開發分支。較舊的預覽版不保證逐版修補。實際可行時，回報問題前請先使用最新 Release 或目前的 `main` 分支確認仍可重現。

### 信任邊界

模型不是授權主體。工具只有在本機政策引擎授權後才能執行。模型回覆、網頁、電子郵件、檔案、語音轉錄、遠端要求、工作流程或 Home Assistant 裝置都不能自行取得權限。

風險等級如下：

- 綠色：讀取、搜尋、狀態查詢及允許清單內的開啟操作。
- 藍色：可復原的本機變更及一般智慧家庭控制。
- 黃色：具有外部效果的操作、相機、遠端畫面、行事曆變更及傳送操作。
- 紅色：破壞性或涉及安全的重要操作。

黃色操作一律需要確認。紅色操作需要兩次確認，否則會被封鎖。付款、購買、匯出密碼、停用安全功能、任意 Shell 及系統管理員 Shell 永久不得自動化。

### 憑證、更新與發行供應鏈

OpenAI、Home Assistant 及 OAuth 機密使用 Windows DPAPI，並分別儲存在獨立檔案。這些資料不得提交至 Git、`SQLite`、紀錄、截圖、匯出的記憶或支援套件。

GitHub 機密掃描與推送保護會持續啟用。由於 GitHub 不向個人公開儲存庫提供帳號層級的非供應商模式掃描或合作夥伴權杖有效性檢查，每個 Pull Request 及 `main` 推送另會執行完整歷史 Gitleaks 掃描。此補償控制能偵測供應商權杖、私鑰、連線字串及其他通用憑證模式，而無須在測試中放入任何真實憑證。

程式內更新器只接受透過 HTTPS 來自 GitHub 官方儲存庫的資訊清單及安裝程式。安裝程式檔名、宣告大小、儲存庫、Release 標籤、語意版本及 SHA256 必須全部驗證通過，才會向使用者提供啟動選項。未經明確確認，絕不安裝更新。

功能受限的 macOS／Linux Preview 安裝包刻意不提供 API 金鑰、OAuth 或 Home Assistant 權杖輸入。在原生 Keychain／Secret Service 介接器分別完成實作、審查及實機驗證前，不得啟用受保護功能。封裝成功絕不構成允許明文備援的理由。

Release 工作流程會將每個 GitHub Action 固定至完整 commit SHA。Linux AppImage 建置工具只能從 AppImage 官方儲存庫下載，且必須與已審查的 SHA-256 完全相符後才能執行。macOS 封裝只使用 runner 原生 Apple 工具。發布資產會附上 `SHA256SUMS`、CycloneDX SBOM 及 GitHub Artifact Attestations。

### 遠端存取

遠端服務預設停用。若要綁定非 loopback 位址，使用者必須明確確認已使用 Tailscale 等加密私人傳輸。不得將服務連接埠轉送至公網。

遠端裝置會取得隨機一次性配對權杖，而資料庫只在 `SQLite` 中保存其 SHA-256 雜湊。權杖可以撤銷。端點採用裝置個別權限、要求大小限制、速率限制、no-store 標頭及受保護檔案規則。

### 智慧家庭

不論模型如何描述，門鎖、警報、暖爐及氣候設備都維持高風險。助理不提供任意 Home Assistant 服務呼叫。實體控制器與生命安全警報必須可獨立運作。

### 回報安全漏洞

請勿將尚未修補的漏洞建立為公開 Issue。請使用 GitHub 的[私人漏洞通報管道](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/security/advisories/new)，並提供：

- 受影響版本及 Windows 版本；
- 最小可重現步驟；
- 預期與實際安全邊界；
- 影響，以及利用漏洞是否需要本機存取；
- 僅限已去識別化的紀錄或截圖。

絕不得提供真實 API 金鑰、OAuth 權杖、地址、臉部、私人電子郵件、錄音、資料庫檔案或 Home Assistant 網址。若無法使用私人通報，請建立標題為 `[Security contact request]` 的公開 Issue，但不得附上技術細節，以便另行安排私人管道。

### 回應目標

維護者目標是在七日內確認收到通報，並於十四日內提供初步研判。這些是處理目標，不是服務保證。請在協調修正完成前暫緩公開揭露。

## 简体中文

### 支持版本

安全修复会应用至当前公开预览版及最新开发分支。较旧的预览版不保证逐版修补。实际可行时，报告问题前请先使用最新 Release 或当前的 `main` 分支确认仍可复现。

### 信任边界

模型不是授权主体。工具只有在本地政策引擎授权后才能执行。模型回复、网页、电子邮件、文件、语音转录、远程请求、工作流程或 Home Assistant 设备都不能自行取得权限。

风险等级如下：

- 绿色：读取、搜索、状态查询及允许列表内的打开操作。
- 蓝色：可恢复的本地变更及一般智能家居控制。
- 黄色：具有外部效果的操作、摄像头、远程画面、日历变更及发送操作。
- 红色：破坏性或涉及安全的重要操作。

黄色操作一律需要确认。红色操作需要两次确认，否则会被阻止。付款、购买、导出密码、停用安全功能、任意 Shell 及系统管理员 Shell 永久不得自动化。

### 凭据、更新与发布供应链

OpenAI、Home Assistant 及 OAuth 机密使用 Windows DPAPI，并分别存储在独立文件。不得将这些数据提交至 Git、`SQLite`、日志、截图、导出的记忆或支持包。

GitHub 机密扫描与推送保护会持续启用。由于 GitHub 不向个人公开仓库提供账号级别的非提供商模式扫描或合作伙伴令牌有效性检查，每个 Pull Request 及 `main` 推送还会执行完整历史 Gitleaks 扫描。此补偿控制能够检测提供商令牌、私钥、连接字符串及其他通用凭据模式，而无需在测试中放入任何真实凭据。

程序内更新器只接受通过 HTTPS 来自 GitHub 官方仓库的清单及安装程序。安装程序文件名、声明大小、仓库、Release 标签、语义版本及 SHA256 必须全部验证通过，才会向用户提供启动选项。未经明确确认，绝不安装更新。

功能受限的 macOS／Linux Preview 安装包刻意不提供 API 密钥、OAuth 或 Home Assistant 令牌输入。在原生 Keychain／Secret Service 适配器分别完成实现、审查及真机验证前，不得启用受保护功能。封装成功绝不构成允许明文备用方案的理由。

Release 工作流程会将每个 GitHub Action 固定至完整 commit SHA。Linux AppImage 构建工具只能从 AppImage 官方仓库下载，且必须与已审查的 SHA-256 完全相符后才能执行。macOS 封装只使用 runner 原生 Apple 工具。发布资产会附上 `SHA256SUMS`、CycloneDX SBOM 及 GitHub Artifact Attestations。

### 远程访问

远程服务默认停用。若要绑定非 loopback 地址，用户必须明确确认已使用 Tailscale 等加密私人传输。不得将服务端口转发至公网。

远程设备会取得随机一次性配对令牌，而数据库只在 `SQLite` 中保存其 SHA-256 哈希。令牌可以撤销。端点采用设备单独权限、请求大小限制、速率限制、no-store 标头及受保护文件规则。

### 智能家居

无论模型如何描述，门锁、警报、暖炉及气候设备都保持高风险。助理不提供任意 Home Assistant 服务调用。实体控制器与生命安全警报必须可独立运行。

### 报告安全漏洞

不得将尚未修补的漏洞创建为公开 Issue。请使用 GitHub 的[私人漏洞报告渠道](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/security/advisories/new)，并提供：

- 受影响版本及 Windows 版本；
- 最小可复现步骤；
- 预期与实际安全边界；
- 影响，以及利用漏洞是否需要本地访问；
- 仅限已去标识化的日志或截图。

绝不得提供真实 API 密钥、OAuth 令牌、地址、面部、私人电子邮件、录音、数据库文件或 Home Assistant 网址。若无法使用私人报告，请创建标题为 `[Security contact request]` 的公开 Issue，但不得附上技术细节，以便另行安排私人渠道。

### 响应目标

维护者目标是在七日内确认收到报告，并于十四日内提供初步研判。这些是处理目标，不是服务保证。请在协调修复完成前暂缓公开披露。

## English

### Supported versions

Security fixes are applied to the current public preview and the latest development branch. Older preview builds may not receive individual patches. Whenever practical, reproduce a problem with the newest Release or current `main` branch before reporting it.

### Trust boundaries

The model is not an authority. Tools execute only when authorized by the local policy engine. A model response, webpage, email, file, voice transcript, remote request, workflow, or Home Assistant device cannot grant itself permission.

Risk levels are:

- Green: read, search, status, and allowlisted open actions.
- Blue: reversible local changes and ordinary smart-home controls.
- Yellow: external effects, camera, remote screen, calendar changes, and sending.
- Red: destructive or safety-sensitive operations.

Yellow actions always require confirmation. Red actions require two confirmations or are blocked. Payment, purchase, password export, disabling security, arbitrary Shell, and administrator Shell are permanently non-automatable.

### Credentials, updates, and release supply chain

OpenAI, Home Assistant, and OAuth secrets use Windows DPAPI and separate files. They must not be committed to Git, `SQLite`, logs, screenshots, exported memory, or support bundles.

GitHub secret scanning and push protection remain enabled. Because GitHub does not expose account-level non-provider pattern scanning or partner-token validity checks to personal public repositories, every Pull Request and `main` push additionally receives a full-history Gitleaks scan. This compensating control detects provider tokens, private keys, connection strings, and other generic credential patterns without placing any real credential in a test.

The in-app updater accepts manifests and installers only from the official GitHub repository over HTTPS. Installer filename, declared size, repository, Release tag, semantic version, and SHA256 must all validate before the user is offered the option to launch it. Updates are never installed without explicit confirmation.

The limited macOS/Linux Preview packages intentionally expose no API-key, OAuth, or Home Assistant token input. Native Keychain/Secret Service adapters must be separately implemented, reviewed, and device-validated before protected features can be enabled. Packaging success never permits a plaintext fallback.

Release workflows pin every GitHub Action to a full commit SHA. The Linux AppImage builder is downloaded only from the official AppImage repository and must match its reviewed SHA-256 before execution. macOS packaging uses only runner-native Apple tools. Published assets receive `SHA256SUMS`, a CycloneDX SBOM, and GitHub Artifact Attestations.

### Remote access

Remote service is disabled by default. Non-loopback binding requires an explicit acknowledgement that an encrypted private transport such as Tailscale is in use. Do not port-forward the service to the public internet.

Remote devices receive random one-time pairing tokens, while the database stores only their SHA-256 hashes in `SQLite`. Tokens can be revoked. Endpoints use per-device permissions, request-size limits, rate limiting, no-store headers, and protected-file rules.

### Smart home

Locks, alarms, heaters, and climate equipment remain high risk regardless of model wording. The assistant does not expose arbitrary Home Assistant service calls. Keep physical controls and life-safety alarms operational independently.

### Reporting a vulnerability

Do not open a public Issue for an unpatched vulnerability. Use GitHub's [private vulnerability reporting channel](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/security/advisories/new) and include:

- the affected version and Windows version;
- the smallest reproducible sequence;
- the expected and observed security boundaries;
- the impact and whether exploitation requires local access;
- redacted logs or screenshots only.

Never include real API keys, OAuth tokens, addresses, faces, private email, recordings, database files, or Home Assistant URLs. If private reporting is unavailable, open a public Issue titled `[Security contact request]` without technical details so that a private channel can be arranged.

### Response targets

The maintainer aims to acknowledge a report within seven days and provide an initial assessment within fourteen days. These are targets rather than service guarantees. Please allow time for a coordinated fix before public disclosure.

## 日本語

### サポート対象バージョン

セキュリティ修正は、現在の公開プレビュー版と最新の開発ブランチに適用されます。古いプレビュー版には個別の修正が提供されない場合があります。可能であれば、問題を報告する前に、最新の Release または現在の `main` ブランチで再現することを確認してください。

### 信頼境界

モデルは権限主体ではありません。ツールは、ローカルポリシーエンジンによって許可された場合にのみ実行されます。モデルの応答、ウェブページ、電子メール、ファイル、音声文字起こし、リモート要求、ワークフロー、Home Assistant デバイスが、自らに権限を付与することはできません。

リスクレベルは次のとおりです。

- 緑：読み取り、検索、状態確認、許可リスト内のオープン操作。
- 青：元に戻せるローカル変更と通常のスマートホーム制御。
- 黄：外部への影響、カメラ、リモート画面、カレンダー変更、送信操作。
- 赤：破壊的な操作または安全性に関わる操作。

黄色の操作には常に確認が必要です。赤色の操作には二回の確認が必要であり、それ以外はブロックされます。支払い、購入、パスワードのエクスポート、セキュリティの無効化、任意の Shell、管理者 Shell は、恒久的に自動化できません。

### 認証情報、更新、リリースサプライチェーン

OpenAI、Home Assistant、OAuth の機密情報には Windows DPAPI を使用し、それぞれ別ファイルに保存します。これらを Git、`SQLite`、ログ、スクリーンショット、エクスポートされた記憶、サポートバンドルへ含めてはなりません。

GitHub のシークレットスキャンと push protection は有効なまま維持します。GitHub は個人の公開リポジトリに対して、アカウント単位の非プロバイダーパターンスキャンやパートナートークンの有効性確認を提供していないため、各 Pull Request と `main` への push では、全履歴を対象とする Gitleaks スキャンも実行します。この補完的な制御により、実在する認証情報をテストへ入れることなく、プロバイダーのトークン、秘密鍵、接続文字列、その他の一般的な認証情報パターンを検出します。

アプリ内アップデーターは、HTTPS 経由で GitHub の公式リポジトリから取得したマニフェストとインストーラーだけを受け入れます。ユーザーへ起動の選択肢を提示する前に、インストーラーのファイル名、申告サイズ、リポジトリ、Release タグ、セマンティックバージョン、SHA256 がすべて検証されなければなりません。明示的な確認なしに更新をインストールすることはありません。

機能が制限された macOS／Linux Preview パッケージは、API キー、OAuth、Home Assistant トークンの入力欄を意図的に提供しません。ネイティブの Keychain／Secret Service アダプターを個別に実装、レビューし、実機で検証するまで、保護対象の機能を有効にしてはなりません。パッケージ作成の成功を、平文フォールバックの許可理由にすることはできません。

Release ワークフローでは、すべての GitHub Action を完全な commit SHA に固定します。Linux AppImage ビルダーは AppImage の公式リポジトリからのみダウンロードし、レビュー済みの SHA-256 と完全に一致した場合に限り実行します。macOS のパッケージ作成には runner 標準の Apple ツールだけを使用します。公開アセットには `SHA256SUMS`、CycloneDX SBOM、GitHub Artifact Attestations が付属します。

### リモートアクセス

リモートサービスは既定で無効です。loopback 以外のアドレスへバインドするには、Tailscale などの暗号化されたプライベート転送を使用していることを明示的に確認する必要があります。サービスを公開インターネットへポートフォワードしないでください。

リモートデバイスにはランダムな一回限りのペアリングトークンを発行し、データベースはその SHA-256 ハッシュだけを `SQLite` に保存します。トークンは取り消せます。エンドポイントには、デバイス単位の権限、要求サイズ制限、レート制限、no-store ヘッダー、保護対象ファイルの規則を適用します。

### スマートホーム

モデルの表現にかかわらず、錠、警報、暖房機器、空調機器は高リスクのままです。アシスタントは任意の Home Assistant サービス呼び出しを公開しません。物理操作系と生命安全警報は、独立して動作できる状態を維持してください。

### 脆弱性の報告

未修正の脆弱性について公開 Issue を作成しないでください。GitHub の[非公開脆弱性報告窓口](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/security/advisories/new)を使用し、次の情報を提供してください。

- 影響を受けるバージョンと Windows のバージョン。
- 最小限の再現手順。
- 期待されるセキュリティ境界と実際のセキュリティ境界。
- 影響、および悪用にローカルアクセスが必要かどうか。
- 編集済みのログまたはスクリーンショットのみ。

実在する API キー、OAuth トークン、住所、顔、個人用電子メール、録音、データベースファイル、Home Assistant URL を決して含めないでください。非公開報告を利用できない場合は、技術的詳細を含めず、`[Security contact request]` というタイトルで公開 Issue を作成し、非公開の連絡経路を調整してください。

### 対応目標

メンテナーは、七日以内の受領確認と十四日以内の初期評価を目標とします。これは対応目標であり、サービス保証ではありません。修正を調整する時間を確保し、完了するまで公開を控えてください。
