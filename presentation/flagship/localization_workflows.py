"""Workflow editor, capability, permission-label, and planner translations."""

from __future__ import annotations

lazy from presentation.flagship.localization_catalog import (
    TranslationCatalog,
    translations,
)

WORKFLOW_TRANSLATIONS: TranslationCatalog = frozendict({
    # Workflow editor.
    "新增安全工作流程": translations(
        "新增安全工作流",
        "Add a Safe Workflow",
        "安全なワークフローを追加",
    ),
    "手動執行": translations("手动执行", "Run manually", "手動で実行"),
    "每天固定時間": translations(
        "每天固定时间", "Daily at a set time", "毎日指定時刻"
    ),
    "開始工作時": translations("开始工作时", "When work starts", "作業開始時"),
    "第一次與高風險操作先預覽": translations(
        "首次与高风险操作先预览",
        "Preview the first run and high-risk actions",
        "初回実行と高リスク操作を事前確認",
    ),
    "流程名稱": translations("流程名称", "Workflow name", "ワークフロー名"),
    "啟動方式": translations("启动方式", "Trigger", "起動条件"),
    "執行時間": translations("执行时间", "Run time", "実行時刻"),
    "排程設定無法讀取": translations(
        "排程设置无法读取",
        "Schedule settings could not be read",
        "スケジュール設定を読み取れません",
    ),
    "自動備份失敗": translations(
        "自动备份失败",
        "Automatic backup failed",
        "自動バックアップに失敗",
    ),
    "每行一個步驟，格式：能力｜說明｜參數。\n範例：open_web｜開啟工作網站｜https://example.com\n範例：home_control｜開啟書房燈｜light.study,turn_on": translations(
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
    "open_web｜開啟工作網站｜https://example.com": translations(
        "open_web｜打开工作网站｜https://example.com",
        "open_web | Open the work site | https://example.com",
        "open_web｜作業サイトを開く｜https://example.com",
    ),
    "{capability} 參數格式必須是 entity_id,service": translations(
        "{capability} 参数格式必须是 entity_id,service",
        "{capability} arguments must use entity_id,service",
        "{capability} の引数は entity_id,service 形式で指定してください",
    ),
    "{capability} 的參數必須是 JSON 物件": translations(
        "{capability} 的参数必须是 JSON 对象",
        "Arguments for {capability} must be a JSON object",
        "{capability} の引数は JSON オブジェクトで指定してください",
    ),
    "步驟格式不正確：{line}": translations(
        "步骤格式不正确：{line}",
        "Invalid step format: {line}",
        "ステップの形式が正しくありません：{line}",
    ),
    # Capability labels.
    "讀取狀態與摘要": translations(
        "读取状态与摘要", "Read status and summary", "状態と概要を読み取る"
    ),
    "搜尋白名單資料夾": translations(
        "搜索白名单文件夹", "Search allowlisted folders", "許可済みフォルダーを検索"
    ),
    "開啟網站": translations("打开网站", "Open websites", "Web サイトを開く"),
    "開啟資料夾": translations("打开文件夹", "Open folders", "フォルダーを開く"),
    "啟動白名單程式": translations(
        "启动白名单程序", "Launch allowlisted apps", "許可済みアプリを起動"
    ),
    "列出可見視窗": translations(
        "列出可见窗口", "List visible windows", "表示中のウィンドウを一覧表示"
    ),
    "切換至指定視窗": translations(
        "切换至指定窗口", "Switch to a specified window", "指定ウィンドウに切り替える"
    ),
    "建立檔案": translations("创建文件", "Create files", "ファイルを作成"),
    "重新命名檔案": translations("重命名文件", "Rename files", "ファイル名を変更"),
    "移動檔案": translations("移动文件", "Move files", "ファイルを移動"),
    "建立行事曆事件": translations(
        "创建日历事件", "Create calendar events", "カレンダー予定を作成"
    ),
    "修改行事曆事件": translations(
        "修改日历事件", "Update calendar events", "カレンダー予定を変更"
    ),
    "讀取行事曆": translations("读取日历", "Read calendars", "カレンダーを読み取る"),
    "讀取電子郵件": translations("读取电子邮件", "Read email", "メールを読み取る"),
    "寄送電子郵件": translations("发送电子邮件", "Send email", "メールを送信"),
    "讀取雲端檔案": translations(
        "读取云端文件", "Read cloud files", "クラウドファイルを読み取る"
    ),
    "建立或修改雲端檔案": translations(
        "创建或修改云端文件",
        "Create or update cloud files",
        "クラウドファイルを作成・変更",
    ),
    "對外發布內容": translations(
        "对外发布内容", "Publish content externally", "外部へコンテンツを公開"
    ),
    "讀取智慧家庭狀態": translations(
        "读取智能家居状态", "Read smart-home status", "スマートホームの状態を読み取る"
    ),
    "控制一般智慧設備": translations(
        "控制一般智能设备", "Control standard smart devices", "一般スマート機器を操作"
    ),
    "控制門鎖": translations("控制门锁", "Control door locks", "ドアロックを操作"),
    "控制警報": translations("控制警报", "Control alarms", "警報を操作"),
    "控制加熱與高溫設備": translations(
        "控制加热与高温设备",
        "Control heating and high-temperature devices",
        "暖房・高温機器を操作",
    ),
    "執行智慧家庭腳本或情境": translations(
        "执行智能家庭脚本或情境",
        "Run a smart-home script or scene",
        "スマートホームのスクリプトまたはシーンを実行",
    ),
    "使用攝影機": translations("使用摄像头", "Use the camera", "カメラを使用"),
    "遠端查看本程式畫面": translations(
        "远程查看本程序画面", "View this app remotely", "このアプリの画面をリモート表示"
    ),
    "遠端下載白名單檔案": translations(
        "远程下载白名单文件",
        "Download allowlisted files remotely",
        "許可済みファイルをリモート取得",
    ),
    "遠端寫入檔案": translations(
        "远程写入文件", "Write files remotely", "リモートでファイルを書き込む"
    ),
    "刪除檔案": translations("删除文件", "Delete files", "ファイルを削除"),
    "關機或重新啟動": translations(
        "关机或重新启动", "Shut down or restart", "シャットダウンまたは再起動"
    ),
    # Risk, permission, trigger and allowlist display labels.
    "低風險": translations("低风险", "Low risk", "低リスク"),
    "一般變更": translations("一般变更", "Standard change", "通常の変更"),
    "外部影響": translations("外部影响", "External impact", "外部への影響"),
    "高風險": translations("高风险", "High risk", "高リスク"),
    "禁止": translations("禁止", "Blocked", "禁止"),
    "每次詢問": translations("每次询问", "Ask every time", "毎回確認"),
    "允許": translations("允许", "Allow", "許可"),
    "手動": translations("手动", "Manual", "手動"),
    "每天 {time}": translations("每天 {time}", "Daily at {time}", "毎日 {time}"),
    "程式啟動時": translations("程序启动时", "When the app starts", "アプリ起動時"),
    "未知": translations("未知", "Unknown", "不明"),
    "{count} 步": translations("{count} 步", "{count} steps", "{count} ステップ"),
    "資料夾": translations("文件夹", "Folder", "フォルダー"),
    "程序": translations("程序", "App", "アプリ"),
    "網站": translations("网站", "Website", "Web サイト"),
    "只讀": translations("只读", "Read only", "読み取り専用"),
    "可寫": translations("可写", "Read and write", "読み書き可能"),
    "控制": translations("控制", "Control", "操作"),
    # Overview and planner.
    "<b>墨寒旗艦任務中心</b>": translations(
        "<b>墨寒旗舰任务中心</b>",
        "<b>MoHan Flagship Task Center</b>",
        "<b>墨寒フラッグシップ・タスクセンター</b>",
    ),
    "所有電腦、雲端、遠端與智慧家庭操作都必須經過："
    "計畫 → 權限判斷 → 確認 → 執行 → 結果驗證 → 稽核。": translations(
        "所有电脑、云端、远程与智能家居操作都必须经过："
        "计划 → 权限判断 → 确认 → 执行 → 结果验证 → 审计。",
        "Every computer, cloud, remote, and smart-home action must pass through: "
        "plan → permission check → confirmation → execution → result verification → audit.",
        "PC、クラウド、リモート、スマートホームのすべての操作は、"
        "計画 → 権限判定 → 確認 → 実行 → 結果検証 → 監査の順に処理されます。",
    ),
    "重新檢查系統狀態": translations(
        "重新检查系统状态", "Recheck system status", "システム状態を再確認"
    ),
    "立即建立可驗證備份": translations(
        "立即创建可验证备份",
        "Create a verifiable backup now",
        "検証可能なバックアップを今すぐ作成",
    ),
    "<b>自然語言工具任務</b>": translations(
        "<b>自然语言工具任务</b>",
        "<b>Natural-language tool task</b>",
        "<b>自然言語ツールタスク</b>",
    ),
    "例如：幫我開啟工作資料夾，然後開啟指定工作網站": translations(
        "例如：帮我打开工作文件夹，然后打开指定工作网站",
        "For example: Open my work folder, then open the specified work website",
        "例：作業フォルダーを開き、指定した作業サイトを開いて",
    ),
    "先產生安全計畫": translations(
        "先生成安全计划", "Create a safety plan first", "安全計画を先に作成"
    ),
    "資料備份": translations("数据备份", "Data Backup", "データバックアップ"),
    "備份失敗：{error}": translations(
        "备份失败：{error}",
        "Backup failed: {error}",
        "バックアップに失敗しました：{error}",
    ),
    "備份與完整性雜湊已建立：\n{target}": translations(
        "备份与完整性哈希已创建：\n{target}",
        "Backup and integrity hash created:\n{target}",
        "バックアップと整合性ハッシュを作成しました：\n{target}",
    ),
    "工具任務": translations("工具任务", "Tool Task", "ツールタスク"),
    "這句話沒有明確要求執行操作，因此不會產生工具計畫。": translations(
        "这句话没有明确要求执行操作，因此不会生成工具计划。",
        "This message does not clearly request an action, so no tool plan will be created.",
        "操作の実行を明確に求めていないため、ツール計画は作成しません。",
    ),
    "規劃中…": translations("规划中…", "Planning…", "計画中…"),
    "讀取 Gmail 郵件": translations(
        "读取 Gmail 邮件", "Read Gmail messages", "Gmail メールを読み取る"
    ),
    "讀取最近 {days} 天內最多 {limit} 封 Gmail 郵件": translations(
        "读取最近 {days} 天内最多 {limit} 封 Gmail 邮件",
        "Read up to {limit} Gmail messages from the last {days} days",
        "過去 {days} 日間の Gmail メールを最大 {limit} 件読み取る",
    ),
    "讀取 Google Calendar": translations(
        "读取 Google Calendar", "Read Google Calendar", "Google Calendar を読み取る"
    ),
    "讀取 Google Calendar 未來 {days} 天行程": translations(
        "读取 Google Calendar 未来 {days} 天的日程",
        "Read Google Calendar events for the next {days} days",
        "Google Calendar の今後 {days} 日間の予定を読み取る",
    ),
    "讀取 Google Drive": translations(
        "读取 Google Drive", "Read Google Drive", "Google Drive を読み取る"
    ),
    "搜尋 Google Drive 檔案：{name}": translations(
        "搜索 Google Drive 文件：{name}",
        "Search Google Drive files: {name}",
        "Google Drive のファイルを検索：{name}",
    ),
    "列出 Google Drive 最近修改的檔案": translations(
        "列出 Google Drive 最近修改的文件",
        "List recently modified Google Drive files",
        "Google Drive で最近変更されたファイルを一覧表示",
    ),
    "（目前沒有白名單目標）": translations(
        "（目前没有白名单目标）",
        "(No allowlisted targets are configured)",
        "（許可済み対象はまだありません）",
    ),
    "工具計畫": translations("工具计划", "Tool Plan", "ツール計画"),
    "計畫驗證失敗：{error}": translations(
        "计划验证失败：{error}",
        "Plan validation failed: {error}",
        "計画の検証に失敗しました：{error}",
    ),
    "資料不足或並非明確操作要求，因此沒有產生任何步驟。": translations(
        "信息不足或并非明确的操作要求，因此没有生成任何步骤。",
        "There was not enough information or no explicit action request, so no steps were created.",
        "情報が不足しているか操作要求が明確でないため、ステップは作成されませんでした。",
    ),
    "執行前計畫預覽": translations(
        "执行前计划预览", "Pre-execution Plan Preview", "実行前の計画確認"
    ),
    "{title}\n\n{preview}\n\n每一步仍會依個別權限與風險再次判斷。是否繼續？": translations(
        "{title}\n\n{preview}\n\n每一步仍会根据各自的权限与风险再次判断。是否继续？",
        "{title}\n\n{preview}\n\nEach step will still be checked against its own permissions and risk. Continue?",
        "{title}\n\n{preview}\n\n各ステップは個別の権限とリスクに基づいて再判定されます。続行しますか？",
    ),
    "任務結果": translations("任务结果", "Task Results", "タスク結果"),
    "無法產生計畫：{error}": translations(
        "无法生成计划：{error}",
        "Could not create a plan: {error}",
        "計画を作成できませんでした：{error}",
    ),
    "工具計畫逾時": translations(
        "工具计划超时", "Tool Plan Timed Out", "ツール計画がタイムアウトしました"
    ),
    "等待 OpenAI 安全計畫超過 50 秒，已自動停止等待。"
    "請確認網路、API 金鑰與文字模型後再試一次。": translations(
        "等待 OpenAI 安全计划超过 50 秒，已自动停止等待。"
        "请确认网络、API 密钥与文本模型后再试一次。",
        "The OpenAI safety plan took longer than 50 seconds, so waiting was stopped. "
        "Check the network, API key, and text model, then try again.",
        "OpenAI の安全計画を 50 秒以上待機したため、自動的に待機を停止しました。"
        "ネットワーク、API キー、テキストモデルを確認して再試行してください。",
    ),
    "Home Assistant：{home}\n遠端服務：{remote}\n已啟用工作流程：{workflows}\n"
    "有效配對裝置：{devices}\n安全狀態：高風險操作不允許免確認；"
    "任意命令列與付款永久禁止。": translations(
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
    "已啟用": translations("已启用", "Enabled", "有効"),
    "未啟用": translations("未启用", "Disabled", "無効"),
    "運作中": translations("运行中", "Running", "稼働中"),
    "新增工作流程": translations("新增工作流", "Add workflow", "ワークフローを追加"),
    "執行選取流程": translations(
        "执行选中流程", "Run selected workflow", "選択したワークフローを実行"
    ),
    "刪除選取流程": translations(
        "删除选中流程", "Delete selected workflow", "選択したワークフローを削除"
    ),
    "請先選取一個流程。": translations(
        "请先选择一个流程。",
        "Select a workflow first.",
        "先にワークフローを選択してください。",
    ),
    "預覽工作流程": translations(
        "预览工作流", "Preview Workflow", "ワークフローを確認"
    ),
    "{title}\n\n{preview}\n\n是否執行？": translations(
        "{title}\n\n{preview}\n\n是否执行？",
        "{title}\n\n{preview}\n\nRun this workflow?",
        "{title}\n\n{preview}\n\nこのワークフローを実行しますか？",
    ),
    "沒有可執行步驟": translations(
        "没有可执行步骤", "No executable steps", "実行できるステップはありません"
    ),
    "刪除工作流程": translations(
        "删除工作流", "Delete Workflow", "ワークフローを削除"
    ),
    "確定刪除「{name}」？": translations(
        "确定删除“{name}”？", "Delete “{name}”?", "「{name}」を削除しますか？"
    ),
})

__all__ = ("WORKFLOW_TRANSLATIONS",)
