# Background Manager–Worker assistants

## 繁體中文

墨寒的背景多工採「經理—工作者」架構。經理只負責排程、冷卻、去重與收集觀察；工作者只能執行明確的唯讀任務。工作者不會直接碰 UI、表情圖片、語音、工具執行器或權限設定。主執行緒收到觀察後，仍須交給既有表情仲裁器決定是否顯示。

`v2.1.0-rc.1` 提供兩個可關閉的工作者：

- 可見程式狀態：只讀取 Windows 可見視窗標題，偵測使用者指定的程式是否剛開啟。
- IDE 診斷報告：只讀取使用者明確指定的 `.txt` 或 `.log` 報告尾端，統計含錯誤或警告的行數；不截取編輯器畫面、不修改專案，也不自動把內容送往雲端。

背景多工預設關閉。啟用後仍遵守：

- 勿擾、會議、離席與休眠模式不插話。
- 墨寒說話、Realtime 對話或其他表情情境進行中不插話。
- 同事件冷卻與全域冷卻，避免碎碎念洗版。
- 背景觀察只使用中性注視表情，不得觸發 thinking、skeptical、抓包、害羞或生氣。
- 行事曆建立、郵件草稿／寄送等既有工具仍遵守本機權限與確認流程；背景工作者不能繞過確認。

## 简体中文

墨寒的后台多任务采用“管理者—工作者”架构。管理者负责调度、冷却和去重；工作者只能执行明确的只读任务，不能直接操作界面、表情、语音、工具或权限。后台功能默认关闭，并遵守勿扰、会议、离席、休眠、对话中不打断及频率限制。

当前工作者可监测用户指定的可见程序名称，并只读用户明确指定的 IDE 诊断报告。它不会截取编辑器内容、修改项目或绕过日历、邮件等工具的确认流程。

## English

MoHan uses a Manager–Worker design for background assistance. The manager schedules bounded work, deduplicates observations, and enforces cooldowns. Workers are read-only and cannot directly touch the UI, expressions, speech, action executor, or permission policy. The main thread remains the sole bridge to the existing expression arbiter.

The feature is off by default. The first workers can observe user-selected visible application names and count issue lines in an explicitly selected IDE diagnostic `.txt` or `.log` report. They do not capture editor content, modify projects, upload report contents, or bypass confirmations for calendar, email, or other tools. Do Not Disturb, meeting, away, sleep, active speech, Realtime conversation, per-event cooldowns, and global cooldowns all suppress unsolicited messages.
