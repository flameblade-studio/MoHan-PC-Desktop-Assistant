"""Security, audit, result, domain-message, and policy translations."""

from __future__ import annotations

lazy from presentation.flagship.localization_catalog import (
    TranslationCatalog,
    translations,
)

SECURITY_AUDIT_TRANSLATIONS: TranslationCatalog = frozendict({
    # Security and auditing.
    "<b>允許操作的資料夾與程式</b>": translations(
        "<b>允许操作的文件夹与程序</b>",
        "<b>Allowed folders and apps</b>",
        "<b>操作を許可するフォルダーとアプリ</b>",
    ),
    "加入資料夾": translations("添加文件夹", "Add folder", "フォルダーを追加"),
    "加入程式": translations("添加程序", "Add app", "アプリを追加"),
    "加入網站": translations("添加网站", "Add website", "Web サイトを追加"),
    "程式": translations("程序", "App", "アプリ"),
    "移除選取項目": translations(
        "移除选中项目", "Remove selected item", "選択項目を削除"
    ),
    "<b>能力權限</b>": translations(
        "<b>能力权限</b>", "<b>Capability permissions</b>", "<b>機能権限</b>"
    ),
    "{label}（{risk}）": translations(
        "{label}（{risk}）", "{label} ({risk})", "{label}（{risk}）"
    ),
    "即使選擇允許，高風險政策仍會要求確認。": translations(
        "即使选择允许，高风险策略仍会要求确认。",
        "High-risk policy still requires confirmation even when Allow is selected.",
        "「許可」を選択しても、高リスク方針により確認が必要です。",
    ),
    "使用麥克風": translations(
        "使用麦克风", "Use microphone", "マイクを使用"
    ),
    "啟動 Realtime 雲端對話": translations(
        "启动 Realtime 云端对话",
        "Start a Realtime cloud conversation",
        "Realtime クラウド会話を開始",
    ),
    "保存安全權限": translations(
        "保存安全权限", "Save security permissions", "セキュリティ権限を保存"
    ),
    "付款、購買、密碼匯出、停用安全防護、任意 PowerShell／管理員命令"
    "永遠禁止自動執行，無法由此頁解除。": translations(
        "付款、购买、密码导出、停用安全防护、任意 PowerShell／管理员命令"
        "始终禁止自动执行，无法在此页面解除。",
        "Payments, purchases, password exports, disabling safeguards, arbitrary PowerShell, "
        "and administrator commands can never run automatically and cannot be enabled here.",
        "支払い、購入、パスワードの書き出し、安全保護の無効化、任意の PowerShell／管理者コマンドは"
        "常に自動実行禁止で、この画面から解除できません。",
    ),
    "選擇允許墨寒操作的資料夾": translations(
        "选择允许墨寒操作的文件夹",
        "Choose a folder MoHan may access",
        "墨寒に操作を許可するフォルダーを選択",
    ),
    "資料夾權限": translations("文件夹权限", "Folder Permission", "フォルダー権限"),
    "輸入 read（只讀）或 write（可建立、移動與重新命名）": translations(
        "输入 read（只读）或 write（可创建、移动与重命名）",
        "Enter read (read only) or write (create, move, and rename)",
        "read（読み取り専用）または write（作成・移動・名前変更可）を入力",
    ),
    "選擇允許墨寒啟動的程式": translations(
        "选择允许墨寒启动的程序",
        "Choose an app MoHan may launch",
        "墨寒に起動を許可するアプリを選択",
    ),
    "Windows 程式 (*.exe);;所有檔案 (*)": translations(
        "Windows 程序 (*.exe);;所有文件 (*)",
        "Windows apps (*.exe);;All files (*)",
        "Windows アプリ (*.exe);;すべてのファイル (*)",
    ),
    "應用程式／可執行檔 (*);;所有檔案 (*)": translations(
        "应用程序／可执行文件 (*);;所有文件 (*)",
        "Apps / executables (*);;All files (*)",
        "アプリ／実行ファイル (*);;すべてのファイル (*)",
    ),
    "程式別名": translations("程序别名", "App Alias", "アプリの別名"),
    "日後對墨寒說的程式名稱": translations(
        "日后对墨寒说的程序名称",
        "The app name you will use when speaking to MoHan",
        "今後、墨寒に伝えるアプリ名",
    ),
    "加入允許網站": translations(
        "添加允许网站", "Add Allowed Website", "許可する Web サイトを追加"
    ),
    "輸入完整 HTTPS 網址（可限制到指定路徑）": translations(
        "输入完整 HTTPS 地址（可限制到指定路径）",
        "Enter a complete HTTPS URL (optionally restricted to a path)",
        "完全な HTTPS URL を入力（特定パスに制限可能）",
    ),
    "網站白名單": translations(
        "网站白名单", "Website Allowlist", "Web サイト許可リスト"
    ),
    "公開網站只接受完整 HTTPS 網址。": translations(
        "公开网站仅接受完整 HTTPS 地址。",
        "Public websites require a complete HTTPS URL.",
        "公開 Web サイトには完全な HTTPS URL のみ使用できます。",
    ),
    "移除允許項目": translations(
        "移除允许项目", "Remove Allowed Item", "許可項目を削除"
    ),
    "確定撤銷墨寒對此項目的存取權？": translations(
        "确定撤销墨寒对此项目的访问权？",
        "Revoke MoHan's access to this item?",
        "この項目に対する墨寒のアクセス権を取り消しますか？",
    ),
    "安全權限已保存。妾會守住這條界線。": translations(
        "安全权限已保存。妾会守住这条界线。",
        "Security permissions saved. I will hold this boundary.",
        "セキュリティ権限を保存しました。妾がこの境界を守ります。",
    ),
    "重新整理": translations("刷新", "Refresh", "更新"),
    "<p>尚無工具操作紀錄。</p>": translations(
        "<p>尚无工具操作记录。</p>",
        "<p>No tool activity has been recorded.</p>",
        "<p>ツール操作の記録はまだありません。</p>",
    ),
    "高風險操作二次確認": translations(
        "高风险操作二次确认",
        "Second Confirmation for High-Risk Action",
        "高リスク操作の再確認",
    ),
    "墨寒請求執行工具": translations(
        "墨寒请求执行工具",
        "MoHan Requests Tool Execution",
        "墨寒がツール実行を要求しています",
    ),
    "風險：{risk}\n來源：{source}\n操作：{description}\n\n參數預覽：\n{detail}\n\n是否允許？": translations(
        "风险：{risk}\n来源：{source}\n操作：{description}\n\n参数预览：\n{detail}\n\n是否允许？",
        "Risk: {risk}\nSource: {source}\nAction: {description}\n\nArgument preview:\n{detail}\n\nAllow this action?",
        "リスク：{risk}\n送信元：{source}\n操作：{description}\n\n引数の確認：\n{detail}\n\n許可しますか？",
    ),
    "已停手。所有工具與遠端連線均已中止。": translations(
        "已停止。所有工具与远程连接均已中止。",
        "Stopped. All tools and remote connections have been terminated.",
        "停止しました。すべてのツールとリモート接続を終了しました。",
    ),
    "緊急停止": translations("紧急停止", "Emergency Stop", "緊急停止"),
    "所有進行中的工具任務與遠端服務均已停止。": translations(
        "所有进行中的工具任务与远程服务均已停止。",
        "All active tool tasks and remote services have been stopped.",
        "実行中のすべてのツールタスクとリモートサービスを停止しました。",
    ),
    # Results generated in this module.
    "已整理目前工作狀態": translations(
        "已整理当前工作状态",
        "Current work status summarized",
        "現在の作業状態を整理しました",
    ),
    "已讀取剪貼簿文字": translations(
        "已读取剪贴板文本",
        "Clipboard text read",
        "クリップボードのテキストを読み取りました",
    ),
    "已寫入剪貼簿": translations(
        "已写入剪贴板", "Copied to clipboard", "クリップボードにコピーしました"
    ),
    "剪貼簿文字不可超過 100,000 字": translations(
        "剪贴板文本不可超过 100,000 字",
        "Clipboard text cannot exceed 100,000 characters",
        "クリップボードのテキストは 100,000 文字を超えられません",
    ),
    "已讀取 {count} 封郵件摘要": translations(
        "已读取 {count} 封邮件摘要",
        "Read {count} email summaries",
        "メールの概要を {count} 件読み取りました",
    ),
    "收件者、主旨與內容不可留空": translations(
        "收件人、主题与内容不可留空",
        "Recipient, subject, and body are required",
        "宛先、件名、本文は必須です",
    ),
    "Gmail 未傳回草稿 ID": translations(
        "Gmail 未返回草稿 ID",
        "Gmail did not return a draft ID",
        "Gmail から下書き ID が返されませんでした",
    ),
    "郵件已寄給 {recipient}": translations(
        "邮件已发送给 {recipient}",
        "Email sent to {recipient}",
        "{recipient} にメールを送信しました",
    ),
    "已讀取 {count} 個行程": translations(
        "已读取 {count} 个日程",
        "Read {count} calendar events",
        "予定を {count} 件読み取りました",
    ),
    "行程標題、開始與結束時間不可留空": translations(
        "日程标题、开始与结束时间不可留空",
        "Event title, start time, and end time are required",
        "予定のタイトル、開始時刻、終了時刻は必須です",
    ),
    "結束時間必須晚於開始時間": translations(
        "结束时间必须晚于开始时间",
        "The end time must be later than the start time",
        "終了時刻は開始時刻より後にしてください",
    ),
    "已建立行程：{title}": translations(
        "已创建日程：{title}",
        "Calendar event created: {title}",
        "予定を作成しました：{title}",
    ),
    "搜尋 OneDrive 時請提供檔案名稱": translations(
        "搜索 OneDrive 时请提供文件名",
        "Provide a file name when searching OneDrive",
        "OneDrive を検索する際はファイル名を指定してください",
    ),
    "找到 {count} 個符合的雲端檔案": translations(
        "找到 {count} 个匹配的云端文件",
        "Found {count} matching cloud files",
        "一致するクラウドファイルが {count} 件見つかりました",
    ),
    "只能上傳白名單內的單一檔案": translations(
        "只能上传白名单内的单个文件",
        "Only one allowlisted file can be uploaded",
        "許可リスト内の単一ファイルのみアップロードできます",
    ),
    "已上傳：{name}": translations(
        "已上传：{name}", "Uploaded: {name}", "アップロードしました：{name}"
    ),
    # Known messages emitted by domain services and displayed by this UI.
    "任務已由使用者取消": translations(
        "任务已由用户取消",
        "Task cancelled by the user",
        "ユーザーがタスクをキャンセルしました",
    ),
    "重複請求已安全略過": translations(
        "重复请求已安全跳过",
        "Duplicate request safely skipped",
        "重複した要求を安全にスキップしました",
    ),
    "使用者未授權執行": translations(
        "用户未授权执行",
        "Execution was not authorized by the user",
        "ユーザーが実行を許可しませんでした",
    ),
    "尚未安裝此工具的執行器": translations(
        "尚未安装此工具的执行器",
        "No executor is installed for this tool",
        "このツールの実行機能はインストールされていません",
    ),
    "工具回報完成，但結果驗證未通過": translations(
        "工具报告完成，但结果验证未通过",
        "The tool reported completion, but result verification failed",
        "ツールは完了を報告しましたが、結果検証に失敗しました",
    ),
    "已開啟網站": translations(
        "已打开网站", "Website opened", "Web サイトを開きました"
    ),
    "已開啟資料夾：{value}": translations(
        "已打开文件夹：{value}",
        "Folder opened: {value}",
        "フォルダーを開きました：{value}",
    ),
    "已啟動：{value}": translations(
        "已启动：{value}", "Launched: {value}", "起動しました：{value}"
    ),
    "已建立檔案：{value}": translations(
        "已创建文件：{value}",
        "File created: {value}",
        "ファイルを作成しました：{value}",
    ),
    "找到 {count} 個符合項目": translations(
        "找到 {count} 个匹配项目",
        "Found {count} matching items",
        "一致する項目が {count} 件見つかりました",
    ),
    "已移動至：{value}": translations(
        "已移动至：{value}", "Moved to: {value}", "移動先：{value}"
    ),
    "目前有 {count} 個可見視窗": translations(
        "目前有 {count} 个可见窗口",
        "There are {count} visible windows",
        "表示中のウィンドウは {count} 個です",
    ),
    "已切換至：{value}": translations(
        "已切换至：{value}", "Switched to: {value}", "切り替え先：{value}"
    ),
    "已執行 {value}": translations(
        "已执行 {value}", "Executed {value}", "{value} を実行しました"
    ),
    "工具執行失敗：{detail}": translations(
        "工具执行失败：{detail}",
        "Tool execution failed: {detail}",
        "ツール実行に失敗しました：{detail}",
    ),
    # Policy reasons are internal canonical values translated only at display time.
    "此能力永不允許自動執行": translations(
        "此能力永不允许自动执行",
        "This capability can never run automatically",
        "この機能は自動実行できません",
    ),
    "未知的指令來源": translations(
        "未知的指令来源", "Unknown command source", "指示の送信元が不明です"
    ),
    "目標位於受保護路徑": translations(
        "目标位于受保护路径",
        "The target is in a protected path",
        "対象は保護されたパスにあります",
    ),
    "權限設定為禁止": translations(
        "权限设置为禁止",
        "Permission is set to Blocked",
        "権限が「禁止」に設定されています",
    ),
    "通過本機權限政策": translations(
        "通过本机权限策略",
        "Passed the local permission policy",
        "ローカル権限方針を通過しました",
    ),
})

__all__ = ("SECURITY_AUDIT_TRANSLATIONS",)
