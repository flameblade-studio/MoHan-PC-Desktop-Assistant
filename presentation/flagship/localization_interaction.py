"""Common controls, companion care, gesture, and visual-status translations."""

from __future__ import annotations

lazy from presentation.flagship.localization_catalog import (
    TranslationCatalog,
    translations,
)

INTERACTION_TRANSLATIONS: TranslationCatalog = frozendict({
    # Common controls and top-level navigation.
    "儲存": translations("保存", "Save", "保存"),
    "取消": translations("取消", "Cancel", "キャンセル"),
    "確定": translations("确定", "OK", "OK"),
    "停手": translations("停手", "STOP", "停止"),
    "緊急停止所有工具與遠端操作（Esc）": translations(
        "紧急停止所有工具与远程操作（Esc）",
        "Emergency stop for all tools and remote operations (Esc)",
        "すべてのツールとリモート操作を緊急停止（Esc）",
    ),
    "任務中心": translations("任务中心", "Task Center", "タスクセンター"),
    "工作流程": translations("工作流", "Workflows", "ワークフロー"),
    "設定讀取": translations("设置读取", "Settings read", "設定の読み取り"),
    '讀取主動提醒設定需要處理，上一組有效值持續使用。': translations(
        '读取主动提醒设置需要处理，上一组有效值持续使用。',
        'Reading proactive reminder settings requires attention; the last valid values remain active.',
        '自発的リマインダー設定の読み取りへの対応が必要です。直前の有効な値を維持します。',
    ),
    "雲端連接器": translations("云端连接器", "Cloud Connectors", "クラウド接続"),
    "智慧家庭": translations("智能家居", "Smart Home", "スマートホーム"),
    "遠端與隱私": translations(
        "远程与隐私", "Remote & Privacy", "リモートとプライバシー"
    ),
    "安全權限": translations("安全权限", "Security Permissions", "セキュリティ権限"),
    "稽核紀錄": translations("审计记录", "Audit Log", "監査ログ"),
    "陪伴與關心": translations("陪伴与关怀", "Companion Care", "寄り添いと気遣い"),
    "<b>主動陪伴與健康提醒</b>": translations(
        "<b>主动陪伴与健康提醒</b>",
        "<b>Proactive care and wellbeing reminders</b>",
        "<b>自発的な気遣いと健康リマインダー</b>",
    ),
    "所有變更會先暫存；只有控制台下方的全域保存設定才會生效。": translations(
        "所有更改会先暂存；只有控制台下方的全局保存设置才会生效。",
        "Changes remain staged until you use the global Save Settings action below.",
        "変更は一時保存され、下部の全体設定を保存したときに反映されます。",
    ),
    "啟用主動陪伴": translations("启用主动陪伴", "Enable proactive care", "自発的な気遣いを有効化"),
    "飲食提醒": translations("饮食提醒", "Meal reminders", "食事リマインダー"),
    "喝水提醒": translations("喝水提醒", "Hydration reminders", "水分補給リマインダー"),
    "休息提醒": translations("休息提醒", "Rest reminders", "休憩リマインダー"),
    "久坐提醒": translations("久坐提醒", "Prolonged-sitting reminders", "長時間着座リマインダー"),
    "特殊節日提醒": translations("特殊节日提醒", "Special-occasion reminders", "特別な日のリマインダー"),
    "墨寒生日提醒": translations("墨寒生日提醒", "MoHan birthday reminders", "墨寒の誕生日リマインダー"),
    "專注時暫停主動提醒": translations("专注时暂停主动提醒", "Pause during focus", "集中時は一時停止"),
    "會議時暫停主動提醒": translations("会议时暂停主动提醒", "Pause during meetings", "会議中は一時停止"),
    "全螢幕時暫停主動提醒": translations("全屏时暂停主动提醒", "Pause in fullscreen", "全画面表示中は一時停止"),
    "短暫離座門檻": translations("短暂离座阈值", "Brief absence threshold", "短時間離席のしきい値"),
    "久候門檻": translations("久候阈值", "Long-wait threshold", "長時間待機のしきい値"),
    "短暫離座門檻（分鐘）": translations("短暂离座阈值（分钟）", "Brief absence threshold (minutes)", "短時間離席のしきい値（分）"),
    "久候門檻（分鐘）": translations("久候阈值（分钟）", "Long-wait threshold (minutes)", "長時間待機のしきい値（分）"),
    "每日主動提醒上限": translations("每日主动提醒上限", "Daily proactive reminder limit", "1日の自発的リマインダー上限"),
    " 分鐘": translations(" 分鐘", " minutes", " 分"),
    "，減少": translations("，减少", ", decrease", "、減らす"),
    "，增加": translations("，增加", ", increase", "、増やす"),
    "主動寒暄模式": translations(
        "主动寒暄模式", "Proactive greeting mode", "自発的な挨拶モード"
    ),
    "歡迎回來的最短離座時間": translations(
        "欢迎回来的最短离座时间",
        "Minimum absence before a welcome-back",
        "おかえり挨拶までの最短離席時間",
    ),
    "歡迎回來的最短離座時間（分鐘）": translations(
        "欢迎回来的最短离座时间（分钟）",
        "Minimum absence before a welcome-back (minutes)",
        "おかえり挨拶までの最短離席時間（分）",
    ),
    "對話沉默關心門檻": translations(
        "对话沉默关怀阈值",
        "Conversation-silence check-in threshold",
        "会話沈黙後の気遣いしきい値",
    ),
    "對話沉默關心門檻（分鐘）": translations(
        "对话沉默关怀阈值（分钟）",
        "Conversation-silence check-in threshold (minutes)",
        "会話沈黙後の気遣いしきい値（分）",
    ),
    "<b>演出偏好</b>": translations(
        "<b>演出偏好</b>",
        "<b>Performance preferences</b>",
        "<b>パフォーマンス設定</b>",
    ),
    "背身與 360° 演出預設關閉；勾選後按全域保存設定才會生效。": translations(
        "背身与 360° 演出默认关闭；勾选后按全局保存设置才会生效。",
        "Back-view and 360° performances are off by default; they take effect only after global Save Settings.",
        "背面と360°パフォーマンスは既定で無効です。チェック後、全体設定を保存すると反映されます。",
    ),
    "允許 360° 視角演出": translations(
        "允许 360° 视角演出",
        "Allow 360° view performances",
        "360°ビューのパフォーマンスを許可",
    ),
    "允許全背身演出": translations(
        "允许全背身演出",
        "Allow full back-view performances",
        "完全な背面パフォーマンスを許可",
    ),
    "允許情緒背身演出": translations(
        "允许情绪背身演出",
        "Allow emotional back-view performances",
        "感情表現の背面パフォーマンスを許可",
    ),
    "允許攝影機情境驅動演出": translations(
        "允许摄像头情境驱动演出",
        "Allow camera-context-driven performances",
        "カメラ状況に応じたパフォーマンスを許可",
    ),
    "演出強度": translations(
        "演出强度", "Performance intensity", "パフォーマンス強度"
    ),
    "<b>介面與無障礙</b>": translations(
        "<b>界面与无障碍</b>",
        "<b>Interface & accessibility</b>",
        "<b>インターフェースとアクセシビリティ</b>",
    ),
    "高對比模式": translations(
        "高对比模式", "High-contrast mode", "ハイコントラストモード"
    ),
    "介面縮放": translations("界面缩放", "Interface scale", "画面の拡大率"),
    "保存設定後立即套用於旗艦中心；主控台重新啟動後套用。": translations(
        "保存设置后立即应用于旗舰中心；主控台重新启动后应用。",
        "Applies to the flagship center right after Save Settings; the dashboard applies it after a restart.",
        "設定を保存するとフラッグシップセンターに即時適用され、ダッシュボードには再起動後に適用されます。",
    ),
    "<b>手勢互動</b>": translations(
        "<b>手势互动</b>", "<b>Gesture interaction</b>", "<b>ジェスチャー操作</b>"
    ),
    "所有手勢變更只會先暫存，按下全域保存設定後才會生效。自訂文字指令會交由既有安全命令流程處理。": translations(
        "所有手势更改只会先暂存，按下全局保存设置后才会生效。自定义文字指令会交由现有安全命令流程处理。",
        "Gesture changes remain staged until global Save Settings. Custom text commands use the existing safe-command flow.",
        "ジェスチャーの変更は一時保存され、全体設定を保存したときだけ反映されます。カスタム文字指示は既存の安全なコマンド処理を通ります。",
    ),
    "啟用手勢互動": translations("启用手势互动", "Enable gesture interaction", "ジェスチャー操作を有効化"),
    "手勢列表": translations("手势列表", "Gesture list", "ジェスチャー一覧"),
    "手勢名稱": translations("手势名称", "Gesture name", "ジェスチャー名"),
    "辨識後動作": translations("识别后动作", "Action after recognition", "認識後の動作"),
    "自訂文字指令": translations("自定义文字指令", "Custom text command", "カスタム文字指示"),
    "輸入一行交給墨寒安全命令流程的文字指令": translations(
        "输入一行交给墨寒安全命令流程的文字指令",
        "Enter one text command for MoHan's safe-command flow",
        "墨寒の安全なコマンド処理へ渡す一行の文字指示を入力",
    ),
    "啟用此手勢": translations("启用此手势", "Enable this gesture", "このジェスチャーを有効化"),
    "錄製狀態": translations("录制状态", "Recording status", "記録状態"),
    "新增自訂手勢": translations("新增自定义手势", "Add custom gesture", "カスタムジェスチャーを追加"),
    "重新命名": translations("重新命名", "Rename", "名前を変更"),
    "刪除自訂手勢": translations("删除自定义手势", "Delete custom gesture", "カスタムジェスチャーを削除"),
    "重設內建手勢": translations("重置内置手势", "Reset built-in gesture", "内蔵ジェスチャーをリセット"),
    "錄製手部特徵": translations("录制手部特征", "Record hand features", "手の特徴を記録"),
    "內建": translations("内置", "Built-in", "内蔵"),
    "自訂": translations("自定义", "Custom", "カスタム"),
    "已停用": translations("已停用", "Disabled", "無効"),
    "內建手勢使用已稽核的偵測器，不需錄製。": translations(
        "内置手势使用已审核的检测器，无需录制。",
        "Built-in gestures use the audited detector and use the audited detector directly.",
        "内蔵ジェスチャーは監査済み検出器を使用するため、記録は不要です。",
    ),
    '錄製僅保存手部特徵資料。': translations(
        '录制仅保存手部特征数据。',
        'Recording stores only hand-feature data.',
        '記録する内容は手の特徴データのみです。',
    ),
    '請先取得穩定的手部 landmark 訊號，再開始安全錄製。': translations(
        '请先取得稳定的手部 landmark 信号，再开始安全录制。',
        'Obtain a stable hand landmark signal before starting a safe recording.',
        '安定した手の landmark 信号を取得してから、安全な記録を開始してください。',
    ),
    '錄製已取消，既有保存資料維持原樣。': translations(
        '录制已取消，现有保存数据保持原样。',
        'Recording cancelled; saved data remains intact.',
        '記録を取り消しました。既存の保存データを維持します。',
    ),
    "已暫存手部特徵；全域保存後才會生效。": translations(
        "已暂存手部特征；全局保存后才会生效。",
        "Hand features are staged and take effect only after global Save Settings.",
        "手の特徴を一時保存しました。全体設定を保存した後に反映されます。",
    ),
    '手勢辨識已就緒，保存內容僅限手部特徵資料。': translations(
        '手势识别已就绪，保存内容仅限手部特征数据。',
        'Gesture recognition is ready; stored content is limited to hand-feature data.',
        'ジェスチャー認識の準備ができました。保存内容は手の特徴データに限定します。',
    ),
    '攝影機就緒後即可啟用手勢互動。': translations(
        '摄像头就绪后即可启用手势交互。',
        'Gesture interaction can start once the camera is ready.',
        'カメラの準備が整うとジェスチャー操作を開始できます。',
    ),
    "手部模型缺失，手勢互動保持停用。": translations(
        "手部模型缺失，手势互动保持停用。",
        "Install the hand models before gesture interaction can begin.",
        "手モデルがないため、ジェスチャー操作は無効のままです。",
    ),
    '請檢查手部模型載入狀態；手勢互動保持暫停。': translations(
        '请检查手部模型加载状态；手势交互保持暂停。',
        'Check hand-model loading; gesture interaction remains paused.',
        '手モデルの読み込み状態を確認してください。ジェスチャー操作を一時停止します。',
    ),
    '手勢辨識連續出現錯誤，已安全暫停，請檢查模型後再試。': translations(
        '手势识别连续出现错误，已安全暂停，请检查模型后重试。',
        'Repeated gesture-recognition errors triggered a safe pause. Check the model and retry.',
        'ジェスチャー認識でエラーが続いたため、安全に一時停止しました。モデルを確認して再試行してください。',
    ),
    "手勢互動目前未啟用。": translations(
        "手势互动目前未启用。",
        "Gesture interaction is currently disabled.",
        "ジェスチャー操作は現在無効です。",
    ),
    '完成既有權限確認後，才可執行此手勢。': translations(
        '完成现有权限确认后，才可执行此手势。',
        'Complete the existing permission confirmation before executing this gesture.',
        '既存の権限確認を完了してから、このジェスチャーを実行できます。',
    ),
    "此手勢已由安全權限阻擋。": translations(
        "此手势已被安全权限阻止。",
        "Security permissions require an update for this gesture.",
        "セキュリティ権限により、このジェスチャーはブロックされました。",
    ),
    '手勢動作執行需要處理；其他功能維持運作。': translations(
        '手势动作执行需要处理；其他功能保持运行。',
        'Gesture execution requires attention; other features keep running.',
        'ジェスチャー実行への対応が必要です。他の機能は動作を継続します。',
    ),
    "手勢未觸發任何動作。": translations(
        "手势未触发任何动作。",
        "The gesture did not trigger an action.",
        "ジェスチャーによる動作はありませんでした。",
    ),
    '請完成手勢設定': translations(
        '请完成手势设置',
        'Complete gesture settings',
        'ジェスチャー設定を完了してください',
    ),
    "選擇自訂文字指令時，必須輸入一行指令後才能保存。": translations(
        "选择自定义文字指令时，必须输入一行指令后才能保存。",
        "Enter one command before saving a custom text-command action.",
        "カスタム文字指示を選んだ場合は、一行の指示を入力してから保存してください。",
    ),
    "<b>多情境陪伴詞庫</b>": translations("<b>多情境陪伴詞庫</b>", "<b>Companion phrasebook</b>", "<b>場面別の寄り添いフレーズ集</b>"),
    "可編輯 24 組問候、關心、健康提醒與特殊節日詞句。": translations(
        "可编辑 24 组问候、关怀、健康提醒与特殊节日词句。",
        "Edit all 24 greeting, care, wellbeing, special-occasion, and wardrobe phrase groups.",
        "挨拶、気遣い、健康、特別な日、新装披露の全24グループを編集できます。",
    ),
    "編輯 28 組多情境詞庫": translations("编辑 28 组多情境词库", "Edit all 28 phrase groups", "28グループのフレーズを編集"),
    "完成編輯": translations("完成编辑", "Done editing", "編集を完了"),
    "用膳提醒": translations("用餐提醒", "Meal reminder", "食事リマインダー"),
    "飲水提醒": translations("饮水提醒", "Hydration reminder", "水分補給リマインダー"),
    "首次": translations("首次", "Initial", "初回"),
    "克制加強": translations("克制加强", "Restrained follow-up", "控えめな再通知"),
    "墨寒生日": translations("墨寒生日", "MoHan's birthday", "墨寒の誕生日"),
    "情人節": translations("情人节", "Valentine's Day", "バレンタインデー"),
    "聖誕節": translations("圣诞节", "Christmas Day", "クリスマス"),
    "含蓄暗示": translations("含蓄暗示", "Subtle hint", "さりげない示唆"),
    "小聲埋怨": translations("小声抱怨", "Restrained grumble", "控えめな拗ね"),
    "<b>OpenAI 雲端視覺理解</b>": translations(
        "<b>OpenAI 云端视觉理解</b>",
        "<b>OpenAI Cloud Vision Understanding</b>",
        "<b>OpenAI クラウド視覚理解</b>",
    ),
    '公開版預設關閉。明確啟用並全域保存後，系統沿用持續授權處理所選事件，直到你主動關閉；狀態始終可見，並可設定配額與成本上限或立即撤銷。本機 OpenCV 獨立運作。': translations(
        '公开版默认关闭。明确启用并全局保存后，系统沿用持续授权处理所选事件，直到你主动关闭；状态始终可见，并可设置额度与成本上限或立即撤销。本机 OpenCV 独立运行。',
        'Public builds start with this feature off. Explicitly enabling and globally saving it grants continuous authorization for selected events until you turn it off. Status stays visible, with quota and cost limits and immediate revocation. Local OpenCV operates independently.',
        '公開版では既定でオフです。明示的に有効化して全体設定を保存すると、自らオフにするまで選択イベントを継続許可の範囲で処理します。状態は常に表示され、利用枠・費用上限の設定と即時取消が可能です。ローカル OpenCV は独立して動作します。',
    ),
    "啟用視覺理解偏好": translations(
        "启用视觉理解偏好",
        "Enable vision-understanding preferences",
        "視覚理解の設定を有効化",
    ),
    "允許物品與場景語意理解": translations(
        "允许物品与场景语义理解",
        "Allow object and scene semantics",
        "物品と場面の意味理解を許可",
    ),
    "允許提出網路查詢建議（絕不自動上網）": translations(
        "允许提出网络查询建议（绝不自动联网）",
        "Allow web-search suggestions (browse only after explicit consent)",
        "ウェブ検索の提案を許可（自動アクセスはしない）",
    ),
    "視覺模型": translations("视觉模型", "Vision model", "視覚モデル"),
    "影像細節": translations("图像细节", "Image detail", "画像の詳細度"),
    "低": translations("低", "Low", "低"),
    "自動": translations("自动", "Auto", "自動"),
    "高": translations("高", "High", "高"),
    "原始細節": translations("原始细节", "Original", "オリジナル"),
    "觸發策略": translations("触发策略", "Trigger policy", "起動方針"),
    "僅手動": translations("仅手动", "Manual only", "手動のみ"),
    "事件需要時（依持續授權與用量限制）": translations(
        "事件需要时（依持续授权与用量限制）",
        "When an event requires it (within continuous authorization and limits)",
        "イベントで必要なとき（継続許可と利用上限の範囲内）",
    ),
    "每日分析上限": translations(
        "每日分析上限", "Daily analysis limit", "1日の解析上限"
    ),
    "每分鐘分析上限": translations(
        "每分钟分析上限", "Per-minute analysis limit", "1分あたりの解析上限"
    ),
    '✓ 原始影像僅供即時處理；API Key 由獨立安全儲存管理。': translations(
        '✓ 原始图像仅供实时处理；API Key 由独立安全存储管理。',
        '✓ Raw images are used only for live processing; API keys are managed in separate secure storage.',
        '✓ 元画像はリアルタイム処理に限定し、API Key は独立した安全な保存先で管理します。',
    ),
    "雲端視覺隱私保護": translations(
        "云端视觉隐私保护",
        "Cloud vision privacy protection",
        "クラウド視覚のプライバシー保護",
    ),
    "允許雲端視覺持續運作": translations(
        "允许云端视觉持续运行",
        "Allow continuous cloud vision",
        "クラウド視覚の継続動作を許可",
    ),
    '明確啟用並全域保存後，雲端視覺依所選事件與用量限制沿用持續授權，直到你主動關閉；狀態始終可見，並可設定配額與成本上限或立即撤銷。原始影像僅供即時處理，網路查詢由你明確決定。': translations(
        '明确启用并全局保存后，云端视觉按所选事件与用量限制沿用持续授权，直到你主动关闭；状态始终可见，并可设置额度与成本上限或立即撤销。原始图像仅供实时处理，网络查询由你明确决定。',
        'After explicit activation and global save, cloud vision uses continuous authorization for selected events within usage limits until you turn it off. Status stays visible, with quota and cost limits and immediate revocation. Raw images are used only for live processing; web searches require your explicit decision.',
        '明示的な有効化と全体保存後、クラウド視覚は自らオフにするまで選択イベントと利用上限の範囲で継続許可を使用します。状態は常に表示され、利用枠・費用上限の設定と即時取消が可能です。元画像はリアルタイム処理に限定し、ウェブ検索はユーザーの明示的な判断に従います。',
    ),
    "雲端視覺狀態": translations(
        "云端视觉状态", "Cloud vision status", "クラウド視覚の状態"
    ),
    "立即關閉雲端視覺": translations(
        "立即关闭云端视觉", "Turn off cloud vision now", "クラウド視覚を今すぐ無効化"
    ),
    "● 雲端視覺持續授權中": translations(
        "● 云端视觉持续授权中",
        "● Cloud vision continuously authorized",
        "● クラウド視覚を継続許可中",
    ),
    "● 已啟用，但尚無可用的 OpenAI 金鑰": translations(
        "● 已启用，但尚无可用的 OpenAI 密钥",
        "● Enabled; set a usable OpenAI key to continue",
        "● 有効ですが、利用可能な OpenAI キーがありません",
    ),
    "○ 雲端視覺已關閉": translations(
        "○ 云端视觉已关闭",
        "○ Cloud vision is off",
        "○ クラウド視覚は無効です",
    ),
    "● 雲端視覺分析中": translations(
        "● 云端视觉分析中",
        "● Cloud vision is analyzing",
        "● クラウド視覚で解析中",
    ),
    "● 雲端視覺已完成最近一次分析": translations(
        "● 云端视觉已完成最近一次分析",
        "● Cloud vision completed the latest analysis",
        "● クラウド視覚で直近の解析が完了しました",
    ),
    "● 雲端視覺暫時未完成分析": translations(
        "● 云端视觉暂未完成分析",
        "● Cloud vision could not complete the analysis",
        "● クラウド視覚で解析を完了できませんでした",
    ),
    '● 雲端視覺服務需要處理': translations(
        '● 云端视觉服务需要处理',
        '● Cloud vision service requires attention',
        '● クラウド視覚サービスへの対応が必要です',
    ),
})

__all__ = ("INTERACTION_TRANSLATIONS",)
