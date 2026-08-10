# 背景經理—工作者助理／后台管理者—工作者助理／Background Manager–Worker Assistants／バックグラウンド・マネージャー—ワーカー・アシスタント

## 繁體中文

墨寒的背景多工採「經理—工作者」架構。經理只負責排程、冷卻、去重與收集
觀察；工作者只能執行明確的唯讀任務。工作者不會直接碰 UI、表情圖片、語音、
工具執行器或權限設定。主執行緒收到觀察後，仍須交給既有表情仲裁器決定是否顯示。

`v2.1.0-rc.1` 提供兩個可關閉的工作者：

- 可見程式狀態：只讀取 Windows 可見視窗標題，偵測使用者指定的程式是否剛開啟。
- IDE 診斷報告：只讀取使用者明確指定的 `.txt` 或 `.log` 報告尾端，統計含錯誤或
  警告的行數；不截取編輯器畫面、不修改專案，也不自動把內容送往雲端。

背景多工預設關閉。啟用後仍遵守：

- 勿擾、會議、離席與休眠模式不插話。
- 墨寒說話、`Realtime` 對話或其他表情情境進行中不插話。
- 同事件冷卻與全域冷卻，避免碎碎念洗版。
- 背景觀察只使用中性注視表情，不得觸發 `thinking`、`skeptical`、抓包、害羞或生氣。
- 行事曆建立、郵件草稿／寄送等既有工具仍遵守本機權限與確認流程；背景工作者
  不能繞過確認。

## 简体中文

墨寒的后台多任务采用“管理者—工作者”架构。管理者只负责调度、冷却、去重与收集
观察；工作者只能执行明确的只读任务。工作者不会直接操作 UI、表情图片、语音、
工具执行器或权限设置。主线程收到观察后，仍须交由现有表情仲裁器决定是否显示。

`v2.1.0-rc.1` 提供两个可以关闭的工作者：

- 可见程序状态：只读取 Windows 可见窗口标题，检测用户指定的程序是否刚刚打开。
- IDE 诊断报告：只读取用户明确指定的 `.txt` 或 `.log` 报告末尾，统计包含错误或
  警告的行数；不截取编辑器画面、不修改项目，也不会自动把内容发送到云端。

后台多任务默认关闭。启用后仍须遵守：

- 请勿打扰、会议、离席与休眠模式下不插话。
- 墨寒说话、`Realtime` 对话或其他表情情境进行中不插话。
- 对同一事件实施冷却与全局冷却，避免反复提示刷屏。
- 后台观察只使用中性注视表情，不得触发 `thinking`、`skeptical`、抓包、害羞或生气。
- 日历建立、邮件草稿／发送等现有工具仍须遵守本机权限与确认流程；后台工作者
  不能绕过确认。

## English

MoHan uses a Manager–Worker architecture for background multitasking. The manager
only schedules work, enforces cooldowns, deduplicates events, and collects observations;
workers can perform only explicit read-only tasks. Workers never directly touch the UI,
expression images, speech, the tool executor, or permission settings. After the main
thread receives an observation, the existing expression arbiter still decides whether
anything is displayed.

`v2.1.0-rc.1` provides two workers that users can disable:

- Visible application status: reads only visible Windows window titles and detects whether
  a user-selected application has just opened.
- IDE diagnostic report: reads only the tail of a user-explicitly selected `.txt` or `.log`
  report and counts lines containing errors or warnings; it does not capture the editor,
  modify the project, or automatically send content to the cloud.

Background multitasking is off by default. When enabled, it still follows these rules:

- Do Not Disturb, meeting, away, and sleep modes suppress interruptions.
- MoHan's speech, a `Realtime` conversation, or another active expression context suppresses
  interruptions.
- Per-event and global cooldowns prevent repetitive messages from flooding the interface.
- Background observations use only a neutral gaze expression and must never trigger
  `thinking`, `skeptical`, caught-in-the-act, shy, or angry expressions.
- Existing tools for calendar creation and email drafting or sending still follow local
  permissions and confirmation flows; background workers cannot bypass confirmation.

## 日本語

墨寒のバックグラウンド並行処理は「マネージャー—ワーカー」アーキテクチャを
採用します。マネージャーはスケジュール、クールダウン、重複排除、観察結果の収集
だけを担当し、ワーカーは明示された読み取り専用タスクだけを実行できます。
ワーカーは UI、表情画像、音声、ツール実行機構、権限設定を直接操作しません。
メインスレッドが観察結果を受け取った後も、表示するかどうかは既存の表情調停器が決定します。

`v2.1.0-rc.1` では、無効化できる二つのワーカーを提供します：

- 表示中アプリケーションの状態：表示されている Windows ウィンドウのタイトルだけを
  読み取り、利用者が指定したアプリケーションが起動した直後かどうかを検出します。
- IDE 診断レポート：利用者が明示的に指定した `.txt` または `.log` レポートの末尾だけを
  読み取り、エラーまたは警告を含む行数を集計します。エディター画面を取得せず、
  プロジェクトを変更せず、内容を自動的にクラウドへ送信しません。

バックグラウンド並行処理は既定で無効です。有効にした場合も、次の規則に従います：

- おやすみモード、会議、離席、休眠の各モードでは割り込みません。
- 墨寒の発話中、`Realtime` 対話中、または別の表情コンテキストの進行中は割り込みません。
- イベント単位と全体のクールダウンにより、同じ通知が繰り返し表示されるのを防ぎます。
- バックグラウンド観察では中立的な視線表情だけを使用し、`thinking`、`skeptical`、
  現場を押さえた表情、恥じらい、怒りを発動してはなりません。
- カレンダー作成、メールの下書き／送信など既存のツールは、引き続きローカル権限と
  確認手順に従います。バックグラウンドワーカーは確認を迂回できません。
