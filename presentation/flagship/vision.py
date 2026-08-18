from __future__ import annotations

lazy import time
lazy from dataclasses import replace

lazy from PySide6.QtCore import Qt
lazy from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
)

lazy from application.cloud_vision_ui_bridge import CloudVisionUIResult
lazy from application.gesture_action_dispatcher import (
    GestureDispatchDisposition,
    GestureDispatchResult,
)
lazy from application.gesture_action_router import GestureActionDecision
lazy from application.vision_runtime import VisionReadiness
lazy from domain.flagship_action_models import ActionRequest
lazy from domain.gesture_configuration import GestureSource
lazy from domain.openai_vision_preferences import (
    OPENAI_VISION_MODELS,
    OpenAIVisionPreferences,
    VisionDetail,
    VisionTriggerPolicy,
)
lazy from domain.safe_error_localization import safe_error_message
lazy from domain.vision_domain import SceneUnderstanding
lazy from presentation.flagship.shared import (
    _VISION_HEALTH_TEXTS,
    CORE_PERMISSION_LABELS,
    GESTURE_PERMISSION_CAPABILITIES,
)

__all__ = ('FlagshipVisionMixin',)


class FlagshipVisionMixin:
    def _openai_vision_preference_card(
        self,
    ) -> QFrame:
        preferences = self._openai_vision_draft.value
        card = QFrame()
        card.setObjectName("openaiVisionPreferenceCard")
        card.setStyleSheet(
            "QFrame#openaiVisionPreferenceCard{background:#f7f5ff;"
            "border:1px solid #cfc5e8;border-radius:12px;padding:8px;}"
        )
        form = QFormLayout(card)
        heading = QLabel(self._t("<b>OpenAI 雲端視覺理解</b>"))
        heading.setStyleSheet("color:#5c4b8a;font-size:16px;")
        form.addRow(heading)
        note = QLabel(
            self._t(
                "公開版預設關閉。每次送出單幀前仍須明確同意；"
                "本機 OpenCV 不受此設定影響。"
            )
        )
        note.setWordWrap(True)
        form.addRow(note)

        self.openai_vision_enabled = self._preference_checkbox(
            self._t("啟用視覺理解偏好"), preferences.enabled
        )
        self.openai_cloud_vision_enabled = self._preference_checkbox(
            self._t("允許雲端視覺持續運作"),
            preferences.cloud_vision_enabled,
        )
        self.openai_vision_object_semantics = self._preference_checkbox(
            self._t("允許物品與場景語意理解"),
            preferences.object_semantics_enabled,
        )
        self.openai_vision_web_suggestions = self._preference_checkbox(
            self._t("允許提出網路查詢建議（絕不自動上網）"),
            preferences.web_search_suggestions_enabled,
        )
        form.addRow(self.openai_vision_enabled)
        form.addRow(self.openai_cloud_vision_enabled)

        self.openai_vision_model = QComboBox()
        for model in OPENAI_VISION_MODELS:
            self.openai_vision_model.addItem(model.label, model.model_id)
        self._select_combo_data(self.openai_vision_model, preferences.model_id)
        self.openai_vision_model.setAccessibleName(self._t("視覺模型"))

        self.openai_vision_detail = QComboBox()
        for value, label in (
            (VisionDetail.LOW, "低"),
            (VisionDetail.AUTO, "自動"),
            (VisionDetail.HIGH, "高"),
            (VisionDetail.ORIGINAL, "原始細節"),
        ):
            self.openai_vision_detail.addItem(self._t(label), value.value)
        self._select_combo_data(
            self.openai_vision_detail, preferences.detail.value
        )
        self.openai_vision_detail.setAccessibleName(self._t("影像細節"))

        self.openai_vision_trigger = QComboBox()
        for value, label in (
            (VisionTriggerPolicy.MANUAL, "僅手動"),
            (
                VisionTriggerPolicy.EVENT_WITH_NOTICE,
                "事件需要時（依持續授權與用量限制）",
            ),
        ):
            self.openai_vision_trigger.addItem(self._t(label), value.value)
        self._select_combo_data(
            self.openai_vision_trigger, preferences.trigger_policy.value
        )
        self.openai_vision_trigger.setAccessibleName(self._t("觸發策略"))

        self.openai_vision_daily_limit = self._vision_limit_control(
            self._t("每日分析上限"), 1, 1000, preferences.daily_limit
        )
        self.openai_vision_per_minute_limit = self._vision_limit_control(
            self._t("每分鐘分析上限"),
            1,
            60,
            preferences.per_minute_limit,
        )
        form.addRow(self._t("視覺模型"), self.openai_vision_model)
        form.addRow(self._t("影像細節"), self.openai_vision_detail)
        form.addRow(self._t("觸發策略"), self.openai_vision_trigger)
        form.addRow(
            self._t("每日分析上限"), self.openai_vision_daily_limit
        )
        form.addRow(
            self._t("每分鐘分析上限"),
            self.openai_vision_per_minute_limit,
        )
        form.addRow(self.openai_vision_object_semantics)
        form.addRow(self.openai_vision_web_suggestions)
        privacy = QLabel(
            self._t("✓ 原始影像不保存；設定檔不包含 API Key。")
        )
        privacy.setWordWrap(True)
        privacy.setAccessibleName(self._t("雲端視覺隱私保護"))
        form.addRow(privacy)
        authorization_note = QLabel(
            self._t(
                "啟用並保存後會依所選事件與用量限制持續運作，直到你關閉；"
                "可能產生成本，原始影像不保存，也不會自動上網。"
            )
        )
        authorization_note.setWordWrap(True)
        form.addRow(authorization_note)
        self.openai_vision_status = QLabel()
        self.openai_vision_status.setWordWrap(True)
        self.openai_vision_status.setAccessibleName(self._t("雲端視覺狀態"))
        self.openai_vision_status.setStyleSheet(
            "padding:6px;border-radius:8px;background:#ece9f6;color:#44386a;"
        )
        self.openai_vision_stop_button = QPushButton(
            self._t("立即關閉雲端視覺")
        )
        self.openai_vision_stop_button.setAccessibleName(
            self._t("立即關閉雲端視覺")
        )
        self.openai_vision_stop_button.clicked.connect(
            self.stop_openai_vision_immediately
        )
        actions = QHBoxLayout()
        actions.addWidget(self.openai_vision_stop_button)
        actions.addStretch(1)
        form.addRow(self.openai_vision_status)
        form.addRow(actions)
        self._refresh_openai_vision_status(preferences)
        return card
    def stop_openai_vision_immediately(self) -> None:
        """Persist revocation immediately and tell any runtime to stop."""

        saved = self.openai_vision_store.load()
        disabled = replace(
            saved,
            enabled=False,
            cloud_vision_enabled=False,
        )
        self.openai_vision_store.save(disabled)
        self.openai_vision_enabled.setChecked(False)
        self.openai_cloud_vision_enabled.setChecked(False)
        self._openai_vision_draft = self.openai_vision_store.begin_edit()
        self._refresh_openai_vision_status(disabled)
        if self.cloud_vision_service is not None:
            self.cloud_vision_service.cancel()
        self.openai_vision_stop_requested.emit()
    def _submit_cloud_vision_event_frame(
        self, rgb: bytes, width: int, height: int
    ) -> None:
        service = self.cloud_vision_service
        if service is None:
            return
        service.submit_event_rgb(rgb, width, height)
    def submit_cloud_vision_manual_frame(
        self, rgb: bytes, width: int, height: int
    ) -> bool:
        service = self.cloud_vision_service
        return bool(
            service is not None
            and service.submit_manual_rgb(rgb, width, height)
        )
    def _cloud_vision_busy_changed(self, busy: bool) -> None:
        if busy:
            self.openai_vision_status.setText(
                self._t("● 雲端視覺分析中")
            )
            return
        self._refresh_openai_vision_status(self.openai_vision_store.load())
    def _cloud_vision_result(self, result: object) -> None:
        if not isinstance(result, CloudVisionUIResult):
            self.openai_vision_status.setText(
                self._t("● 雲端視覺服務目前無法使用")
            )
            return
        if result.status.value == "success":
            self.openai_vision_status.setText(
                self._t("● 雲端視覺已完成最近一次分析")
            )
            interpretation = result.interpretation
            local_scene = self._latest_local_scene
            if (
                interpretation is not None
                and local_scene is not None
                and interpretation.operation_id > self._latest_cloud_operation_id
                and not self._closed
            ):
                try:
                    merged = self._cloud_scene_interpreter.merge(
                        local_scene,
                        local_observed_at=self._latest_local_scene_observed_at,
                        cloud=interpretation,
                    )
                except (TypeError, ValueError):
                    return
                self._latest_cloud_operation_id = interpretation.operation_id
                self.visual_scene_changed.emit(merged.scene)
        else:
            self.openai_vision_status.setText(
                self._t("● 雲端視覺暫時未完成分析")
            )
    def _refresh_openai_vision_status(
        self, preferences: OpenAIVisionPreferences
    ) -> None:
        active = preferences.enabled and preferences.cloud_vision_enabled
        if active and self._openai_vision_has_key():
            source = "● 雲端視覺持續授權中"
        elif active:
            source = "● 已啟用，但尚無可用的 OpenAI 金鑰"
        else:
            source = "○ 雲端視覺已關閉"
        self.openai_vision_status.setText(self._t(source))
        self.openai_vision_stop_button.setEnabled(active)
    def _openai_vision_has_key(self) -> bool:
        try:
            if self._openai_vision_key_probe is not None:
                return self._openai_vision_key_probe() is True
            return bool(self.openai_secret.load().strip())
        except Exception:  # noqa: BLE001 -- external status boundary fails closed
            return False
    @staticmethod
    def _vision_limit_control(
        accessible_name: str, minimum: int, maximum: int, value: int
    ) -> QSpinBox:
        control = QSpinBox()
        control.setRange(minimum, maximum)
        control.setValue(value)
        control.setAccessibleName(accessible_name)
        return control
    def apply_camera_settings(self) -> None:
        enabled = self.camera_enabled.isChecked()
        if not enabled:
            if self.cloud_vision_service is not None:
                self.cloud_vision_service.cancel()
            self.camera_presence.stop()
            self.vision_controller.stop()
            self.multimodal_controller.configure(enabled=False)
            if self._gesture_controller is not None:
                self._gesture_controller.stop()
            self.camera_presence.configure_gesture_sampling(False)
            self.face_identity.setEnabled(False)
            self.local_perception_status.setText(
                self._t("本機臉部、虹膜與手勢模型尚未啟動")
            )
            self.db.set_setting("camera_presence_enabled", False)
            self.db.set_setting("face_identity_enabled", False)
            return
        decision = self.policy.evaluate(
            ActionRequest(
                "camera_view",
                "啟用本機攝影機在場偵測",
            )
        )
        if not decision.allowed:
            self.camera_enabled.setChecked(False)
            QMessageBox.information(
                self,
                self._t("攝影機權限"),
                self._t(
                    "安全政策已阻擋：{reason}",
                    reason=self._system_text(decision.reason),
                ),
            )
            return
        if (
            QMessageBox.question(
                self,
                self._t("啟用攝影機"),
                self._t(
                    "墨寒會在本機分析在場狀態、臉部與眼神特徵、手勢及"
                    "場景線索；不保存原始影像、不傳送雲端，未登錄的人物"
                    "不會建立身分。是否啟用？"
                ),
            )
            != QMessageBox.Yes
        ):
            self.camera_enabled.setChecked(False)
            return
        try:
            # The presence/gesture pipeline must never be held hostage by
            # face-recognition readiness (cv2 FaceDetectorYN/FaceRecognizerSF
            # plus three exactly-matched ONNX models).  A webcam that reports
            # video inputs is enough to start presence detection and gesture
            # sampling; vision readiness only gates face/scene analysis.
            if not self.camera_presence.available():
                raise RuntimeError("camera-unavailable")
            health = self.vision_controller.configure(
                enabled=True,
                camera_available=True,
            )
            self.multimodal_controller.configure(enabled=True)
            self.camera_presence.start()
            self._configure_gesture_runtime()
        except RuntimeError as exc:
            self.camera_enabled.setChecked(False)
            self.camera_status.setText(
                self._t(
                    "攝影機啟動失敗：{error}",
                    error=safe_error_message(self.language, exc),
                )
            )
            return
        self.db.set_setting("camera_presence_enabled", True)
        self.face_identity.setEnabled(health.ready)
        self.db.set_setting(
            "face_identity_enabled",
            self.face_identity.isChecked(),
        )
    def _restore_camera_if_enabled(self) -> None:
        if self._closed:
            return
        if not self.camera_enabled.isChecked():
            return
        try:
            if not self.camera_presence.available():
                return
            health = self.vision_controller.configure(
                enabled=True,
                camera_available=True,
            )
            self.multimodal_controller.configure(enabled=True)
            self.camera_presence.start()
            self.face_identity.setEnabled(health.ready)
            self._configure_gesture_runtime()
        except RuntimeError as exc:
            self.camera_status.setText(
                self._t(
                    "攝影機啟動失敗：{error}",
                    error=safe_error_message(self.language, exc),
                )
            )
    def _configure_gesture_runtime(self) -> None:
        controller = self._gesture_controller
        if controller is None:
            self.camera_presence.configure_gesture_sampling(False)
            return
        health = controller.configure(
            self.gesture_store.load(),
            camera_available=self.camera_presence.available(),
            perception_enabled=self.camera_enabled.isChecked(),
        )
        self.camera_presence.configure_gesture_sampling(health.ready)
        self._gesture_health_changed(health)
    def authorize_gesture_action(self, decision: GestureActionDecision) -> bool:
        """Apply the established persisted policy to permission-bound gestures."""

        if not isinstance(decision, GestureActionDecision):
            return False
        capability = GESTURE_PERMISSION_CAPABILITIES.get(decision.action)
        if capability is None:
            return False
        description = self._t(CORE_PERMISSION_LABELS[capability])
        request = ActionRequest(
            capability,
            description,
            {"gesture_id": decision.gesture_id},
            source="local",
            reversible=True,
        )
        policy_decision = self.policy.evaluate(request)
        allowed = policy_decision.allowed and all(
            self._confirm_action(request, policy_decision, index)
            for index in range(1, policy_decision.confirmation_count + 1)
        )
        self.db.audit_event(
            "gesture_authorization",
            {
                "gesture_id": decision.gesture_id,
                "action": decision.action.value,
                "capability": capability,
                "allowed": allowed,
                "reason": policy_decision.reason,
            },
        )
        return allowed
    def _gesture_health_changed(self, health: object) -> None:
        if not hasattr(self, "gesture_record_status"):
            return
        ready = bool(getattr(health, "ready", False))
        status = str(getattr(getattr(health, "status", ""), "value", ""))
        message = {
            "ready": "手勢辨識已就緒；不保存照片或影像。",
            "camera-unavailable": "攝影機尚未就緒，手勢互動保持停用。",
            "model-missing": "手部模型缺失，手勢互動保持停用。",
            "model-load-failed": "手部模型無法載入，手勢互動保持停用。",
            "inference-failed": "手勢辨識連續失敗，已安全停用。",
        }.get(status, "手勢互動目前未啟用。")
        self.gesture_record_status.setText(self._t(message))
        selected = self._selected_gesture()
        self.gesture_record_button.setEnabled(
            ready
            and selected is not None
            and selected.source is GestureSource.CUSTOM
        )
    def _gesture_dispatch_completed(self, result: object) -> None:
        if not isinstance(result, GestureDispatchResult):
            return
        self.db.audit_event(
            "gesture_dispatch",
            {
                "action": result.action.value,
                "disposition": result.disposition.value,
                "reason": result.reason_code,
            },
        )
        if result.disposition is GestureDispatchDisposition.EXECUTED:
            return
        self.gesture_record_status.setText(
            self._t(
                {
                    GestureDispatchDisposition.CONFIRMATION_REQUIRED: (
                        "此手勢需要既有權限確認，尚未執行。"
                    ),
                    GestureDispatchDisposition.DENIED: "此手勢已由安全權限阻擋。",
                    GestureDispatchDisposition.FAILED: "手勢動作執行失敗，未變更其他功能。",
                }.get(result.disposition, "手勢未觸發任何動作。")
            )
        )
    def enroll_face_identity(self) -> None:
        if not self.camera_enabled.isChecked() or not self.face_identity.isChecked():
            QMessageBox.information(
                self,
                self._t("臉部身分登錄"),
                self._t("請先啟用靈視與臉部身分辨識。"),
            )
            return
        display_name, accepted = self._simple_text_dialog(
            self._t("臉部身分登錄"),
            self._t("墨寒辨識到你時使用的稱呼"),
        )
        if not accepted:
            return
        try:
            self.vision_controller.begin_enrollment(display_name)
        except (RuntimeError, ValueError) as exc:
            self.camera_status.setText(
                self._t("無法開始臉部登錄：{error}", error=safe_error_message(self.language, exc))
            )
    def clear_face_identities(self) -> None:
        if QMessageBox.question(
            self,
            self._t("刪除全部臉部身分"),
            self._t("這會刪除本機加密的臉部特徵，且無法復原。是否繼續？"),
        ) != QMessageBox.Yes:
            return
        self.face_identities.clear()
        self._refresh_face_profiles()
        self.camera_status.setText(self._t("已刪除全部臉部身分。"))
    def _refresh_face_profiles(self) -> None:
        self.face_profile_list.clear()
        try:
            profiles = self.face_identities.profiles()
        except (RuntimeError, ValueError):
            profiles = ()
        for profile in profiles:
            item = QListWidgetItem(profile.display_name)
            item.setData(Qt.UserRole, profile.profile_id)
            self.face_profile_list.addItem(item)
    def delete_selected_face_identity(self) -> None:
        selected = self.face_profile_list.currentItem()
        if selected is None:
            return
        if QMessageBox.question(
            self,
            self._t("刪除選取的臉部身分"),
            self._t("這會刪除選取的本機加密臉部特徵。是否繼續？"),
        ) != QMessageBox.Yes:
            return
        self.face_identities.delete(str(selected.data(Qt.UserRole)))
        self._refresh_face_profiles()
    def _vision_health_changed(self, health) -> None:
        if self._closed:
            return
        messages = _VISION_HEALTH_TEXTS.get(health.readiness)
        if messages is None:
            messages = _VISION_HEALTH_TEXTS[VisionReadiness.RUNTIME_ERROR]
        self.camera_status.setText(messages.get(self.language, messages["zh-TW"]))

    def _face_mesh_health_changed(self, ready: bool, _reason: str) -> None:
        if self._closed or not hasattr(self, "local_perception_status"):
            return
        self.local_perception_status.setText(
            self._t(
                "本機臉部、虹膜與手勢模型已就緒"
                if ready
                else "本機細緻臉部與虹膜模型無法使用；其餘功能維持運作"
            )
        )
    def _vision_scene_changed(self, scene) -> None:
        if self._closed:
            return
        if isinstance(scene, SceneUnderstanding):
            self._latest_local_scene = scene
            self._latest_local_scene_observed_at = time.monotonic()
        self.visual_scene_changed.emit(scene)
    def _enrollment_progress(self, current: int, total: int) -> None:
        if self._closed:
            return
        self.camera_status.setText(
            self._t("正在登錄臉部：{current}/{total}", current=current, total=total)
        )
    def _enrollment_completed(self, name: str) -> None:
        if self._closed:
            return
        self._refresh_face_profiles()
        self.camera_status.setText(self._t("已完成 {name} 的臉部登錄。", name=name))
    def _enrollment_failed(self, _reason: str) -> None:
        if self._closed:
            return
        self.camera_status.setText(self._t("請讓畫面中只出現一張清楚的正面臉孔。"))
    def _camera_status_changed(self, status: str) -> None:
        if self._closed:
            return
        if hasattr(self, "camera_status"):
            self.camera_status.setText(self._camera_status_text(status))
    def _camera_status_text(self, status: str) -> str:
        value = str(status)
        if value == "攝影機已關閉":
            return self._t("攝影機已關閉")
        if value.startswith("攝影機錯誤："):
            return self._t(
                "攝影機錯誤：{error}",
                error=value.removeprefix("攝影機錯誤："),
            )
        prefix = "攝影機使用中："
        source_suffix = "（僅本機在場偵測）"
        if value.startswith(prefix) and value.endswith(source_suffix):
            return self._t(
                "攝影機使用中：{device}（本機多感知分析）",
                device=value[len(prefix) : -len(source_suffix)],
            )
        return value
    def _presence_changed(self, present: bool) -> None:
        if self._closed:
            return
        self.db.set_setting("camera_presence_state", bool(present))
        if hasattr(self, "camera_status"):
            base = self.camera_status.text().split("｜", 1)[0]
            self.camera_status.setText(
                self._t(
                    "{base}｜偵測到有人在場" if present else "{base}｜暫未偵測到在場",
                    base=base,
                )
            )
