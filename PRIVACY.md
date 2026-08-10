# 隱私說明／隐私说明／Privacy／プライバシー

## 繁體中文

### 預設儲存在本機

待辦、靈感、設定、工作階段、對話、記憶、連接器中繼資料、權限、工作流程及稽核紀錄均儲存在本機應用程式資料目錄。已驗證的備份儲存在其 `backups` 子目錄。

### 雲端處理

只有使用者啟用相應功能時，才會進行雲端處理：

- OpenAI 會收到完成該次要求所需的文字、音訊或工具規劃內容。
- Google、Microsoft 或 GitHub 會收到經使用者本人 OAuth 同意所授權的 API 要求。
- Home Assistant 會收到本機裝置要求。

本程式不會自動讓助理取得 ChatGPT 帳號歷史。長期記憶是由使用者控制、明確啟用的本機資料庫。

### 相機

相機在場偵測預設關閉。啟用後，程式只在本機取樣低解析度亮度及動態；影格不會儲存或上傳。相機使用期間，畫面會持續顯示狀態標籤。除非另行安裝可稽核的本機供應器，且使用者明確登錄身分，否則身分辨識維持停用。

### 遠端存取

遠端存取預設關閉。選用的行動版頁面使用保存在瀏覽器工作階段儲存空間中的裝置權杖。遠端截圖只包含應用程式視窗。遠端檔案必須位於使用者允許清單內；金鑰、密碼、憑證、SSH、GnuPG 及應用程式資料等敏感位置均會被封鎖。

### 使用者控制

使用者可隨時檢視、編輯、刪除及匯出記憶；清除選定對話；撤銷已配對裝置及 OAuth 權杖；停用連接器；移除允許清單；停止遠端伺服器；停止相機；以及使用緊急停止。

### 可攜式個人設定檔

可攜式 `.mohan-profile` 檔案包含使用者共用進度，包括對話、記憶、待辦、靈感、工作歷程、提醒、工作流程、角色設定及一般偏好。檔案不包含 DPAPI 機密、OAuth 或 Home Assistant 權杖、已配對裝置權杖、本機允許清單或機器權限。這些檔案仍可能含有私人對話及工作內容，因此必須當作私人文件保存與傳輸。

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

摄像头在场检测默认关闭。启用后，程序只在本地采样低分辨率亮度及动态；帧不会存储或上传。摄像头使用期间，界面会持续显示状态标签。除非另行安装可审计的本地提供程序，且用户明确登记身份，否则身份识别保持停用。

### 远程访问

远程访问默认关闭。可选的移动版页面使用保存在浏览器会话存储空间中的设备令牌。远程截图只包含应用程序窗口。远程文件必须位于用户允许列表内；密钥、密码、凭据、SSH、GnuPG 及应用程序数据等敏感位置均会被阻止。

### 用户控制

用户可以随时查看、编辑、删除及导出记忆；清除选定对话；撤销已配对设备及 OAuth 令牌；停用连接器；移除允许列表；停止远程服务器；停止摄像头；以及使用紧急停止。

### 可移植个人配置文件

可移植 `.mohan-profile` 文件包含用户共享进度，包括对话、记忆、任务、灵感、工作历史、提醒、工作流程、角色设置及一般偏好。文件不包含 DPAPI 机密、OAuth 或 Home Assistant 令牌、已配对设备令牌、本地允许列表或机器权限。这些文件仍可能含有私人对话及工作内容，因此必须作为私人文档保存与传输。

文件清单也包含随机生成的安装标识符与快照标识符，用于避免意外重复导入或导入较旧数据。这些标识符不含 Windows 账号名称或计算机名称。

## English

### Local by default

Tasks, ideas, settings, work sessions, conversations, memories, connector metadata, permissions, workflows, and audit records are stored in the local application-data directory. Verified backups are stored in its `backups` subdirectory.

### Cloud processing

Cloud processing occurs only when a user enables the relevant feature:

- OpenAI receives the text, audio, or tool-planning context needed for the request.
- Google, Microsoft, or GitHub receives API requests authorized through the user's own OAuth consent.
- Home Assistant receives local device requests.

The application does not make ChatGPT account history automatically available to the assistant. Long-term memory is an explicit local database controlled by the user.

### Camera

Camera presence detection is off by default. When enabled, the application samples low-resolution brightness and movement locally; frames are neither stored nor uploaded. A visible status label remains active while the camera is in use. Identity recognition remains disabled unless a separate auditable local provider is installed and the user explicitly enrolls identities.

### Remote access

Remote access is off by default. The optional mobile page uses a device token kept in browser session storage. Remote screenshots contain only the application window. Remote files must be inside a user allowlist; sensitive key, password, credential, SSH, GnuPG, and application-data locations are blocked.

### User control

Users can view, edit, delete, and export memories; clear selected conversations; revoke paired devices and OAuth tokens; disable connectors; remove allowlists; stop the remote server; stop the camera; and use emergency stop at any time.

### Portable profile

Portable `.mohan-profile` files contain the user's shared progress, including conversations, memories, tasks, ideas, work history, reminders, workflows, persona, and general preferences. They do not contain DPAPI secrets, OAuth or Home Assistant tokens, paired-device tokens, local allowlists, or machine permissions. These files can still contain private conversations and work content, so they must be stored and transferred as private documents.

The manifest also contains randomly generated installation and snapshot identifiers used to prevent accidental repeated or older imports. These identifiers do not contain the Windows account name or computer name.

## 日本語

### ローカル保存が既定

タスク、アイデア、設定、作業セッション、会話、記憶、コネクターのメタデータ、権限、ワークフロー、監査記録は、ローカルのアプリケーションデータディレクトリに保存されます。検証済みのバックアップは、その `backups` サブディレクトリに保存されます。

### クラウド処理

クラウド処理は、ユーザーが該当機能を有効にした場合にのみ行われます。

- OpenAI は、その要求に必要なテキスト、音声、またはツール計画のコンテキストを受信します。
- Google、Microsoft、または GitHub は、ユーザー自身の OAuth 同意によって許可された API 要求を受信します。
- Home Assistant は、ローカルデバイスからの要求を受信します。

このアプリケーションが ChatGPT アカウントの履歴をアシスタントへ自動的に提供することはありません。長期記憶は、ユーザーが管理し、明示的に使用するローカルデータベースです。

### カメラ

カメラによる在席検知は既定で無効です。有効にすると、アプリケーションは低解像度の明るさと動きをローカルでサンプリングしますが、フレームを保存またはアップロードしません。カメラの使用中は、状態ラベルが画面に表示され続けます。別途監査可能なローカルプロバイダーを導入し、ユーザーが明示的に本人情報を登録しない限り、本人認識は無効のままです。

### リモートアクセス

リモートアクセスは既定で無効です。任意で使用するモバイルページは、ブラウザーのセッションストレージに保持されるデバイストークンを使用します。リモートスクリーンショットには、アプリケーションウィンドウだけが含まれます。リモートファイルはユーザーの許可リスト内になければならず、キー、パスワード、認証情報、SSH、GnuPG、アプリケーションデータなどの機密性が高い場所はブロックされます。

### ユーザーによる管理

ユーザーはいつでも、記憶の表示、編集、削除、エクスポート、選択した会話の消去、ペアリング済みデバイスと OAuth トークンの取り消し、コネクターの無効化、許可リストの削除、リモートサーバーの停止、カメラの停止、緊急停止を行えます。

### ポータブルプロファイル

ポータブル `.mohan-profile` ファイルには、会話、記憶、タスク、アイデア、作業履歴、リマインダー、ワークフロー、ペルソナ、一般設定など、ユーザーの共有進捗が含まれます。DPAPI の機密情報、OAuth または Home Assistant のトークン、ペアリング済みデバイスのトークン、ローカル許可リスト、マシン権限は含まれません。これらのファイルには非公開の会話や作業内容が含まれる可能性があるため、私的文書として保存および転送する必要があります。

マニフェストには、誤って同じデータや古いデータを取り込むことを防ぐために使用する、ランダム生成のインストール識別子とスナップショット識別子も含まれます。これらの識別子には、Windows のアカウント名やコンピューター名は含まれません。
