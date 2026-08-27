from __future__ import annotations

lazy import queue
lazy from typing import Any

lazy from PySide6.QtCore import QBuffer, QByteArray, QIODevice, Qt
lazy from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QWidget,
)

lazy from domain.safe_error_localization import safe_error_message
lazy from domain.time_utils import local_wall_time
lazy from integrations.remote_control import (
    RemoteControlServer,
    RemoteServerConfig,
    RemoteServerServices,
    TokenRegistry,
)

__all__ = ('FlagshipRemoteMixin',)


class FlagshipRemoteMixin:
    def _remote_port_control(self) -> QWidget:
        self.remote_port = QSpinBox()
        self.remote_port.setRange(1024, 65535)
        self.remote_port.setValue(int(self.db.setting("remote_port", 8765)))
        self.remote_port.setButtonSymbols(QAbstractSpinBox.NoButtons)
        port_control = QWidget()
        port_line = QHBoxLayout(port_control)
        port_line.setContentsMargins(0, 0, 0, 0)
        port_line.setSpacing(0)
        self.remote_port_up = QPushButton("▲")
        self.remote_port_down = QPushButton("▼")
        for button, tooltip in (
            (self.remote_port_up, self._t("增加連線埠")),
            (self.remote_port_down, self._t("減少連線埠")),
        ):
            button.setFixedWidth(46)
            button.setAutoRepeat(True)
            button.setAutoRepeatDelay(350)
            button.setAutoRepeatInterval(90)
            button.setToolTip(tooltip)
        self.remote_port_up.clicked.connect(self.remote_port.stepUp)
        self.remote_port_down.clicked.connect(self.remote_port.stepDown)
        port_line.addWidget(self.remote_port, 1)
        port_line.addWidget(self.remote_port_up)
        port_line.addWidget(self.remote_port_down)
        return port_control
    def _initialize_remote_fields(self) -> None:
        self.remote_enabled = QCheckBox(self._t("啟用手機／私人網路遠端服務"))
        self.remote_host = QComboBox()
        self.remote_host.addItem(
            self._t("僅本機測試（127.0.0.1）"),
            "127.0.0.1",
        )
        self.remote_host.addItem(
            self._t("私人網路／Tailscale（0.0.0.0）"),
            "0.0.0.0",
        )
        self.remote_trusted = QCheckBox(
            self._t("我確認已使用 Tailscale、Home Assistant Cloud 或其他加密私人網路")
        )
        self.remote_commands = QCheckBox(self._t("允許傳送文字指令"))
        self.remote_commands.setChecked(True)
        self.remote_screen = QCheckBox(
            self._t("允許查看墨寒程式視窗（不擷取整個桌面）")
        )
        self.remote_files = QCheckBox(self._t("允許下載白名單內的非敏感檔案"))
        self.camera_enabled = QCheckBox(self._t("啟用墨寒本機視覺感知"))
        self.face_identity = QCheckBox(
            self._t("辨識我已明確登錄的臉部身分")
        )
        self.camera_enabled.setChecked(
            bool(self.db.setting("camera_presence_enabled", False))
        )
        self.face_identity.setChecked(
            bool(self.db.setting("face_identity_enabled", False))
        )
        self.face_identity.setEnabled(self.camera_enabled.isChecked())
        self.proactive_enabled = QCheckBox(
            self._t("允許墨寒主動寒暄與關心")
        )
        self.proactive_enabled.setChecked(
            bool(self.db.setting("proactive_interaction_enabled", True))
        )
        self.proactive_mode = QComboBox()
        for label, value in (
            (self._t("安靜（不主動寒暄）"), "quiet"),
            (self._t("適度（推薦）"), "balanced"),
            (self._t("積極（較常主動關心）"), "active"),
        ):
            self.proactive_mode.addItem(label, value)
        mode_index = self.proactive_mode.findData(
            str(self.db.setting("proactive_interaction_mode", "balanced"))
        )
        self.proactive_mode.setCurrentIndex(max(0, mode_index))
        self.minimum_away_minutes = QSpinBox()
        self.minimum_away_minutes.setRange(1, 30)
        self.minimum_away_minutes.setValue(
            max(
                1,
                round(
                    float(
                        self.db.setting(
                            "multisensory_welcome_minimum_seconds", 60
                        )
                    )
                    / 60
                ),
            )
        )
        self.conversation_silence_minutes = QSpinBox()
        self.conversation_silence_minutes.setRange(10, 240)
        self.conversation_silence_minutes.setValue(
            max(
                10,
                round(
                    float(
                        self.db.setting(
                            "multisensory_conversation_silence_seconds",
                            45 * 60,
                        )
                    )
                    / 60
                ),
            )
        )
        # These four are unmounted value holders read at save time (see
        # settings_security); the visible controls live on the dashboard
        # settings page. They stay parentless (the dashboard's control
        # consistency contract audits every child control), so register them
        # for explicit release in close_services() to avoid leaking them as
        # top-level widgets.
        self._unmounted_value_holders = (
            self.proactive_enabled,
            self.proactive_mode,
            self.minimum_away_minutes,
            self.conversation_silence_minutes,
        )
        self.face_profile_list = QListWidget()
        self.face_profile_list.setMaximumHeight(100)
        self._refresh_face_profiles()
        self.camera_status = QLabel(self._t("攝影機已關閉"))
        self.camera_status.setWordWrap(True)
        self.local_perception_status = QLabel(
            self._t("本機臉部、虹膜與手勢模型尚未啟動")
        )
        self.local_perception_status.setWordWrap(True)
        self.remote_status = QLabel(self._t("遠端功能預設關閉"))
        self.remote_status.setWordWrap(True)
        self.device_list = QListWidget()
    def _remote_action_controls(self) -> QWidget:
        controls = QWidget()
        line = QHBoxLayout(controls)
        line.setContentsMargins(0, 0, 0, 0)
        start = QPushButton(self._t("啟動／套用"))
        stop = QPushButton(self._t("停止遠端服務"))
        pair = QPushButton(self._t("配對新手機"))
        line.addWidget(start)
        line.addWidget(stop)
        line.addWidget(pair)
        start.clicked.connect(self.start_remote)
        stop.clicked.connect(self.stop_remote)
        pair.clicked.connect(self.pair_device)
        return controls
    def _populate_remote_form(
        self,
        form: QFormLayout,
        port_control: QWidget,
        controls: QWidget,
    ) -> None:
        apply_camera = QPushButton(self._t("套用靈視設定"))
        enroll_face = QPushButton(self._t("登錄我的臉部身分"))
        clear_faces = QPushButton(self._t("刪除全部臉部身分"))
        delete_face = QPushButton(self._t("刪除選取的臉部身分"))
        revoke = QPushButton(self._t("撤銷選取裝置"))
        form.addRow(self.remote_enabled)
        form.addRow(self._t("監聽範圍"), self.remote_host)
        form.addRow(self._t("連線埠"), port_control)
        form.addRow("", self.remote_trusted)
        form.addRow("", self.remote_commands)
        form.addRow("", self.remote_screen)
        form.addRow("", self.remote_files)
        form.addRow(QLabel(self._t("<b>攝影機與身分辨識</b>")))
        form.addRow("", self.camera_enabled)
        form.addRow("", self.face_identity)
        form.addRow("", apply_camera)
        face_actions = QWidget()
        face_line = QHBoxLayout(face_actions)
        face_line.setContentsMargins(0, 0, 0, 0)
        face_line.addWidget(enroll_face)
        face_line.addWidget(clear_faces)
        form.addRow("", face_actions)
        form.addRow(self._t("已登錄身分"), self.face_profile_list)
        form.addRow("", delete_face)
        form.addRow(self._t("攝影機狀態"), self.camera_status)
        form.addRow(self._t("本機感知模型"), self.local_perception_status)
        camera_note = QLabel(
            self._t(
                "攝影機預設關閉；啟用時必須顯示狀態。畫面不會默默上傳，"
                "也不會辨識未登錄的陌生人。"
            )
        )
        camera_note.setWordWrap(True)
        form.addRow(camera_note)
        form.addRow("", controls)
        form.addRow(self._t("服務狀態"), self.remote_status)
        form.addRow(self._t("已配對裝置"), self.device_list)
        form.addRow("", revoke)
        revoke.clicked.connect(self.revoke_device)
        apply_camera.clicked.connect(self.apply_camera_settings)
        enroll_face.clicked.connect(self.enroll_face_identity)
        clear_faces.clicked.connect(self.clear_face_identities)
        delete_face.clicked.connect(self.delete_selected_face_identity)
    def _remote_tab(self) -> QWidget:
        scroll, form = self._scroll_form()
        self._initialize_remote_fields()
        port_control = self._remote_port_control()
        controls = self._remote_action_controls()
        self._populate_remote_form(form, port_control, controls)
        self.refresh_devices()
        return scroll
    def start_remote(self) -> None:
        self.stop_remote(silent=True)
        if not self.remote_enabled.isChecked():
            self.remote_status.setText(self._t("遠端服務未啟用"))
            return
        host = str(self.remote_host.currentData())
        trusted = self.remote_trusted.isChecked()
        config = RemoteServerConfig(
            host=host,
            port=self.remote_port.value(),
            enabled=True,
            trusted_private_transport=trusted,
            allow_commands=self.remote_commands.isChecked(),
            allow_screen=self.remote_screen.isChecked(),
            allow_files=self.remote_files.isChecked(),
            language=self.language,
        )
        folders = [
            str(row["target_value"])
            for row in self.db.allowed_targets("folder")
            if str(row["access_mode"]) in {"read", "write"}
        ]
        self.remote_server = RemoteControlServer(
            config,
            TokenRegistry(self.db),
            RemoteServerServices(
                status_provider=self._remote_status_payload,
                command_handler=self._queue_remote_command,
                screen_provider=self._screen_bytes,
                allowed_folders=tuple(folders),
            ),
        )
        try:
            self.remote_server.start()
        except (OSError, PermissionError) as exc:
            self.remote_server = None
            self.remote_status.setText(
                self._t(
                    "啟動失敗：{error}",
                    error=safe_error_message(self.language, exc),
                )
            )
            return
        self.db.set_setting("remote_port", self.remote_port.value())
        self.db.set_setting("camera_presence_enabled", self.camera_enabled.isChecked())
        self.db.set_setting("face_identity_enabled", self.face_identity.isChecked())
        self.remote_status.setText(
            self._t(
                "已啟動：http://{host}:{port}\n"
                "只有已配對且具備相應權限的裝置可以存取。",
                host=host,
                port=self.remote_port.value(),
            )
        )
        self.refresh_health()
    def stop_remote(self, _checked=False, *, silent: bool = False) -> None:
        if self.remote_server:
            self.remote_server.stop()
            self.remote_server = None
        if hasattr(self, "remote_status") and not silent:
            self.remote_status.setText(
                self._t("遠端服務已停止，既有權杖未刪除但無法連線。")
            )
        if hasattr(self, "health_summary"):
            self.refresh_health()
    def pair_device(self) -> None:
        name, ok = self._simple_text_dialog(
            self._t("配對新裝置"),
            self._t("裝置名稱"),
        )
        if not ok:
            return
        permissions = ["status"]
        if self.remote_commands.isChecked():
            permissions.append("commands")
        if self.remote_screen.isChecked():
            permissions.append("screen")
        if self.remote_files.isChecked():
            permissions.append("files")
        token = TokenRegistry(self.db).pair(name, permissions)
        QMessageBox.information(
            self,
            self._t("一次性配對權杖"),
            self._t(
                "請只在可信任裝置輸入下列權杖。關閉視窗後不會再次顯示：\n\n{token}",
                token=token,
            ),
        )
        self.refresh_devices()
    def refresh_devices(self) -> None:
        self.device_list.clear()
        for row in self.db.paired_devices():
            item = QListWidgetItem(
                self._t(
                    "{status}｜{device}｜最後連線：{last_seen}",
                    status=self._t("有效" if row["enabled"] else "已撤銷"),
                    device=row["device_name"],
                    last_seen=row["last_seen_at"] or self._t("從未"),
                )
            )
            item.setData(Qt.UserRole, int(row["id"]))
            self.device_list.addItem(item)
    def revoke_device(self) -> None:
        item = self.device_list.currentItem()
        if item is None:
            return
        self.db.revoke_paired_device(int(item.data(Qt.UserRole)))
        self.refresh_devices()
    def _remote_status_payload(self) -> dict[str, Any]:
        return dict(self._remote_status_cache)
    def _update_remote_status_cache(self) -> None:
        self._remote_status_cache = {
            "assistant": str(self.db.setting("assistant_name", "墨寒")),
            "mode": str(self.db.setting("mode", "工作")),
            "work_seconds": self.db.today_work_seconds(),
            "todos": [
                {"id": int(row["id"]), "title": str(row["title"])}
                for row in self.db.list_todos()[:20]
            ],
            "timestamp": local_wall_time().isoformat(timespec="seconds"),
        }
    def _queue_remote_command(self, text: str, device_name: str) -> dict[str, Any]:
        try:
            self._remote_commands.put_nowait((text, device_name))
        except queue.Full:
            return {
                "accepted": False,
                "message": self._t("待處理的遠端指令已達安全上限，請稍後重試"),
            }
        return {
            "accepted": True,
            "message": self._t("已送交墨寒並等待本機權限判斷"),
        }
    def _drain_remote_commands(self) -> None:
        if self._closed:
            return
        while True:
            try:
                text, device = self._remote_commands.get_nowait()
            except queue.Empty:
                return
            self.db.audit_event(
                "remote_command_received",
                {"device": device, "text": text[:500]},
            )
            self.remote_command_received.emit(
                self._t(
                    "[遠端裝置：{device}] {text}",
                    device=device,
                    text=text,
                )
            )
    def _refresh_screen_cache(self) -> None:
        if self._closed:
            return
        self._update_remote_status_cache()
        if not (
            self.remote_server
            and self.remote_server.running
            and self.remote_server.config.allow_screen
        ):
            self._screen_cache = b""
            return
        pixmap = self.window().grab()
        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QIODevice.WriteOnly)
        pixmap.save(buffer, "PNG")
        self._screen_cache = bytes(data)
    def _screen_bytes(self) -> bytes:
        if not self._screen_cache:
            raise PermissionError(self._t("尚無可用的程式視窗畫面"))
        return self._screen_cache
