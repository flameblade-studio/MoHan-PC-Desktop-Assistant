from __future__ import annotations

lazy import json

lazy from PySide6.QtCore import QObject, QRunnable, Signal
lazy from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QWidget,
)

lazy from domain.flagship_action_models import ActionPlan, ActionRequest
lazy from domain.safe_error_localization import safe_error_message
lazy from integrations.home_assistant import (
    HomeAssistantClient,
    HomeAssistantConfig,
    classify_home_capability,
    home_health_issues,
)

__all__ = ('FlagshipHomeMixin',)

HOME_CAPABILITIES = (
    "home_read",
    "home_control",
    "home_lock",
    "home_alarm",
    "home_heat",
)


class _HomeProbeSignals(QObject):
    done = Signal(str, object)
    failed = Signal(str, str)


class _HomeProbeWorker(QRunnable):
    """Run one blocking Home Assistant call off the UI thread."""

    def __init__(self, operation: str, client, language: str) -> None:
        super().__init__()
        self._operation = operation
        self._client = client
        self._language = language
        self.signals = _HomeProbeSignals()

    def run(self) -> None:
        try:
            result = (
                self._client.health()
                if self._operation == "health"
                else self._client.states()
            )
        except Exception as exc:
            self.signals.failed.emit(
                self._operation,
                safe_error_message(self._language, exc),
            )
            return
        self.signals.done.emit(self._operation, result)


class FlagshipHomeMixin:
    def _home_tab(self) -> QWidget:
        scroll, form = self._scroll_form()
        self.ha_enabled = QCheckBox(self._t("啟用 Home Assistant 整合"))
        self.ha_url = QLineEdit()
        self.ha_url.setPlaceholderText(self._t("例如：http://homeassistant.local:8123"))
        self.ha_token = QLineEdit()
        self.ha_token.setEchoMode(QLineEdit.Password)
        self.ha_token.setPlaceholderText(
            self._t("已由作業系統安全保存（留空不變）")
            if self.ha_secret.load()
            else self._t("貼上 Home Assistant 長期存取權杖")
        )
        self.ha_tls = QCheckBox(self._t("驗證 HTTPS 憑證"))
        self.ha_tls.setChecked(True)
        row = self.db.connector("home_assistant")
        if row:
            config = json.loads(row["configuration"])
            self.ha_enabled.setChecked(bool(row["enabled"]))
            self.ha_url.setText(str(config.get("base_url", "")))
            self.ha_tls.setChecked(bool(config.get("verify_tls", True)))
        buttons = QWidget()
        buttons_layout = QHBoxLayout(buttons)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        test = QPushButton(self._t("測試連線"))
        load = QPushButton(self._t("讀取裝置"))
        buttons_layout.addWidget(test)
        buttons_layout.addWidget(load)
        self.ha_status = QLabel(self._t("尚未測試"))
        self.ha_entities = QListWidget()
        self.ha_entities.setMinimumHeight(260)
        form.addRow(self.ha_enabled)
        form.addRow(self._t("Home Assistant 位址"), self.ha_url)
        form.addRow(self._t("長期存取權杖"), self.ha_token)
        form.addRow("", self.ha_tls)
        form.addRow("", buttons)
        form.addRow(self._t("連線狀態"), self.ha_status)
        form.addRow(self._t("裝置狀態"), self.ha_entities)
        warning = QLabel(
            self._t(
                "門鎖、警報與加熱設備永遠套用高風險政策。"
                "墨寒不能因對話內容自行降低安全等級。"
            )
        )
        warning.setWordWrap(True)
        warning.setStyleSheet("color:#8a5a13;")
        form.addRow(warning)
        test.clicked.connect(self.test_home_connection)
        load.clicked.connect(self.load_home_entities)
        if not self.platform_services.capabilities.secure_secret_storage:
            unavailable = self._t(
                "{platform} 的安全金鑰保存尚未完成實機驗證；"
                "Home Assistant 連線暫停，且不會儲存明文權杖。",
                platform=self.platform_services.capabilities.display_name,
            )
            self.ha_enabled.setChecked(False)
            self.ha_enabled.setEnabled(False)
            self.ha_token.setEnabled(False)
            self.ha_token.setPlaceholderText(unavailable)
            self.ha_status.setText(unavailable)
        return scroll
    def save_home_settings(self) -> None:
        url = self.ha_url.text().strip()
        token = self.ha_token.text().strip()
        if self.ha_enabled.isChecked() and not url:
            QMessageBox.information(
                self,
                "Home Assistant",
                self._t("請先填入連線位址。"),
            )
            return
        if token:
            try:
                self.ha_secret.save(token)
            except OSError as exc:
                safe_message = safe_error_message(self.language, exc)
                self.ha_status.setText(
                    self._t("無法安全保存權杖：{error}", error=safe_message)
                )
                QMessageBox.warning(
                    self,
                    "Home Assistant",
                    self._t("無法安全保存權杖：{error}", error=safe_message),
                )
                return
            self.ha_token.clear()
            self.ha_token.setPlaceholderText(
                self._t("已由作業系統安全保存（留空不變）")
            )
        self.db.save_connector(
            "home_assistant",
            "Home Assistant",
            self.ha_enabled.isChecked(),
            {
                "base_url": url,
                "verify_tls": self.ha_tls.isChecked(),
            },
        )
        self._register_home_tools()
        self.refresh_health()
        self.ha_status.setText(self._t("設定已保存"))
    def _home_client(self) -> HomeAssistantClient:
        row = self.db.connector("home_assistant")
        token = self.ha_secret.load()
        if row is None or not bool(row["enabled"]):
            raise PermissionError(self._t("Home Assistant 尚未啟用"))
        if not token:
            raise PermissionError(self._t("尚未保存 Home Assistant 權杖"))
        config = json.loads(row["configuration"])
        return HomeAssistantClient(
            HomeAssistantConfig(
                str(config.get("base_url", "")),
                token,
                verify_tls=bool(config.get("verify_tls", True)),
            )
        )
    def _register_home_tools(self) -> None:
        try:
            client = self._home_client()
        except PermissionError, ValueError:
            # 停用或未設定時必須反註冊：dashboard 的全域保存流程會先
            # 重建 executor（讀到舊設定）、之後才寫入 home 設定並再次
            # 呼叫本方法；若不移除，舊的 Home Assistant 工具會殘留到
            # 下一次重建為止。
            for capability in HOME_CAPABILITIES:
                self.executor.unregister(capability)
            return
        self.executor.register("home_read", client.action_read)
        for capability in (
            "home_control",
            "home_lock",
            "home_alarm",
            "home_heat",
        ):
            self.executor.register(
                capability,
                client.action_control,
                client.verify_control,
            )
    def _start_home_probe(self, operation: str) -> bool:
        """Launch health()/states() in a worker so HTTP can never block the UI."""

        if getattr(self, "_home_probe_worker", None) is not None:
            return False
        try:
            client = self._home_client()
        except Exception as exc:
            self.ha_status.setText(
                self._t(
                    "連線失敗：{error}" if operation == "health" else "讀取失敗：{error}",
                    error=safe_error_message(self.language, exc),
                )
            )
            return False
        worker = _HomeProbeWorker(operation, client, self.language)
        worker.setAutoDelete(False)
        self._home_probe_worker = worker
        worker.signals.done.connect(self._home_probe_done)
        worker.signals.failed.connect(self._home_probe_failed)
        self.ha_status.setText(self._t("測試中…"))
        self.thread_pool.start(worker)
        return True

    def _home_probe_done(self, operation: str, result: object) -> None:
        if self._closed:
            return
        self._home_probe_worker = None
        if operation == "health":
            self.ha_status.setText(
                self._t("連線正常" if bool(result) else "API 回應不正確")
            )
            return
        self._render_home_entities(list(result))

    def _home_probe_failed(self, operation: str, message: str) -> None:
        if self._closed:
            return
        self._home_probe_worker = None
        self.ha_status.setText(
            self._t(
                "連線失敗：{error}" if operation == "health" else "讀取失敗：{error}",
                error=message,
            )
        )

    def test_home_connection(self) -> None:
        self.save_home_settings()
        self._start_home_probe("health")
    def load_home_entities(self) -> None:
        self.ha_entities.clear()
        self._start_home_probe("states")
    def _render_home_entities(self, states: list) -> None:
        for state in states:
            entity = str(state.get("entity_id", ""))
            if entity.split(".", 1)[0] not in {
                "light",
                "switch",
                "fan",
                "cover",
                "scene",
                "script",
                "climate",
                "media_player",
                "lock",
                "alarm_control_panel",
                "sensor",
                "binary_sensor",
            }:
                continue
            name = str(state.get("attributes", {}).get("friendly_name", entity))
            self.ha_entities.addItem(f"{name}　｜　{entity}　｜　{state.get('state')}")
        issues = home_health_issues(states)
        issue_text = (
            "；".join(
                self._translator.home_issue(issue["message"]) for issue in issues[:5]
            )
            if issues
            else self._t("未發現離線或低電量裝置")
        )
        self.ha_status.setText(
            self._t(
                "已讀取 {count} 個可用項目。{issues}",
                count=self.ha_entities.count(),
                issues=issue_text,
            )
        )
    def _register_home_action_from_request(
        self,
        entity_id: str,
        service: str,
        description: str,
        source: str = "local",
    ) -> ActionPlan:
        domain = entity_id.split(".", 1)[0]
        capability = classify_home_capability(domain, service)
        return ActionPlan(
            description,
            [
                ActionRequest(
                    capability,
                    description,
                    {
                        "domain": domain,
                        "service": service,
                        "data": {"entity_id": entity_id},
                    },
                    source=source,
                )
            ],
        )
