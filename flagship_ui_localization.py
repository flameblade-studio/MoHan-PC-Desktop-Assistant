from __future__ import annotations

lazy import re
lazy from dataclasses import dataclass
lazy from typing import Any

lazy from language_support import canonical_ui_language

_TRANSLATION_INDEX = frozendict({"zh-CN": 0, "en": 1, "ja-JP": 2})


def _translations(
    simplified_chinese: str,
    english: str,
    japanese: str,
) -> tuple[str, str, str]:
    return simplified_chinese, english, japanese


# Traditional Chinese is the canonical source text and remains the default.
# Every non-default language is kept beside it so missing translations fail
# immediately instead of silently leaking the wrong language into the UI.
FLAGSHIP_TRANSLATIONS = frozendict({
    # Common controls and top-level navigation.
    "儲存": _translations("保存", "Save", "保存"),
    "取消": _translations("取消", "Cancel", "キャンセル"),
    "確定": _translations("确定", "OK", "OK"),
    "緊急停止所有工具與遠端操作（Esc）": _translations(
        "紧急停止所有工具与远程操作（Esc）",
        "Emergency stop for all tools and remote operations (Esc)",
        "すべてのツールとリモート操作を緊急停止（Esc）",
    ),
    "任務中心": _translations("任务中心", "Task Center", "タスクセンター"),
    "工作流程": _translations("工作流", "Workflows", "ワークフロー"),
    "雲端連接器": _translations("云端连接器", "Cloud Connectors", "クラウド接続"),
    "智慧家庭": _translations("智能家居", "Smart Home", "スマートホーム"),
    "遠端與隱私": _translations(
        "远程与隐私", "Remote & Privacy", "リモートとプライバシー"
    ),
    "安全權限": _translations("安全权限", "Security Permissions", "セキュリティ権限"),
    "稽核紀錄": _translations("审计记录", "Audit Log", "監査ログ"),
    # Workflow editor.
    "新增安全工作流程": _translations(
        "新增安全工作流",
        "Add a Safe Workflow",
        "安全なワークフローを追加",
    ),
    "手動執行": _translations("手动执行", "Run manually", "手動で実行"),
    "每天固定時間": _translations(
        "每天固定时间", "Daily at a set time", "毎日指定時刻"
    ),
    "開始工作時": _translations("开始工作时", "When work starts", "作業開始時"),
    "第一次與高風險操作先預覽": _translations(
        "首次与高风险操作先预览",
        "Preview the first run and high-risk actions",
        "初回実行と高リスク操作を事前確認",
    ),
    "流程名稱": _translations("流程名称", "Workflow name", "ワークフロー名"),
    "啟動方式": _translations("启动方式", "Trigger", "起動条件"),
    "執行時間": _translations("执行时间", "Run time", "実行時刻"),
    "每行一個步驟，格式：能力｜說明｜參數。\n"
    "範例：open_web｜開啟工作網站｜https://example.com\n"
    "範例：home_control｜開啟書房燈｜light.study,turn_on": _translations(
        "每行一个步骤，格式：能力｜说明｜参数。\n"
        "示例：open_web｜打开工作网站｜https://example.com\n"
        "示例：home_control｜打开书房灯｜light.study,turn_on",
        "Enter one step per line as: capability | description | arguments.\n"
        "Example: open_web | Open the work site | https://example.com\n"
        "Example: home_control | Turn on the study light | light.study,turn_on",
        "1 行に 1 ステップを「機能｜説明｜引数」の形式で入力します。\n"
        "例：open_web｜作業サイトを開く｜https://example.com\n"
        "例：home_control｜書斎の照明をつける｜light.study,turn_on",
    ),
    "open_web｜開啟工作網站｜https://example.com": _translations(
        "open_web｜打开工作网站｜https://example.com",
        "open_web | Open the work site | https://example.com",
        "open_web｜作業サイトを開く｜https://example.com",
    ),
    "{capability} 參數格式必須是 entity_id,service": _translations(
        "{capability} 参数格式必须是 entity_id,service",
        "{capability} arguments must use entity_id,service",
        "{capability} の引数は entity_id,service 形式で指定してください",
    ),
    "{capability} 的參數必須是 JSON 物件": _translations(
        "{capability} 的参数必须是 JSON 对象",
        "Arguments for {capability} must be a JSON object",
        "{capability} の引数は JSON オブジェクトで指定してください",
    ),
    "步驟格式不正確：{line}": _translations(
        "步骤格式不正确：{line}",
        "Invalid step format: {line}",
        "ステップの形式が正しくありません：{line}",
    ),
    # Capability labels.
    "讀取狀態與摘要": _translations(
        "读取状态与摘要", "Read status and summary", "状態と概要を読み取る"
    ),
    "搜尋白名單資料夾": _translations(
        "搜索白名单文件夹", "Search allowlisted folders", "許可済みフォルダーを検索"
    ),
    "開啟網站": _translations("打开网站", "Open websites", "Web サイトを開く"),
    "開啟資料夾": _translations("打开文件夹", "Open folders", "フォルダーを開く"),
    "啟動白名單程式": _translations(
        "启动白名单程序", "Launch allowlisted apps", "許可済みアプリを起動"
    ),
    "列出可見視窗": _translations(
        "列出可见窗口", "List visible windows", "表示中のウィンドウを一覧表示"
    ),
    "切換至指定視窗": _translations(
        "切换至指定窗口", "Switch to a specified window", "指定ウィンドウに切り替える"
    ),
    "建立檔案": _translations("创建文件", "Create files", "ファイルを作成"),
    "重新命名檔案": _translations("重命名文件", "Rename files", "ファイル名を変更"),
    "移動檔案": _translations("移动文件", "Move files", "ファイルを移動"),
    "建立行事曆事件": _translations(
        "创建日历事件", "Create calendar events", "カレンダー予定を作成"
    ),
    "修改行事曆事件": _translations(
        "修改日历事件", "Update calendar events", "カレンダー予定を変更"
    ),
    "讀取行事曆": _translations("读取日历", "Read calendars", "カレンダーを読み取る"),
    "讀取電子郵件": _translations("读取电子邮件", "Read email", "メールを読み取る"),
    "寄送電子郵件": _translations("发送电子邮件", "Send email", "メールを送信"),
    "讀取雲端檔案": _translations(
        "读取云端文件", "Read cloud files", "クラウドファイルを読み取る"
    ),
    "建立或修改雲端檔案": _translations(
        "创建或修改云端文件",
        "Create or update cloud files",
        "クラウドファイルを作成・変更",
    ),
    "對外發布內容": _translations(
        "对外发布内容", "Publish content externally", "外部へコンテンツを公開"
    ),
    "讀取智慧家庭狀態": _translations(
        "读取智能家居状态", "Read smart-home status", "スマートホームの状態を読み取る"
    ),
    "控制一般智慧設備": _translations(
        "控制一般智能设备", "Control standard smart devices", "一般スマート機器を操作"
    ),
    "控制門鎖": _translations("控制门锁", "Control door locks", "ドアロックを操作"),
    "控制警報": _translations("控制警报", "Control alarms", "警報を操作"),
    "控制加熱與高溫設備": _translations(
        "控制加热与高温设备",
        "Control heating and high-temperature devices",
        "暖房・高温機器を操作",
    ),
    "使用攝影機": _translations("使用摄像头", "Use the camera", "カメラを使用"),
    "遠端查看本程式畫面": _translations(
        "远程查看本程序画面", "View this app remotely", "このアプリの画面をリモート表示"
    ),
    "遠端下載白名單檔案": _translations(
        "远程下载白名单文件",
        "Download allowlisted files remotely",
        "許可済みファイルをリモート取得",
    ),
    "遠端寫入檔案": _translations(
        "远程写入文件", "Write files remotely", "リモートでファイルを書き込む"
    ),
    "刪除檔案": _translations("删除文件", "Delete files", "ファイルを削除"),
    "關機或重新啟動": _translations(
        "关机或重新启动", "Shut down or restart", "シャットダウンまたは再起動"
    ),
    # Risk, permission, trigger and allowlist display labels.
    "低風險": _translations("低风险", "Low risk", "低リスク"),
    "一般變更": _translations("一般变更", "Standard change", "通常の変更"),
    "外部影響": _translations("外部影响", "External impact", "外部への影響"),
    "高風險": _translations("高风险", "High risk", "高リスク"),
    "禁止": _translations("禁止", "Blocked", "禁止"),
    "每次詢問": _translations("每次询问", "Ask every time", "毎回確認"),
    "允許": _translations("允许", "Allow", "許可"),
    "手動": _translations("手动", "Manual", "手動"),
    "每天 {time}": _translations("每天 {time}", "Daily at {time}", "毎日 {time}"),
    "程式啟動時": _translations("程序启动时", "When the app starts", "アプリ起動時"),
    "未知": _translations("未知", "Unknown", "不明"),
    "{count} 步": _translations("{count} 步", "{count} steps", "{count} ステップ"),
    "資料夾": _translations("文件夹", "Folder", "フォルダー"),
    "程式": _translations("程序", "App", "アプリ"),
    "網站": _translations("网站", "Website", "Web サイト"),
    "只讀": _translations("只读", "Read only", "読み取り専用"),
    "可寫": _translations("可写", "Read and write", "読み書き可能"),
    "控制": _translations("控制", "Control", "操作"),
    # Overview and planner.
    "<b>墨寒旗艦任務中心</b>": _translations(
        "<b>墨寒旗舰任务中心</b>",
        "<b>MoHan Flagship Task Center</b>",
        "<b>墨寒フラッグシップ・タスクセンター</b>",
    ),
    "所有電腦、雲端、遠端與智慧家庭操作都必須經過："
    "計畫 → 權限判斷 → 確認 → 執行 → 結果驗證 → 稽核。": _translations(
        "所有电脑、云端、远程与智能家居操作都必须经过："
        "计划 → 权限判断 → 确认 → 执行 → 结果验证 → 审计。",
        "Every computer, cloud, remote, and smart-home action must pass through: "
        "plan → permission check → confirmation → execution → result verification → audit.",
        "PC、クラウド、リモート、スマートホームのすべての操作は、"
        "計画 → 権限判定 → 確認 → 実行 → 結果検証 → 監査の順に処理されます。",
    ),
    "重新檢查系統狀態": _translations(
        "重新检查系统状态", "Recheck system status", "システム状態を再確認"
    ),
    "立即建立可驗證備份": _translations(
        "立即创建可验证备份",
        "Create a verifiable backup now",
        "検証可能なバックアップを今すぐ作成",
    ),
    "<b>自然語言工具任務</b>": _translations(
        "<b>自然语言工具任务</b>",
        "<b>Natural-language tool task</b>",
        "<b>自然言語ツールタスク</b>",
    ),
    "例如：幫我開啟工作資料夾，然後開啟指定工作網站": _translations(
        "例如：帮我打开工作文件夹，然后打开指定工作网站",
        "For example: Open my work folder, then open the specified work website",
        "例：作業フォルダーを開き、指定した作業サイトを開いて",
    ),
    "先產生安全計畫": _translations(
        "先生成安全计划", "Create a safety plan first", "安全計画を先に作成"
    ),
    "資料備份": _translations("数据备份", "Data Backup", "データバックアップ"),
    "備份失敗：{error}": _translations(
        "备份失败：{error}",
        "Backup failed: {error}",
        "バックアップに失敗しました：{error}",
    ),
    "備份與完整性雜湊已建立：\n{target}": _translations(
        "备份与完整性哈希已创建：\n{target}",
        "Backup and integrity hash created:\n{target}",
        "バックアップと整合性ハッシュを作成しました：\n{target}",
    ),
    "工具任務": _translations("工具任务", "Tool Task", "ツールタスク"),
    "這句話沒有明確要求執行操作，因此不會產生工具計畫。": _translations(
        "这句话没有明确要求执行操作，因此不会生成工具计划。",
        "This message does not clearly request an action, so no tool plan will be created.",
        "操作の実行を明確に求めていないため、ツール計画は作成しません。",
    ),
    "規劃中…": _translations("规划中…", "Planning…", "計画中…"),
    "讀取 Gmail 郵件": _translations(
        "读取 Gmail 邮件", "Read Gmail messages", "Gmail メールを読み取る"
    ),
    "讀取最近 {days} 天內最多 {limit} 封 Gmail 郵件": _translations(
        "读取最近 {days} 天内最多 {limit} 封 Gmail 邮件",
        "Read up to {limit} Gmail messages from the last {days} days",
        "過去 {days} 日間の Gmail メールを最大 {limit} 件読み取る",
    ),
    "讀取 Google Calendar": _translations(
        "读取 Google Calendar", "Read Google Calendar", "Google Calendar を読み取る"
    ),
    "讀取 Google Calendar 未來 {days} 天行程": _translations(
        "读取 Google Calendar 未来 {days} 天的日程",
        "Read Google Calendar events for the next {days} days",
        "Google Calendar の今後 {days} 日間の予定を読み取る",
    ),
    "讀取 Google Drive": _translations(
        "读取 Google Drive", "Read Google Drive", "Google Drive を読み取る"
    ),
    "搜尋 Google Drive 檔案：{name}": _translations(
        "搜索 Google Drive 文件：{name}",
        "Search Google Drive files: {name}",
        "Google Drive のファイルを検索：{name}",
    ),
    "列出 Google Drive 最近修改的檔案": _translations(
        "列出 Google Drive 最近修改的文件",
        "List recently modified Google Drive files",
        "Google Drive で最近変更されたファイルを一覧表示",
    ),
    "（目前沒有白名單目標）": _translations(
        "（目前没有白名单目标）",
        "(No allowlisted targets are configured)",
        "（許可済み対象はまだありません）",
    ),
    "工具計畫": _translations("工具计划", "Tool Plan", "ツール計画"),
    "計畫驗證失敗：{error}": _translations(
        "计划验证失败：{error}",
        "Plan validation failed: {error}",
        "計画の検証に失敗しました：{error}",
    ),
    "資料不足或並非明確操作要求，因此沒有產生任何步驟。": _translations(
        "信息不足或并非明确的操作要求，因此没有生成任何步骤。",
        "There was not enough information or no explicit action request, so no steps were created.",
        "情報が不足しているか操作要求が明確でないため、ステップは作成されませんでした。",
    ),
    "執行前計畫預覽": _translations(
        "执行前计划预览", "Pre-execution Plan Preview", "実行前の計画確認"
    ),
    "{title}\n\n{preview}\n\n每一步仍會依個別權限與風險再次判斷。是否繼續？": _translations(
        "{title}\n\n{preview}\n\n每一步仍会根据各自的权限与风险再次判断。是否继续？",
        "{title}\n\n{preview}\n\nEach step will still be checked against its own permissions and risk. Continue?",
        "{title}\n\n{preview}\n\n各ステップは個別の権限とリスクに基づいて再判定されます。続行しますか？",
    ),
    "任務結果": _translations("任务结果", "Task Results", "タスク結果"),
    "無法產生計畫：{error}": _translations(
        "无法生成计划：{error}",
        "Could not create a plan: {error}",
        "計画を作成できませんでした：{error}",
    ),
    "工具計畫逾時": _translations(
        "工具计划超时", "Tool Plan Timed Out", "ツール計画がタイムアウトしました"
    ),
    "等待 OpenAI 安全計畫超過 50 秒，已自動停止等待。"
    "請確認網路、API 金鑰與文字模型後再試一次。": _translations(
        "等待 OpenAI 安全计划超过 50 秒，已自动停止等待。"
        "请确认网络、API 密钥与文本模型后再试一次。",
        "The OpenAI safety plan took longer than 50 seconds, so waiting was stopped. "
        "Check the network, API key, and text model, then try again.",
        "OpenAI の安全計画を 50 秒以上待機したため、自動的に待機を停止しました。"
        "ネットワーク、API キー、テキストモデルを確認して再試行してください。",
    ),
    "Home Assistant：{home}\n遠端服務：{remote}\n已啟用工作流程：{workflows}\n"
    "有效配對裝置：{devices}\n安全狀態：高風險操作不允許免確認；"
    "任意命令列與付款永久禁止。": _translations(
        "Home Assistant：{home}\n远程服务：{remote}\n已启用工作流：{workflows}\n"
        "有效配对设备：{devices}\n安全状态：高风险操作不允许免确认；"
        "任意命令行与付款永久禁止。",
        "Home Assistant: {home}\nRemote service: {remote}\nEnabled workflows: {workflows}\n"
        "Active paired devices: {devices}\nSecurity: high-risk actions always require confirmation; "
        "arbitrary command lines and payments are permanently blocked.",
        "Home Assistant：{home}\nリモートサービス：{remote}\n有効なワークフロー：{workflows}\n"
        "有効なペアリング済み端末：{devices}\nセキュリティ：高リスク操作は必ず確認し、"
        "任意のコマンドラインと支払いは常に禁止されます。",
    ),
    "已啟用": _translations("已启用", "Enabled", "有効"),
    "未啟用": _translations("未启用", "Disabled", "無効"),
    "運作中": _translations("运行中", "Running", "稼働中"),
    "新增工作流程": _translations("新增工作流", "Add workflow", "ワークフローを追加"),
    "執行選取流程": _translations(
        "执行选中流程", "Run selected workflow", "選択したワークフローを実行"
    ),
    "刪除選取流程": _translations(
        "删除选中流程", "Delete selected workflow", "選択したワークフローを削除"
    ),
    "請先選取一個流程。": _translations(
        "请先选择一个流程。",
        "Select a workflow first.",
        "先にワークフローを選択してください。",
    ),
    "預覽工作流程": _translations(
        "预览工作流", "Preview Workflow", "ワークフローを確認"
    ),
    "{title}\n\n{preview}\n\n是否執行？": _translations(
        "{title}\n\n{preview}\n\n是否执行？",
        "{title}\n\n{preview}\n\nRun this workflow?",
        "{title}\n\n{preview}\n\nこのワークフローを実行しますか？",
    ),
    "沒有可執行步驟": _translations(
        "没有可执行步骤", "No executable steps", "実行できるステップはありません"
    ),
    "刪除工作流程": _translations(
        "删除工作流", "Delete Workflow", "ワークフローを削除"
    ),
    "確定刪除「{name}」？": _translations(
        "确定删除“{name}”？", "Delete “{name}”?", "「{name}」を削除しますか？"
    ),
    # Cloud connectors.
    "權杖由作業系統安全加密保存，不寫入資料庫或設定檔。": _translations(
        "令牌由操作系统安全加密保存，不写入数据库或配置文件。",
        "Tokens are encrypted by the operating system and are never written to the database or configuration files.",
        "トークンは OS により安全に暗号化され、データベースや設定ファイルには保存されません。",
    ),
    "{platform} 的原生安全金鑰保存尚未完成實機驗證，因此 OAuth 連線暫停；"
    "墨寒不會改用明文保存。": _translations(
        "{platform} 的原生安全密钥保存尚未完成真机验证，因此 OAuth 连接暂停；"
        "墨寒不会改用明文保存。",
        "Native secure secret storage on {platform} has not yet passed real-device verification, "
        "so OAuth connections are disabled; MoHan will not fall back to plaintext storage.",
        "{platform} のネイティブ安全保管は実機検証が未完了のため、OAuth 接続を停止しています。"
        "墨寒が平文保存へ切り替えることはありません。",
    ),
    "Google、Microsoft 與 GitHub 預設停用。連線時使用瀏覽器 OAuth；{note}": _translations(
        "Google、Microsoft 与 GitHub 默认停用。连接时使用浏览器 OAuth；{note}",
        "Google, Microsoft, and GitHub are disabled by default. Browser OAuth is used for connections; {note}",
        "Google、Microsoft、GitHub は既定で無効です。接続にはブラウザー OAuth を使用します。{note}",
    ),
    "貼上你在服務商後台建立的 Desktop App Client ID": _translations(
        "粘贴你在服务商后台创建的 Desktop App Client ID",
        "Paste the Desktop App Client ID created in the provider console",
        "サービス管理画面で作成した Desktop App Client ID を貼り付け",
    ),
    "若服務商提供 Client Secret 才需填寫": _translations(
        "仅在服务商提供 Client Secret 时填写",
        "Enter only if the provider supplies a Client Secret",
        "サービスから Client Secret が発行された場合のみ入力",
    ),
    "開啟瀏覽器安全連線": _translations(
        "打开浏览器安全连接", "Open secure browser connection", "ブラウザーで安全に接続"
    ),
    "測試選取服務": _translations(
        "测试选中服务", "Test selected service", "選択したサービスをテスト"
    ),
    "撤銷選取服務": _translations(
        "撤销选中服务", "Revoke selected service", "選択したサービスを解除"
    ),
    "服務": _translations("服务", "Service", "サービス"),
    "授權範圍": _translations("授权范围", "OAuth scopes", "認可スコープ"),
    "狀態": _translations("状态", "Status", "状態"),
    "已設定服務": _translations(
        "已配置服务", "Configured services", "設定済みサービス"
    ),
    "{platform} 尚無經過實機驗證的安全金鑰保存；OAuth 連線已安全停用。": _translations(
        "{platform} 尚无通过真机验证的安全密钥保存；OAuth 连接已安全停用。",
        "{platform} does not yet have real-device-verified secure secret storage; OAuth connections are safely disabled.",
        "{platform} では安全な秘密情報保管の実機検証が未完了のため、OAuth 接続を安全に無効化しています。",
    ),
    "請先填入服務商後台建立的 OAuth Client ID。": _translations(
        "请先填写服务商后台创建的 OAuth Client ID。",
        "Enter the OAuth Client ID created in the provider console first.",
        "サービス管理画面で作成した OAuth Client ID を先に入力してください。",
    ),
    "等待瀏覽器授權，請勿關閉墨寒……": _translations(
        "等待浏览器授权，请勿关闭墨寒……",
        "Waiting for browser authorization. Do not close MoHan…",
        "ブラウザーでの認可を待っています。墨寒を閉じないでください…",
    ),
    "無法安全保存 OAuth 權杖：{error}": _translations(
        "无法安全保存 OAuth 令牌：{error}",
        "Could not securely store the OAuth token: {error}",
        "OAuth トークンを安全に保存できませんでした：{error}",
    ),
    "{provider} 已安全連線": _translations(
        "{provider} 已安全连接",
        "{provider} connected securely",
        "{provider} に安全に接続しました",
    ),
    "{provider} 連線失敗：{error}": _translations(
        "{provider} 连接失败：{error}",
        "{provider} connection failed: {error}",
        "{provider} への接続に失敗しました：{error}",
    ),
    "測試失敗：{error}": _translations(
        "测试失败：{error}", "Test failed: {error}", "テストに失敗しました：{error}"
    ),
    "測試中…": _translations("测试中…", "Testing…", "テスト中…"),
    "正在分別檢查 Gmail、Google Calendar 與 Google Drive……": _translations(
        "正在分别检查 Gmail、Google Calendar 与 Google Drive……",
        "Checking Gmail, Google Calendar, and Google Drive separately…",
        "Gmail、Google Calendar、Google Drive を個別に確認しています…",
    ),
    "正在檢查選取的服務……": _translations(
        "正在检查选中的服务……",
        "Checking the selected service…",
        "選択したサービスを確認しています…",
    ),
    "{name}：{status}（{detail}）": _translations(
        "{name}：{status}（{detail}）",
        "{name}: {status} ({detail})",
        "{name}：{status}（{detail}）",
    ),
    "正常": _translations("正常", "Healthy", "正常"),
    "失敗": _translations("失败", "Failed", "失敗"),
    "Google 三項服務測試": _translations(
        "Google 三项服务测试", "Google Three-Service Test", "Google 3 サービスのテスト"
    ),
    "雲端服務測試": _translations(
        "云端服务测试", "Cloud Service Test", "クラウドサービステスト"
    ),
    "失敗項目通常代表該 API 尚未啟用、OAuth 範圍不足，或網路暫時無法連線。": _translations(
        "失败项目通常表示该 API 尚未启用、OAuth 范围不足，或网络暂时无法连接。",
        "A failed item usually means its API is not enabled, the OAuth scopes are insufficient, or the network is temporarily unavailable.",
        "失敗した項目は通常、API が未有効、OAuth スコープ不足、または一時的なネットワーク障害を示します。",
    ),
    "雲端測試超過 35 秒，已停止等待；請查看個別服務的 API 與網路狀態。": _translations(
        "云端测试超过 35 秒，已停止等待；请检查各服务的 API 与网络状态。",
        "The cloud test exceeded 35 seconds and was stopped. Check each service API and the network status.",
        "クラウドテストが 35 秒を超えたため待機を停止しました。各サービスの API とネットワーク状態を確認してください。",
    ),
    "撤銷雲端服務": _translations(
        "撤销云端服务", "Revoke Cloud Service", "クラウドサービスを解除"
    ),
    "確定移除 {provider} 的本機權杖？": _translations(
        "确定移除 {provider} 的本地令牌？",
        "Remove the local token for {provider}?",
        "{provider} のローカルトークンを削除しますか？",
    ),
    "本機權杖已移除": _translations(
        "本地令牌已移除", "Local token removed", "ローカルトークンを削除しました"
    ),
    "尚未測試": _translations("尚未测试", "Not tested", "未テスト"),
    "未設定": _translations("未配置", "Not configured", "未設定"),
    "已撤銷": _translations("已撤销", "Revoked", "解除済み"),
    "OAuth 已連線": _translations("OAuth 已连接", "OAuth connected", "OAuth 接続済み"),
    "尚未完成 OAuth 連線": _translations(
        "尚未完成 OAuth 连接",
        "OAuth connection has not been completed",
        "OAuth 接続が完了していません",
    ),
    "無法安全更新 OAuth 權杖：{error}": _translations(
        "无法安全更新 OAuth 令牌：{error}",
        "Could not securely update the OAuth token: {error}",
        "OAuth トークンを安全に更新できませんでした：{error}",
    ),
    "OAuth 權杖資料不完整": _translations(
        "OAuth 令牌数据不完整",
        "OAuth token data is incomplete",
        "OAuth トークンのデータが不完全です",
    ),
    "Google 與 Microsoft 均已連線，請明確指定要使用哪個帳戶": _translations(
        "Google 与 Microsoft 均已连接，请明确指定要使用哪个帐户",
        "Both Google and Microsoft are connected; specify which account to use",
        "Google と Microsoft の両方に接続されています。使用するアカウントを明示してください",
    ),
    "尚未連線 Google 或 Microsoft，或工具計畫未指定供應商": _translations(
        "尚未连接 Google 或 Microsoft，或工具计划未指定供应商",
        "Google or Microsoft is not connected, or the tool plan did not specify a provider",
        "Google または Microsoft に未接続か、ツール計画でプロバイダーが指定されていません",
    ),
    "此工具目前只支援 google 或 microsoft": _translations(
        "此工具目前仅支持 google 或 microsoft",
        "This tool currently supports only google or microsoft",
        "このツールは現在 google または microsoft のみ対応しています",
    ),
    "全部正常": _translations("全部正常", "All healthy", "すべて正常"),
    "部分功能異常": _translations(
        "部分功能异常", "Some features have issues", "一部の機能に問題があります"
    ),
    "主要日曆可讀取": _translations(
        "主要日历可读取",
        "Primary calendar is readable",
        "メインカレンダーを読み取れます",
    ),
    "雲端硬碟中繼資料可讀取": _translations(
        "云端硬盘元数据可读取",
        "Drive metadata is readable",
        "ドライブのメタデータを読み取れます",
    ),
    "Google 帳戶": _translations("Google 帐户", "Google account", "Google アカウント"),
    "Microsoft 帳戶": _translations(
        "Microsoft 帐户", "Microsoft account", "Microsoft アカウント"
    ),
    "GitHub 帳戶": _translations("GitHub 帐户", "GitHub account", "GitHub アカウント"),
    # Home Assistant.
    "啟用 Home Assistant 整合": _translations(
        "启用 Home Assistant 集成",
        "Enable Home Assistant integration",
        "Home Assistant 連携を有効化",
    ),
    "例如：http://homeassistant.local:8123": _translations(
        "例如：http://homeassistant.local:8123",
        "Example: http://homeassistant.local:8123",
        "例：http://homeassistant.local:8123",
    ),
    "已由作業系統安全保存（留空不變）": _translations(
        "已由操作系统安全保存（留空不变）",
        "Securely stored by the operating system (leave blank to keep it)",
        "OS により安全に保存済み（空欄なら変更なし）",
    ),
    "貼上 Home Assistant 長期存取權杖": _translations(
        "粘贴 Home Assistant 长期访问令牌",
        "Paste the Home Assistant long-lived access token",
        "Home Assistant の長期アクセストークンを貼り付け",
    ),
    "驗證 HTTPS 憑證": _translations(
        "验证 HTTPS 证书", "Verify HTTPS certificate", "HTTPS 証明書を検証"
    ),
    "保存連線設定": _translations(
        "保存连接设置", "Save connection settings", "接続設定を保存"
    ),
    "測試連線": _translations("测试连接", "Test connection", "接続をテスト"),
    "讀取裝置": _translations("读取设备", "Load devices", "機器を読み取る"),
    "Home Assistant 位址": _translations(
        "Home Assistant 地址", "Home Assistant address", "Home Assistant アドレス"
    ),
    "長期存取權杖": _translations(
        "长期访问令牌", "Long-lived access token", "長期アクセストークン"
    ),
    "連線狀態": _translations("连接状态", "Connection status", "接続状態"),
    "裝置狀態": _translations("设备状态", "Device status", "機器の状態"),
    "門鎖、警報與加熱設備永遠套用高風險政策。"
    "墨寒不能因對話內容自行降低安全等級。": _translations(
        "门锁、警报与加热设备始终应用高风险策略。墨寒不能因对话内容自行降低安全等级。",
        "Door locks, alarms, and heating devices always use the high-risk policy. "
        "MoHan cannot lower their security level based on conversation content.",
        "ドアロック、警報、加熱機器には常に高リスク方針を適用します。"
        "会話内容を理由に墨寒が安全レベルを下げることはできません。",
    ),
    "{platform} 的安全金鑰保存尚未完成實機驗證；Home Assistant 連線暫停，"
    "且不會儲存明文權杖。": _translations(
        "{platform} 的安全密钥保存尚未完成真机验证；Home Assistant 连接暂停，"
        "且不会保存明文令牌。",
        "Secure secret storage on {platform} has not passed real-device verification; "
        "Home Assistant is disabled and plaintext tokens will not be stored.",
        "{platform} の安全な秘密情報保管は実機検証が未完了です。Home Assistant 接続を停止し、"
        "平文トークンは保存しません。",
    ),
    "請先填入連線位址。": _translations(
        "请先填写连接地址。",
        "Enter the connection address first.",
        "接続先アドレスを先に入力してください。",
    ),
    "無法安全保存權杖：{error}": _translations(
        "无法安全保存令牌：{error}",
        "Could not securely store the token: {error}",
        "トークンを安全に保存できませんでした：{error}",
    ),
    "設定已保存": _translations("设置已保存", "Settings saved", "設定を保存しました"),
    "Home Assistant 尚未啟用": _translations(
        "Home Assistant 尚未启用",
        "Home Assistant is not enabled",
        "Home Assistant は有効ではありません",
    ),
    "尚未保存 Home Assistant 權杖": _translations(
        "尚未保存 Home Assistant 令牌",
        "No Home Assistant token has been saved",
        "Home Assistant トークンが保存されていません",
    ),
    "連線失敗：{error}": _translations(
        "连接失败：{error}", "Connection failed: {error}", "接続に失敗しました：{error}"
    ),
    "連線正常": _translations("连接正常", "Connection healthy", "接続は正常です"),
    "API 回應不正確": _translations(
        "API 响应不正确", "Unexpected API response", "API 応答が正しくありません"
    ),
    "讀取失敗：{error}": _translations(
        "读取失败：{error}", "Read failed: {error}", "読み取りに失敗しました：{error}"
    ),
    "未發現離線或低電量裝置": _translations(
        "未发现离线或低电量设备",
        "No offline or low-battery devices found",
        "オフラインまたは低バッテリーの機器はありません",
    ),
    "已讀取 {count} 個可用項目。{issues}": _translations(
        "已读取 {count} 个可用项目。{issues}",
        "Loaded {count} available items. {issues}",
        "利用可能な項目を {count} 件読み取りました。{issues}",
    ),
    "{name} 目前{state}": _translations(
        "{name} 目前{state}",
        "{name} is currently {state}",
        "{name} の現在の状態：{state}",
    ),
    "{name} 電量只剩 {value}": _translations(
        "{name} 电量仅剩 {value}",
        "{name} has only {value} battery remaining",
        "{name} のバッテリー残量は {value} です",
    ),
    # Remote access and camera privacy.
    "增加連線埠": _translations("增加端口", "Increase port", "ポート番号を増やす"),
    "減少連線埠": _translations("减少端口", "Decrease port", "ポート番号を減らす"),
    "啟用手機／私人網路遠端服務": _translations(
        "启用手机／私人网络远程服务",
        "Enable phone/private-network remote service",
        "スマートフォン／プライベートネットワークのリモート機能を有効化",
    ),
    "僅本機測試（127.0.0.1）": _translations(
        "仅本机测试（127.0.0.1）",
        "Local testing only (127.0.0.1)",
        "ローカルテストのみ（127.0.0.1）",
    ),
    "私人網路／Tailscale（0.0.0.0）": _translations(
        "私人网络／Tailscale（0.0.0.0）",
        "Private network / Tailscale (0.0.0.0)",
        "プライベートネットワーク／Tailscale（0.0.0.0）",
    ),
    "我確認已使用 Tailscale、Home Assistant Cloud 或其他加密私人網路": _translations(
        "我确认已使用 Tailscale、Home Assistant Cloud 或其他加密私人网络",
        "I confirm that I use Tailscale, Home Assistant Cloud, or another encrypted private network",
        "Tailscale、Home Assistant Cloud、または別の暗号化プライベートネットワークを使用していることを確認します",
    ),
    "允許傳送文字指令": _translations(
        "允许发送文本指令", "Allow text commands", "テキスト指示を許可"
    ),
    "允許查看墨寒程式視窗（不擷取整個桌面）": _translations(
        "允许查看墨寒程序窗口（不截取整个桌面）",
        "Allow viewing the MoHan app window (not the whole desktop)",
        "墨寒のアプリ画面の表示を許可（デスクトップ全体は取得しません）",
    ),
    "允許下載白名單內的非敏感檔案": _translations(
        "允许下载白名单内的非敏感文件",
        "Allow downloads of non-sensitive allowlisted files",
        "許可済みの非機密ファイルのダウンロードを許可",
    ),
    "允許本機攝影機在場偵測": _translations(
        "允许本机摄像头在场检测",
        "Allow local camera presence detection",
        "ローカルカメラでの在席検知を許可",
    ),
    "本機臉部身分辨識（需另裝可稽核的辨識外掛）": _translations(
        "本机人脸身份识别（需另装可审计的识别插件）",
        "Local face identification (requires a separately installed, auditable recognition plugin)",
        "ローカル顔識別（監査可能な認識プラグインの追加導入が必要）",
    ),
    "攝影機已關閉": _translations("摄像头已关闭", "Camera is off", "カメラはオフです"),
    "遠端功能預設關閉": _translations(
        "远程功能默认关闭",
        "Remote features are off by default",
        "リモート機能は既定でオフです",
    ),
    "啟動／套用": _translations("启动／应用", "Start / Apply", "起動／適用"),
    "停止遠端服務": _translations(
        "停止远程服务", "Stop remote service", "リモートサービスを停止"
    ),
    "配對新手機": _translations(
        "配对新手机", "Pair a new phone", "新しいスマートフォンをペアリング"
    ),
    "套用攝影機隱私設定": _translations(
        "应用摄像头隐私设置",
        "Apply camera privacy settings",
        "カメラのプライバシー設定を適用",
    ),
    "撤銷選取裝置": _translations(
        "撤销选中设备", "Revoke selected device", "選択した端末を解除"
    ),
    "監聽範圍": _translations("监听范围", "Listening scope", "待受範囲"),
    "連線埠": _translations("端口", "Port", "ポート"),
    "<b>攝影機與身分辨識</b>": _translations(
        "<b>摄像头与身份识别</b>", "<b>Camera & Identity</b>", "<b>カメラと本人識別</b>"
    ),
    "攝影機狀態": _translations("摄像头状态", "Camera status", "カメラの状態"),
    "攝影機預設關閉；啟用時必須顯示狀態。畫面不會默默上傳，"
    "也不會辨識未登錄的陌生人。": _translations(
        "摄像头默认关闭；启用时必须显示状态。画面不会静默上传，"
        "也不会识别未登记的陌生人。",
        "The camera is off by default and its status must remain visible when enabled. "
        "Images are never silently uploaded, and unregistered people are not identified.",
        "カメラは既定でオフです。有効時は状態を常に表示します。映像を無断でアップロードせず、"
        "未登録の人物を識別しません。",
    ),
    "服務狀態": _translations("服务状态", "Service status", "サービス状態"),
    "已配對裝置": _translations("已配对设备", "Paired devices", "ペアリング済み端末"),
    "攝影機權限": _translations("摄像头权限", "Camera Permission", "カメラ権限"),
    "安全政策已阻擋：{reason}": _translations(
        "安全策略已阻止：{reason}",
        "Blocked by security policy: {reason}",
        "セキュリティ方針によりブロックされました：{reason}",
    ),
    "啟用攝影機": _translations("启用摄像头", "Enable Camera", "カメラを有効化"),
    "墨寒只會在本機分析粗略移動與明暗，不保存影像、"
    "不傳送雲端，也不辨識陌生人。是否啟用？": _translations(
        "墨寒只会在本机分析粗略移动与明暗，不保存图像、"
        "不传送云端，也不识别陌生人。是否启用？",
        "MoHan will analyze only coarse movement and brightness locally. Images are not saved, "
        "sent to the cloud, or used to identify strangers. Enable the camera?",
        "墨寒は端末内で大まかな動きと明暗のみを分析します。映像の保存やクラウド送信、"
        "見知らぬ人の識別は行いません。カメラを有効にしますか？",
    ),
    "攝影機啟動失敗：{error}": _translations(
        "摄像头启动失败：{error}",
        "Could not start the camera: {error}",
        "カメラを起動できませんでした：{error}",
    ),
    "攝影機錯誤：{error}": _translations(
        "摄像头错误：{error}", "Camera error: {error}", "カメラエラー：{error}"
    ),
    "攝影機使用中：{device}（僅本機在場偵測）": _translations(
        "摄像头使用中：{device}（仅本机在场检测）",
        "Camera active: {device} (local presence detection only)",
        "カメラ使用中：{device}（ローカル在席検知のみ）",
    ),
    "{base}｜偵測到有人在場": _translations(
        "{base}｜检测到有人在场", "{base} | Presence detected", "{base}｜在席を検知"
    ),
    "{base}｜暫未偵測到在場": _translations(
        "{base}｜暂未检测到在场",
        "{base} | No presence detected",
        "{base}｜現在は在席を検知していません",
    ),
    "遠端服務未啟用": _translations(
        "远程服务未启用", "Remote service is not enabled", "リモートサービスは無効です"
    ),
    "啟動失敗：{error}": _translations(
        "启动失败：{error}", "Start failed: {error}", "起動に失敗しました：{error}"
    ),
    "已啟動：http://{host}:{port}\n只有已配對且具備相應權限的裝置可以存取。": _translations(
        "已启动：http://{host}:{port}\n只有已配对且具备相应权限的设备可以访问。",
        "Started: http://{host}:{port}\nOnly paired devices with the required permissions can connect.",
        "起動しました：http://{host}:{port}\n必要な権限を持つペアリング済み端末のみ接続できます。",
    ),
    "遠端服務已停止，既有權杖未刪除但無法連線。": _translations(
        "远程服务已停止，现有令牌未删除但无法连接。",
        "Remote service stopped. Existing tokens were not deleted, but cannot connect.",
        "リモートサービスを停止しました。既存トークンは削除されていませんが、接続できません。",
    ),
    "配對新裝置": _translations(
        "配对新设备", "Pair New Device", "新しい端末をペアリング"
    ),
    "裝置名稱": _translations("设备名称", "Device name", "端末名"),
    "一次性配對權杖": _translations(
        "一次性配对令牌", "One-time Pairing Token", "一回限りのペアリングトークン"
    ),
    "請只在可信任裝置輸入下列權杖。關閉視窗後不會再次顯示：\n\n{token}": _translations(
        "请只在可信任设备输入下列令牌。关闭窗口后不会再次显示：\n\n{token}",
        "Enter the following token only on a trusted device. It will not be shown again after this window closes:\n\n{token}",
        "次のトークンは信頼できる端末にのみ入力してください。この画面を閉じると再表示できません：\n\n{token}",
    ),
    "有效": _translations("有效", "Active", "有効"),
    "從未": _translations("从未", "Never", "なし"),
    "{status}｜{device}｜最後連線：{last_seen}": _translations(
        "{status}｜{device}｜最后连接：{last_seen}",
        "{status} | {device} | Last connection: {last_seen}",
        "{status}｜{device}｜最終接続：{last_seen}",
    ),
    "已送交墨寒並等待本機權限判斷": _translations(
        "已提交给墨寒并等待本机权限判断",
        "Sent to MoHan and awaiting local permission checks",
        "墨寒へ送信し、ローカル権限の判定を待っています",
    ),
    "[遠端裝置：{device}] {text}": _translations(
        "[远程设备：{device}] {text}",
        "[Remote device: {device}] {text}",
        "[リモート端末：{device}] {text}",
    ),
    "尚無可用的程式視窗畫面": _translations(
        "尚无可用的程序窗口画面",
        "No app-window image is available",
        "利用可能なアプリ画面がありません",
    ),
    # Security and auditing.
    "<b>允許操作的資料夾與程式</b>": _translations(
        "<b>允许操作的文件夹与程序</b>",
        "<b>Allowed folders and apps</b>",
        "<b>操作を許可するフォルダーとアプリ</b>",
    ),
    "加入資料夾": _translations("添加文件夹", "Add folder", "フォルダーを追加"),
    "加入程式": _translations("添加程序", "Add app", "アプリを追加"),
    "加入網站": _translations("添加网站", "Add website", "Web サイトを追加"),
    "移除選取項目": _translations(
        "移除选中项目", "Remove selected item", "選択項目を削除"
    ),
    "<b>能力權限</b>": _translations(
        "<b>能力权限</b>", "<b>Capability permissions</b>", "<b>機能権限</b>"
    ),
    "{label}（{risk}）": _translations(
        "{label}（{risk}）", "{label} ({risk})", "{label}（{risk}）"
    ),
    "即使選擇允許，高風險政策仍會要求確認。": _translations(
        "即使选择允许，高风险策略仍会要求确认。",
        "High-risk policy still requires confirmation even when Allow is selected.",
        "「許可」を選択しても、高リスク方針により確認が必要です。",
    ),
    "保存安全權限": _translations(
        "保存安全权限", "Save security permissions", "セキュリティ権限を保存"
    ),
    "付款、購買、密碼匯出、停用安全防護、任意 PowerShell／管理員命令"
    "永遠禁止自動執行，無法由此頁解除。": _translations(
        "付款、购买、密码导出、停用安全防护、任意 PowerShell／管理员命令"
        "始终禁止自动执行，无法在此页面解除。",
        "Payments, purchases, password exports, disabling safeguards, arbitrary PowerShell, "
        "and administrator commands can never run automatically and cannot be enabled here.",
        "支払い、購入、パスワードの書き出し、安全保護の無効化、任意の PowerShell／管理者コマンドは"
        "常に自動実行禁止で、この画面から解除できません。",
    ),
    "選擇允許墨寒操作的資料夾": _translations(
        "选择允许墨寒操作的文件夹",
        "Choose a folder MoHan may access",
        "墨寒に操作を許可するフォルダーを選択",
    ),
    "資料夾權限": _translations("文件夹权限", "Folder Permission", "フォルダー権限"),
    "輸入 read（只讀）或 write（可建立、移動與重新命名）": _translations(
        "输入 read（只读）或 write（可创建、移动与重命名）",
        "Enter read (read only) or write (create, move, and rename)",
        "read（読み取り専用）または write（作成・移動・名前変更可）を入力",
    ),
    "選擇允許墨寒啟動的程式": _translations(
        "选择允许墨寒启动的程序",
        "Choose an app MoHan may launch",
        "墨寒に起動を許可するアプリを選択",
    ),
    "Windows 程式 (*.exe);;所有檔案 (*)": _translations(
        "Windows 程序 (*.exe);;所有文件 (*)",
        "Windows apps (*.exe);;All files (*)",
        "Windows アプリ (*.exe);;すべてのファイル (*)",
    ),
    "應用程式／可執行檔 (*);;所有檔案 (*)": _translations(
        "应用程序／可执行文件 (*);;所有文件 (*)",
        "Apps / executables (*);;All files (*)",
        "アプリ／実行ファイル (*);;すべてのファイル (*)",
    ),
    "程式別名": _translations("程序别名", "App Alias", "アプリの別名"),
    "日後對墨寒說的程式名稱": _translations(
        "日后对墨寒说的程序名称",
        "The app name you will use when speaking to MoHan",
        "今後、墨寒に伝えるアプリ名",
    ),
    "加入允許網站": _translations(
        "添加允许网站", "Add Allowed Website", "許可する Web サイトを追加"
    ),
    "輸入完整 HTTPS 網址（可限制到指定路徑）": _translations(
        "输入完整 HTTPS 地址（可限制到指定路径）",
        "Enter a complete HTTPS URL (optionally restricted to a path)",
        "完全な HTTPS URL を入力（特定パスに制限可能）",
    ),
    "網站白名單": _translations(
        "网站白名单", "Website Allowlist", "Web サイト許可リスト"
    ),
    "公開網站只接受完整 HTTPS 網址。": _translations(
        "公开网站仅接受完整 HTTPS 地址。",
        "Public websites require a complete HTTPS URL.",
        "公開 Web サイトには完全な HTTPS URL のみ使用できます。",
    ),
    "移除允許項目": _translations(
        "移除允许项目", "Remove Allowed Item", "許可項目を削除"
    ),
    "確定撤銷墨寒對此項目的存取權？": _translations(
        "确定撤销墨寒对此项目的访问权？",
        "Revoke MoHan's access to this item?",
        "この項目に対する墨寒のアクセス権を取り消しますか？",
    ),
    "安全權限已保存。妾會守住這條界線。": _translations(
        "安全权限已保存。妾会守住这条界线。",
        "Security permissions saved. I will hold this boundary.",
        "セキュリティ権限を保存しました。妾がこの境界を守ります。",
    ),
    "重新整理": _translations("刷新", "Refresh", "更新"),
    "<p>尚無工具操作紀錄。</p>": _translations(
        "<p>尚无工具操作记录。</p>",
        "<p>No tool activity has been recorded.</p>",
        "<p>ツール操作の記録はまだありません。</p>",
    ),
    "高風險操作二次確認": _translations(
        "高风险操作二次确认",
        "Second Confirmation for High-Risk Action",
        "高リスク操作の再確認",
    ),
    "墨寒請求執行工具": _translations(
        "墨寒请求执行工具",
        "MoHan Requests Tool Execution",
        "墨寒がツール実行を要求しています",
    ),
    "風險：{risk}\n來源：{source}\n操作：{description}\n\n參數預覽：\n{detail}\n\n是否允許？": _translations(
        "风险：{risk}\n来源：{source}\n操作：{description}\n\n参数预览：\n{detail}\n\n是否允许？",
        "Risk: {risk}\nSource: {source}\nAction: {description}\n\nArgument preview:\n{detail}\n\nAllow this action?",
        "リスク：{risk}\n送信元：{source}\n操作：{description}\n\n引数の確認：\n{detail}\n\n許可しますか？",
    ),
    "已停手。所有工具與遠端連線均已中止。": _translations(
        "已停止。所有工具与远程连接均已中止。",
        "Stopped. All tools and remote connections have been terminated.",
        "停止しました。すべてのツールとリモート接続を終了しました。",
    ),
    "緊急停止": _translations("紧急停止", "Emergency Stop", "緊急停止"),
    "所有進行中的工具任務與遠端服務均已停止。": _translations(
        "所有进行中的工具任务与远程服务均已停止。",
        "All active tool tasks and remote services have been stopped.",
        "実行中のすべてのツールタスクとリモートサービスを停止しました。",
    ),
    # Results generated in this module.
    "已整理目前工作狀態": _translations(
        "已整理当前工作状态",
        "Current work status summarized",
        "現在の作業状態を整理しました",
    ),
    "已讀取剪貼簿文字": _translations(
        "已读取剪贴板文本",
        "Clipboard text read",
        "クリップボードのテキストを読み取りました",
    ),
    "已寫入剪貼簿": _translations(
        "已写入剪贴板", "Written to the clipboard", "クリップボードに書き込みました"
    ),
    "剪貼簿文字不可超過 100,000 字": _translations(
        "剪贴板文本不可超过 100,000 字",
        "Clipboard text cannot exceed 100,000 characters",
        "クリップボードのテキストは 100,000 文字を超えられません",
    ),
    "已讀取 {count} 封郵件摘要": _translations(
        "已读取 {count} 封邮件摘要",
        "Read {count} email summaries",
        "メールの概要を {count} 件読み取りました",
    ),
    "收件者、主旨與內容不可留空": _translations(
        "收件人、主题与内容不可留空",
        "Recipient, subject, and body are required",
        "宛先、件名、本文は必須です",
    ),
    "Gmail 未傳回草稿 ID": _translations(
        "Gmail 未返回草稿 ID",
        "Gmail did not return a draft ID",
        "Gmail から下書き ID が返されませんでした",
    ),
    "郵件已寄給 {recipient}": _translations(
        "邮件已发送给 {recipient}",
        "Email sent to {recipient}",
        "{recipient} にメールを送信しました",
    ),
    "已讀取 {count} 個行程": _translations(
        "已读取 {count} 个日程",
        "Read {count} calendar events",
        "予定を {count} 件読み取りました",
    ),
    "行程標題、開始與結束時間不可留空": _translations(
        "日程标题、开始与结束时间不可留空",
        "Event title, start time, and end time are required",
        "予定のタイトル、開始時刻、終了時刻は必須です",
    ),
    "結束時間必須晚於開始時間": _translations(
        "结束时间必须晚于开始时间",
        "The end time must be later than the start time",
        "終了時刻は開始時刻より後にしてください",
    ),
    "已建立行程：{title}": _translations(
        "已创建日程：{title}",
        "Calendar event created: {title}",
        "予定を作成しました：{title}",
    ),
    "搜尋 OneDrive 時請提供檔案名稱": _translations(
        "搜索 OneDrive 时请提供文件名",
        "Provide a file name when searching OneDrive",
        "OneDrive を検索する際はファイル名を指定してください",
    ),
    "找到 {count} 個符合的雲端檔案": _translations(
        "找到 {count} 个匹配的云端文件",
        "Found {count} matching cloud files",
        "一致するクラウドファイルが {count} 件見つかりました",
    ),
    "只能上傳白名單內的單一檔案": _translations(
        "只能上传白名单内的单个文件",
        "Only one allowlisted file can be uploaded",
        "許可リスト内の単一ファイルのみアップロードできます",
    ),
    "已上傳：{name}": _translations(
        "已上传：{name}", "Uploaded: {name}", "アップロードしました：{name}"
    ),
    # Known messages emitted by domain services and displayed by this UI.
    "任務已由使用者取消": _translations(
        "任务已由用户取消",
        "Task cancelled by the user",
        "ユーザーがタスクをキャンセルしました",
    ),
    "重複請求已安全略過": _translations(
        "重复请求已安全跳过",
        "Duplicate request safely skipped",
        "重複した要求を安全にスキップしました",
    ),
    "使用者未授權執行": _translations(
        "用户未授权执行",
        "Execution was not authorized by the user",
        "ユーザーが実行を許可しませんでした",
    ),
    "尚未安裝此工具的執行器": _translations(
        "尚未安装此工具的执行器",
        "No executor is installed for this tool",
        "このツールの実行機能はインストールされていません",
    ),
    "工具回報完成，但結果驗證未通過": _translations(
        "工具报告完成，但结果验证未通过",
        "The tool reported completion, but result verification failed",
        "ツールは完了を報告しましたが、結果検証に失敗しました",
    ),
    "已開啟網站": _translations(
        "已打开网站", "Website opened", "Web サイトを開きました"
    ),
    "已開啟資料夾：{value}": _translations(
        "已打开文件夹：{value}",
        "Folder opened: {value}",
        "フォルダーを開きました：{value}",
    ),
    "已啟動：{value}": _translations(
        "已启动：{value}", "Launched: {value}", "起動しました：{value}"
    ),
    "已建立檔案：{value}": _translations(
        "已创建文件：{value}",
        "File created: {value}",
        "ファイルを作成しました：{value}",
    ),
    "找到 {count} 個符合項目": _translations(
        "找到 {count} 个匹配项目",
        "Found {count} matching items",
        "一致する項目が {count} 件見つかりました",
    ),
    "已移動至：{value}": _translations(
        "已移动至：{value}", "Moved to: {value}", "移動先：{value}"
    ),
    "目前有 {count} 個可見視窗": _translations(
        "目前有 {count} 个可见窗口",
        "There are {count} visible windows",
        "表示中のウィンドウは {count} 個です",
    ),
    "已切換至：{value}": _translations(
        "已切换至：{value}", "Switched to: {value}", "切り替え先：{value}"
    ),
    "已執行 {value}": _translations(
        "已执行 {value}", "Executed {value}", "{value} を実行しました"
    ),
    "工具執行失敗：{detail}": _translations(
        "工具执行失败：{detail}",
        "Tool execution failed: {detail}",
        "ツール実行に失敗しました：{detail}",
    ),
    # Policy reasons are internal canonical values translated only at display time.
    "此能力永不允許自動執行": _translations(
        "此能力永不允许自动执行",
        "This capability can never run automatically",
        "この機能は自動実行できません",
    ),
    "未知的指令來源": _translations(
        "未知的指令来源", "Unknown command source", "指示の送信元が不明です"
    ),
    "目標位於受保護路徑": _translations(
        "目标位于受保护路径",
        "The target is in a protected path",
        "対象は保護されたパスにあります",
    ),
    "權限設定為禁止": _translations(
        "权限设置为禁止",
        "Permission is set to Blocked",
        "権限が「禁止」に設定されています",
    ),
    "通過本機權限政策": _translations(
        "通过本机权限策略",
        "Passed the local permission policy",
        "ローカル権限方針を通過しました",
    ),
})


_SYSTEM_PATTERNS = (
    (r"^安全政策已阻擋：(?P<reason>.*)$", "安全政策已阻擋：{reason}"),
    (r"^工具執行失敗：(?P<detail>.*)$", "工具執行失敗：{detail}"),
    (r"^已開啟資料夾：(?P<value>.*)$", "已開啟資料夾：{value}"),
    (r"^已啟動：(?P<value>.*)$", "已啟動：{value}"),
    (r"^已建立檔案：(?P<value>.*)$", "已建立檔案：{value}"),
    (r"^找到 (?P<count>\d+) 個符合項目$", "找到 {count} 個符合項目"),
    (r"^已移動至：(?P<value>.*)$", "已移動至：{value}"),
    (r"^目前有 (?P<count>\d+) 個可見視窗$", "目前有 {count} 個可見視窗"),
    (r"^已切換至：(?P<value>.*)$", "已切換至：{value}"),
    (r"^已執行 (?P<value>.*)$", "已執行 {value}"),
)


@dataclass(frozen=True, slots=True)
class FlagshipTranslator:
    """Strict, centralized localization boundary for the flagship UI."""

    language: str = "zh-TW"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "language",
            canonical_ui_language(self.language),
        )

    def text(self, source: str, /, **values: Any) -> str:
        template = source
        if self.language != "zh-TW":
            try:
                template = FLAGSHIP_TRANSLATIONS[source][
                    _TRANSLATION_INDEX[self.language]
                ]
            except KeyError as exc:
                raise KeyError(
                    f"Missing flagship translation for {source!r} in {self.language}"
                ) from exc
        return template.format_map(values) if values else template

    def system_message(self, message: str) -> str:
        """Translate known system prose while preserving data and error detail."""
        value = str(message)
        if self.language == "zh-TW":
            return value
        if value in FLAGSHIP_TRANSLATIONS:
            return self.text(value)
        for pattern, source in _SYSTEM_PATTERNS:
            match = re.fullmatch(pattern, value)
            if match is None:
                continue
            fields = match.groupdict()
            if "reason" in fields:
                fields["reason"] = self.system_message(fields["reason"])
            return self.text(source, **fields)
        return value

    def home_issue(self, message: str) -> str:
        value = str(message)
        if self.language == "zh-TW":
            return value
        if " 電量只剩 " in value:
            name, remaining = value.rsplit(" 電量只剩 ", 1)
            return self.text(
                "{name} 電量只剩 {value}",
                name=name,
                value=remaining,
            )
        if " 目前" in value:
            name, state = value.rsplit(" 目前", 1)
            return self.text("{name} 目前{state}", name=name, state=state)
        return value


def validate_flagship_translations() -> None:
    """Fail fast when any catalog row is incomplete or blank."""
    for source, translations in FLAGSHIP_TRANSLATIONS.items():
        if not source or len(translations) != len(_TRANSLATION_INDEX):
            raise ValueError(f"Invalid flagship translation row: {source!r}")
        if any(not value.strip() for value in translations):
            raise ValueError(f"Blank flagship translation: {source!r}")


validate_flagship_translations()
