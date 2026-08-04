from __future__ import annotations

from collections.abc import Mapping


JAPANESE_UI: Mapping[str, str] = {
    "first_run_title": "初回セットアップ",
    "first_run_heading": "<b>墨寒デスクトップアシスタントへようこそ</b>",
    "first_run_hero_tagline": (
        "北宋から来た千年の女剣魂。話を聴き、記憶し、仕事を整えるあなたの伴侶です。"
    ),
    "first_run_intro": (
        "最初にプロフィールを設定してください。ここで選んだ内容は後から"
        "「設定」で変更でき、特定の会社や職業には固定されません。"
    ),
    "assistant_name": "アシスタント名",
    "user_title": "アシスタントからの呼び方",
    "organization_name": "会社／チーム名",
    "window_title": "ウィンドウの完全なタイトル",
    "work_type": "仕事の種類",
    "ui_language": "画面と返答の言語",
    "wake_word": "音声ウェイクワード",
    "assistant_name_placeholder": "例：墨寒、MoHan、Ava",
    "user_title_placeholder": "例：主様、Alex、マネージャー",
    "organization_placeholder": "会社、スタジオ、チーム名（任意）",
    "window_title_placeholder": "空欄なら「アシスタント名・組織名」を使用",
    "wake_word_placeholder": "例：墨寒、MoHan",
    "first_run_note": (
        "仕事プラットフォームは空の状態で始まります。実際に使う社内システム、"
        "共同作業ツール、管理画面、ウェブサイトだけを追加してください。"
    ),
    "finish_setup": "設定を完了して開始",
    "required_title": "必須情報がありません",
    "required_identity": "アシスタント名と、あなたへの呼び方を入力してください。",
    "mode": "モード",
    "start_work": "仕事を開始",
    "stop_work": "仕事を終了",
    "tab_chat": "会話",
    "tab_today": "今日",
    "tab_platforms": "仕事プラットフォーム",
    "tab_memory": "長期記憶",
    "tab_voice": "音声",
    "tab_permissions": "パソコンの権限",
    "tab_settings": "設定",
    "chat_retention": "会話はこのパソコンに保存され、自動削除されません",
    "load_older_chat": "過去の会話を読み込む",
    "manage_chat": "会話の管理／消去",
    "chat_placeholder": "墨寒に話しかける……",
    "microphone": "🎙 マイク",
    "send_text": "送信",
    "voice_ready": "音声状態：準備完了",
    "speech_recognition": "一回ごとのマイク音声認識",
    "transcription_model": "文字起こしモデル",
    "transcription_language": "文字起こし言語",
    "transcription_prompt": "文字起こしのヒント／よく使う語句",
    "windows_transcription_fallback": "Windows 代替認識",
    "last_transcription": "直近の文字起こし診断",
    "voice_engine": "読み上げ方法",
    "windows_voice": "Windows 音声",
    "tts_voice": "OpenAI 読み上げ音声",
    "realtime_voice": "Realtime 会話音声",
    "realtime_model": "Realtime モデル",
    "realtime_transcription_model": "Realtime 文字起こしモデル",
    "realtime_noise": "Realtime マイクノイズ低減",
    "realtime_turn": "Realtime 発話区切り検出",
    "realtime_screen_transcript": "Realtime 画面文字起こし",
    "echo_guard": "エコー防止",
    "local_rate": "本機音声の速度",
    "mohan_volume": "墨寒の音量",
    "voice_style": "話し方",
    "realtime": "Realtime 音声",
    "windows_engine": "Windows 本機音声",
    "openai_engine": "OpenAI 自然音声",
    "realtime_engine": "Realtime 音声",
    "azure_engine": "Azure Speech（プレビュー）",
    "azure_voice": "Azure Speech 女性音声",
    "azure_region": "Azure Speech リージョン",
    "azure_key": "Azure Speech キー",
    "azure_region_placeholder": "例：japaneast",
    "azure_key_saved": "Windows で暗号化済み（空欄なら保持）",
    "azure_key_missing": "Azure Speech リソースキーを貼り付け",
    "azure_remove_key": "Azure Speech キーを削除",
    "azure_remove_key_confirm": (
        "Windows で暗号化保存した Azure Speech キーを削除しますか？"
    ),
    "azure_key_save_failed": "Azure Speech キーを安全に保存できません：{error}",
    "azure_speech_note": (
        "プレビュー機能です。ご自身の Azure Speech リソースキーと対応する"
        "リージョンが必要です。確認済みの女性音声だけを表示し、設定不足または"
        "サービス障害時は Windows 女性音声へ戻ります。料金と利用条件は"
        " Microsoft の最新規定に従います。"
    ),
    "azure_fallback_missing_settings": (
        "Azure Speech の設定が未完了です。クラウドへ送信せず、Windows 女性音声を使用します。"
    ),
    "no_female_voice": "確認済みの Windows 女性音声が見つかりません",
    "female_voice_note": (
        "Windows が女性と明示しているインストール済み音声だけを表示します。"
        "画面言語と一致する音声を優先します。"
    ),
    "transcription_language_placeholder": "ISO 言語コード（空欄なら自動判定）",
    "openai_fallback": "OpenAI 失敗時に Windows オフライン認識を使用",
    "openai_recognition": "OpenAI 高精度認識（推奨）",
    "windows_recognition": "Windows オフライン認識",
    "no_transcription_error": "文字起こしエラーはありません",
    "preview_voice": "試聴：主様、妾はここにおります。",
    "realtime_disconnected": "Realtime：未接続",
    "start_realtime": "Realtime 会話を開始",
    "stop_realtime": "Realtime 会話を停止",
    "near_field": "近距離マイク（推奨）",
    "far_field": "遠距離／ノートパソコンのマイク",
    "noise_off": "ノイズ低減なし",
    "stable_vad": "安定した発話区切り（約 0.85 秒の間）",
    "semantic_vad": "意味による発話区切り（早く切れる場合あり）",
    "echo_guard_option": "墨寒が自分の声を聞かないようにする",
    "hybrid_transcript": "画面には高精度の最終文字起こしを表示",
    "mute": "ミュート",
    "rate_down": "本機音声を遅くする",
    "rate_up": "本機音声を速くする",
    "level_suffix": " 段階",
    "realtime_note": (
        "Realtime は有効な間だけマイクを使用します。安定モードは発話終了後"
        "約 0.85 秒待って送信し、停止すると音声送信も直ちに止まります。"
    ),
    "model_access_note": (
        "OpenAI の画面でモデルを有効にしても利用できない場合は、モデルと"
        "API キーが同じ Project に属することを確認し、設定で新しいキーを保存してください。"
    ),
    "echo_guard_note": (
        "エコー防止を有効にすると、墨寒の発話中はマイク送信を止め、再生終了後に"
        "再開します。会話画面には高精度の最終文字起こしだけを表示します。"
    ),
    "recognition_note": (
        "一回ごとのマイク認識は約 0.85 秒の無音後に送信し、最大 10 秒録音します。"
        "もう一度マイクを押すと早めに送信できます。"
    ),
    "permissions_intro": (
        "機能ごとに権限を設定してください。「毎回確認」では実行前に確認します。"
        "ファイル削除は初期状態で禁止されています。"
    ),
    "permission_open_web": "指定ウェブサイトを開く",
    "permission_open_folder": "作業フォルダーを開く",
    "permission_launch_app": "別のアプリを起動する",
    "permission_write_files": "ファイルを作成／変更する",
    "permission_delete_files": "ファイルを削除する",
    "permission_deny": "禁止",
    "permission_ask": "毎回確認",
    "permission_allow": "許可",
    "permissions_warning": (
        "安全規則：会話だけで墨寒の権限を増やすことはできません。AI は操作を"
        "提案できますが、実際に実行できる範囲は本機の権限設定だけで決まります。"
    ),
    "save_permissions": "ツール権限を保存",
    "permission_blocked": "権限により停止",
    "permission_blocked_message": "墨寒には現在、{action}権限がありません。",
    "permission_request": "墨寒がパソコンの権限を求めています",
    "permission_request_message": "今回だけ墨寒に{action}ことを許可しますか？",
    "permission_saved_speech": "パソコンの権限を保存しました。妾はこの境界を守ります。",
    "profile_heading": "<b>名前とプロフィール</b>",
    "system_heading": "<b>仕事とシステム設定</b>",
    "api_key": "OpenAI API キー",
    "text_model": "テキストモデル",
    "persona_prompt": "AI 人格プロンプト",
    "remove_api_key": "保存済み API キーを削除",
    "save_settings": "設定を保存",
    "api_key_saved": "安全に保存済み（空欄なら変更しません）",
    "api_key_missing": "sk- で始まる OpenAI Project API キーを貼り付け",
    "api_status_saved": "OpenAI API：キーは Windows で暗号化済み",
    "api_status_offline": "OpenAI API：未設定、オフライン人格を使用",
    "restart_language_note": "画面言語は墨寒の再起動後に完全適用されます。",
    "reminder_work": "仕事開始",
    "reminder_lunch": "昼食",
    "reminder_dinner": "夕食",
    "reminder_offwork": "仕事終了",
    "enabled": "有効",
    "reminder_message_label": "{label}メッセージ",
    "reminder_message_placeholder": "このリマインダーで墨寒が話す内容",
    "continuous_work_reminder": "連続作業リマインダー",
    "overwork_message": "長時間作業／働き過ぎの警告メッセージ",
    "minutes_suffix": " 分",
    "read_replies": "墨寒の返答を読み上げる",
    "voice_settings_saved": "音声設定を保存しました。",
    "settings_saved": "設定を保存しました。",
    "work_timer_already_running": "作業時間はすでに計測中です。重ねて開始する必要はありません。",
    "work_timer_not_started": "本日の作業時間はまだ計測されていません。",
}


JAPANESE_MODE_LABELS: Mapping[str, str] = {
    "工作": "仕事",
    "陪伴": "お供",
    "勿擾": "集中",
    "會議": "会議",
    "離席": "離席",
    "休眠": "休眠",
}


JAPANESE_WORK_TYPE_LABELS: Mapping[str, str] = {
    "一般辦公／行政": "一般事務／管理",
    "專案管理": "プロジェクト管理",
    "自由工作者／接案": "フリーランス／受託",
    "創作／內容工作": "創作／コンテンツ制作",
    "軟體開發／技術": "ソフトウェア開発／技術",
    "教育／研究": "教育／研究",
    "銷售／客戶服務": "営業／カスタマーサービス",
    "其他（可自行輸入）": "その他（自由入力）",
}
