from __future__ import annotations

lazy import json

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
    def test_home_connection(self) -> None:
        self.save_home_settings()
        try:
            healthy = self._home_client().health()
        except Exception as exc:  # noqa: BLE001 -- user-visible integration boundary
            self.ha_status.setText(
                self._t(
                    "連線失敗：{error}",
                    error=safe_error_message(self.language, exc),
                )
            )
            return
        self.ha_status.setText(self._t("連線正常" if healthy else "API 回應不正確"))
    def load_home_entities(self) -> None:
        self.ha_entities.clear()
        try:
            states = self._home_client().states()
        except Exception as exc:  # noqa: BLE001 -- user-visible integration boundary
            self.ha_status.setText(
                self._t(
                    "讀取失敗：{error}",
                    error=safe_error_message(self.language, exc),
                )
            )
            return
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
