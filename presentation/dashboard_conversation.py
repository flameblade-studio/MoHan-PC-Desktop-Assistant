from __future__ import annotations

lazy import html

from PySide6.QtCore import QTimer
lazy from PySide6.QtCore import Qt
lazy from PySide6.QtGui import QFont
lazy from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

lazy from application.companion_phrasebook import (
    PHRASEBOOK_SETTING,
    CompanionPhrasebook,
)
lazy from application.outfit_reveal import (
    LAST_REVEALED_OUTFIT_KEY,
    is_outfit_origin_question,
    outfit_origin_reply,
)
lazy from application.presentation_ports import (
    DEFAULT_TEXT_MODEL,
    AIWorkerRequest,
    format_duration,
)
lazy from domain.app_profile import (
    persona_for_profile,
    personalize_text,
    profile_setting,
)
lazy from domain.command_parser import is_start_work_command, is_stop_work_command
lazy from domain.expression_system import parse_internal_emotion, plan_wait_expressions
lazy from domain.language_support import is_english, is_japanese, is_simplified_chinese
lazy from domain.text_normalizer import to_taiwan_traditional
lazy from presentation.dashboard_dialogs import ChatHistoryDialog, ZoomTextBrowser

__all__ = ("DashboardConversationMixin", "classify_memory_text")

MIN_CHAT_ZOOM_PERCENT = 60
MAX_CHAT_ZOOM_PERCENT = 200

EMERGENCY_COMMANDS = frozenset(
    {
        "墨寒停手",
        "寒停手",
        "停手",
        "停止所有操作",
        "取消所有任務",
    }
)

TEASING_COMMAND_MARKERS = (
    "妳在看我",
    "你在看我",
    "偷看我",
    "一直看我",
    "喜歡我嗎",
    "喜歡我吧",
    "是不是喜歡",
    "愛慕我",
    "在意我吧",
)

TODAY_WORK_DURATION_MARKERS = ("多久", "幾小時", "工作時間")

IDEA_CAPTURE_MARKERS = ("靈感", "點子", "構想")

EXPLICIT_TOOL_COMMAND_MARKERS = (
    "請執行",
    "幫我開啟",
    "替我開啟",
    "幫我控制",
    "幫我建立檔案",
    "幫我移動",
    "幫我啟動",
)


def classify_memory_text(text: str) -> str:
    normalized = to_taiwan_traditional(text)
    category_terms = (
        (
            "重要日期",
            ("生日", "紀念日", "日期", "截止日", "每年", "月號"),
        ),
        (
            "目標",
            ("目標", "希望完成", "想要達成", "計畫達成", "今年要"),
        ),
        (
            "人物",
            (
                "朋友",
                "家人",
                "同事",
                "客戶",
                "主管",
                "老師",
                "學生",
                "名字叫",
                "名叫",
                "是我的",
            ),
        ),
        (
            "工作流程",
            (
                "工作流程",
                "工作習慣",
                "我習慣",
                "每次都先",
                "完成後再",
                "上架",
                "交稿",
            ),
        ),
        (
            "偏好",
            (
                "偏好",
                "喜歡",
                "不喜歡",
                "比較想",
                "習慣用",
                "常用",
            ),
        ),
    )
    for category, terms in category_terms:
        if any(term in normalized for term in terms):
            return category
    return "其他"


class DashboardConversationMixin:
    def _chat_history_controls(self) -> QHBoxLayout:
        history_row = QHBoxLayout()
        self.chat_retention = QLabel(
            self._t(
                "chat_retention",
                "對話保存在本機，不會自動刪除",
            )
        )
        self.chat_retention.setStyleSheet("color: #356d88;")
        self.load_older_chat_btn = QPushButton(
            self._t("load_older_chat", "載入較早對話")
        )
        self.load_older_chat_btn.setToolTip(
            self._t(
                "load_older_chat_tooltip",
                "每次向前載入 50 則本機對話",
            )
        )
        self.manage_chat_btn = QPushButton(
            self._t("manage_chat", "管理／清除對話")
        )
        self.manage_chat_btn.setToolTip(
            self._t(
                "manage_chat_tooltip",
                "勾選並刪除指定對話，其他內容不受影響",
            )
        )
        self.chat_zoom_down = QPushButton("A－")
        self.chat_zoom_down.setToolTip(
            self._t(
                "chat_zoom_out_tooltip",
                "縮小對話文字（Ctrl＋滑鼠滾輪向下）",
            )
        )
        self.chat_zoom_down.setFixedWidth(48)
        self.chat_zoom_label = QLabel()
        self.chat_zoom_label.setMinimumWidth(48)
        self.chat_zoom_label.setAlignment(Qt.AlignCenter)
        self.chat_zoom_up = QPushButton("A＋")
        self.chat_zoom_up.setToolTip(
            self._t(
                "chat_zoom_in_tooltip",
                "放大對話文字（Ctrl＋滑鼠滾輪向上）",
            )
        )
        self.chat_zoom_up.setFixedWidth(48)
        history_row.addWidget(self.chat_retention)
        history_row.addStretch()
        history_row.addWidget(self.load_older_chat_btn)
        history_row.addWidget(self.manage_chat_btn)
        history_row.addWidget(self.chat_zoom_down)
        history_row.addWidget(self.chat_zoom_label)
        history_row.addWidget(self.chat_zoom_up)
        return history_row


    def _connect_chat_controls(self, send_button: QPushButton) -> None:
        send_button.clicked.connect(self.send_chat)
        self.chat_input.returnPressed.connect(self.send_chat)
        self.mic_btn.clicked.connect(self.listener.toggle_listening)
        self.load_older_chat_btn.clicked.connect(
            self.load_older_chat
        )
        self.manage_chat_btn.clicked.connect(
            self.manage_chat_history
        )
        self.chat_zoom_down.clicked.connect(
            lambda: self.adjust_chat_zoom(-1)
        )
        self.chat_zoom_up.clicked.connect(
            lambda: self.adjust_chat_zoom(1)
        )
        self.chat.zoom_step_requested.connect(self.adjust_chat_zoom)


    def _chat_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        history_row = self._chat_history_controls()
        self.chat = ZoomTextBrowser()
        self.chat.setOpenExternalLinks(True)
        self.chat_base_point_size = self.chat.font().pointSizeF()
        if self.chat_base_point_size <= 0:
            self.chat_base_point_size = 10.0
        row = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText(
            self._t(
                "chat_placeholder",
                "對寒說話，例如：我開始工作了／幫我記一下……",
            )
        )
        self.mic_btn = QPushButton(self._t("microphone", "🎙 麥克風"))
        send = QPushButton(self._t("send_text", "送出文字"))
        row.addWidget(self.chat_input, 1)
        row.addWidget(self.mic_btn)
        row.addWidget(send)
        layout.addLayout(history_row)
        layout.addWidget(self.chat, 1)
        layout.addLayout(row)
        self.voice_phase = QLabel(
            self._t("voice_ready", "語音狀態：準備就緒")
        )
        self.voice_phase.setStyleSheet("color: #356d88; padding-left: 4px;")
        layout.addWidget(self.voice_phase)
        self._connect_chat_controls(send)
        self.apply_chat_zoom(self.chat_zoom_percent, persist=False)
        return tab


    def append_chat(self, speaker: str, text: str) -> None:
        color = (
            "#2f6987"
            if speaker == self.assistant_name
            else "#8a4f82"
        )
        display_text = personalize_text(self.db, text)
        safe_text = html.escape(display_text).replace("\n", "<br>")
        self.chat.append(
            f'<p><b style="color:{color}">{speaker}</b><br>{safe_text}</p>'
        )
        self.chat.verticalScrollBar().setValue(self.chat.verticalScrollBar().maximum())


    def refresh_chat(self) -> None:
        self.chat.clear()
        total = self.db.chat_count()
        for row in self.db.recent_chat(self.chat_loaded_limit):
            self.append_chat(
                self.user_title
                if row["role"] == "user"
                else self.assistant_name,
                row["content"],
            )
        shown = min(total, self.chat_loaded_limit)
        self.chat_retention.setText(
            self._t(
                "chat_retention_status",
                "本機保存 {total} 則對話，目前顯示最近 {shown} 則",
                total=total,
                shown=shown,
            )
        )
        self.load_older_chat_btn.setEnabled(shown < total)
        # QTextDocument.clear()/append() may restore the document's default
        # font.  Reapply the persisted zoom after the initial/history reload so
        # the displayed text agrees with the already-correct percentage label.
        self.apply_chat_zoom(self.chat_zoom_percent, persist=False)


    def load_older_chat(self) -> None:
        self.chat_loaded_limit += 50
        self.refresh_chat()


    def manage_chat_history(self) -> None:
        manager = ChatHistoryDialog(
            self.db,
            self,
            language=self.ui_language,
        )
        manager.exec()
        if manager.changed:
            self.refresh_chat()


    def adjust_chat_zoom(self, steps: int) -> None:
        self.apply_chat_zoom(self.chat_zoom_percent + (steps * 10))


    def apply_chat_zoom(self, percent: int, *, persist: bool = True) -> None:
        self.chat_zoom_percent = max(60, min(200, int(percent)))
        font = QFont(self.chat.font())
        font.setPointSizeF(
            self.chat_base_point_size * self.chat_zoom_percent / 100.0
        )
        self.chat.setFont(font)
        self.chat.document().setDefaultFont(font)
        self.chat_zoom_label.setText(f"{self.chat_zoom_percent}%")
        self.chat_zoom_down.setEnabled(self.chat_zoom_percent > MIN_CHAT_ZOOM_PERCENT)
        self.chat_zoom_up.setEnabled(self.chat_zoom_percent < MAX_CHAT_ZOOM_PERCENT)
        if persist:
            self.db.set_setting("chat_zoom_percent", self.chat_zoom_percent)


    def send_chat(self) -> None:
        text = self.chat_input.text().strip()
        if not text:
            QMessageBox.information(
                self,
                self._t(
                    "send_chat_required_title",
                    "尚未輸入內容",
                ),
                self._t(
                    "send_chat_required",
                    "請先在左側輸入文字，再按「送出文字」；"
                    "也可以按麥克風直接說話。",
                ),
            )
            self.chat_input.setFocus()
            return
        self.chat_input.clear()
        self.human_interaction.emit()
        self.append_chat(self.user_title, text)
        self.db.log_chat("user", text)
        self._capture_explicit_memory(text)
        source = getattr(self, "_input_source", "local")
        self._input_source = "local"
        if self._handle_command(text, source=source):
            return
        self.ai_queue.append((text, self.mode))
        self.set_voice_phase(
            self._t(
                "thinking_status",
                "{assistant}思考中…",
                assistant=self.assistant_name,
            )
        )
        self._start_next_ai_request()


    def _receive_remote_command(self, text: str) -> None:
        normalized = text.strip()
        if not normalized:
            return
        # The remote server has already authenticated and audited the device.
        # It enters the same command path as local text so it cannot bypass
        # command parsing, conversation history, or the flagship policy layer.
        bracket = normalized.find("] ")
        command = normalized[bracket + 2 :] if bracket >= 0 else normalized
        self._input_source = "remote"
        self.chat_input.setText(command)
        self.send_chat()


    def _start_next_ai_request(self) -> None:
        if self.ai_busy or not self.ai_queue:
            return
        text, mode = self.ai_queue.popleft()
        self.ai_busy = True
        self.set_voice_phase(
            self._t(
                "thinking_status",
                "{assistant}思考中…",
                assistant=self.assistant_name,
            )
        )
        history = [
            {"role": row["role"], "content": row["content"]}
            for row in self.db.recent_chat_context()
        ]
        worker = self.ai_worker_factory(
            AIWorkerRequest(
                user_text=text,
                mode=mode,
                history=tuple(history),
                api_key=self.secret_store.load(),
                memories=self.db.memory_context(query=text),
                model=str(self.db.setting("ai_model", DEFAULT_TEXT_MODEL)),
                persona=persona_for_profile(self.db),
                assistant_name=self.assistant_name,
                user_title=self.user_title,
                response_language=profile_setting(
                    self.db, "ui_language"
                ),
            )
        )
        worker.signals.done.connect(self._ai_done)
        worker.signals.failed.connect(self._ai_failed)
        self.thread_pool.start(worker)
        self._schedule_ai_wait_expressions(text)


    def _schedule_ai_wait_expressions(self, text: str) -> None:
        """Schedule optional reactions; the status label is display-only."""
        self._finish_ai_wait_expression()
        self.ai_wait_generation += 1
        generation = self.ai_wait_generation
        self.active_ai_wait_generation = generation
        for cue in plan_wait_expressions(text):
            QTimer.singleShot(
                cue.delay_ms,
                lambda cue=cue: self._emit_ai_wait_expression(
                    generation,
                    cue.expression,
                    cue.intensity,
                ),
            )


    def _emit_ai_wait_expression(
        self,
        generation: int,
        expression: str,
        intensity: float,
    ) -> None:
        if (
            self.ai_busy
            and generation == self.active_ai_wait_generation
        ):
            self.ai_wait_expression_requested.emit(
                generation,
                expression,
                intensity,
            )


    def _finish_ai_wait_expression(self) -> None:
        generation = self.active_ai_wait_generation
        if not generation:
            return
        self.active_ai_wait_generation = 0
        self.ai_wait_expression_finished.emit(generation)


    def cancel_ai_wait_expression(self) -> None:
        """Invalidate pending visual reactions without cancelling the API."""
        self._finish_ai_wait_expression()


    def _capture_explicit_memory(self, text: str) -> None:
        if not bool(self.db.setting("auto_memory", True)):
            return
        markers = (
            "請記住",
            "你要記得",
            "我的偏好是",
            "我喜歡",
            "我不喜歡",
            "我習慣",
            "我的目標是",
            "我的生日是",
            "我的朋友",
            "我的家人",
            "我的同事",
            "我的客戶",
            "工作流程是",
        )
        if any(marker in text for marker in markers):
            category = classify_memory_text(text)
            self.db.add_memory(text, category, "conversation", 4)
            self.refresh_memories()


    def _handle_command(self, text: str, source: str = "local") -> bool:
        return (
            self._handle_emergency_command(text)
            or self._handle_outfit_origin_question(text)
            or self._handle_teasing_command(text)
            or self._handle_work_status_command(text)
            or self._handle_quick_capture_command(text)
            or self._handle_tool_instruction(text, source)
        )

    def _handle_outfit_origin_question(self, text: str) -> bool:
        revealed = str(
            self.db.setting(LAST_REVEALED_OUTFIT_KEY, "") or ""
        ).strip()
        language = profile_setting(self.db, "ui_language")
        if not revealed or not is_outfit_origin_question(text, language):
            return False
        phrasebook = CompanionPhrasebook.from_setting(
            self.db.setting(PHRASEBOOK_SETTING, {})
        )
        reply = outfit_origin_reply(
            language,
            variation_index=0,
            phrasebook=phrasebook,
        )
        if not reply:
            return False
        self._reply(reply, "shy_cute_front", source="wardrobe-origin")
        return True


    def _handle_emergency_command(self, text: str) -> bool:
        normalized = text.replace("，", "").replace(",", "").strip()
        if normalized not in EMERGENCY_COMMANDS:
            return False
        self._emergency_stop()
        return True


    def _handle_teasing_command(self, text: str) -> bool:
        if not any(marker in text for marker in TEASING_COMMAND_MARKERS):
            return False
        self._reply(
            "主上莫要自作多情。妾不過是在觀察你的神色，"
            "好替你籌謀下一步。至於旁的……並無此事。",
            "caught",
        )
        return True


    def _handle_work_status_command(self, text: str) -> bool:
        if is_start_work_command(text):
            self.start_work()
        elif is_stop_work_command(text):
            self.stop_work()
        elif "今天" in text and any(
            marker in text for marker in TODAY_WORK_DURATION_MARKERS
        ):
            duration = format_duration(
                self.db.today_work_seconds(),
                self.ui_language,
            )
            self._reply(f"主上今日已工作 {duration}。", "speaking")
        else:
            return False
        return True


    def _handle_quick_capture_command(self, text: str) -> bool:
        marker = "幫我記一下"
        if marker not in text:
            return False
        content = text.split(marker, 1)[1].lstrip("：:，, ").strip()
        if not content:
            self._reply("主上想讓妾記下什麼？", "worried")
        elif any(marker in content for marker in IDEA_CAPTURE_MARKERS):
            self.db.add_idea(content)
            self.refresh_ideas()
            self._reply("靈感已收入卷冊。", "happy")
        else:
            self.db.add_todo(content, "其他")
            self.refresh_todos()
            self._reply("已加入今日待辦。", "happy")
        return True


    def _handle_tool_instruction(self, text: str, source: str) -> bool:
        flagship_center = getattr(self, "flagship_center", None)
        if flagship_center is None:
            return False
        recognized = flagship_center.recognizes_safe_instruction(text)
        explicitly_requested = any(
            marker in text for marker in EXPLICIT_TOOL_COMMAND_MARKERS
        )
        if not (recognized or explicitly_requested):
            return False
        flagship_center.plan_instruction(text, source=source)
        self._reply(
            "妾先整理成安全計畫，確認權限與目標後再請主上過目。",
            "thinking_front",
        )
        return True


    def _emergency_stop(self) -> None:
        if hasattr(self, "flagship_center"):
            self.flagship_center.emergency_stop()


    def _reply(
        self,
        text: str,
        state: str,
        *,
        intensity: float = 0.5,
        source: str = "conversation",
    ) -> None:
        text = personalize_text(self.db, text)
        self.db.log_chat("assistant", text)
        self.append_chat(self.assistant_name, text)
        self.set_voice_phase(self._t("answering_status", "回答中…"))
        self.next_expression_metadata = (
            state,
            max(0.0, min(1.0, float(intensity))),
            source,
        )
        self.speak_requested.emit(text, state)


    def _ai_done(self, text: str) -> None:
        self._finish_ai_wait_expression()
        tagged = parse_internal_emotion(text)
        clean = tagged.text or "妾在。主上方才所言，容妾再細想一遍。"
        expression = (
            tagged.expression
            if tagged.valid_tag and tagged.expression is not None
            else self._reply_expression(clean)
        )
        self._reply(
            clean,
            expression,
            intensity=tagged.intensity,
            source="ai_tag" if tagged.valid_tag else "fallback",
        )
        self.ai_busy = False
        self._start_next_ai_request()


    @staticmethod
    def _reply_expression(text: str) -> str:
        compact = "".join(str(text).split())
        rules = (
            (
                "mock_hit_front",
                (
                    "再胡說妾便敲你",
                    "再胡說妾可要敲你",
                    "當心妾敲你",
                    "放肆，妾可要",
                ),
            ),
            (
                "mock_scold",
                ("休得胡言", "莫要踰矩", "休要亂說"),
            ),
            (
                "shy_cute_front",
                (
                    "莫要自作多情",
                    "才沒有偷看",
                    "妾並未偷看",
                    "誰在注視你",
                    "並無此事，主上",
                ),
            ),
            (
                "eureka_front",
                ("妾想到了", "妾有辦法了", "關鍵原來在於"),
            ),
            (
                "protective_front",
                (
                    "妾會護著主上",
                    "不許任何人傷你",
                    "誰也不得傷主上",
                    "有妾護著主上",
                ),
            ),
            (
                "exasperated_front",
                (
                    "真拿主上沒辦法",
                    "主上又來了",
                    "讓妾省點心",
                ),
            ),
            (
                "restrained_amused_front",
                (
                    "妾忍俊不禁",
                    "主上是在逗妾",
                    "倒是有趣得很",
                ),
            ),
            (
                "attentive_front",
                ("妾在聽", "主上慢慢說", "請繼續說", "妾願聞其詳"),
            ),
            (
                "determined_front",
                ("計策已定", "便照此執行", "就這麼辦", "此事交給妾"),
            ),
            (
                "surprised_front",
                ("真沒想到", "出乎妾意料", "竟會如此"),
            ),
            (
                "worried_front",
                (
                    "妾很擔心",
                    "主上別逞強",
                    "主上莫要逞強",
                    "先處理傷勢",
                    "你已經很疲憊",
                    "妾放心不下",
                ),
            ),
            (
                "reminder",
                (
                    "該吃飯了",
                    "先去吃飯",
                    "該休息了",
                    "先休息片刻",
                    "喝些水",
                    "到了下班時辰",
                    "妾提醒主上",
                ),
            ),
            (
                "relieved_front",
                ("主上平安便好", "沒事就好", "妾總算放心"),
            ),
            (
                "proud_front",
                ("不出妾所料", "正如妾所料", "依妾之計"),
            ),
            (
                "gentle_smile_front",
                (
                    "主上做得很好",
                    "妾替主上高興",
                    "此事值得恭喜",
                ),
            ),
            (
                "thinking_front",
                (
                    "妾先分析",
                    "先分析風險",
                    "妾的建議是",
                    "先排優先順序",
                    "此事需從長計議",
                ),
            ),
        )
        for expression, phrases in rules:
            if any(phrase in compact for phrase in phrases):
                return expression
        return "speaking"


    def _ai_failed(self, error: str) -> None:
        self._finish_ai_wait_expression()
        if is_english(self.ui_language):
            message = (
                "The cloud connection is temporarily unavailable. I remain "
                "here, but cannot draw on external knowledge just now."
            )
        elif is_simplified_chinese(self.ui_language):
            message = "云端连接暂时中断。妾仍在，只是此刻无法借用外部知识。"
        elif is_japanese(self.ui_language):
            message = (
                "クラウドとの接続が一時的に途切れました。妾はここにおりますが、"
                "今は外部の知識を借りられません。"
            )
        else:
            message = "雲端傳音暫時中斷。妾仍在，只是此刻無法借用外部智識。"
        self._reply(message, "worried")
        self.api_status.setText(
            self._t(
                "api_connection_failed",
                "OpenAI API：連線失敗（{error}）",
                error=error[:70],
            )
        )
        self.ai_busy = False
        self._start_next_ai_request()


    def _voice_text(self, text: str) -> None:
        text = text.strip()
        self.set_voice_phase(
            self._t(
                "thinking_status",
                "{assistant}思考中…",
                assistant=self.assistant_name,
            )
        )
        wake_word = profile_setting(self.db, "wake_word")
        self.chat_input.setText(
            text.replace(wake_word, "", 1).strip() or text
        )
        self._input_source = "voice"
        self.send_chat()


    def _voice_error(self, message: str) -> None:
        self.set_voice_phase(
            self._t("voice_ready_short", "準備就緒")
        )
        self.append_chat("寒", message)
        self.speak_requested.emit(message, "worried")


    def _listening_changed(self, listening: bool) -> None:
        if not listening:
            self.mic_btn.setText(
                self._t("microphone_idle", "🎙 麥克風")
            )
            self.mic_btn.setEnabled(True)
        elif self.listener.is_recording:
            self.mic_btn.setText(
                self._t("microphone_send_now", "⏹ 立即送出")
            )
            self.mic_btn.setEnabled(True)
        else:
            self.mic_btn.setText(
                self._t("microphone_recognizing", "辨識中…")
            )
            self.mic_btn.setEnabled(False)


    def _recording_changed(self, recording: bool) -> None:
        if recording:
            self.mic_btn.setText(
                self._t("microphone_send_now", "⏹ 立即送出")
            )
            self.mic_btn.setEnabled(True)
        else:
            self.mic_btn.setText(
                self._t("microphone_recognizing", "辨識中…")
            )
            self.mic_btn.setEnabled(False)


    def _transcription_diagnostic(self, message: str) -> None:
        self.db.set_setting("last_transcription_diagnostic", message)
        if hasattr(self, "transcription_diagnostic"):
            self.transcription_diagnostic.setText(message)


    def set_voice_phase(self, phase: str) -> None:
        self.set_desktop_companion_status("voice", phase)
        self.voice_phase.setText(
            self._t(
                "voice_status_format",
                "語音狀態：{phase}",
                phase=phase,
            )
        )
