from __future__ import annotations

lazy from PySide6.QtCore import QPoint, QTimer
lazy from PySide6.QtWidgets import QMessageBox

lazy from application.behavior_director import (
    BehaviorInput,
    SpeechLifecycle,
)
lazy from application.performance_app_bridge import PerformanceBridgeInput
lazy from application.presentation_ports import (
    DEFAULT_TRANSCRIPTION_PROMPT,
    REALTIME_OUTPUT_OPENAI,
    AzureRealtimeVoice,
    LocalRealtimeVoice,
    RealtimeSessionConfig,
    RealtimeSpeechOutputConfigRequest,
    RealtimeVoiceRequest,
    resembles_transcription_prompt,
    sanitize_realtime_transcription_prompt,
)
lazy from domain.app_profile import (
    persona_for_profile,
    personalize_text,
    profile_setting,
)
lazy from domain.command_parser import is_start_work_command, is_stop_work_command
lazy from domain.companion_animation_contract import (
    CHEEK_SPEECH_CLOSED_EXPRESSION,
    EXPRESSION_POSES,
    EXPRESSION_SPEECH_EXPRESSIONS,
    EXPRESSION_SPEECH_FRAMES,
    HAPPY_SPEECH_CLOSED_EXPRESSION,
    MOUTH_CLOSE_DEADLINE_MS,
)
lazy from domain.expression_system import parse_internal_emotion
lazy from domain.language_support import (
    is_english,
    is_japanese,
    is_simplified_chinese,
    response_language_instruction,
)
lazy from domain.performance_preferences import PerformancePreferences
lazy from domain.safe_error_localization import safe_error_message
lazy from domain.speech_configuration import (
    VOICE_ENGINE_AZURE,
    VOICE_ENGINE_AZURE_HD,
    VOICE_ENGINE_OPENAI,
    VOICE_ENGINE_SYSTEM,
    VOICE_GENERATION_PROMPT,
    QueuedSpeech,
    SpeechCredentials,
)
lazy from domain.speech_providers import (
    SpeechRequest,
    normalize_speech_provider_id,
)
lazy from presentation.companion_speech_emotion import (
    _emotion_rate_adjustment,
    _semantic_emotion_for_state,
)
lazy from presentation.companion_wait_expression import (
    finish_ai_wait_expression,
    start_ai_wait_expression,
)
lazy from presentation.ui_localization import ui_text
lazy import contextlib

__all__ = ("CompanionSpeechRuntimeMixin",)


class CompanionSpeechRuntimeMixin:
    """Provider-neutral speech, Realtime, and return-to-idle runtime."""

    _start_ai_wait_expression = start_ai_wait_expression
    _finish_ai_wait_expression = finish_ai_wait_expression

    def _stop_gesture_animation(self) -> None:
        animation = getattr(self, "state_animation", None)
        if animation is not None and animation.state():
            animation.stop()
        self.gesture_motion_x = 0.0
        self.gesture_motion_y = 0.0
        self._compose_character_position()

    def _apply_gesture_motion(self, value: QPoint) -> None:
        self.gesture_motion_x = float(value.x())
        self.gesture_motion_y = float(value.y())
        self._compose_character_position()

    def _finish_gesture_motion(self) -> None:
        self.gesture_motion_x = 0.0
        self.gesture_motion_y = 0.0
        self._compose_character_position()

    def _prepare_speech_performance(self, provider_id: str) -> None:
        """Start one provider-neutral body-performance generation."""

        self._record_speech_performance(
            self.speech_performance.prepare(provider_id)
        )

    def _record_speech_performance(self, update: object | None) -> None:
        """Feed one provider-neutral speech event into the adaptive body pipeline."""

        if update is None:
            return
        event, directive = update
        self.last_speech_performance_event = event
        self.last_speech_performance_directive = directive
        bridge = getattr(self, "_performance_app_bridge", None)
        if bridge is None:
            return
        previous = bridge.last_known_good
        current_pose = (
            previous.performance.pose
            if previous is not None
            else "front-crossed"
        )
        lifecycle = {
            "preparing": SpeechLifecycle.STARTING,
            "speaking": SpeechLifecycle.SPEAKING,
            "pausing": SpeechLifecycle.SPEAKING,
            "settling": SpeechLifecycle.ENDING,
            "interrupted": SpeechLifecycle.ENDING,
            "idle": SpeechLifecycle.IDLE,
        }[directive.phase.value]
        emotion = _semantic_emotion_for_state(
            str(getattr(self, "state", "idle"))
        )
        self._adaptive_behavior_generation = (
            getattr(self, "_adaptive_behavior_generation", 0) + 1
        )
        preferences = PerformancePreferences(
            proactive_body_enabled=bool(
                self.db.setting("performance_proactive_body_enabled", True)
            ),
            intensity_percent=int(
                self.db.setting("performance_intensity_percent", 60)
            ),
            view_360_enabled=bool(
                self.db.setting("performance_360_view_enabled", True)
            ),
            full_back_view_enabled=bool(
                self.db.setting("performance_full_back_view_enabled", True)
            ),
            emotional_back_view_enabled=bool(
                self.db.setting("performance_emotional_back_view_enabled", True)
            ),
            left_gestures_enabled=bool(
                self.db.setting("performance_left_gestures_enabled", True)
            ),
            right_gestures_enabled=bool(
                self.db.setting("performance_right_gestures_enabled", True)
            ),
            camera_context_enabled=bool(
                self.db.setting("performance_camera_context_enabled", True)
            ),
        )
        bridge.dispatch(
            PerformanceBridgeInput(
                event,
                directive,
                self._adaptive_behavior_generation,
                BehaviorInput(
                    lifecycle,
                    emotion,
                    max(
                        0.0,
                        min(
                            1.0,
                            float(getattr(self, "after_speech_intensity", 0.5)),
                        ),
                    ),
                    max(0, int(getattr(self, "expression_generation", 0))),
                    True,
                    True,
                    0.0,
                    current_pose,
                    str(getattr(self, "state", "idle")),
                    False,
                ),
                preferences,
                frozenset({"idle_front.png", "idle_lean.png", "idle.png"}),
                True,
            )
        )

    def speak(self, text: str, state: str = "speaking") -> None:
        text = personalize_text(self.db, text)
        if not text.strip():
            return
        intensity = 0.5
        source = "reminder" if state == "reminder" else "conversation"
        pending = self.dashboard.consume_expression_metadata(state)
        if pending is not None:
            _, intensity, source = pending
        self.speech_queue.append(
            QueuedSpeech(text, state, intensity, source)
        )
        self._start_next_speech()

    def _start_next_speech(self) -> None:
        if self.speech_playing or not self.speech_queue:
            return
        self.speech_finish_timer.stop()
        queued = self.speech_queue.popleft()
        self._begin_speech_presentation(queued)
        tts_enabled = bool(self.db.setting("tts_enabled", True))
        self._start_mouth_animation(audio_driven=tts_enabled)
        self.show()
        self.raise_()
        if tts_enabled:
            self._start_speech_provider(queued.text, queued.requested_state)
            return
        self._prepare_speech_performance("visual-only")
        QTimer.singleShot(
            max(1200, min(5000, len(queued.text) * 80)),
            self._speech_audio_finished,
        )

    def _begin_speech_presentation(self, queued: QueuedSpeech) -> None:
        self.speech_playing = True
        self.active_speech_text = queued.text
        self.active_speech_engine = ""
        self.active_speech_source = queued.source
        self.active_speech_delivery_token = queued.delivery_token
        self.cloud_fallback_active = False
        self.speech_fallback_attempts.clear()
        self._show_bubble(queued.text)
        state = self._accepted_speech_state(queued)
        self.after_speech_state = state if state != "speaking" else "idle"
        self.after_speech_intensity = queued.intensity
        emotional_base = (
            state
            if state in EXPRESSION_POSES
            and state in self.expression_pixmaps
            else self._idle_expression()
        )
        self._configure_speech_frames(emotional_base)
        self.expression_generation += 1
        self.state = "speaking"
        self.expression_arbiter.request(
            "speaking",
            source="conversation",
            force=True,
        )

    def _accepted_speech_state(self, queued: QueuedSpeech) -> str:
        if queued.requested_state not in EXPRESSION_POSES:
            return queued.requested_state
        decision = self.expression_arbiter.request(
            queued.requested_state,
            source=queued.source,
            intensity=queued.intensity,
        )
        return queued.requested_state if decision.accepted else "speaking"

    def _configure_speech_frames(self, emotional_base: str) -> None:
        speech_pose = self.physics_expression_poses.get(
            emotional_base,
            self.idle_pose,
        )
        self.speech_pose_suffix = self._pose_suffix(speech_pose)
        self.speech_gesture_expression = (
            emotional_base
            if emotional_base in EXPRESSION_SPEECH_EXPRESSIONS
            else None
        )
        if self.speech_gesture_expression is not None:
            frames = EXPRESSION_SPEECH_FRAMES[
                self.speech_gesture_expression
            ]
            self.speech_closed_expression = (
                HAPPY_SPEECH_CLOSED_EXPRESSION
                if self.speech_gesture_expression == "happy"
                else self.speech_gesture_expression
            )
            self.speech_mid_expression = frames["mid"]
            self.speech_open_expression = frames["open"]
        else:
            self.speech_closed_expression = (
                CHEEK_SPEECH_CLOSED_EXPRESSION
                if self.speech_pose_suffix == ""
                else f"idle{self.speech_pose_suffix}"
            )
            self.speech_mid_expression = (
                f"mouth_mid{self.speech_pose_suffix}"
            )
            self.speech_open_expression = (
                f"speaking{self.speech_pose_suffix}"
            )

    def _speech_credentials(self) -> SpeechCredentials:
        azure_api_key = (
            self.azure_secret_store.load()
            if self.azure_secret_store is not None
            else ""
        )
        azure_hd_api_key = (
            self.azure_hd_secret_store.load()
            if self.azure_hd_secret_store is not None
            else ""
        )
        return SpeechCredentials(
            openai_api_key=self.secret_store.load(),
            azure_api_key=azure_api_key,
            azure_region=str(
                self.db.setting("azure_speech_region", "")
            ).strip(),
            azure_hd_api_key=azure_hd_api_key,
            azure_hd_region=str(
                self.db.setting("azure_hd_speech_region", "")
            ).strip(),
        )

    def _configured_speech_providers(
        self,
        credentials: SpeechCredentials,
    ) -> tuple[str, ...]:
        availability = (
            (
                VOICE_ENGINE_SYSTEM,
                self.platform_services.capabilities.system_local_speech,
            ),
            (VOICE_ENGINE_OPENAI, bool(credentials.openai_api_key)),
            (
                VOICE_ENGINE_AZURE,
                bool(credentials.azure_api_key and credentials.azure_region),
            ),
            (
                VOICE_ENGINE_AZURE_HD,
                bool(
                    credentials.azure_hd_api_key
                    and credentials.azure_hd_region
                ),
            ),
        )
        return tuple(
            provider_id
            for provider_id, configured in availability
            if configured
        )

    def _start_speech_provider(self, text: str, state: str = "speaking") -> None:
        credentials = self._speech_credentials()
        selected_provider_id = normalize_speech_provider_id(
            self.db.setting("voice_engine", VOICE_ENGINE_SYSTEM)
        )
        provider_id = self.speech_providers.output_provider_id(
            selected_provider_id,
            realtime_running=bool(self.realtime.running),
            cloud_available=bool(credentials.openai_api_key),
            configured_provider_ids=self._configured_speech_providers(
                credentials
            ),
        )
        self._report_azure_fallback(selected_provider_id, provider_id)
        self.active_speech_engine = provider_id
        self._prepare_speech_performance(provider_id)
        self.speech_fallback_attempts.add(provider_id)
        voice, api_key = self._speech_voice_and_key(provider_id, credentials)
        # Emotional prosody: a shy or gentle line is spoken a touch slower,
        # while an excited or proud line is spoken a touch faster.  The user's
        # configured rate remains the baseline; the emotion only nudges it.
        base_rate = int(self.db.setting("voice_rate", -1))
        rate = base_rate + _emotion_rate_adjustment(state)
        request = SpeechRequest(
            text=text,
            voice=voice,
            rate=rate,
            api_key=api_key,
            instructions=str(
                self.db.setting(
                    "voice_instructions",
                    VOICE_GENERATION_PROMPT,
                )
            ),
            options={
                "region": (
                    credentials.azure_hd_region
                    if provider_id == VOICE_ENGINE_AZURE_HD
                    else credentials.azure_region
                ),
                "locale": str(self.db.setting("ui_language", "zh-TW")),
            },
        )
        self.speech_providers.provider(provider_id).speak(request)

    def _report_azure_fallback(
        self,
        selected_provider_id: str,
        provider_id: str,
    ) -> None:
        if (
            selected_provider_id
            not in {VOICE_ENGINE_AZURE, VOICE_ENGINE_AZURE_HD}
            or provider_id == selected_provider_id
        ):
            return
        fallback_available = (
            self.speech_providers.fallback_provider_id(selected_provider_id)
            is not None
        )
        message_key = (
            "azure_fallback_missing_settings"
            if fallback_available
            else "azure_missing_no_local_fallback"
        )
        default_message = (
            "所選 Azure 語音尚未完成設定；已直接使用可用的備援"
            "語音，未送出該項雲端請求。"
            if fallback_available
            else "Azure Speech 尚未完成設定，且此平台沒有已驗證的"
            "本機語音；本次不會播放，也不會送出雲端請求。"
        )
        self.dashboard.set_api_status(
            ui_text(
                str(self.db.setting("ui_language", "zh-TW")),
                message_key,
                default_message,
            )
        )

    def _speech_voice_and_key(
        self,
        provider_id: str,
        credentials: SpeechCredentials,
    ) -> tuple[str, str]:
        if provider_id == VOICE_ENGINE_SYSTEM:
            voice = str(self.db.setting("windows_voice", ""))
            api_key = ""
        elif provider_id == VOICE_ENGINE_AZURE:
            voice = str(self.db.setting("azure_speech_voice", ""))
            api_key = credentials.azure_api_key
        elif provider_id == VOICE_ENGINE_AZURE_HD:
            voice = str(self.db.setting("azure_hd_speech_voice", ""))
            api_key = credentials.azure_hd_api_key
        else:
            voice = str(
                self.db.setting(
                    "tts_voice",
                    self.db.setting("cloud_voice", "coral"),
                )
            )
            api_key = credentials.openai_api_key
        return voice, api_key

    def preview_voice(self) -> None:
        language = profile_setting(self.db, "ui_language")
        if is_english(language):
            self.speak(
                f"{profile_setting(self.db, 'user_title')}, I am here. "
                "There is no need to look so surprised.",
                "happy",
            )
            return
        if is_simplified_chinese(language):
            self.speak(
                f"{profile_setting(self.db, 'user_title')}，妾在。"
                "今日的安排，交给妾与你一同理清。",
                "happy",
            )
            return
        if is_japanese(language):
            self.speak(
                f"{profile_setting(self.db, 'user_title')}、妾はここにおります。"
                "今日の予定も、ともに整えてまいりましょう。",
                "happy",
            )
            return
        self.speak(
            f"{profile_setting(self.db, 'user_title')}，妾在。"
            "今日的安排，交給妾與你一同理清。",
            "happy",
        )

    def _apply_voice_volume(
        self,
        volume_percent: int,
        muted: bool,
    ) -> None:
        engines = [self.tts, self.cloud_tts, self.realtime]
        if self.azure_tts is not None:
            engines.append(self.azure_tts)
        if self.azure_hd_tts is not None:
            engines.append(self.azure_hd_tts)
        if self.realtime_speech_output is not None:
            engines.append(self.realtime_speech_output)
        for engine in engines:
            engine.set_volume(volume_percent, muted)

    def _recent_realtime_context(
        self,
        transcription_prompt: str,
    ) -> str:
        safe_prompt = (
            sanitize_realtime_transcription_prompt(transcription_prompt)
        )
        labels = {
            "user": profile_setting(self.db, "user_title"),
            "assistant": profile_setting(self.db, "assistant_name"),
        }
        lines = []
        for row in self.db.recent_chat(16):
            role = str(row["role"])
            content = str(row["content"]).strip()
            if not content or role not in labels:
                continue
            if (
                role == "user"
                and resembles_transcription_prompt(
                    content,
                    transcription_prompt,
                    safe_prompt,
                )
            ):
                continue
            lines.append(f"{labels[role]}：{content}")
        return "\n".join(lines)[-5000:]

    def _configure_realtime_speech_output(self, mode: str) -> None:
        output = self.realtime_speech_output
        if output is None:
            if mode == REALTIME_OUTPUT_OPENAI:
                return
            raise RuntimeError(
                ui_text(
                    profile_setting(self.db, "ui_language"),
                    "realtime_output_unavailable",
                    "Realtime Azure 語音輸出服務尚未建立，未啟動即時對話。",
                )
            )
        credentials = self._speech_credentials()
        output.configure(
            self.presentation_ports.realtime_output_config_factory(
                RealtimeSpeechOutputConfigRequest(
                    mode=mode,
                    locale=profile_setting(self.db, "ui_language"),
                    azure=AzureRealtimeVoice(
                        credentials.azure_api_key,
                        credentials.azure_region,
                        str(self.db.setting("azure_speech_voice", "")),
                    ),
                    azure_hd=AzureRealtimeVoice(
                        credentials.azure_hd_api_key,
                        credentials.azure_hd_region,
                        str(self.db.setting("azure_hd_speech_voice", "")),
                    ),
                    local=LocalRealtimeVoice(
                        available=bool(
                            self.platform_services.capabilities.system_local_speech
                            and self.db.setting("windows_voice", "")
                        ),
                        voice=str(self.db.setting("windows_voice", "")),
                        rate=int(self.db.setting("voice_rate", -1)),
                    ),
                ),
            )
        )

    def toggle_realtime(self, enabled: bool) -> None:
        if not enabled:
            self._stop_realtime_output()
            self.dashboard.set_realtime_status(
                ui_text(
                    profile_setting(self.db, "ui_language"),
                    "realtime_disconnected_status",
                    "未連線",
                ),
                False,
            )
            return
        self.dashboard.cancel_ai_wait_expression()
        self.dashboard.save_voice_settings(silent=True)
        voice_prompt = str(
            self.db.setting(
                "voice_instructions",
                VOICE_GENERATION_PROMPT,
            )
        ).strip() or VOICE_GENERATION_PROMPT
        transcription_prompt = str(
            self.db.setting(
                "transcription_prompt",
                DEFAULT_TRANSCRIPTION_PROMPT,
            )
        )
        output_mode = str(
            self.db.setting(
                "realtime_output_mode",
                REALTIME_OUTPUT_OPENAI,
            )
        )
        try:
            self._configure_realtime_speech_output(output_mode)
        except (RuntimeError, ValueError) as exc:
            language = profile_setting(self.db, "ui_language")
            safe_message = safe_error_message(language, exc)
            self.dashboard.set_realtime_status(
                ui_text(
                    language,
                    "realtime_error_status",
                    "錯誤：{error}",
                    error=safe_message,
                ),
                False,
            )
            QMessageBox.warning(
                self.dashboard,
                ui_text(
                    language,
                    "realtime_voice_title",
                    "Realtime 語音",
                ),
                safe_message,
            )
            return
        self.realtime.start(
            RealtimeVoiceRequest(
                api_key=self.secret_store.load(),
                instructions=(
                    persona_for_profile(self.db)
                    + "\n\n## 語音生成指示\n"
                    + voice_prompt
                    + f"\n目前模式：{self.dashboard.mode}模式。"
                    + "\n助理名稱："
                    + profile_setting(self.db, "assistant_name")
                    + "。稱呼使用者為："
                    + profile_setting(self.db, "user_title")
                    + "。回覆語言／地區："
                    + profile_setting(self.db, "ui_language")
                    + "。"
                    + response_language_instruction(
                        profile_setting(self.db, "ui_language")
                    )
                ),
                memory_context=self.db.memory_context(),
                recent_context=self._recent_realtime_context(
                    transcription_prompt
                ),
                echo_guard=bool(
                    self.db.setting("realtime_echo_guard", True)
                ),
                session=RealtimeSessionConfig(
                    model=str(
                        self.db.setting(
                            "realtime_model",
                            "gpt-realtime-2.1-mini",
                        )
                    ),
                    voice=str(
                        self.db.setting("realtime_voice", "coral")
                    ),
                    transcription_model=str(
                        self.db.setting(
                            "realtime_transcription_model",
                            "gpt-4o-mini-transcribe",
                        )
                    ),
                    transcription_language=str(
                        self.db.setting(
                            "transcription_language",
                            "zh",
                        )
                    ),
                    transcription_prompt=transcription_prompt,
                    noise_reduction=str(
                        self.db.setting(
                            "realtime_noise_reduction",
                            "near_field",
                        )
                    ),
                    turn_detection=str(
                        self.db.setting(
                            "realtime_turn_detection",
                            "server_vad",
                        )
                    ),
                    external_transcription=bool(
                        self.db.setting(
                            "realtime_hybrid_transcription",
                            True,
                        )
                    ),
                    output_mode=str(
                        output_mode
                    ),
                    locale=profile_setting(self.db, "ui_language"),
                ),
            ),
        )

    def _apply_realtime_voice_change(self, _voice: str) -> None:
        if not self.realtime.running:
            return
        self.toggle_realtime(False)
        self.toggle_realtime(True)

    def _refresh_realtime_output_settings(self) -> None:
        if not self.realtime.running:
            return
        mode = str(
            self.db.setting("realtime_output_mode", REALTIME_OUTPUT_OPENAI)
        )
        if mode != REALTIME_OUTPUT_OPENAI:
            self._configure_realtime_speech_output(mode)

    def _realtime_status(self, status: str) -> None:
        self.dashboard.set_realtime_status(status, self.realtime.running)

    def _realtime_user_text(self, text: str) -> None:
        text = text.strip()
        wake_word = profile_setting(self.db, "wake_word")
        clean = text.replace(wake_word, "", 1).strip() or text
        self._note_human_interaction()
        self.db.log_chat("user", clean)
        self.dashboard.append_chat(
            profile_setting(self.db, "user_title"), clean
        )
        self.dashboard.capture_explicit_memory(clean)
        self._observe_personality_mirror()
        self._handle_realtime_local_command(clean)

    def _handle_realtime_local_command(self, text: str) -> None:
        if is_start_work_command(text):
            self.db.start_work()
            self.dashboard.refresh_work_time()
        elif is_stop_work_command(text):
            self.db.stop_work()
            self.dashboard.refresh_work_time()
        elif "幫我記一下" in text:
            content = text.split("幫我記一下", 1)[1].lstrip("：:，, ").strip()
            if content:
                if any(word in content for word in ("靈感", "點子", "構想")):
                    self.db.add_idea(content)
                    self.dashboard.refresh_ideas()
                else:
                    self.db.add_todo(content, "其他")
                    self.dashboard.refresh_todos()
        elif "開啟工作室資料夾" in text:
            self.dashboard.open_work_folder()
        elif "開啟" in text:
            for platform in (
                row["platform"] for row in self.db.platform_rows()
            ):
                if platform.lower() in text.lower():
                    self.dashboard.open_platform(platform)
                    break

    def _realtime_assistant_text(self, text: str) -> None:
        tagged = parse_internal_emotion(text)
        text = tagged.text.strip()
        if not text:
            return
        self.db.log_chat("assistant", text)
        self.dashboard.append_chat(
            profile_setting(self.db, "assistant_name"), text
        )
        reply_expression = (
            tagged.expression
            if tagged.valid_tag and tagged.expression is not None
            else self.dashboard.reply_expression(text)
        )
        self.realtime_after_speech_intensity = tagged.intensity
        # "speaking" is a mouth-animation state, not a valid expression after
        # playback. A neutral reply must return to the current idle pose.
        self.realtime_after_speech_state = (
            "idle" if reply_expression == "speaking" else reply_expression
        )
        self._show_bubble(text)
        QTimer.singleShot(3200, self.bubble.hide)

    def _realtime_speaking(self, speaking: bool) -> None:
        if self._closing:
            return
        if speaking:
            self.dashboard.cancel_ai_wait_expression()
            self.speech_gesture_expression = None
            self.realtime_mouth_active = True
            # Never carry an emotion selected for the preceding answer into a
            # new turn. The transcript may replace this with the new emotion.
            self.realtime_after_speech_state = "idle"
            self.realtime_after_speech_intensity = 0.5
            realtime_provider_id = (
                str(
                    self.db.setting(
                        "realtime_output_mode",
                        REALTIME_OUTPUT_OPENAI,
                    )
                ).strip()
                or REALTIME_OUTPUT_OPENAI
            )
            self._prepare_speech_performance(realtime_provider_id)
            self.realtime_finish_timer.stop()
            self.expression_generation += 1
            self.state = "speaking"
            self.expression_arbiter.request(
                "speaking",
                source="conversation",
                force=True,
            )
            self.speech_pose_suffix = (
                "_lean"
                if self.idle_pose == "lean"
                else "_front"
                if self.idle_pose == "front"
                else ""
            )
            self.speech_closed_expression = (
                self._closed_speech_expression()
            )
            self.speech_mid_expression = self._mouth_mid_expression()
            self.speech_open_expression = self._speaking_expression()
            self._start_mouth_animation(audio_driven=True)
        else:
            is_realtime_mouth = (
                self.realtime_mouth_active
                or (
                    self.state == "speaking"
                    and self.audio_driven_mouth
                    and not self.speech_playing
                )
            )
            self.realtime_mouth_active = False
            if not is_realtime_mouth:
                return
            self._record_speech_performance(
                self.speech_performance.final_audio()
            )
            self._begin_speech_motion_release()
            if self.realtime_finish_timer.isActive():
                return
            if (
                self.audio_driven_mouth
                and self.current_expression
                != self.speech_closed_expression
            ):
                self.mouth_closing = True
                self.viseme_dynamics.current = "CLOSED"
                self.mouth_open = False
                self.speech_current_expression = (
                    self.speech_closed_expression
                )
                self._queue_audio_mouth_transition(
                    self.speech_closed_expression
                )
                self.realtime_finish_timer.start(
                    MOUTH_CLOSE_DEADLINE_MS
                )
            else:
                self._complete_realtime_speaking_stop()

    def _complete_realtime_speaking_stop(self) -> None:
        self.realtime_finish_timer.stop()
        was_realtime_speaking = (
            self.state == "speaking"
            and self.audio_driven_mouth
            and not self.speech_playing
        )
        if not was_realtime_speaking:
            self.realtime_mouth_active = False
            if self.audio_driven_mouth or self.mouth_visual_timer.isActive():
                self._stop_mouth_animation()
            self._record_speech_performance(
                self.speech_performance.mouth_closed()
            )
            return
        if self._wait_for_speech_motion_release(
            self.realtime_finish_timer,
            "realtime_motion_release_attempts",
        ):
            return
        self.realtime_mouth_active = False
        if self.audio_driven_mouth or self.mouth_visual_timer.isActive():
            self._stop_mouth_animation()
        self._record_speech_performance(
            self.speech_performance.mouth_closed()
        )
        final_state = self.realtime_after_speech_state
        self.realtime_after_speech_state = "idle"
        if (
            final_state == "speaking"
            or final_state.startswith(
                (
                    "mouth_",
                    "viseme_",
                    "blink_open",
                    "blink_mid",
                    "blink_wide",
                    "blink_round",
                    "blink_i",
                    "blink_o",
                )
            )
            or final_state not in self.expression_pixmaps
        ):
            final_state = "idle"
        final_intensity = getattr(
            self,
            "realtime_after_speech_intensity",
            0.5,
        )
        self.set_state(
            final_state,
            source="ai_tag",
            intensity=final_intensity,
            force=True,
            animate_gesture=False,
        )
        if final_state != "idle":
            self._schedule_return_to_idle(
                self.expression_arbiter.hold_duration(
                    final_state,
                    final_intensity,
                ),
                final_state,
            )

    def _realtime_failed(self, message: str) -> None:
        language = profile_setting(self.db, "ui_language")
        safe_message = safe_error_message(language, message)
        self._stop_realtime_output()
        self.dashboard.set_realtime_status(
            ui_text(
                language,
                "realtime_error_status",
                "錯誤：{error}",
                error=safe_message,
            ),
            False,
        )
        QMessageBox.warning(
            self.dashboard,
            ui_text(
                language,
                "realtime_voice_title",
                "Realtime 語音",
            ),
            safe_message,
        )

    def _stop_realtime_output(self) -> None:
        barrier = self.realtime.stop()
        if self.realtime_speech_output is not None:
            self.realtime_speech_output.cancel(barrier)

    def _cloud_voice_failed(self, message: str) -> None:
        self._online_voice_failed(
            VOICE_ENGINE_OPENAI,
            "OpenAI 語音",
            message,
        )

    def _azure_voice_failed(self, message: str) -> None:
        self._online_voice_failed(
            VOICE_ENGINE_AZURE,
            "Azure Speech",
            message,
        )

    def _azure_hd_voice_failed(self, message: str) -> None:
        self._online_voice_failed(
            VOICE_ENGINE_AZURE_HD,
            "Azure Dragon HD",
            message,
        )

    def _online_voice_failed(
        self,
        failed_provider_id: str,
        provider_label: str,
        message: str,
    ) -> None:
        # Track consecutive failures so a repeatedly failing provider is
        # proactively demoted on the next synthesis request.
        with contextlib.suppress(AttributeError, LookupError):
            self.speech_providers.record_failure(failed_provider_id)
        language = profile_setting(self.db, "ui_language")
        safe_message = safe_error_message(language, message)
        credentials = self._speech_credentials()
        configured = set(self._configured_speech_providers(credentials))
        candidates = (
            (VOICE_ENGINE_AZURE, VOICE_ENGINE_SYSTEM)
            if failed_provider_id == VOICE_ENGINE_AZURE_HD
            else (VOICE_ENGINE_SYSTEM,)
        )
        fallback_provider_id = next(
            (
                provider_id
                for provider_id in candidates
                if provider_id in configured
                and provider_id not in self.speech_fallback_attempts
            ),
            None,
        )
        if fallback_provider_id is not None:
            fallback_label = (
                "Azure Speech"
                if fallback_provider_id == VOICE_ENGINE_AZURE
                else f"{self.platform_services.capabilities.display_name} 本機女聲"
            )
            self.dashboard.set_api_status(
                f"{provider_label}失敗，已切換 {fallback_label}："
                f"{safe_message}"
            )
        else:
            self.dashboard.set_api_status(
                f"{provider_label}失敗；此平台沒有已驗證的本機語音備援："
                f"{safe_message}"
            )
        if (
            self.speech_playing
            and self.active_speech_engine == failed_provider_id
            and self.active_speech_text.strip()
        ):
            if fallback_provider_id is None:
                self._speech_audio_finished()
                return
            self.cloud_fallback_active = True
            self.active_speech_engine = fallback_provider_id
            self.speech_fallback_attempts.add(fallback_provider_id)
            voice, api_key = self._speech_voice_and_key(
                fallback_provider_id,
                credentials,
            )
            self.speech_providers.provider(fallback_provider_id).speak(
                SpeechRequest(
                    text=self.active_speech_text,
                    voice=voice,
                    rate=int(self.db.setting("voice_rate", -1)),
                    api_key=api_key,
                    instructions=str(
                        self.db.setting(
                            "voice_instructions",
                            VOICE_GENERATION_PROMPT,
                        )
                    ),
                    options={
                        "region": (
                            credentials.azure_region
                            if fallback_provider_id == VOICE_ENGINE_AZURE
                            else ""
                        ),
                        "locale": str(
                            self.db.setting("ui_language", "zh-TW")
                        ),
                    },
                )
            )
            return
        self._speech_audio_finished()

    def _windows_voice_failed(self, message: str) -> None:
        with contextlib.suppress(AttributeError, LookupError):
            self.speech_providers.record_failure(VOICE_ENGINE_SYSTEM)
        platform_name = self.platform_services.capabilities.display_name
        language = profile_setting(self.db, "ui_language")
        self.dashboard.set_api_status(
            f"{platform_name} 本機語音失敗："
            f"{safe_error_message(language, message)}"
        )

    def _speech_audio_finished(self) -> None:
        if not self.speech_playing:
            return
        self._record_speech_performance(
            self.speech_performance.final_audio()
        )
        self._begin_speech_motion_release()
        if self.speech_finish_timer.isActive():
            return
        if (
            self.audio_driven_mouth
            and self.current_expression
            != self.speech_closed_expression
        ):
            self.mouth_closing = True
            self.viseme_dynamics.current = "CLOSED"
            self.mouth_open = False
            self.speech_current_expression = (
                self.speech_closed_expression
            )
            self._queue_audio_mouth_transition(
                self.speech_closed_expression
            )
            self.speech_finish_timer.start(
                MOUTH_CLOSE_DEADLINE_MS
            )
            return
        self._complete_speech_audio_finished()

    def _complete_speech_audio_finished(self) -> None:
        if not self.speech_playing:
            return
        self.speech_finish_timer.stop()
        if self._wait_for_speech_motion_release(
            self.speech_finish_timer,
            "speech_motion_release_attempts",
        ):
            return
        self._stop_mouth_animation()
        self._record_speech_performance(
            self.speech_performance.mouth_closed()
        )
        final_state = self.after_speech_state
        final_intensity = getattr(self, "after_speech_intensity", 0.5)
        self.set_state(
            final_state,
            source="conversation",
            intensity=final_intensity,
            force=True,
            animate_gesture=False,
        )
        completed_source = self.active_speech_source
        with contextlib.suppress(AttributeError, LookupError):
            self.speech_providers.record_success(self.active_speech_engine)
        self._complete_proactive_companion_speech(True)
        self.speech_playing = False
        self.active_speech_text = ""
        self.active_speech_engine = ""
        self.active_speech_source = ""
        self.cloud_fallback_active = False
        self.speech_fallback_attempts.clear()
        if self.speech_queue:
            QTimer.singleShot(120, self._start_next_speech)
        else:
            language = profile_setting(self.db, "ui_language")
            self.dashboard.set_voice_phase(
                ui_text(
                    language,
                    "voice_ready_short",
                    "準備就緒",
                )
            )
            if final_state != "idle":
                self._schedule_return_to_idle(
                    self.expression_arbiter.hold_duration(
                        final_state,
                        final_intensity,
                    ),
                    final_state,
                )
            QTimer.singleShot(
                2800,
                lambda: None if self.speech_playing else self.bubble.hide(),
            )
            if completed_source == "wardrobe-origin":
                QTimer.singleShot(120, self._wink_once)

    def _schedule_return_to_idle(
        self,
        delay_ms: int,
        expected_state: str,
    ) -> None:
        self.scheduled_expression_state = expected_state
        self.scheduled_expression_generation = self.expression_generation
        self.expression_return_timer.start(delay_ms)

    def _release_scheduled_expression(self) -> None:
        self.expression_return_timer.stop()
        expected_state = self.scheduled_expression_state
        generation = self.scheduled_expression_generation
        self.scheduled_expression_state = ""
        self.scheduled_expression_generation = 0
        self._return_to_idle_if_current(
            expected_state,
            generation,
        )

    def _return_to_idle_if_current(
        self,
        expected_state: str,
        generation: int,
    ) -> None:
        if (
            generation != self.expression_generation
            or self.state != expected_state
            or self.speech_playing
            or self.realtime_mouth_active
        ):
            return
        self.set_state("idle")

    def _return_to_idle(self) -> None:
        if (
            self.state == "speaking"
            or self.speech_playing
            or self.realtime_mouth_active
        ):
            return
        self.set_state("idle")
