# 隱私說明／隐私说明／Privacy／プライバシー

## 繁體中文

### 預設儲存在本機

待辦、靈感、設定、工作階段、對話、記憶、連接器中繼資料、權限、工作流程及稽核紀錄均儲存在本機應用程式資料目錄。已驗證的備份儲存在其 `backups` 子目錄。

### 雲端處理

只有使用者啟用相應功能時，才會進行雲端處理：

- OpenAI 會收到完成該次要求所需的文字、音訊或工具規劃內容。
- Google、Microsoft 或 GitHub 會收到經使用者本人 OAuth 同意所授權的 API 要求。
- Home Assistant 會收到本機裝置要求。

助理可使用的長期資料範圍由使用者明確啟用並存於本機資料庫；ChatGPT 帳號歷史位於此範圍之外。

### 相機

相機在場偵測由使用者主動啟用。啟用後，程式只在本機取樣低解析度亮度及動態；影格保持即時暫存，處理後即釋放。相機使用期間，畫面會持續顯示狀態標籤。身分辨識須先安裝可稽核的本機供應器，並由使用者明確登錄身分後啟用。

啟用手勢／視覺融合時，程式在本機以最高 10 Hz 處理手部 21 點骨架，並以最高 1 Hz 使用短時嘴部區域證據；資料會先統一至 selfie 座標系，最長 1.5 秒後失效。原始影像與嘴部裁切保持即時暫存，處理後即釋放。權限、攝影機、模型、時間及信心檢查皆通過時才產生動作；其餘結果統一為未知或保持原狀，以延續既有功能安全性。

### 遠端存取

遠端存取預設關閉。選用的行動版頁面使用保存在瀏覽器工作階段儲存空間中的裝置權杖。遠端截圖只包含應用程式視窗。遠端檔案必須位於使用者允許清單內；金鑰、密碼、憑證、SSH、GnuPG 及應用程式資料等敏感位置均會被封鎖。

### 使用者控制

使用者可隨時完整管理記憶、選定對話、已配對裝置、OAuth 權杖、連接器、允許清單、遠端伺服器與相機，並可立即啟動緊急停止。管理能力包含檢視、編輯、匯出、清除、撤銷及移除。

### 可攜式個人設定檔

可攜式 `.mohan-profile` 檔案包含使用者共用進度，包括對話、記憶、待辦、靈感、工作歷程、提醒、工作流程、角色設定及一般偏好。檔案不包含 DPAPI 機密、OAuth 或 Home Assistant 權杖、已配對裝置權杖、本機允許清單或機器權限。這些檔案仍可能含有私人對話及工作內容，因此必須當作私人文件保存與傳輸。

一般資料庫與一般攜帶檔的手勢資料範圍限於開關、名稱及動作映射等非敏感中繼資料。自訂 21 點骨架樣本只在使用者明確錄製並選擇敏感資料保護流程後，進入受保護的加密儲存或強密碼加密的敏感攜帶內容；原始影像保持即時暫存，處理後即釋放。

檔案清單亦包含隨機產生的安裝識別碼與快照識別碼，用於避免意外重複匯入或匯入較舊資料。這些識別碼不含 Windows 帳號名稱或電腦名稱。

## 简体中文

### 默认存储在本地

任务、灵感、设置、工作会话、对话、记忆、连接器元数据、权限、工作流程及审计记录均存储在本地应用程序数据目录。已验证的备份存储在其 `backups` 子目录。

### 云端处理

只有用户启用相应功能时，才会进行云端处理：

- OpenAI 会收到完成该次请求所需的文本、音频或工具规划内容。
- Google、Microsoft 或 GitHub 会收到经用户本人 OAuth 同意所授权的 API 请求。
- Home Assistant 会收到本地设备请求。

本程序不会自动让助理取得 ChatGPT 账号历史。长期记忆是由用户控制、明确启用的本地数据库。

### 摄像头

摄像头在场检测由用户主动启用。启用后，程序只在本地采样低分辨率亮度及动态；帧保持即时暂存，处理后即释放。摄像头使用期间，界面会持续显示状态标签。身份识别须先安装可审计的本地提供程序，并由用户明确登记身份后启用。

启用手势／视觉融合时，程序在本地以最高 10 Hz 处理手部 21 点骨架，并以最高 1 Hz 使用短时嘴部区域证据；数据会先统一到 selfie 坐标系，最长 1.5 秒后失效。原始图像与嘴部裁剪保持即时暂存，处理后即释放。权限、摄像头、模型、时间及置信度检查全部通过时才产生动作；其余结果统一为未知或保持原状，以延续现有功能的安全性。

### 远程访问

远程访问默认关闭。可选的移动版页面使用保存在浏览器会话存储空间中的设备令牌。远程截图只包含应用程序窗口。远程文件必须位于用户允许列表内；密钥、密码、凭据、SSH、GnuPG 及应用程序数据等敏感位置均会被阻止。

### 用户控制

用户可以随时完整管理记忆、选定对话、已配对设备、OAuth 令牌、连接器、允许列表、远程服务器与摄像头，并可立即启动紧急停止。管理能力包括查看、编辑、导出、清除、撤销及移除。

### 可移植个人配置文件

可移植 `.mohan-profile` 文件包含用户共享进度，包括对话、记忆、任务、灵感、工作历史、提醒、工作流程、角色设置及一般偏好。文件不包含 DPAPI 机密、OAuth 或 Home Assistant 令牌、已配对设备令牌、本地允许列表或机器权限。这些文件仍可能含有私人对话及工作内容，因此必须作为私人文档保存与传输。

普通数据库与普通可移植文件的手势数据范围限于开关、名称及动作映射等非敏感元数据。自定义 21 点骨架样本只在用户明确录制并选择敏感数据保护流程后，进入受保护的加密存储或强密码加密的敏感可移植内容；原始图像保持即时暂存，处理后即释放。

文件清单也包含随机生成的安装标识符与快照标识符，用于避免意外重复导入或导入较旧数据。这些标识符不含 Windows 账号名称或计算机名称。

## English

### Local by default

Tasks, ideas, settings, work sessions, conversations, memories, connector metadata, permissions, workflows, and audit records are stored in the local application-data directory. Verified backups are stored in its `backups` subdirectory.

### Cloud processing

Cloud processing occurs only when a user enables the relevant feature:

- OpenAI receives the text, audio, or tool-planning context needed for the request.
- Google, Microsoft, or GitHub receives API requests authorized through the user's own OAuth consent.
- Home Assistant receives local device requests.

The assistant's long-term data scope is explicitly enabled by the user and stored in a local database; ChatGPT account history is outside that scope.

### Camera

Camera presence detection is off by default. When enabled, the application samples low-resolution brightness and movement locally; frames are neither stored nor uploaded. A visible status label remains active while the camera is in use. Identity recognition remains disabled unless a separate auditable local provider is installed and the user explicitly enrolls identities.

When gesture and vision fusion is enabled, the application processes 21-point hand skeletons locally at up to 10 Hz and uses short-lived mouth-region evidence at up to 1 Hz. Inputs are normalized into one selfie coordinate system and expire after at most 1.5 seconds. Raw images and mouth crops remain transient and are released after processing. An action is produced only when permission, camera, model, timing, and confidence checks all pass; every other result resolves to unknown or preserves the current state, maintaining established safety.

### Remote access

Remote access is off by default. The optional mobile page uses a device token kept in browser session storage. Remote screenshots contain only the application window. Remote files must be inside a user allowlist; sensitive key, password, credential, SSH, GnuPG, and application-data locations are blocked.

### User control

Users can view, edit, delete, and export memories; clear selected conversations; revoke paired devices and OAuth tokens; disable connectors; remove allowlists; stop the remote server; stop the camera; and use emergency stop at any time.

### Portable profile

Portable `.mohan-profile` files contain the user's shared progress, including conversations, memories, tasks, ideas, work history, reminders, workflows, persona, and general preferences. Their scope excludes DPAPI secrets, OAuth and Home Assistant tokens, paired-device tokens, local allowlists, and machine permissions. These files can still contain private conversations and work content, so they must be stored and transferred as private documents.

The gesture-data scope of ordinary databases and portable profiles consists only of non-sensitive metadata such as switches, names, and action mappings. Custom 21-point skeleton samples may enter protected encrypted storage or strong-password-encrypted sensitive portable content only after explicit recording and selection of the sensitive-data protection flow. Raw images remain transient and are released after processing.

The manifest also contains randomly generated installation and snapshot identifiers used to prevent accidental repeated or older imports. These identifiers consist solely of random values, independent of the Windows account name and computer name.

## 日本語

### ローカル保存が既定

タスク、アイデア、設定、作業セッション、会話、記憶、コネクターのメタデータ、権限、ワークフロー、監査記録は、ローカルのアプリケーションデータディレクトリに保存されます。検証済みのバックアップは、その `backups` サブディレクトリに保存されます。

### クラウド処理

クラウド処理は、ユーザーが該当機能を有効にした場合にのみ行われます。

- OpenAI は、その要求に必要なテキスト、音声、またはツール計画のコンテキストを受信します。
- Google、Microsoft、または GitHub は、ユーザー自身の OAuth 同意によって許可された API 要求を受信します。
- Home Assistant は、ローカルデバイスからの要求を受信します。

アシスタントが使用できる長期データの範囲は、ユーザーが明示的に有効化し、ローカルデータベースに保存した内容です。ChatGPT アカウントの履歴はこの範囲外です。

### カメラ

カメラによる在席検知はユーザーが明示的に有効化します。有効化後、アプリケーションは低解像度の明るさと動きをローカルでサンプリングし、フレームを処理後に解放します。カメラの使用中は、状態ラベルが画面に表示され続けます。本人認識は、監査可能なローカルプロバイダーを導入し、ユーザーが本人情報を明示的に登録した後に有効化できます。

ジェスチャーと視覚の融合を有効にすると、アプリケーションは 21 点の手骨格を最大 10 Hz でローカル処理し、短時間だけ有効な口元領域の証拠を最大 1 Hz で使用します。入力は同一の selfie 座標系へ正規化され、最長 1.5 秒で失効します。元画像と口元の切り抜きは一時的に処理され、その後解放されます。権限、カメラ、モデル、時刻、信頼度の検査がすべて通過した場合にのみ動作を生成し、それ以外は不明または現状維持として既存機能の安全性を保ちます。

### リモートアクセス

リモートアクセスはユーザーが明示的に有効化します。任意で使用するモバイルページは、ブラウザーのセッションストレージに保持されるデバイストークンを使用します。リモートスクリーンショットの範囲はアプリケーションウィンドウに限定されます。リモートファイルの範囲はユーザーの許可リスト内に限定され、キー、パスワード、認証情報、SSH、GnuPG、アプリケーションデータなどの機密性が高い場所は保護領域として扱われます。

### ユーザーによる管理

ユーザーはいつでも、記憶、選択した会話、ペアリング済みデバイス、OAuth トークン、コネクター、許可リスト、リモートサーバー、カメラを一括管理し、緊急停止を即時に実行できます。管理機能には表示、編集、エクスポート、消去、取り消し、削除が含まれます。

### ポータブルプロファイル

ポータブル `.mohan-profile` ファイルには、会話、記憶、タスク、アイデア、作業履歴、リマインダー、ワークフロー、ペルソナ、一般設定など、ユーザーの共有進捗が含まれます。DPAPI の機密情報、OAuth または Home Assistant のトークン、ペアリング済みデバイスのトークン、ローカル許可リスト、マシン権限は含まれません。これらのファイルには非公開の会話や作業内容が含まれる可能性があるため、私的文書として保存および転送する必要があります。

通常のデータベースと可搬プロファイルのジェスチャーデータ範囲は、有効状態、名前、動作割り当てなどの非機密メタデータに限定されます。カスタム 21 点骨格サンプルは、利用者が明示的に記録して機密データ保護フローを選択した場合に限り、保護された暗号化ストレージまたは強力なパスワードで暗号化した機密可搬内容へ保存できます。元画像は一時的に処理され、その後解放されます。

マニフェストには、誤って同じデータや古いデータを取り込むことを防ぐために使用する、ランダム生成のインストール識別子とスナップショット識別子も含まれます。これらの識別子には、Windows のアカウント名やコンピューター名は含まれません。
