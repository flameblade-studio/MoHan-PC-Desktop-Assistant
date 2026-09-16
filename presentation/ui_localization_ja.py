from __future__ import annotations

lazy from collections.abc import Mapping

lazy from domain.immutable_config import deep_freeze

JAPANESE_UI: Mapping[str, str] = deep_freeze({
    "first_run_title": "初回セットアップ",
    "first_run_brand": "墨寒  MoHan",
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
        '仕事プラットフォームのページを会社のシステム用に準備しました。使用するシステム、共同作業ツール、管理画面、ウェブサイトを追加してください。'
    ),
    "finish_setup": "設定を完了して開始",
    "required_title": '必要な情報を入力',
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
    "navigation_brand": "墨寒",
    "nav_realm_companion": "寄り添い",
    "nav_realm_today": "業務",
    "nav_realm_wardrobe": "装い",
    "nav_realm_machine": "システム",
    "nav_realm_other": "その他",
    "draft_bar_clean": "適用済み",
    "draft_bar_clean_message": "設定は現在の動作状態と一致しています",
    "draft_bar_dirty": "下書き",
    "draft_bar_dirty_message": "未適用の変更が {count} 件あります",
    "draft_bar_error": '読み取りに確認が必要',
    "draft_bar_error_message": '設定の読み取りに確認が必要です。もう一度お試しください。',
    "today_input_placeholder": "予定を入力（例：漫画第3話の絵コンテを完成）",
    "todo_category_comic": "漫画",
    "todo_category_article": "文章",
    "todo_category_music": "音楽",
    "todo_category_stickers": "スタンプ",
    "todo_category_publishing": "出版",
    "todo_category_administration": "管理",
    "todo_category_other": "その他",
    "add_todo": "＋ 予定を追加",
    "save_as_idea": "✦ アイデアに保存",
    "today_tasks_heading": "<b>今日の予定</b>",
    "creative_ideas_heading": "<b>創作アイデア</b>",
    "edit_selected_idea": "選択したアイデアを編集",
    "edit_selected_idea_tooltip": (
        "下のアイデアをダブルクリックしても編集できます"
    ),
    "delete_checked_ideas": "チェックしたアイデアを削除",
    "delete_checked_ideas_tooltip": (
        "チェックしたアイデアだけを確認後に削除します"
    ),
    "todo_complete_tooltip": "完了としてマーク",
    "todo_category_suffix": "今日の予定",
    "delete": "削除",
    "delete_todo_tooltip": "この予定を削除",
    "idea_editor_title": "創作アイデアを編集",
    "idea_title": "<b>アイデアのタイトル</b>",
    "idea_title_placeholder": "分かりやすいタイトルを付けてください",
    "idea_content": "<b>アイデアの内容</b>",
    "idea_content_placeholder": (
        "場面、台詞、音楽の方向性、次の行動などを記録…"
    ),
    "cancel": "キャンセル",
    "save_idea": "アイデアを保存",
    "idea_title_required_title": "タイトルが必要です",
    "idea_title_required": "先にアイデアのタイトルを入力してください。",
    "todo_count": "未完了 {count} 件",
    "todo_empty": (
        '今日の予定を最初のタスクに使える状態です。\n最も大切なことを一つ書いてください。'
    ),
    "idea_count": "{count} 件",
    "idea_empty": (
        'アイデア一覧を用意しました。上に入力して「アイデアに保存」を選んでください。'
    ),
    "idea_edit_tooltip": "ダブルクリックしてタイトルと内容を編集",
    "today_time": "今日 {total}｜{state}",
    "timing_active": "計測中",
    "timing_inactive": 'タイマーは一時停止中',
    "todo_title_required": "先に予定のタイトルを入力してください。",
    "todo_added": "✓ 予定を追加：{text}",
    "todo_added_speech": "今日の予定に追加しました。",
    "idea_capture_required": "先に保存するアイデアを入力してください。",
    "idea_added": "✓ アイデアを保存：{text}",
    "idea_added_speech": "消えてしまう前に、そのアイデアを保存しました。",
    "idea_select_edit": "先に編集するアイデアを選択してください。",
    "idea_not_found": (
        'アイデア一覧を更新し、利用できる項目を選択してください。'
    ),
    "idea_updated": "✓ アイデアを更新：{title}",
    "idea_select_delete": "先に削除するアイデアをチェックしてください。",
    "idea_delete_title": "創作アイデアを削除",
    "idea_delete_confirm": (
        "チェックした {count} 件のアイデアを完全に削除しますか？"
    ),
    "idea_deleted": "✓ {count} 件のアイデアを削除しました。",
    "platform_name_placeholder": "プラットフォーム／システム名（例：ERP、Notion）",
    "platform_url_placeholder": "URL（任意、例：https://example.com）",
    "add_platform": "仕事プラットフォームを追加",
    "platform_filter_all": "すべて",
    "platform_filter_active": "進行中",
    "platform_filter_blocked": '確認が必要な情報',
    "platform_filter_finished": "完了／公開済み",
    "platform_filter_not_started": '開始待ち',
    "save_all_platforms": "すべて今すぐ保存",
    "show": "表示",
    "platform_empty": (
        '仕事プラットフォーム一覧を用意しました。\n会社のシステム、共同作業ツール、顧客ポータル、利用中のプラットフォームを上に追加してください。'
    ),
    "platform_intro": (
        '仕事で使うプラットフォーム、システム、顧客ポータル、共同作業ツールを管理します。利用者ごとに一覧を作成し、仕事に合わせて保持します。'
    ),
    "platform_auto_save_note": "変更は自動保存され、各カードの保存ボタンも使えます。",
    "platform_item_placeholder": "現在の仕事、プロジェクト、案件",
    "platform_missing_placeholder": '追加資料、返信待ち、対応項目。情報がそろったら入力してください',
    "platform_next_placeholder": "次の具体的な行動と期限",
    "platform_notes_placeholder": "メモ、規則、連絡先など",
    "platform_url_card_placeholder": "https://…（任意）",
    "platform_not_saved": '保存待ち',
    "save_platform": "このプラットフォームを保存",
    "platform_field_item": "仕事／プロジェクト",
    "platform_field_missing": '確認が必要',
    "platform_field_next": "次の行動",
    "platform_field_notes": "メモ",
    "platform_field_url": "URL",
    "open_platform": "ウェブサイト／ツールを開く",
    "delete_platform": "プラットフォームを削除",
    "platform_updated": "更新：{updated}",
    "platform_updated_unknown": '更新時刻を確認中',
    "save_changes": "変更を保存",
    "platform_waiting_auto_save": "{platform} の変更を自動保存します…",
    "platform_validation_finished_blocked": 'この作業は完了しており、追加情報または対応項目があります。',
    "platform_validation_revision_details": '修正内容を追加情報、次の行動、またはメモに記入してください。',
    "platform_validation_not_started_data": "仕事の情報があります。状態を「資料準備」に変更するか確認してください。",
    "platform_validation_item_name": "後で識別しやすいよう、仕事やプロジェクト名を入力してください。",
    "platform_summary_unsaved": "｜未保存 {count}",
    "platform_summary": (
        '{total} 件｜完了 {finished}｜進行中 {active}｜開始待ち {not_started}｜確認が必要 {blocked}{unsaved}'
    ),
    "platform_saved": "{platform} を保存しました。",
    "platform_saved_automatic": "{platform} を自動保存しました。",
    "all_platforms_saved": 'すべて保存しました。{count} 件に追加情報または対応項目があります。',
    "all_platforms_saved_speech": '仕事プラットフォームを保存しました。{count} 件に追加情報または対応項目があります。',
    "memory_intro": (
        "墨寒は許可された人物、好み、目標、ワークフロー、重要な日付だけを"
        "保存します。記憶はこのパソコンに保存され、分類別の閲覧、個別編集、"
        "削除ができます。"
    ),
    "memory_input_placeholder": "例：漫画を終えてから管理作業を行う",
    "remember": "記憶する",
    "memory_filter_label": "分類別に表示",
    "all_memories": "すべての記憶",
    "edit_selected_memory": "選択した記憶を編集",
    "edit_memory_tooltip": "下の記憶をダブルクリックしても編集できます",
    "delete_checked_memories": "チェックした記憶を削除",
    "delete_checked_memories_tooltip": "チェックした記憶だけを確認後に削除します",
    "clear_all_memories": "すべての記憶を消去",
    "optimize_memories": "安全に記憶を整理",
    "optimize_memories_tooltip": "重要度の低い重複を統合し、古い超過分は先に保管します",
    "view_archived_memories": "保管済み記憶を表示",
    "auto_memory": "「覚えて」「好き」「いつも」など明確な表現から記憶を作成",
    "memory_count": "{count} 件",
    "memory_empty": 'この分類は記憶を追加できる状態です。',
    "memory_source_manual_short": "手動",
    "memory_source_conversation_short": "会話",
    "memory_untitled": "無題の記憶",
    "corrupt_data_title": "データ読み取り警告",
    "corrupt_data_message": '設定または記憶の読み取りに確認が必要です。元のファイルを保持しました。',
    "memory_item": (
        "【{category}】{title}　重要度 {importance}／5\n{content}\n"
        "出典：{source}　更新：{updated}"
    ),
    "memory_added_speech": "記憶しました。後から一件ずつ確認や変更ができます。",
    "memory_select_edit_title": '記憶を選択',
    "memory_select_edit": "先に編集する記憶を選択してください。",
    "memory_not_found_title": '記憶一覧を更新',
    "memory_not_found": 'この記憶はすでに削除されています。一覧を更新します。',
    "memory_save_failed_title": '記憶の保存に確認が必要',
    "memory_save_failed": '同じ内容の記憶がすでにある可能性があります。既存データはそのまま保持します。',
    "memory_select_delete_title": '記憶を選択',
    "memory_select_delete": "先に削除する記憶をチェックしてください。",
    "memory_delete_title": "長期記憶を削除",
    "memory_delete_confirm": "チェックした {count} 件の記憶を完全に削除しますか？",
    "memory_clear_title": "長期記憶を消去",
    "memory_clear_confirm": '墨寒が保存した長期記憶をすべて削除しますか？この操作は恒久的です。続行しますか？',
    "memory_optimize_title": "記憶の整理が完了しました",
    "memory_optimize_result": (
        "類似した記憶を {deduplicated} 件統合し、古く重要度の低い記憶を "
        "{pruned} 件保管しました。\n使用中：{active} 件、復元可能：{archived} 件。"
    ),
    "memory_editor_title": "長期記憶を編集",
    "memory_title_label": "<b>記憶のタイトル</b>",
    "memory_title_placeholder": "短いタイトルでこの記憶を識別",
    "memory_category_label": "<b>分類</b>",
    "memory_importance_label": "<b>重要度</b>",
    "memory_content_label": "<b>記憶の内容</b>",
    "memory_content_placeholder": "人物、好み、目標、ワークフロー、重要な日付を記録…",
    "memory_source_manual": "手動で作成",
    "memory_source_conversation": "会話で明示的に記憶",
    "memory_metadata": "出典：{source}　作成：{created}　更新：{updated}",
    "save_memory": "記憶を保存",
    "memory_title_required_title": "タイトルが必要です",
    "memory_title_required": "先に記憶のタイトルを入力してください。",
    "memory_content_required_title": "内容が必要です",
    "memory_content_required": "先に記憶の内容を入力してください。",
    "archived_memory_title": "保管済みの長期記憶",
    "archived_memory_intro": (
        '自動整理は古く重要度の低い会話記憶だけを保管し、内容を保持します。ここで項目を確認して復元できます。'
    ),
    "restore_checked_memories": "チェックした記憶を復元",
    "close": "閉じる",
    "archived_memory_item": (
        "【{category}】{title}\n{content}\n保管理由：{reason}　保管日時：{archived}"
    ),
    "archived_memory_corrupt": (
        '【読み取りに確認が必要】保管した記憶の元ファイルを保持しました。\n保管理由：{reason}  保管日時：{archived}'
    ),
    "archived_memory_count": "復元可能な記憶：{count} 件",
    "archived_memory_select_title": '記憶を選択',
    "archived_memory_select": "先に復元する記憶をチェックしてください。",
    "archived_memory_restored": "{count} 件の記憶を復元しました。",
    "chat_history_title": "会話の管理／消去",
    "chat_history_intro": (
        '会話はこのパソコンに保存され、明示的に削除するまで保持されます。完全に削除する項目だけを選択してください。'
    ),
    "delete_checked_chats": "チェックした会話を削除",
    "chat_history_item": "{created}｜{speaker}\n{content}",
    "chat_history_truncated_suffix": "（この画面には最近の 500 件だけを表示）",
    "chat_history_status": "このパソコンに {count} 件の会話を保存中。{suffix}",
    "chat_select_delete_title": '会話を選択',
    "chat_select_delete": "先に削除する会話をチェックしてください。",
    "chat_delete_title": "会話を完全に削除",
    "chat_delete_confirm": "チェックした {count} 件の会話を完全に削除しますか？",
    "load_older_chat_tooltip": "このパソコンから過去の会話を 50 件ずつ読み込み",
    "manage_chat_tooltip": '必要な会話を選択して削除し、他の会話は保持します',
    "chat_zoom_out_tooltip": "会話の文字を縮小（Ctrl＋ホイール下）",
    "chat_zoom_in_tooltip": "会話の文字を拡大（Ctrl＋ホイール上）",
    "chat_retention_status": "このパソコンに {total} 件を保存中。最近の {shown} 件を表示",
    "platform_name_required": "先にプラットフォーム、システム、またはツール名を入力してください。",
    "platform_duplicate": "「{platform}」は既にあります。別の名前を使用してください。",
    "platform_added": "仕事プラットフォームを追加：{platform}",
    "platform_delete_title": "仕事プラットフォームを削除",
    "platform_delete_confirm": '「{platform}」と作業の進捗を削除しますか？この操作は恒久的です。続行しますか？',
    "platform_not_found": '仕事プラットフォーム一覧を更新し、この項目を確認してください：{platform}',
    "platform_deleted": "仕事プラットフォームを削除：{platform}",
    "platform_url_missing_title": 'URL を設定',
    "platform_url_missing": "先に「{platform}」カードへウェブサイトまたはツールの URL を入力してください。",
    "platform_url_unsupported_title": '対応する URL 形式を入力',
    "platform_url_unsupported": "http:// または https:// の URL だけを開けます。",
    "permission_open_platform": "{platform} のウェブサイトを開く",
    "echo_guard_tooltip": (
        '墨寒の発話中はマイク送信を一時停止し、再生後に再開します。この設定では現在の操作を継続します。'
    ),
    "hybrid_transcript_tooltip": (
        "Realtime 本来の音声理解を保ち、発話後の画面文字には録音全体の "
        "OpenAI 高精度文字起こしを使用します。成功後に墨寒が返答します。"
    ),
    "flagship_heading": "<b>フラッグシップ操作センター</b>",
    "increase": "増やす",
    "decrease": "減らす",
    "voice_section": "音声",
    "profile_required_title": '必須プロフィール項目を入力',
    "profile_required": 'アシスタント名と呼び方を入力してください。',
    "send_chat_required_title": 'メッセージを入力',
    "send_chat_required": "左側に文字を入力して送信してください。マイクから話すこともできます。",
    "thinking_status": "{assistant}が考えています…",
    "answering_status": "回答中…",
    "api_connection_failed": 'OpenAI API：接続設定を確認してください（{error}）。',
    "voice_vad_degraded": "音声検出が低下したため、RMSに切り替えました。",
    "voice_ready_short": "準備完了",
    "voice_muted_short": "ミュート中",
    "sleep_mode_status": (
        "休眠モードを開始しました。墨寒は静かに待機し、リマインダーと緊急通知は規則どおり処理します。"
    ),
    "desktop_status_title": "墨寒はデスクトップであなたと対話しています",
    "desktop_status_description": (
        "デスクトップ上の墨寒だけが表示・ドラッグ・応答するキャラクターです。"
    ),
    "desktop_status_mode": "モード",
    "desktop_status_expression": "姿勢／表情",
    "desktop_status_voice": "音声",
    "desktop_status_vision": "カメラ認識",
    "desktop_status_gesture": "ジェスチャー",
    "desktop_status_idle": "待機中",
    "desktop_status_camera_waiting": "カメラ待機中",
    "desktop_status_gesture_waiting": "ジェスチャー待機中",
    "desktop_status_vision_present": "あなたを確認しました",
    "desktop_status_vision_away": 'カメラ映像は現在、伴侶を映していません',
    "desktop_status_vision_motion": "動きを検出しました",
    "desktop_status_vision_unknown": "カメラ待機中",
    "desktop_status_gesture_wave": "手を振る動きを認識しました",
    "microphone_idle": "🎙 マイク",
    "microphone_send_now": "⏹ 今すぐ送信",
    "microphone_recognizing": "認識中…",
    "voice_status_format": "音声状態：{phase}",
    "bubble_full_content": "…\n（全文は会話ページで確認できます）",
    "tray_open_today": "今日を開く",
    "tray_quit": "墨寒を終了",
    "chat_retention": '会話はこのパソコンに保存され、明示的に削除するまで保持されます',
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
    "offline_fallback": "オフライン代替認識",
    "platform_offline_fallback_unavailable": (
        '{platform} のオフライン認識は端末確認を待っています'
    ),
    "last_transcription": "直近の文字起こし診断",
    "voice_engine": "読み上げ方法",
    "windows_voice": "Windows 音声",
    "platform_local_voice": "{platform} 本機音声",
    "platform_local_voice_unavailable": (
        '{platform} の本機音声は端末確認を待っています'
    ),
    "tts_voice": "OpenAI 読み上げ音声",
    "realtime_output_source": "Realtime 応答音声の出力元",
    "realtime_output_openai": (
        "OpenAI Realtime ネイティブ音声（最小遅延、従来の初期設定）"
    ),
    "realtime_output_azure": "Azure Speech 女性音声（穏やかなストリーミング）",
    "realtime_output_azure_hd": (
        "Azure Dragon HD 女性音声（S0 必須）"
    ),
    "realtime_output_note_openai": (
        "下の「OpenAI Realtime ネイティブ音声」を使用します。遅延が最も"
        "小さく、OpenAI Realtime 本来のリアルタイム音声出力を維持します。"
    ),
    "realtime_output_note_azure": (
        "上で設定した Azure Speech 女性音声、リージョン、キーを使用します。"
        "リアルタイムの理解は OpenAI Realtime、音声のストリーミング再生は "
        "Azure が担当します。"
    ),
    "realtime_output_note_azure_hd": (
        "上で設定した Dragon HD 女性音声、S0 リージョン、専用キーを使用します。"
        "リアルタイムの理解は OpenAI Realtime、音声のストリーミング再生は "
        "Dragon HD が担当します。"
    ),
    "realtime_voice": "OpenAI Realtime ネイティブ音声",
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
    "azure_hd_engine": "Azure Dragon HD（プレビュー、S0 必須）",
    "azure_voice": "Azure Speech 女性音声",
    "azure_region": "Azure Speech リージョン",
    "azure_key": "Azure Speech キー",
    "azure_region_choose": "Azure リソースを作成したリージョンを選択",
    "azure_region_saved": "既存の設定 · {region}",
    "azure_key_saved": "Windows で暗号化済み（空欄なら保持）",
    "azure_key_missing": "Azure Speech リソースキーを貼り付け",
    "azure_remove_key": "Azure Speech キーを削除",
    "azure_remove_key_confirm": (
        "Windows で暗号化保存した Azure Speech キーを削除しますか？"
    ),
    "azure_key_save_failed": 'Azure Speech キーの保存設定を確認してください：{error}',
    "azure_hd_voice": "Dragon HD 女性音声",
    "azure_hd_region": "Dragon HD リソースのリージョン",
    "azure_hd_key": "Dragon HD S0 リソースキー",
    "azure_hd_key_saved": "Dragon HD S0 キーは Windows で暗号化済み（空欄なら保持）",
    "azure_hd_key_missing": "独立した Dragon HD S0 リソースキーを貼り付け",
    "azure_hd_remove_key": "Dragon HD S0 キーを削除",
    "azure_hd_remove_key_confirm": (
        "{platform} で安全に保存した Dragon HD S0 キーを削除しますか？"
    ),
    "azure_hd_key_save_failed": 'Dragon HD S0 キーの保存設定を確認してください：{error}',
    "azure_hd_speech_note": (
        '任意のプレビュー機能です。独立した S0 Speech リソース、キー、対応リージョンを使用してください。MoHan は Dragon HD で音声駆動のリップシンクを使用します。発話開始までの遅延はネットワークとリージョン間の距離に依存します。合成に確認が必要な場合は、標準 Azure Speech、Windows 本機音声の順に各 1 回だけフォールバックします。'
    ),
    "azure_speech_note": (
        'プレビュー機能です。Azure Speech リソースキーと対応リージョンを用意してください。確認済みの女性音声だけを表示します。設定の補完またはサービスの確認が必要な場合は Windows 女性音声へ戻ります。Azure の利用量と料金は Microsoft の規定に従います。'
    ),
    "azure_speech_note_no_local_fallback": (
        'プレビュー機能です。Azure Speech リソースキーと対応リージョンを用意してください。この端末の本機音声は確認を待っているため、サービスの確認が必要な場合は安全に再生を停止します。'
    ),
    "azure_fallback_missing_settings": (
        'Azure Speech の設定を完了するとクラウド音声を使えます。この発話は Windows 女性音声だけを本機で使用します。'
    ),
    "azure_missing_no_local_fallback": (
        'Azure Speech の設定を完了するとクラウド音声を使えます。この端末の本機音声は確認を待っているため、再生とクラウド要求は保留します。'
    ),
    "no_female_voice": '確認済みの Windows 女性音声をインストール',
    "female_voice_note": (
        "Windows が女性と明示しているインストール済み音声だけを表示します。"
        "画面言語と一致する音声を優先します。"
    ),
    "platform_local_voice_note": (
        '{platform} の本機音声は端末確認を待っています。墨寒は現在のプラットフォームで確認済みの音声だけを表示し、端末テストでオフライン音声対応を確認します。'
    ),
    "transcription_language_placeholder": "ISO 言語コード（空欄なら自動判定）",
    "openai_fallback": 'OpenAI の回復経路として Windows オフライン認識を使用',
    "openai_recognition": "OpenAI 高精度認識（推奨）",
    "windows_recognition": "Windows オフライン認識",
    "no_transcription_error": '文字起こしは準備完了です。エラー記録はありません',
    "preview_voice": "試聴：主様、妾はここにおります。",
    "realtime_disconnected": 'Realtime：接続待ち',
    "realtime_status_format": "Realtime：{status}",
    "realtime_disconnected_status": '接続待ち',
    "realtime_error_status": "確認が必要です：{error}",
    "realtime_voice_title": "Realtime 音声",
    "realtime_output_unavailable": (
        'Realtime Azure 音声出力の確認が必要なため、リアルタイム会話を開始できません。'
    ),
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
    "recognition_note_no_offline": (
        "一回ごとのマイク入力には OpenAI 高精度認識を使用します。"
        "この環境のオフライン認識は実機検証完了まで表示しません。"
    ),
    "platform_secret_storage_unavailable": (
        '{platform} の安全なキー保存は端末確認を待っています'
    ),
    "platform_autostart_unavailable": (
        '{platform} の自動起動は端末確認を待っています'
    ),
    "autostart": "自動起動",
    "permissions_intro": (
        '機能ごとに権限を付与します。「毎回確認」では実行前に確認を表示します。ファイル削除には明示的な確認が必要です。'
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
        '安全規則：会話は墨寒の設定済み権限の範囲内で動作します。AI はツール要求を提案できますが、実行できる内容は本機の権限設定で決まります。'
    ),
    "save_permissions": "ツール権限を保存",
    "permission_blocked": '権限の更新が必要',
    "permission_blocked_message": '続行するには、墨寒の {action} 権限を有効にしてください。',
    "permission_request": "墨寒がパソコンの権限を求めています",
    "permission_request_message": "今回だけ墨寒に{action}ことを許可しますか？",
    "permission_saved_speech": "パソコンの権限を保存しました。妾はこの境界を守ります。",
    "profile_heading": "<b>名前とプロフィール</b>",
    "system_heading": "<b>仕事とシステム設定</b>",
    "api_key": "OpenAI API キー",
    "text_model": "テキストモデル",
    "persona_prompt": "AI 人格プロンプト",
    "remove_api_key": "保存済み API キーを削除",
    "remove_api_key_confirm": (
        "{platform} で安全に保存された OpenAI API キーを削除しますか？"
    ),
    "save_settings": "設定を保存",
    "api_key_saved": "安全に保存済み（空欄なら変更しません）",
    "api_key_missing": "sk- で始まる OpenAI Project API キーを貼り付け",
    "api_key_save_failed": 'OpenAI API キーの保存設定を確認してください：{error}',
    "secret_auto_save_hint": (
        "Enter キーを押すかフォーカスを移すと、自動的に安全に保存されます。"
    ),
    "api_status_saved": "OpenAI API：キーは OS により安全に保管済み",
    "api_status_environment": "OpenAI API：環境変数からキーを使用中",
    "api_status_secret_unavailable": (
        'OpenAI API：{platform} の安全なキー保存は端末確認を待っています'
    ),
    "api_status_offline": 'OpenAI API：接続用キーを設定してください。現在はオフライン人格を使用しています',
    "restart_language_note": "画面言語は墨寒の再起動後に完全適用されます。",
    "about_heading": "<b>墨寒について</b>",
    "about_body": (
        "墨寒デスクトップアシスタント v{version}、Copyright © 2026"
        " CHOU MING HUA および MoHan Desktop Assistant コントリビューター、"
        "MIT License で公開。<br>本ソフトウェアは Qt for Python（PySide6、"
        "GNU LGPL-3.0 ライセンス）を動的リンクで使用しています。Qt"
        " ライブラリはインストールフォルダーの _internal に独立ファイルとして"
        "同梱され、確認や差し替えが可能です。<br>第三者ライセンスの詳細は"
        "インストールフォルダーの THIRD_PARTY_NOTICES.md と"
        " third_party_licenses フォルダーを参照してください。Qt のソース"
        'コードは <a href="https://download.qt.io/official_releases/'
        'QtForPython/">Qt 公式ダウンロードアーカイブ</a>から取得できます。'
    ),
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
    "work_timer_already_running": '作業タイマーはすでに動作中です。現在のセッションを続けます。',
    "work_timer_not_started": '準備ができたら今日の作業タイマーを開始してください。',
})


JAPANESE_MODE_LABELS: Mapping[str, str] = frozendict({
    "工作": "仕事",
    "陪伴": "お供",
    "勿擾": "集中",
    "會議": "会議",
    "離席": "離席",
    "休眠": "休眠",
})


JAPANESE_WORK_TYPE_LABELS: Mapping[str, str] = frozendict({
    "一般辦公／行政": "一般事務／管理",
    "專案管理": "プロジェクト管理",
    "自由工作者／接案": "フリーランス／受託",
    "創作／內容工作": "創作／コンテンツ制作",
    "軟體開發／技術": "ソフトウェア開発／技術",
    "教育／研究": "教育／研究",
    "銷售／客戶服務": "営業／カスタマーサービス",
    "其他（可自行輸入）": "その他（自由入力）",
})


JAPANESE_PLATFORM_STATUS_LABELS: Mapping[str, str] = frozendict({
    "尚未開始": "未着手",
    "準備資料": "資料準備",
    "進行中": "進行中",
    "待送出": "提出待ち",
    "等待回覆": "返信待ち",
    "審核中": "審査中",
    "需修正": "修正が必要",
    "已排程": "予定済み",
    "已完成": "完了",
    "已上架": "公開済み",
    "暫停": "一時停止",
})


JAPANESE_MEMORY_CATEGORY_LABELS: Mapping[str, str] = frozendict({
    "人物": "人物",
    "偏好": "好み",
    "目標": "目標",
    "工作流程": "ワークフロー",
    "重要日期": "重要な日付",
    "其他": "その他",
})


__all__ = (
    "JAPANESE_MEMORY_CATEGORY_LABELS",
    "JAPANESE_MODE_LABELS",
    "JAPANESE_PLATFORM_STATUS_LABELS",
    "JAPANESE_UI",
    "JAPANESE_WORK_TYPE_LABELS",
)
