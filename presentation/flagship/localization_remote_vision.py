"""Remote-access, privacy, camera, and vision translations."""

from __future__ import annotations

lazy from presentation.flagship.localization_catalog import (
    TranslationCatalog,
    translations,
)

REMOTE_VISION_TRANSLATIONS: TranslationCatalog = frozendict({
    # Remote access and camera privacy.
    "增加連線埠": translations("增加端口", "Increase port", "ポート番号を増やす"),
    "減少連線埠": translations("减少端口", "Decrease port", "ポート番号を減らす"),
    "啟用手機／私人網路遠端服務": translations(
        "启用手机／私人网络远程服务",
        "Enable phone/private-network remote service",
        "スマートフォン／プライベートネットワークのリモート機能を有効化",
    ),
    "僅本機測試（127.0.0.1）": translations(
        "仅本机测试（127.0.0.1）",
        "Local testing only (127.0.0.1)",
        "ローカルテストのみ（127.0.0.1）",
    ),
    "私人網路／Tailscale（0.0.0.0）": translations(
        "私人网络／Tailscale（0.0.0.0）",
        "Private network / Tailscale (0.0.0.0)",
        "プライベートネットワーク／Tailscale（0.0.0.0）",
    ),
    "我確認已使用 Tailscale、Home Assistant Cloud 或其他加密私人網路": translations(
        "我确认已使用 Tailscale、Home Assistant Cloud 或其他加密私人网络",
        "I confirm that I use Tailscale, Home Assistant Cloud, or another encrypted private network",
        "Tailscale、Home Assistant Cloud、または別の暗号化プライベートネットワークを使用していることを確認します",
    ),
    "允許傳送文字指令": translations(
        "允许发送文本指令", "Allow text commands", "テキスト指示を許可"
    ),
    "允許查看墨寒程式視窗（不擷取整個桌面）": translations(
        "允许查看墨寒程序窗口（不截取整个桌面）",
        "Allow viewing the MoHan app window (not the whole desktop)",
        "墨寒のアプリ画面の表示を許可（デスクトップ全体は取得しません）",
    ),
    "允許下載白名單內的非敏感檔案": translations(
        "允许下载白名单内的非敏感文件",
        "Allow downloads of non-sensitive allowlisted files",
        "許可済みの非機密ファイルのダウンロードを許可",
    ),
    "允許本機攝影機在場偵測": translations(
        "允许本机摄像头在场检测",
        "Allow local camera presence detection",
        "ローカルカメラでの在席検知を許可",
    ),
    "本機臉部身分辨識（需另裝可稽核的辨識外掛）": translations(
        "本机人脸身份识别（需另装可审计的识别插件）",
        "Local face identification (requires a separately installed, auditable recognition plugin)",
        "ローカル顔識別（監査可能な認識プラグインの追加導入が必要）",
    ),
    "啟用墨寒本機視覺感知": translations(
        "启用墨寒本机视觉感知",
        "Enable MoHan's local visual perception",
        "墨寒のローカル視覚認識を有効化",
    ),
    "辨識我已明確登錄的臉部身分": translations(
        "识别我已明确登记的人脸身份",
        "Identify faces I have explicitly enrolled",
        "明示的に登録した顔を本人として識別",
    ),
    "允許墨寒主動寒暄與關心": translations(
        "允许墨寒主动寒暄与关心",
        "Allow MoHan to greet me and check in proactively",
        "墨寒から自発的に挨拶や気遣いをすることを許可",
    ),
    "安靜（不主動寒暄）": translations(
        "安静（不主动寒暄）",
        "Quiet (no proactive greetings)",
        "静か（自発的に挨拶しない）",
    ),
    "適度（推薦）": translations(
        "适度（推荐）",
        "Moderate (recommended)",
        "適度（推奨）",
    ),
    "積極（較常主動關心）": translations(
        "积极（更常主动关心）",
        "Active (checks in more often)",
        "積極的（より頻繁に気遣う）",
    ),
    "攝影機已關閉": translations("摄像头已关闭", "Camera is off", "カメラはオフです"),
    "遠端功能預設關閉": translations(
        "远程功能默认关闭",
        "Remote features are off by default",
        "リモート機能は既定でオフです",
    ),
    "啟動／套用": translations("启动／应用", "Start / Apply", "起動／適用"),
    "停止遠端服務": translations(
        "停止远程服务", "Stop remote service", "リモートサービスを停止"
    ),
    "配對新手機": translations(
        "配对新手机", "Pair a new phone", "新しいスマートフォンをペアリング"
    ),
    "套用攝影機隱私設定": translations(
        "应用摄像头隐私设置",
        "Apply camera privacy settings",
        "カメラのプライバシー設定を適用",
    ),
    "套用靈視設定": translations(
        "应用灵视设置",
        "Apply Vision Settings",
        "視覚認識設定を適用",
    ),
    "登錄我的臉部身分": translations(
        "登记我的人脸身份",
        "Enroll My Face Identity",
        "自分の顔を本人として登録",
    ),
    "刪除全部臉部身分": translations(
        "删除全部人脸身份",
        "Delete All Face Identities",
        "登録済みの顔をすべて削除",
    ),
    "刪除選取的臉部身分": translations(
        "删除选中的人脸身份",
        "Delete Selected Face Identity",
        "選択した顔の本人登録を削除",
    ),
    "編輯多情境陪伴詞庫": translations(
        "编辑多情境陪伴语句库",
        "Edit Context-Aware Companion Phrasebook",
        "状況別の会話フレーズ集を編集",
    ),
    "撤銷選取裝置": translations(
        "撤销选中设备", "Revoke selected device", "選択した端末を解除"
    ),
    "監聽範圍": translations("监听范围", "Listening scope", "待受範囲"),
    "連線埠": translations("端口", "Port", "ポート"),
    "<b>攝影機與身分辨識</b>": translations(
        "<b>摄像头与身份识别</b>", "<b>Camera & Identity</b>", "<b>カメラと本人識別</b>"
    ),
    "已登錄身分": translations(
        "已登记身份",
        "Enrolled Identities",
        "登録済みの本人",
    ),
    "<b>主動陪伴</b>": translations(
        "<b>主动陪伴</b>",
        "<b>Proactive Companionship</b>",
        "<b>自発的な寄り添い</b>",
    ),
    "主動程度": translations(
        "主动程度",
        "Proactivity Level",
        "自発性の程度",
    ),
    "短暫離席不問候（分鐘）": translations(
        "短暂离席不问候（分钟）",
        "No greeting after a brief absence (minutes)",
        "短時間の離席後は挨拶しない（分）",
    ),
    "安靜多久後主動關心（分鐘）": translations(
        "安静多久后主动关心（分钟）",
        "Check in after this much quiet time (minutes)",
        "この時間静かだった場合に声をかける（分）",
    ),
    "攝影機狀態": translations("摄像头状态", "Camera status", "カメラの状態"),
    "攝影機預設關閉；啟用時必須顯示狀態。畫面不會默默上傳，"
    "也不會辨識未登錄的陌生人。": translations(
        "摄像头默认关闭；启用时必须显示状态。画面不会静默上传，"
        "也不会识别未登记的陌生人。",
        "The camera is off by default and its status must remain visible when enabled. "
        "Images are never silently uploaded, and unregistered people are not identified.",
        "カメラは既定でオフです。有効時は状態を常に表示します。映像を無断でアップロードせず、"
        "未登録の人物を識別しません。",
    ),
    "「啟動／套用」只會啟動遠端服務；攝影機與臉部辨識須按"
    "「套用靈視設定」並完成同意後才會生效。": translations(
        "「启动／应用」只会启动远程服务；摄像头与面部识别须按"
        "「应用灵视设置」并完成同意后才会生效。",
        "\"Start / Apply\" only starts the remote service; the camera and "
        "face identity take effect only after pressing \"Apply Vision "
        "Settings\" and completing the consent step.",
        "「起動／適用」はリモート機能のみを起動します。カメラと顔識別は"
        "「視覚認識設定を適用」を押して同意を完了した後にのみ有効になります。",
    ),
    "服務狀態": translations("服务状态", "Service status", "サービス状態"),
    "已配對裝置": translations("已配对设备", "Paired devices", "ペアリング済み端末"),
    "攝影機權限": translations("摄像头权限", "Camera Permission", "カメラ権限"),
    "本機感知模型": translations(
        "本机感知模型", "Local perception models", "ローカル認識モデル"
    ),
    "本機臉部、虹膜與手勢模型尚未啟動": translations(
        "本机面部、虹膜与手势模型尚未启动",
        "Local face, iris, and hand models have not started",
        "ローカルの顔・虹彩・手モデルはまだ起動していません",
    ),
    "本機臉部、虹膜與手勢模型已就緒": translations(
        "本机面部、虹膜与手势模型已就绪",
        "Local face, iris, and hand models are ready",
        "ローカルの顔・虹彩・手モデルは準備完了です",
    ),
    "本機細緻臉部與虹膜模型無法使用；其餘功能維持運作": translations(
        "本机精细面部与虹膜模型无法使用；其余功能保持运行",
        "Local detailed face and iris models are unavailable; other features remain active",
        "ローカルの詳細な顔・虹彩モデルは利用できません。その他の機能は継続します",
    ),
    "安全政策已阻擋：{reason}": translations(
        "安全策略已阻止：{reason}",
        "Blocked by security policy: {reason}",
        "セキュリティ方針によりブロックされました：{reason}",
    ),
    "啟用攝影機": translations("启用摄像头", "Enable Camera", "カメラを有効化"),
    "墨寒會在本機分析在場狀態、臉部與眼神特徵、手勢及場景線索；不保存原始影像、不傳送雲端，未登錄的人物不會建立身分。是否啟用？": translations(
        "墨寒会在本机分析在场状态、面部与视线特征、手势及场景线索；"
        "不保存原始图像、不传送云端，未登记的人物不会建立身份。是否启用？",
        "MoHan will locally analyze presence, facial and gaze features, gestures, and scene cues. "
        "Original images are not saved or sent to the cloud, and unregistered people are not "
        "assigned an identity. Enable the camera?",
        "墨寒は端末内で在席状態、顔と視線の特徴、ジェスチャー、場面の手掛かりを分析します。"
        "元の映像は保存もクラウド送信もされず、未登録の人物に身元情報は作成されません。"
        "カメラを有効にしますか？",
    ),
    "攝影機啟動失敗：{error}": translations(
        "摄像头启动失败：{error}",
        "Could not start the camera: {error}",
        "カメラを起動できませんでした：{error}",
    ),
    "臉部身分登錄": translations(
        "人脸身份登记",
        "Face Identity Enrollment",
        "顔による本人登録",
    ),
    "請先啟用靈視與臉部身分辨識。": translations(
        "请先启用灵视与人脸身份识别。",
        "Enable Vision and face identification first.",
        "先に視覚認識と顔による本人識別を有効にしてください。",
    ),
    "墨寒辨識到你時使用的稱呼": translations(
        "墨寒识别到你时使用的称呼",
        "Name MoHan should use when she recognizes you",
        "墨寒があなたを認識したときに使う呼び名",
    ),
    "無法開始臉部登錄：{error}": translations(
        "无法开始人脸登记：{error}",
        "Could not start face enrollment: {error}",
        "顔の登録を開始できませんでした：{error}",
    ),
    "這會刪除本機加密的臉部特徵，且無法復原。是否繼續？": translations(
        "这会删除本机加密的人脸特征，且无法恢复。是否继续？",
        "This will delete the locally encrypted facial features and cannot be undone. Continue?",
        "端末内で暗号化された顔特徴を削除します。この操作は取り消せません。続行しますか？",
    ),
    "這會刪除選取的本機加密臉部特徵。是否繼續？": translations(
        "这会删除选中的本机加密人脸特征。是否继续？",
        "This will delete the selected locally encrypted facial features. Continue?",
        "選択した端末内の暗号化済み顔特徴を削除します。続行しますか？",
    ),
    "已刪除全部臉部身分。": translations(
        "已删除全部人脸身份。",
        "All face identities have been deleted.",
        "登録済みの顔をすべて削除しました。",
    ),
    "多情境陪伴詞庫": translations(
        "多情境陪伴语句库",
        "Context-Aware Companion Phrasebook",
        "状況別の会話フレーズ集",
    ),
    "每行一句；留白時使用公開版中性預設。": translations(
        "每行一句；留空时使用公开版中性默认语句。",
        "Enter one sentence per line. Leave blank to use the neutral public defaults.",
        "1 行に 1 文ずつ入力してください。空欄の場合は公開版の中立的な既定文を使用します。",
    ),
    "靈視環境已就緒": translations(
        "灵视环境已就绪",
        "Vision is ready",
        "視覚認識の準備ができました",
    ),
    "正在登錄臉部：{current}/{total}": translations(
        "正在登记人脸：{current}/{total}",
        "Enrolling face: {current}/{total}",
        "顔を登録しています：{current}/{total}",
    ),
    "已完成 {name} 的臉部登錄。": translations(
        "已完成 {name} 的人脸登记。",
        "Face enrollment for {name} is complete.",
        "{name} の顔登録が完了しました。",
    ),
    "請讓畫面中只出現一張清楚的正面臉孔。": translations(
        "请确保画面中只出现一张清晰的正面人脸。",
        "Ensure that exactly one clear, front-facing face is visible.",
        "画面には、正面を向いた鮮明な顔が一つだけ映るようにしてください。",
    ),
    "短暫回座": translations(
        "短暂回座",
        "Quick Return",
        "短時間の離席から戻ったとき",
    ),
    "一般歸來": translations(
        "一般归来",
        "Return",
        "通常の帰席",
    ),
    "久候歸來": translations(
        "久候归来",
        "Return After a Long Absence",
        "長時間の不在から戻ったとき",
    ),
    "早晨相見": translations(
        "早晨相见",
        "Morning Greeting",
        "朝に会ったとき",
    ),
    "深夜歸來": translations(
        "深夜归来",
        "Late-Night Return",
        "深夜に戻ったとき",
    ),
    "帶著飲品": translations(
        "带着饮品",
        "Returning with a Drink",
        "飲み物を持っているとき",
    ),
    "帶著書本": translations(
        "带着书本",
        "Returning with a Book",
        "本を持っているとき",
    ),
    "寒暄與主動關心": translations(
        "寒暄与主动关心",
        "Greetings and Proactive Check-Ins",
        "挨拶と自発的な気遣い",
    ),
    "歸來問候": translations("归来问候", "Returns", "帰席の挨拶"),
    "日常關心": translations("日常关心", "Daily Care", "日々の気遣い"),
    "健康提醒": translations("健康关怀", "Wellbeing", "健康への気遣い"),
    "特殊節日": translations("特殊节日", "Special Days", "特別な日"),
    "用膳提醒・首次": translations(
        "用餐提醒・首次", "Meal・First", "食事・初回"
    ),
    "用膳提醒・克制加強": translations(
        "用膳提醒・克制加强", "Meal・Restrained follow-up", "食事・控えめな再通知"
    ),
    "飲水提醒・首次": translations(
        "饮水提醒・首次", "Hydration・First", "水分補給・初回"
    ),
    "飲水提醒・克制加強": translations(
        "饮水提醒・克制加强", "Hydration・Restrained follow-up", "水分補給・控えめな再通知"
    ),
    "休息提醒・首次": translations(
        "休息提示・首次", "Rest・First", "休息・初回"
    ),
    "休息提醒・克制加強": translations(
        "休息提醒・克制加强", "Rest・Restrained follow-up", "休息・控えめな再通知"
    ),
    "久坐提醒・首次": translations(
        "久坐提示・首次", "Sitting・First", "長時間の着席・初回"
    ),
    "久坐提醒・克制加強": translations(
        "久坐提醒・克制加强", "Sitting・Restrained follow-up", "長時間の着席・控えめな再通知"
    ),
    "墨寒生日・含蓄暗示": translations(
        "墨寒生日・含蓄提示", "MoHan's birthday・Subtle hint", "墨寒の誕生日・控えめな合図"
    ),
    "墨寒生日・小聲埋怨": translations(
        "墨寒生日・小声埋怨", "MoHan's birthday・Quiet grumble", "墨寒の誕生日・小さな不満"
    ),
    "情人節・含蓄暗示": translations(
        "情人节・含蓄暗示", "Valentine's Day・Subtle hint", "バレンタイン・控えめな合図"
    ),
    "情人節・小聲埋怨": translations(
        "情人节・小声埋怨", "Valentine's Day・Quiet grumble", "バレンタイン・小さな不満"
    ),
    "聖誕節・含蓄暗示": translations(
        "圣诞节・含蓄暗示", "Christmas・Subtle hint", "クリスマス・控えめな合図"
    ),
    "聖誕節・小聲埋怨": translations(
        "圣诞节・小声埋怨", "Christmas・Quiet grumble", "クリスマス・小さな不満"
    ),
    "攝影機錯誤：{error}": translations(
        "摄像头错误：{error}", "Camera error: {error}", "カメラエラー：{error}"
    ),
    "攝影機使用中：{device}（本機多感知分析）": translations(
        "摄像头使用中：{device}（本机多感知分析）",
        "Camera active: {device} (local multisensory analysis)",
        "カメラ使用中：{device}（ローカル多感覚分析）",
    ),
    "{base}｜偵測到有人在場": translations(
        "{base}｜检测到有人在场", "{base} | Presence detected", "{base}｜在席を検知"
    ),
    "{base}｜暫未偵測到在場": translations(
        "{base}｜暂未检测到在场",
        "{base} | No presence detected",
        "{base}｜現在は在席を検知していません",
    ),
    "遠端服務未啟用": translations(
        "远程服务未启用", "Remote service is not enabled", "リモートサービスは無効です"
    ),
    "啟動失敗：{error}": translations(
        "启动失败：{error}", "Start failed: {error}", "起動に失敗しました：{error}"
    ),
    "已啟動：http://{host}:{port}\n只有已配對且具備相應權限的裝置可以存取。": translations(
        "已启动：http://{host}:{port}\n只有已配对且具备相应权限的设备可以访问。",
        "Started: http://{host}:{port}\nOnly paired devices with the required permissions can connect.",
        "起動しました：http://{host}:{port}\n必要な権限を持つペアリング済み端末のみ接続できます。",
    ),
    "遠端服務已停止，既有權杖未刪除但無法連線。": translations(
        "远程服务已停止，现有令牌未删除但无法连接。",
        "Remote service stopped. Existing tokens were not deleted, but cannot connect.",
        "リモートサービスを停止しました。既存トークンは削除されていませんが、接続できません。",
    ),
    "配對新裝置": translations(
        "配对新设备", "Pair New Device", "新しい端末をペアリング"
    ),
    "裝置名稱": translations("设备名称", "Device name", "端末名"),
    "一次性配對權杖": translations(
        "一次性配对令牌", "One-time Pairing Token", "一回限りのペアリングトークン"
    ),
    "請只在可信任裝置輸入下列權杖。關閉視窗後不會再次顯示：\n\n{token}": translations(
        "请只在可信任设备输入下列令牌。关闭窗口后不会再次显示：\n\n{token}",
        "Enter the following token only on a trusted device. It will not be shown again after this window closes:\n\n{token}",
        "次のトークンは信頼できる端末にのみ入力してください。この画面を閉じると再表示できません：\n\n{token}",
    ),
    "有效": translations("有效", "Active", "有効"),
    "從未": translations("从未", "Never", "なし"),
    "{status}｜{device}｜最後連線：{last_seen}": translations(
        "{status}｜{device}｜最后连接：{last_seen}",
        "{status} | {device} | Last connection: {last_seen}",
        "{status}｜{device}｜最終接続：{last_seen}",
    ),
    "已送交墨寒並等待本機權限判斷": translations(
        "已提交给墨寒并等待本机权限判断",
        "Sent to MoHan and awaiting local permission checks",
        "墨寒へ送信し、ローカル権限の判定を待っています",
    ),
    "待處理的遠端指令已達安全上限，請稍後重試": translations(
        "待处理的远程指令已达安全上限，请稍后重试",
        "The remote-command queue is at its safe limit. Please retry shortly.",
        "リモート指令の待機数が安全上限に達しました。しばらくしてから再試行してください",
    ),
    "[遠端裝置：{device}] {text}": translations(
        "[远程设备：{device}] {text}",
        "[Remote device: {device}] {text}",
        "[リモート端末：{device}] {text}",
    ),
    "尚無可用的程式視窗畫面": translations(
        "尚无可用的程序窗口画面",
        "No app-window image is available",
        "利用可能なアプリ画面がありません",
    ),
})

__all__ = ("REMOTE_VISION_TRANSLATIONS",)
