from __future__ import annotations

lazy import json
lazy import mimetypes
lazy import time
lazy from datetime import datetime, timedelta
lazy from email.message import EmailMessage
lazy from typing import Any

lazy from collections.abc import Callable

lazy from PySide6.QtCore import QObject, QRunnable, Signal
lazy from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QWidget,
)

lazy from domain.contracts import SecretStorePort
lazy from domain.flagship_action_models import ActionRequest, ActionResult
lazy from domain.safe_error_localization import safe_error_message
lazy from domain.time_utils import local_aware_time
lazy from integrations.cloud_connectors import (
    PROVIDERS,
    GmailConnector,
    GoogleCalendarConnector,
    GoogleDriveConnector,
    MicrosoftGraphConnector,
    normalize_cloud_provider,
    refresh_oauth_token,
)
lazy from presentation.flagship.cloud_health import CloudHealthWorker
lazy from presentation.flagship.oauth import OAuthWorker

__all__ = ('FlagshipCloudMixin',)


class _CloudTestSignals(QObject):
    done = Signal(str, object)
    failed = Signal(str, str)


class _CloudTokenHealthWorker(QRunnable):
    """Resolve (and possibly refresh) the OAuth token off the UI thread.

    ``_cloud_token`` may perform a synchronous network refresh; running it on
    the UI thread froze the dashboard.  The token resolution therefore happens
    inside this worker before the regular health probes run.
    """

    def __init__(
        self,
        provider_id: str,
        resolve_token: Callable[[str], str],
        language: str,
    ) -> None:
        super().__init__()
        self.provider_id = provider_id
        self._resolve_token = resolve_token
        self._language = language
        self.signals = _CloudTestSignals()

    def run(self) -> None:
        try:
            token = self._resolve_token(self.provider_id)
        except Exception as exc:
            self.signals.failed.emit(
                self.provider_id,
                safe_error_message(self._language, exc),
            )
            return
        probe = CloudHealthWorker(self.provider_id, token, self._language)
        probe.signals.done.connect(self.signals.done)
        probe.run()


class FlagshipCloudMixin:
    def _cloud_tab(self) -> QWidget:
        scroll, form = self._scroll_form()
        if self.platform_services.capabilities.secure_secret_storage:
            secret_note = self._t("權杖由作業系統安全加密保存，不寫入資料庫或設定檔。")
        else:
            secret_note = self._t(
                "{platform} 的原生安全金鑰保存尚未完成實機驗證，因此 OAuth 連線暫停；"
                "墨寒不會改用明文保存。",
                platform=self.platform_services.capabilities.display_name,
            )
        intro = QLabel(
            self._t(
                "Google、Microsoft 與 GitHub 預設停用。連線時使用瀏覽器 OAuth；{note}",
                note=secret_note,
            )
        )
        intro.setWordWrap(True)
        self.cloud_provider = QComboBox()
        for provider in PROVIDERS.values():
            self.cloud_provider.addItem(
                provider.display_name,
                provider.provider_id,
            )
        self.cloud_client_id = QLineEdit()
        self.cloud_client_id.setPlaceholderText(
            self._t("貼上你在服務商後台建立的 Desktop App Client ID")
        )
        self.cloud_client_secret = QLineEdit()
        self.cloud_client_secret.setEchoMode(QLineEdit.Password)
        self.cloud_client_secret.setPlaceholderText(
            self._t("若服務商提供 Client Secret 才需填寫")
        )
        self.cloud_scopes = QTextEdit()
        self.cloud_scopes.setMaximumHeight(110)
        self.cloud_status = QLabel()
        self.cloud_status.setWordWrap(True)
        self.cloud_connections = QListWidget()
        buttons = QWidget()
        line = QHBoxLayout(buttons)
        line.setContentsMargins(0, 0, 0, 0)
        self.cloud_connect_button = QPushButton(self._t("開啟瀏覽器安全連線"))
        self.cloud_test_button = QPushButton(self._t("測試選取服務"))
        revoke = QPushButton(self._t("撤銷選取服務"))
        line.addWidget(self.cloud_connect_button)
        line.addWidget(self.cloud_test_button)
        line.addWidget(revoke)
        form.addRow(intro)
        form.addRow(self._t("服務"), self.cloud_provider)
        form.addRow("OAuth Client ID", self.cloud_client_id)
        form.addRow("OAuth Client Secret", self.cloud_client_secret)
        form.addRow(self._t("授權範圍"), self.cloud_scopes)
        form.addRow("", buttons)
        form.addRow(self._t("狀態"), self.cloud_status)
        form.addRow(self._t("已設定服務"), self.cloud_connections)
        self.cloud_provider.currentIndexChanged.connect(self._cloud_provider_changed)
        self.cloud_connect_button.clicked.connect(self.connect_cloud)
        self.cloud_test_button.clicked.connect(self.test_cloud)
        revoke.clicked.connect(self.revoke_cloud)
        if not self.platform_services.capabilities.secure_secret_storage:
            self.cloud_connect_button.setEnabled(False)
            self.cloud_client_secret.setEnabled(False)
            self.cloud_connect_button.setToolTip(secret_note)
            self.cloud_status.setText(secret_note)
        self._cloud_provider_changed()
        self.refresh_cloud_connections()
        return scroll
    def _cloud_provider_changed(self, _index: int = 0) -> None:
        provider_id = str(self.cloud_provider.currentData())
        provider = PROVIDERS[provider_id]
        row = self.db.connector(provider_id)
        config = json.loads(row["configuration"]) if row else {}
        self.cloud_client_id.setText(str(config.get("client_id", "")))
        self.cloud_scopes.setPlainText(
            "\n".join(config.get("scopes", provider.default_scopes))
        )
        self.cloud_client_secret.clear()
    def _oauth_store(self, provider_id: str) -> SecretStorePort:
        return self.secret_store_factory(
            self.data_path / f"oauth-{provider_id}.dpapi",
            f"MoHan {provider_id} OAuth token",
        )
    def connect_cloud(self) -> None:
        if not self.platform_services.capabilities.secure_secret_storage:
            self.cloud_status.setText(
                self._t(
                    "{platform} 尚無經過實機驗證的安全金鑰保存；OAuth 連線已安全停用。",
                    platform=self.platform_services.capabilities.display_name,
                )
            )
            return
        # 連線期間擋住連點：同時只允許一個 OAuth 流程進行。
        if getattr(self, "_cloud_connecting", False):
            return
        provider_id = str(self.cloud_provider.currentData())
        client_id = self.cloud_client_id.text().strip()
        if not client_id:
            QMessageBox.information(
                self,
                self._t("雲端連接器"),
                self._t("請先填入服務商後台建立的 OAuth Client ID。"),
            )
            return
        scopes = [
            line.strip()
            for line in self.cloud_scopes.toPlainText().splitlines()
            if line.strip()
        ]
        self.cloud_status.setText(self._t("等待瀏覽器授權，請勿關閉墨寒……"))
        worker = OAuthWorker(
            provider_id,
            client_id,
            self.cloud_client_secret.text().strip(),
            scopes,
        )
        # 完成回呼必須使用發起當下的 scopes 快照；瀏覽器授權期間使用者
        # 可能已切換供應商，直接讀 UI 會把 A 供應商的 scopes 寫進 B。
        worker.signals.done.connect(
            lambda done_provider, token, snapshot=tuple(scopes): (
                self._cloud_connected(done_provider, token, snapshot)
            )
        )
        worker.signals.failed.connect(self._cloud_failed)
        # Keep the worker reachable so close_services() can abandon its
        # loopback wait at shutdown instead of blocking on ~QThreadPool.
        worker.setAutoDelete(False)
        self._cloud_connecting = True
        self._oauth_worker = worker
        self.cloud_connect_button.setEnabled(False)
        self.thread_pool.start(worker)
    def _finish_cloud_connect_attempt(self) -> None:
        self._cloud_connecting = False
        self._oauth_worker = None
        if hasattr(self, "cloud_connect_button"):
            self.cloud_connect_button.setEnabled(
                self.platform_services.capabilities.secure_secret_storage
            )
    def _cloud_connected(
        self,
        provider_id: str,
        token: dict[str, Any],
        scopes: tuple[str, ...] = (),
    ) -> None:
        self._oauth_worker = None
        if self._closed:
            return
        self._finish_cloud_connect_attempt()
        try:
            self._oauth_store(provider_id).save(json.dumps(token, ensure_ascii=False))
        except OSError as exc:
            self.cloud_status.setText(
                self._t(
                    "無法安全保存 OAuth 權杖：{error}",
                    error=safe_error_message(self.language, exc),
                )
            )
            self.db.audit_event(
                "oauth_secret_store_unavailable",
                {"provider": provider_id, "error_type": type(exc).__name__},
            )
            return
        provider = PROVIDERS[provider_id]
        self.db.save_connector(
            provider_id,
            provider.display_name,
            True,
            {
                "client_id": token.get("client_id", ""),
                "scopes": list(scopes),
            },
            # Stored language-neutral (canonical zh-TW catalog source); the
            # list view translates it to the active UI language on display.
            last_health="OAuth 已連線",
        )
        self.cloud_client_secret.clear()
        self.cloud_status.setText(
            self._t(
                "{provider} 已安全連線",
                provider=provider.display_name,
            )
        )
        self._register_cloud_tools()
        self.refresh_cloud_connections()
    def _cloud_failed(self, provider_id: str, error: str) -> None:
        self._oauth_worker = None
        if self._closed:
            return
        self._finish_cloud_connect_attempt()
        self.cloud_status.setText(
            self._t(
                "{provider} 連線失敗：{error}",
                provider=PROVIDERS[provider_id].display_name,
                error=safe_error_message(self.language, error),
            )
        )
    def _cloud_token(self, provider_id: str) -> str:
        raw = self._oauth_store(provider_id).load()
        if not raw:
            raise PermissionError(self._t("尚未完成 OAuth 連線"))
        payload = json.loads(raw)
        expires_in = int(payload.get("expires_in", 0) or 0)
        obtained_at = int(payload.get("obtained_at", 0) or 0)
        if expires_in and obtained_at and time.time() >= obtained_at + expires_in - 90:
            payload = refresh_oauth_token(PROVIDERS[provider_id], payload)
            try:
                self._oauth_store(provider_id).save(
                    json.dumps(payload, ensure_ascii=False)
                )
            except OSError as exc:
                raise PermissionError(
                    self._t(
                        "無法安全更新 OAuth 權杖：{error}",
                        error=safe_error_message(self.language, exc),
                    )
                ) from exc
        token = str(payload.get("access_token", ""))
        if not token:
            raise PermissionError(self._t("OAuth 權杖資料不完整"))
        return token
    def _register_cloud_tools(self) -> None:
        if any(
            self._oauth_store(provider_id).load()
            for provider_id in ("google", "microsoft")
        ):
            self.executor.register("email_read", self._action_email_read)
            self.executor.register("email_send", self._action_email_send)
            self.executor.register("calendar_read", self._action_calendar_read)
            self.executor.register(
                "calendar_create",
                self._action_calendar_create,
            )
            self.executor.register(
                "cloud_file_read",
                self._action_cloud_file_read,
            )
            self.executor.register(
                "cloud_file_write",
                self._action_cloud_file_write,
            )
    def _provider_from_request(self, request: ActionRequest) -> str:
        provider_value = (
            request.arguments.get("provider")
            or request.arguments.get("service")
            or request.arguments.get("account_provider")
            or request.arguments.get("source")
            or ""
        )
        provider = normalize_cloud_provider(
            str(provider_value),
            request.description,
        )
        if not provider:
            connected = [
                provider_id
                for provider_id in ("google", "microsoft")
                if self._oauth_store(provider_id).load()
            ]
            if len(connected) == 1:
                provider = connected[0]
            elif len(connected) > 1:
                raise ValueError(
                    self._t("Google 與 Microsoft 均已連線，請明確指定要使用哪個帳戶")
                )
            else:
                raise ValueError(
                    self._t("尚未連線 Google 或 Microsoft，或工具計畫未指定供應商")
                )
        if provider not in {"google", "microsoft"}:
            raise ValueError(self._t("此工具目前只支援 google 或 microsoft"))
        return provider
    @staticmethod
    def _calendar_read_bounds(
        arguments: dict[str, Any],
    ) -> tuple[str, str]:
        start = str(
            arguments.get("start")
            or arguments.get("time_min")
            or arguments.get("start_time")
            or ""
        ).strip()
        end = str(
            arguments.get("end")
            or arguments.get("time_max")
            or arguments.get("end_time")
            or ""
        ).strip()
        if start and end:
            datetime.fromisoformat(start)
            datetime.fromisoformat(end)
            return start, end

        range_name = (
            str(
                arguments.get("range")
                or arguments.get("time_range")
                or arguments.get("date_range")
                or ""
            )
            .casefold()
            .strip()
        )
        now = local_aware_time()
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        aliases = {
            "today": 1,
            "today_only": 1,
            "今日": 1,
            "今天": 1,
            "today_to_tomorrow": 2,
            "today_and_tomorrow": 2,
            "今天到明天": 2,
            "next_7_days": 7,
            "next_week": 7,
            "未來一週": 7,
            "未來7天": 7,
        }
        days = aliases.get(range_name, 7)
        return day_start.isoformat(), (day_start + timedelta(days=days)).isoformat()
    def _action_email_read(self, request: ActionRequest) -> ActionResult:
        provider = self._provider_from_request(request)
        token = self._cloud_token(provider)
        if provider == "google":
            rows = GmailConnector(token).search(
                str(request.arguments.get("query", "newer_than:7d")),
                int(request.arguments.get("limit", 20)),
            )
        else:
            rows = MicrosoftGraphConnector(token).messages(
                int(request.arguments.get("limit", 20))
            )
        return ActionResult(
            request.request_id,
            True,
            self._t("已讀取 {count} 封郵件摘要", count=len(rows)),
            {"messages": rows},
        )
    def _action_email_send(self, request: ActionRequest) -> ActionResult:
        provider = self._provider_from_request(request)
        recipient = str(request.arguments.get("to", "")).strip()
        subject = str(request.arguments.get("subject", "")).strip()
        body = str(request.arguments.get("body", "")).strip()
        if not recipient or "@" not in recipient or not subject or not body:
            raise ValueError(self._t("收件者、主旨與內容不可留空"))
        token = self._cloud_token(provider)
        if provider == "google":
            message = EmailMessage()
            message["To"] = recipient
            message["Subject"] = subject
            message.set_content(body)
            draft = GmailConnector(token).create_draft(message.as_bytes())
            draft_id = str(draft.get("id", ""))
            if not draft_id:
                raise RuntimeError(self._t("Gmail 未傳回草稿 ID"))
            result = GmailConnector(token).send_draft(draft_id)
            message_id = str(result.get("id", ""))
        else:
            payload = {
                "subject": subject,
                "body": {"contentType": "Text", "content": body},
                "toRecipients": [{"emailAddress": {"address": recipient}}],
            }
            MicrosoftGraphConnector(token).send_message(payload)
            message_id = "microsoft-sent"
        return ActionResult(
            request.request_id,
            True,
            self._t("郵件已寄給 {recipient}", recipient=recipient),
            {"message_id": message_id, "recipient": recipient},
        )
    def _action_calendar_read(self, request: ActionRequest) -> ActionResult:
        provider = self._provider_from_request(request)
        start, end = self._calendar_read_bounds(request.arguments)
        token = self._cloud_token(provider)
        if provider == "google":
            rows = GoogleCalendarConnector(token).events(
                time_min=start,
                time_max=end,
            )
        else:
            rows = MicrosoftGraphConnector(token).calendar_events(start, end)
        return ActionResult(
            request.request_id,
            True,
            self._t("已讀取 {count} 個行程", count=len(rows)),
            {"events": rows},
        )
    def _action_calendar_create(self, request: ActionRequest) -> ActionResult:
        provider = self._provider_from_request(request)
        title = str(request.arguments.get("title", "")).strip()
        start = str(request.arguments.get("start", "")).strip()
        end = str(request.arguments.get("end", "")).strip()
        timezone = str(request.arguments.get("timezone", "Asia/Taipei"))
        if not title or not start or not end:
            raise ValueError(self._t("行程標題、開始與結束時間不可留空"))
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
        if end_dt <= start_dt:
            raise ValueError(self._t("結束時間必須晚於開始時間"))
        token = self._cloud_token(provider)
        if provider == "google":
            result = GoogleCalendarConnector(token).create_event({
                "summary": title,
                "description": str(request.arguments.get("description", "")),
                "start": {"dateTime": start, "timeZone": timezone},
                "end": {"dateTime": end, "timeZone": timezone},
            })
        else:
            result = MicrosoftGraphConnector(token).create_event({
                "subject": title,
                "body": {
                    "contentType": "Text",
                    "content": str(request.arguments.get("description", "")),
                },
                "start": {"dateTime": start, "timeZone": timezone},
                "end": {"dateTime": end, "timeZone": timezone},
            })
        return ActionResult(
            request.request_id,
            True,
            self._t("已建立行程：{title}", title=title),
            {"event": result},
        )
    def _action_cloud_file_read(self, request: ActionRequest) -> ActionResult:
        provider = self._provider_from_request(request)
        name = str(
            request.arguments.get("name")
            or request.arguments.get("query")
            or request.arguments.get("search_term")
            or request.arguments.get("filename")
            or ""
        ).strip()
        limit = max(1, min(100, int(request.arguments.get("limit", 20))))
        token = self._cloud_token(provider)
        if provider == "google":
            connector = GoogleDriveConnector(token)
            rows = connector.search(name, limit) if name else connector.recent(limit)
        else:
            if not name:
                raise ValueError(self._t("搜尋 OneDrive 時請提供檔案名稱"))
            rows = MicrosoftGraphConnector(token).search_drive(name)
        return ActionResult(
            request.request_id,
            True,
            self._t("找到 {count} 個符合的雲端檔案", count=len(rows)),
            {"files": rows},
        )
    def _action_cloud_file_write(self, request: ActionRequest) -> ActionResult:
        provider = self._provider_from_request(request)
        raw_path = str(request.arguments.get("path", ""))
        path = self.toolbox._allowed_path(raw_path, must_exist=True)
        if not path.is_file():
            raise ValueError(self._t("只能上傳白名單內的單一檔案"))
        content = path.read_bytes()
        mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        token = self._cloud_token(provider)
        if provider == "google":
            result = GoogleDriveConnector(token).upload_small(
                path.name,
                content,
                mime_type,
            )
        else:
            result = MicrosoftGraphConnector(token).upload_small(
                path.name,
                content,
                mime_type,
            )
        return ActionResult(
            request.request_id,
            True,
            self._t("已上傳：{name}", name=path.name),
            {"file": result, "source": str(path)},
        )
    def test_cloud(self) -> None:
        provider_id = str(self.cloud_provider.currentData())
        self._cloud_test_generation += 1
        generation = self._cloud_test_generation
        self.cloud_test_button.setEnabled(False)
        self.cloud_test_button.setText(self._t("測試中…"))
        self.cloud_status.setText(
            self._t("正在分別檢查 Gmail、Google Calendar 與 Google Drive……")
            if provider_id == "google"
            else self._t("正在檢查選取的服務……")
        )
        # 權杖到期時 _cloud_token 會同步向服務商換發新權杖；這屬於網路
        # 呼叫，必須連同健康檢查一起移出 UI 執行緒。
        worker = _CloudTokenHealthWorker(
            provider_id,
            self._cloud_token,
            self.language,
        )
        worker.setAutoDelete(False)
        self._cloud_test_worker = worker
        worker.signals.done.connect(
            lambda result_provider, results, request_generation=generation: (
                self._cloud_test_done(
                    result_provider,
                    results,
                    request_generation,
                )
            )
        )
        worker.signals.failed.connect(
            lambda result_provider, message, request_generation=generation: (
                self._cloud_test_failed(
                    result_provider,
                    message,
                    request_generation,
                )
            )
        )
        self.cloud_test_timeout.start()
        self.thread_pool.start(worker)
    def _cloud_test_failed(
        self,
        _provider_id: str,
        message: str,
        generation: int,
    ) -> None:
        if self._closed or generation != self._cloud_test_generation:
            return
        self.cloud_test_timeout.stop()
        self._cloud_test_worker = None
        self.cloud_test_button.setEnabled(True)
        self.cloud_test_button.setText(self._t("測試選取服務"))
        self.cloud_status.setText(
            self._t("測試失敗：{error}", error=message)
        )
    def _cloud_test_done(
        self,
        provider_id: str,
        results: dict[str, Any],
        generation: int,
    ) -> None:
        if self._closed or generation != self._cloud_test_generation:
            return
        self.cloud_test_timeout.stop()
        self._cloud_test_worker = None
        self.cloud_test_button.setEnabled(True)
        self.cloud_test_button.setText(self._t("測試選取服務"))
        lines = [
            self._t(
                "{name}：{status}（{detail}）",
                name=name,
                status=self._t("正常" if value.get("ok") else "失敗"),
                detail=value.get("detail", ""),
            )
            for name, value in results.items()
        ]
        all_ok = bool(results) and all(
            bool(value.get("ok")) for value in results.values()
        )
        row = self.db.connector(provider_id)
        configuration = json.loads(row["configuration"]) if row else {}
        # Persist a language-neutral structured record instead of composed
        # prose so the connection list can re-translate the status prefix and
        # per-service labels whenever the UI language changes.  Probe details
        # remain data snapshots (account names or safe error text).
        health = json.dumps(
            {
                "all_ok": all_ok,
                "services": [
                    {
                        "name": name,
                        "ok": bool(value.get("ok")),
                        "detail": str(value.get("detail", "")),
                    }
                    for name, value in results.items()
                ],
            },
            ensure_ascii=False,
        )
        self.db.save_connector(
            provider_id,
            PROVIDERS[provider_id].display_name,
            True,
            configuration,
            last_health=health,
        )
        self.cloud_status.setText("\n".join(lines))
        self.refresh_cloud_connections()
        title = self._t(
            "Google 三項服務測試" if provider_id == "google" else "雲端服務測試"
        )
        if all_ok:
            QMessageBox.information(self, title, "\n".join(lines))
        else:
            QMessageBox.warning(
                self,
                title,
                "\n".join(lines)
                + "\n\n"
                + self._t(
                    "失敗項目通常代表該 API 尚未啟用、OAuth 範圍不足，"
                    "或網路暫時無法連線。"
                ),
            )
    def _cloud_test_timed_out(self) -> None:
        if self._closed:
            return
        self.cloud_test_timeout.stop()
        self._cloud_test_generation += 1
        self._cloud_test_worker = None
        if hasattr(self, "cloud_test_button"):
            self.cloud_test_button.setEnabled(True)
            self.cloud_test_button.setText(self._t("測試選取服務"))
        self.cloud_status.setText(
            self._t("雲端測試超過 35 秒，已停止等待；請查看個別服務的 API 與網路狀態。")
        )
        self.db.audit_event(
            "cloud_health_timeout",
            {"timeout_seconds": 35},
        )
    def revoke_cloud(self) -> None:
        provider_id = str(self.cloud_provider.currentData())
        if (
            QMessageBox.question(
                self,
                self._t("撤銷雲端服務"),
                self._t(
                    "確定移除 {provider} 的本機權杖？",
                    provider=PROVIDERS[provider_id].display_name,
                ),
            )
            != QMessageBox.Yes
        ):
            return
        self._oauth_store(provider_id).clear()
        row = self.db.connector(provider_id)
        config = json.loads(row["configuration"]) if row else {}
        self.db.save_connector(
            provider_id,
            PROVIDERS[provider_id].display_name,
            False,
            config,
            last_health="已撤銷",
        )
        self._configure_executor()
        self.refresh_cloud_connections()
        self.cloud_status.setText(self._t("本機權杖已移除"))
    def _health_summary(self, record: object) -> str:
        """Render one stored ``last_health`` value in the active UI language.

        Structured JSON records (the current format) are recomposed and
        translated on every call; plain prose rows written by older builds
        fall back to the catalog-based system-message translation.
        """

        value = str(record or "")
        if not value:
            return self._t("尚未測試")
        try:
            payload = json.loads(value)
        except ValueError:
            return self._system_text(value)
        if not isinstance(payload, dict) or "services" not in payload:
            return self._system_text(value)
        lines = [
            self._t(
                "{name}：{status}（{detail}）",
                name=str(service.get("name", "")),
                status=self._t("正常" if service.get("ok") else "失敗"),
                detail=str(service.get("detail", "")),
            )
            for service in payload["services"]
        ]
        prefix = self._t("全部正常" if payload.get("all_ok") else "部分功能異常")
        return prefix + "｜" + "；".join(lines)
    def refresh_cloud_connections(self) -> None:
        self.cloud_connections.clear()
        for provider_id, provider in PROVIDERS.items():
            row = self.db.connector(provider_id)
            enabled = bool(row["enabled"]) if row else False
            health = (
                self._health_summary(row["last_health"])
                if row
                else self._t("未設定")
            )
            self.cloud_connections.addItem(
                f"{self._t('已啟用' if enabled else '未啟用')}｜"
                f"{provider.display_name}｜{health}"
            )
