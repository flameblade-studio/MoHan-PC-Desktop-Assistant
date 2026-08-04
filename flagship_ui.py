from __future__ import annotations

import json
import mimetypes
import queue
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from PySide6.QtCore import (
    QBuffer,
    QByteArray,
    QIODevice,
    QObject,
    QRunnable,
    QThreadPool,
    QTimer,
    Qt,
    Signal,
)
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QTextBrowser,
    QTextEdit,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from flagship_core import (
    ActionExecutor,
    ActionPlan,
    ActionRequest,
    ActionResult,
    PolicyDecision,
    PolicyEngine,
    RISK_NAMES,
    WindowsToolbox,
    parse_plan_json,
)
from ai_client import ActionPlannerWorker, DEFAULT_TEXT_MODEL
from backup_manager import BackupManager
from cloud_connectors import (
    GitHubConnector,
    GmailConnector,
    GoogleCalendarConnector,
    GoogleDriveConnector,
    MicrosoftGraphConnector,
    OAuthPKCEFlow,
    PROVIDERS,
    normalize_cloud_provider,
    refresh_oauth_token,
)
from camera_presence import CameraPresenceController
from home_assistant import (
    HomeAssistantClient,
    HomeAssistantConfig,
    classify_home_capability,
    home_health_issues,
)
from remote_control import RemoteControlServer, RemoteServerConfig, TokenRegistry
from secret_store import SecretStore
from workflow_engine import Workflow
from windows_tools import WindowTools


CORE_PERMISSION_LABELS = {
    "read_status": "讀取狀態與摘要",
    "search_local": "搜尋白名單資料夾",
    "open_web": "開啟網站",
    "open_folder": "開啟資料夾",
    "launch_app": "啟動白名單程式",
    "window_list": "列出可見視窗",
    "window_activate": "切換至指定視窗",
    "create_file": "建立檔案",
    "rename_file": "重新命名檔案",
    "move_file": "移動檔案",
    "calendar_create": "建立行事曆事件",
    "calendar_update": "修改行事曆事件",
    "calendar_read": "讀取行事曆",
    "email_read": "讀取電子郵件",
    "email_send": "寄送電子郵件",
    "cloud_file_read": "讀取雲端檔案",
    "cloud_file_write": "建立或修改雲端檔案",
    "publish_external": "對外發布內容",
    "home_read": "讀取智慧家庭狀態",
    "home_control": "控制一般智慧設備",
    "home_lock": "控制門鎖",
    "home_alarm": "控制警報",
    "home_heat": "控制加熱與高溫設備",
    "camera_view": "使用攝影機",
    "remote_screen": "遠端查看本程式畫面",
    "remote_file_read": "遠端下載白名單檔案",
    "remote_file_write": "遠端寫入檔案",
    "delete_file": "刪除檔案",
    "shutdown_pc": "關機或重新啟動",
}


class OAuthSignals(QObject):
    done = Signal(str, object)
    failed = Signal(str, str)


class OAuthWorker(QRunnable):
    def __init__(
        self,
        provider_id: str,
        client_id: str,
        client_secret: str,
        scopes: list[str],
    ):
        super().__init__()
        self.provider_id = provider_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.scopes = scopes
        self.signals = OAuthSignals()

    def run(self) -> None:
        try:
            token = OAuthPKCEFlow(
                PROVIDERS[self.provider_id],
                self.client_id,
                client_secret=self.client_secret,
                scopes=self.scopes,
            ).authorize()
            if self.client_secret:
                token["client_secret"] = self.client_secret
            self.signals.done.emit(self.provider_id, token)
        except Exception as exc:
            self.signals.failed.emit(self.provider_id, str(exc))


class CloudHealthSignals(QObject):
    done = Signal(str, object)


class CloudHealthWorker(QRunnable):
    """Probe cloud services concurrently so a slow API cannot freeze the UI."""

    def __init__(self, provider_id: str, token: str):
        super().__init__()
        self.provider_id = provider_id
        self.token = token
        self.signals = CloudHealthSignals()

    def _google_probes(self) -> dict[str, Any]:
        def gmail() -> str:
            payload = GmailConnector(self.token).request("GET", "/profile")
            return str(payload.get("emailAddress", "Google 帳戶"))

        def calendar() -> str:
            GoogleCalendarConnector(self.token).request(
                "GET",
                "/calendars/primary/events",
                query={
                    "maxResults": 1,
                    "singleEvents": "true",
                    "timeMin": datetime.now().astimezone().isoformat(),
                },
            )
            return "主要日曆可讀取"

        def drive() -> str:
            GoogleDriveConnector(self.token).request(
                "GET",
                "/files",
                query={
                    "pageSize": 1,
                    "fields": "files(id,name)",
                    "q": "trashed=false",
                },
            )
            return "雲端硬碟中繼資料可讀取"

        probes = {"Gmail": gmail, "Calendar": calendar, "Drive": drive}
        results: dict[str, Any] = {}
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {pool.submit(probe): name for name, probe in probes.items()}
            for future in as_completed(futures):
                name = futures[future]
                try:
                    results[name] = {"ok": True, "detail": future.result()}
                except Exception as exc:
                    results[name] = {
                        "ok": False,
                        "detail": f"{type(exc).__name__}: {exc}",
                    }
        return results

    def run(self) -> None:
        if self.provider_id == "google":
            results = self._google_probes()
        else:
            try:
                if self.provider_id == "microsoft":
                    payload = MicrosoftGraphConnector(self.token).request(
                        "GET",
                        "/me",
                    )
                    identity = payload.get("displayName", "Microsoft 帳戶")
                else:
                    payload = GitHubConnector(self.token).viewer()
                    identity = payload.get("login", "GitHub 帳戶")
                results = {
                    PROVIDERS[self.provider_id].display_name: {
                        "ok": True,
                        "detail": str(identity),
                    }
                }
            except Exception as exc:
                results = {
                    PROVIDERS[self.provider_id].display_name: {
                        "ok": False,
                        "detail": f"{type(exc).__name__}: {exc}",
                    }
                }
        self.signals.done.emit(self.provider_id, results)


class WorkflowEditor(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("新增安全工作流程")
        self.resize(620, 560)
        root = QVBoxLayout(self)
        form = QFormLayout()
        self.name = QLineEdit()
        self.trigger = QComboBox()
        self.trigger.addItems(["手動執行", "每天固定時間", "開始工作時"])
        self.at = QTimeEdit()
        self.at.setDisplayFormat("HH:mm")
        self.preview = QCheckBox("第一次與高風險操作先預覽")
        self.preview.setChecked(True)
        form.addRow("流程名稱", self.name)
        form.addRow("啟動方式", self.trigger)
        form.addRow("執行時間", self.at)
        form.addRow("", self.preview)
        root.addLayout(form)

        note = QLabel(
            "每行一個步驟，格式：能力｜說明｜參數。\n"
            "範例：open_web｜開啟工作網站｜https://example.com\n"
            "範例：home_control｜開啟書房燈｜light.study,turn_on"
        )
        note.setWordWrap(True)
        note.setStyleSheet("color:#356f8d;")
        self.steps = QTextEdit()
        self.steps.setPlaceholderText(
            "open_web｜開啟工作網站｜https://example.com"
        )
        root.addWidget(note)
        root.addWidget(self.steps, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def workflow(self) -> Workflow:
        trigger_text = self.trigger.currentText()
        if trigger_text == "每天固定時間":
            trigger = {
                "type": "schedule",
                "time": self.at.time().toString("HH:mm"),
                "weekdays": list(range(7)),
            }
        elif trigger_text == "開始工作時":
            trigger = {"type": "work_start"}
        else:
            trigger = {"type": "manual"}
        steps: list[dict[str, Any]] = []
        for raw_line in self.steps.toPlainText().splitlines():
            line = raw_line.strip()
            if not line:
                continue
            parts = [part.strip() for part in line.split("｜", 2)]
            if len(parts) != 3:
                raise ValueError(f"步驟格式不正確：{line}")
            capability, description, raw_argument = parts
            arguments: dict[str, Any]
            if capability == "open_web":
                arguments = {"url": raw_argument}
            elif capability == "open_folder":
                arguments = {"path": raw_argument}
            elif capability == "launch_app":
                arguments = {"name": raw_argument}
            elif capability in {
                "home_control",
                "home_lock",
                "home_alarm",
                "home_heat",
            }:
                entity, service = [
                    value.strip() for value in raw_argument.split(",", 1)
                ]
                domain = entity.split(".", 1)[0]
                arguments = {
                    "domain": domain,
                    "service": service,
                    "data": {"entity_id": entity},
                }
            elif capability == "home_read":
                arguments = {"entity_id": raw_argument}
            else:
                try:
                    arguments = json.loads(raw_argument)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"{capability} 的參數必須是 JSON 物件"
                    ) from exc
            steps.append(
                {
                    "capability": capability,
                    "description": description,
                    "arguments": arguments,
                }
            )
        workflow = Workflow(
            None,
            self.name.text().strip(),
            True,
            trigger,
            steps,
            self.preview.isChecked(),
        )
        workflow.validate()
        return workflow


class FlagshipControlCenter(QWidget):
    speak_requested = Signal(str, str)
    remote_command_received = Signal(str)
    emergency_stop_requested = Signal()

    def __init__(self, db, data_path: Path, parent=None):
        super().__init__(parent)
        self.db = db
        self.data_path = data_path
        self.ha_secret = SecretStore(data_path / "home-assistant-token.dpapi")
        self.openai_secret = SecretStore(data_path / "openai-key.dpapi")
        # 工具工作使用獨立執行緒池，避免一般 AI 對話佔滿全域池後，
        # Gmail 等工具一直停留在「規劃中」。
        self.thread_pool = QThreadPool(self)
        self.thread_pool.setMaxThreadCount(3)
        self.planner_busy = False
        self._planner_worker: ActionPlannerWorker | None = None
        self._planner_generation = 0
        self.planner_timeout = QTimer(self)
        self.planner_timeout.setSingleShot(True)
        self.planner_timeout.setInterval(50_000)
        self.planner_timeout.timeout.connect(self._planner_timed_out)
        self._cloud_test_generation = 0
        self._cloud_test_worker: CloudHealthWorker | None = None
        self.cloud_test_timeout = QTimer(self)
        self.cloud_test_timeout.setSingleShot(True)
        self.cloud_test_timeout.setInterval(35_000)
        self.cloud_test_timeout.timeout.connect(self._cloud_test_timed_out)
        self.remote_server: RemoteControlServer | None = None
        self.camera_presence = CameraPresenceController(self)
        self.camera_presence.status_changed.connect(
            self._camera_status_changed
        )
        self.camera_presence.presence_changed.connect(
            self._presence_changed
        )
        self._screen_cache = b""
        self._closed = False
        self._remote_status_cache: dict[str, Any] = {
            "assistant": str(self.db.setting("assistant_name", "墨寒")),
            "status": "starting",
        }
        self._remote_commands: queue.Queue[tuple[str, str]] = queue.Queue()
        self._permission_controls: dict[str, QComboBox] = {}
        self._configure_executor()

        root = QVBoxLayout(self)
        emergency = QPushButton("緊急停止所有工具與遠端操作（Esc）")
        emergency.setStyleSheet(
            "QPushButton{background:#772f3a;color:white;font-weight:bold;"
            "padding:10px;border-radius:8px;}"
        )
        emergency.clicked.connect(self.emergency_stop)
        root.addWidget(emergency)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._overview_tab(), "任務中心")
        self.tabs.addTab(self._workflow_tab(), "工作流程")
        self.tabs.addTab(self._cloud_tab(), "雲端連接器")
        self.tabs.addTab(self._home_tab(), "智慧家庭")
        self.tabs.addTab(self._remote_tab(), "遠端與隱私")
        self.tabs.addTab(self._security_tab(), "安全權限")
        self.tabs.addTab(self._audit_tab(), "稽核紀錄")
        root.addWidget(self.tabs, 1)

        self.remote_poll = QTimer(self)
        self.remote_poll.timeout.connect(self._drain_remote_commands)
        self.remote_poll.start(250)
        self.screen_timer = QTimer(self)
        self.screen_timer.timeout.connect(self._refresh_screen_cache)
        self.screen_timer.start(2000)
        self.workflow_timer = QTimer(self)
        self.workflow_timer.timeout.connect(self.run_due_workflows)
        self.workflow_timer.start(30000)

    def _configure_executor(self) -> None:
        permissions = self.db.setting("flagship_permissions", {})
        protected = [
            str(Path.home() / ".ssh"),
            str(Path.home() / ".gnupg"),
            str(Path.home() / "AppData"),
        ]
        self.policy = PolicyEngine(permissions, protected_paths=protected)
        self.executor = ActionExecutor(
            self.policy,
            confirm=self._confirm_action,
            audit=self.db.audit_event,
        )
        allowed_folders = [
            str(row["target_value"])
            for row in self.db.allowed_targets("folder")
        ]
        allowed_apps = {
            str(row["display_name"]): str(row["target_value"])
            for row in self.db.allowed_targets("app")
        }
        allowed_websites = [
            str(row["target_value"])
            for row in self.db.allowed_targets("web")
        ]
        self.toolbox = WindowsToolbox(
            allowed_folders=allowed_folders,
            allowed_apps=allowed_apps,
            allowed_websites=allowed_websites,
        )
        self.toolbox.register_with(self.executor)
        self.window_tools = WindowTools()
        self.window_tools.register_with(self.executor)
        self.executor.register("clipboard_read", self._clipboard_read)
        self.executor.register("clipboard_write", self._clipboard_write)
        self.executor.register("read_status", self._action_read_status)
        self._register_home_tools()
        self._register_cloud_tools()

    def _action_read_status(self, request: ActionRequest) -> ActionResult:
        return ActionResult(
            request.request_id,
            True,
            "已整理目前工作狀態",
            self._remote_status_payload(),
        )

    @staticmethod
    def _clipboard_read(request: ActionRequest) -> ActionResult:
        text = QApplication.clipboard().text()
        return ActionResult(
            request.request_id,
            True,
            "已讀取剪貼簿文字",
            {"text": text[:100000]},
        )

    @staticmethod
    def _clipboard_write(request: ActionRequest) -> ActionResult:
        text = str(request.arguments.get("text", ""))
        if len(text) > 100000:
            raise ValueError("剪貼簿文字不可超過 100,000 字")
        QApplication.clipboard().setText(text)
        return ActionResult(
            request.request_id,
            True,
            "已寫入剪貼簿",
        )

    def _overview_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        title = QLabel("<b>墨寒旗艦任務中心</b>")
        title.setStyleSheet("font-size:18px;color:#2f6987;")
        note = QLabel(
            "所有電腦、雲端、遠端與智慧家庭操作都必須經過："
            "計畫 → 權限判斷 → 確認 → 執行 → 結果驗證 → 稽核。"
        )
        note.setWordWrap(True)
        self.health_summary = QLabel()
        self.health_summary.setWordWrap(True)
        refresh = QPushButton("重新檢查系統狀態")
        refresh.clicked.connect(self.refresh_health)
        backup = QPushButton("立即建立可驗證備份")
        backup.clicked.connect(self.create_backup)
        task_label = QLabel("<b>自然語言工具任務</b>")
        self.task_instruction = QLineEdit()
        self.task_instruction.setPlaceholderText(
            "例如：幫我開啟工作資料夾，然後開啟指定工作網站"
        )
        self.plan_button = QPushButton("先產生安全計畫")
        self.plan_button.clicked.connect(
            lambda: self.plan_instruction(
                self.task_instruction.text(),
                source="local",
            )
        )
        layout.addWidget(title)
        layout.addWidget(note)
        layout.addWidget(self.health_summary)
        layout.addWidget(refresh)
        layout.addWidget(backup)
        layout.addSpacing(12)
        layout.addWidget(task_label)
        layout.addWidget(self.task_instruction)
        layout.addWidget(self.plan_button)
        layout.addStretch()
        self.refresh_health()
        return page

    def create_backup(self) -> None:
        try:
            target = BackupManager(
                self.db,
                self.data_path / "backups",
            ).create("manual")
        except Exception as exc:
            QMessageBox.warning(self, "資料備份", f"備份失敗：{exc}")
            return
        QMessageBox.information(
            self,
            "資料備份",
            f"備份與完整性雜湊已建立：\n{target}",
        )

    def plan_instruction(self, text: str, *, source: str = "local") -> None:
        instruction = str(text).strip()
        if not instruction or self.planner_busy:
            return
        if not any(
            marker in instruction
            for marker in (
                "幫我",
                "請",
                "替我",
                "執行",
                "開啟",
                "建立",
                "移動",
                "控制",
                "關閉",
            )
        ):
            QMessageBox.information(
                self,
                "工具任務",
                "這句話沒有明確要求執行操作，因此不會產生工具計畫。",
            )
            return
        self.planner_busy = True
        self._planner_generation += 1
        generation = self._planner_generation
        if hasattr(self, "plan_button"):
            self.plan_button.setEnabled(False)
            self.plan_button.setText("規劃中…")

        # 明確、唯讀且低風險的 Google 指令不需要再繞到 OpenAI 規劃。
        # 這也避免網路或模型暫時不穩時，基本郵件讀取被卡住。
        local_plan = self._known_safe_plan(instruction)
        if local_plan is not None:
            self.db.audit_event(
                "planner_local_fast_path",
                {
                    "capability": local_plan["steps"][0]["capability"],
                    "source": source,
                    "generation": generation,
                },
            )
            QTimer.singleShot(
                0,
                lambda payload=local_plan, origin=source,
                request_generation=generation: self._planner_done_if_current(
                    payload,
                    origin,
                    request_generation,
                ),
            )
            return

        self.planner_timeout.start()
        worker = ActionPlannerWorker(
            instruction,
            api_key=self.openai_secret.load(),
            model=str(self.db.setting("ai_model", DEFAULT_TEXT_MODEL)),
            available_targets=self._planner_targets(),
            source=source,
        )
        worker.signals.done.connect(
            lambda payload, origin=source, request_generation=generation: (
                self._planner_done_if_current(
                    payload,
                    origin,
                    request_generation,
                )
            )
        )
        worker.signals.failed.connect(
            lambda error, request_generation=generation: (
                self._planner_failed_if_current(error, request_generation)
            )
        )
        # QRunnable 必須保留到完成訊號送達，避免 Python 包裝物過早釋放。
        worker.setAutoDelete(False)
        self._planner_worker = worker
        self.thread_pool.start(worker)

    def recognizes_safe_instruction(self, instruction: str) -> bool:
        """Return whether a chat command maps to a deterministic safe plan."""
        return self._known_safe_plan(instruction) is not None

    @staticmethod
    def _known_safe_plan(instruction: str) -> dict[str, Any] | None:
        """Return deterministic plans for simple read-only Google requests."""
        normalized = str(instruction).strip()
        folded = normalized.casefold()
        wants_read = any(
            marker in normalized
            for marker in (
                "讀取",
                "查看",
                "搜尋",
                "查詢",
                "查找",
                "尋找",
                "找出",
                "列出",
                "整理",
                "顯示",
                "檢查",
                "測試",
                "瀏覽",
                "取得",
            )
        )

        mentions_mail = any(
            marker in folded
            for marker in ("gmail", "郵件", "電子郵件", "信件", "信箱")
        )
        send_requested = (
            any(marker in normalized for marker in ("寄信", "寄出", "發信", "傳送郵件"))
            and not any(
                marker in normalized
                for marker in ("不要寄", "不用寄", "不寄出", "不要傳送")
            )
        )
        if mentions_mail and not send_requested and (
            wants_read or any(marker in normalized for marker in ("幫我", "請", "替我", "執行"))
        ):
            days = 7
            chinese_days = {
                "一天": 1,
                "一日": 1,
                "三天": 3,
                "三日": 3,
                "七天": 7,
                "七日": 7,
                "一週": 7,
                "一周": 7,
                "兩週": 14,
                "兩周": 14,
                "一個月": 30,
            }
            for marker, value in chinese_days.items():
                if marker in normalized:
                    days = value
                    break
            numeric_days = re.search(r"最近\s*(\d{1,3})\s*(?:天|日)", normalized)
            if numeric_days:
                days = max(1, min(365, int(numeric_days.group(1))))

            limit = 3
            chinese_limits = {
                "一封": 1,
                "兩封": 2,
                "三封": 3,
                "五封": 5,
                "十封": 10,
            }
            for marker, value in chinese_limits.items():
                if marker in normalized:
                    limit = value
                    break
            numeric_limit = re.search(
                r"(?:最多|前|最近)?\s*(\d{1,3})\s*封",
                normalized,
            )
            if numeric_limit:
                limit = max(1, min(100, int(numeric_limit.group(1))))

            return {
                "title": "讀取 Gmail 郵件",
                "steps": [
                    {
                        "capability": "email_read",
                        "description": f"讀取最近 {days} 天內最多 {limit} 封 Gmail 郵件",
                        "arguments": {
                            "provider": "google",
                            "query": f"newer_than:{days}d",
                            "limit": limit,
                        },
                    }
                ],
            }

        mentions_calendar = any(
            marker in folded
            for marker in (
                "google calendar",
                "googlecalendar",
                "calendar",
                "日曆",
                "行事曆",
                "行程",
            )
        )
        if mentions_calendar and (wants_read or "幫我" in normalized or "請" in normalized) and not any(
            marker in normalized for marker in ("建立", "新增", "加入", "取消", "刪除")
        ):
            now = datetime.now().astimezone()
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            days = 7
            if "明天" in normalized:
                start += timedelta(days=1)
                days = 1
            elif "今天" in normalized or "今日" in normalized:
                days = 1
            end = start + timedelta(days=days)
            return {
                "title": "讀取 Google Calendar",
                "steps": [
                    {
                        "capability": "calendar_read",
                        "description": f"讀取 Google Calendar 未來 {days} 天行程",
                        "arguments": {
                            "provider": "google",
                            "start": start.isoformat(),
                            "end": end.isoformat(),
                        },
                    }
                ],
            }

        mentions_drive = any(
            marker in folded
            for marker in ("google drive", "googledrive", "雲端硬碟", "雲端檔案")
        )
        if mentions_drive and (wants_read or "幫我" in normalized or "請" in normalized) and not any(
            marker in normalized for marker in ("上傳", "寫入", "修改", "刪除", "移動")
        ):
            name = ""
            quoted = re.search(r"[「『\"]([^」』\"]+)[」』\"]", normalized)
            if quoted:
                name = quoted.group(1).strip()
            return {
                "title": "讀取 Google Drive",
                "steps": [
                    {
                        "capability": "cloud_file_read",
                        "description": (
                            f"搜尋 Google Drive 檔案：{name}"
                            if name
                            else "列出 Google Drive 最近修改的檔案"
                        ),
                        "arguments": {
                            "provider": "google",
                            "name": name,
                            "limit": 20,
                        },
                    }
                ],
            }
        return None

    def _planner_targets(self) -> str:
        lines = []
        for row in self.db.allowed_targets():
            lines.append(
                f"- {row['target_type']}：{row['display_name']}＝"
                f"{row['target_value']}（{row['access_mode']}）"
            )
        if hasattr(self, "ha_entities"):
            for index in range(min(200, self.ha_entities.count())):
                lines.append(f"- home：{self.ha_entities.item(index).text()}")
        return "\n".join(lines) or "（目前沒有白名單目標）"

    def _planner_done_if_current(
        self,
        payload: dict[str, Any],
        source: str,
        generation: int,
    ) -> None:
        if generation != self._planner_generation or not self.planner_busy:
            return
        self._planner_done(payload, source)

    def _planner_done(self, payload: dict[str, Any], source: str) -> None:
        self._planner_reset()
        try:
            plan = parse_plan_json(
                json.dumps(payload, ensure_ascii=False),
                source=source,
            )
        except (ValueError, json.JSONDecodeError) as exc:
            QMessageBox.warning(self, "工具計畫", f"計畫驗證失敗：{exc}")
            return
        if not plan.steps:
            self.db.audit_event(
                "planner_empty_plan",
                {
                    "source": source,
                    "title": str(payload.get("title", ""))[:120],
                },
            )
            QMessageBox.information(
                self,
                "工具計畫",
                "資料不足或並非明確操作要求，因此沒有產生任何步驟。",
            )
            return
        preview = "\n".join(
            f"{index}. {step.description}"
            for index, step in enumerate(plan.steps, 1)
        )
        if QMessageBox.question(
            self,
            "執行前計畫預覽",
            f"{plan.title}\n\n{preview}\n\n"
            "每一步仍會依個別權限與風險再次判斷。是否繼續？",
        ) != QMessageBox.Yes:
            return
        results = self.executor.execute(plan)
        QMessageBox.information(
            self,
            "任務結果",
            "\n".join(result.message for result in results),
        )
        self.refresh_audit()

    def _planner_failed_if_current(
        self,
        error: str,
        generation: int,
    ) -> None:
        if generation != self._planner_generation or not self.planner_busy:
            return
        self._planner_failed(error)

    def _planner_failed(self, error: str) -> None:
        self._planner_reset()
        QMessageBox.warning(self, "工具計畫", f"無法產生計畫：{error}")

    def _planner_timed_out(self) -> None:
        if not self.planner_busy:
            return
        self.db.audit_event(
            "planner_timeout",
            {
                "model": str(self.db.setting("ai_model", DEFAULT_TEXT_MODEL)),
                "timeout_seconds": 50,
            },
        )
        self._planner_generation += 1
        self._planner_reset()
        QMessageBox.warning(
            self,
            "工具計畫逾時",
            "等待 OpenAI 安全計畫超過 50 秒，已自動停止等待。"
            "請確認網路、API 金鑰與文字模型後再試一次。",
        )

    def _planner_reset(self) -> None:
        self.planner_timeout.stop()
        self.planner_busy = False
        self._planner_worker = None
        if hasattr(self, "plan_button"):
            self.plan_button.setEnabled(True)
            self.plan_button.setText("先產生安全計畫")

    def refresh_health(self) -> None:
        workflow_count = len(self.db.workflows(enabled_only=True))
        paired_count = sum(bool(row["enabled"]) for row in self.db.paired_devices())
        ha = self.db.connector("home_assistant")
        ha_text = "已啟用" if ha and bool(ha["enabled"]) else "未啟用"
        remote_text = "運作中" if self.remote_server and self.remote_server.running else "未啟用"
        self.health_summary.setText(
            f"Home Assistant：{ha_text}\n"
            f"遠端服務：{remote_text}\n"
            f"已啟用工作流程：{workflow_count}\n"
            f"有效配對裝置：{paired_count}\n"
            "安全狀態：高風險操作不允許免確認；任意命令列與付款永久禁止。"
        )

    def _workflow_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        top = QHBoxLayout()
        add = QPushButton("新增工作流程")
        run = QPushButton("執行選取流程")
        delete = QPushButton("刪除選取流程")
        top.addWidget(add)
        top.addWidget(run)
        top.addWidget(delete)
        top.addStretch()
        self.workflow_list = QListWidget()
        layout.addLayout(top)
        layout.addWidget(self.workflow_list, 1)
        add.clicked.connect(self.add_workflow)
        run.clicked.connect(self.run_selected_workflow)
        delete.clicked.connect(self.delete_selected_workflow)
        self.refresh_workflows()
        return page

    def refresh_workflows(self) -> None:
        self.workflow_list.clear()
        for row in self.db.workflows():
            workflow = Workflow.from_row(row)
            trigger = {
                "manual": "手動",
                "schedule": f"每天 {workflow.trigger.get('time', '')}",
                "work_start": "開始工作時",
                "app_start": "程式啟動時",
            }.get(str(workflow.trigger.get("type")), "未知")
            item = QListWidgetItem(
                f"{'●' if workflow.enabled else '○'} "
                f"{workflow.name}　｜　{trigger}　｜　{len(workflow.steps)} 步"
            )
            item.setData(Qt.UserRole, int(row["id"]))
            self.workflow_list.addItem(item)

    def add_workflow(self) -> None:
        dialog = WorkflowEditor(self)
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            workflow = dialog.workflow()
            self.db.save_workflow(
                workflow.name,
                workflow.to_json(),
                enabled=workflow.enabled,
            )
        except (ValueError, json.JSONDecodeError) as exc:
            QMessageBox.warning(self, "工作流程", str(exc))
            return
        self.refresh_workflows()

    def _selected_workflow(self) -> Workflow | None:
        item = self.workflow_list.currentItem()
        if item is None:
            return None
        row = self.db.workflow(int(item.data(Qt.UserRole)))
        return Workflow.from_row(row) if row is not None else None

    def run_selected_workflow(self) -> None:
        workflow = self._selected_workflow()
        if workflow is None:
            QMessageBox.information(self, "工作流程", "請先選取一個流程。")
            return
        self.run_workflow(workflow)

    def run_workflow(self, workflow: Workflow) -> None:
        try:
            plan = workflow.to_plan()
        except ValueError as exc:
            QMessageBox.warning(self, "工作流程", str(exc))
            return
        if workflow.require_preview:
            preview = "\n".join(
                f"{index}. {step.description}"
                for index, step in enumerate(plan.steps, 1)
            )
            if QMessageBox.question(
                self,
                "預覽工作流程",
                f"{plan.title}\n\n{preview}\n\n是否執行？",
            ) != QMessageBox.Yes:
                return
        results = self.executor.execute(plan)
        if workflow.workflow_id:
            self.db.mark_workflow_run(workflow.workflow_id)
        message = "\n".join(result.message for result in results)
        QMessageBox.information(self, "任務結果", message or "沒有可執行步驟")
        self.refresh_audit()

    def delete_selected_workflow(self) -> None:
        workflow = self._selected_workflow()
        if workflow is None or workflow.workflow_id is None:
            return
        if QMessageBox.question(
            self,
            "刪除工作流程",
            f"確定刪除「{workflow.name}」？",
        ) == QMessageBox.Yes:
            self.db.delete_workflow(workflow.workflow_id)
            self.refresh_workflows()

    def run_due_workflows(self) -> None:
        if self._closed:
            return
        from workflow_engine import schedule_due

        now = datetime.now()
        for row in self.db.workflows(enabled_only=True):
            workflow = Workflow.from_row(row)
            if schedule_due(workflow, now, row["last_run_at"]):
                # Scheduled plans never bypass their own preview setting.
                self.run_workflow(workflow)

    def work_started(self) -> None:
        for row in self.db.workflows(enabled_only=True):
            workflow = Workflow.from_row(row)
            if workflow.trigger.get("type") == "work_start":
                self.run_workflow(workflow)

    def _cloud_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        form = QFormLayout(content)
        scroll.setWidget(content)
        intro = QLabel(
            "Google、Microsoft 與 GitHub 預設停用。連線時使用瀏覽器 OAuth；"
            "權杖由 Windows 加密保存，不寫入資料庫或設定檔。"
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
            "貼上你在服務商後台建立的 Desktop App Client ID"
        )
        self.cloud_client_secret = QLineEdit()
        self.cloud_client_secret.setEchoMode(QLineEdit.Password)
        self.cloud_client_secret.setPlaceholderText(
            "若服務商提供 Client Secret 才需填寫"
        )
        self.cloud_scopes = QTextEdit()
        self.cloud_scopes.setMaximumHeight(110)
        self.cloud_status = QLabel()
        self.cloud_status.setWordWrap(True)
        self.cloud_connections = QListWidget()
        buttons = QWidget()
        line = QHBoxLayout(buttons)
        line.setContentsMargins(0, 0, 0, 0)
        connect = QPushButton("開啟瀏覽器安全連線")
        self.cloud_test_button = QPushButton("測試選取服務")
        revoke = QPushButton("撤銷選取服務")
        line.addWidget(connect)
        line.addWidget(self.cloud_test_button)
        line.addWidget(revoke)
        form.addRow(intro)
        form.addRow("服務", self.cloud_provider)
        form.addRow("OAuth Client ID", self.cloud_client_id)
        form.addRow("OAuth Client Secret", self.cloud_client_secret)
        form.addRow("授權範圍", self.cloud_scopes)
        form.addRow("", buttons)
        form.addRow("狀態", self.cloud_status)
        form.addRow("已設定服務", self.cloud_connections)
        self.cloud_provider.currentIndexChanged.connect(
            self._cloud_provider_changed
        )
        connect.clicked.connect(self.connect_cloud)
        self.cloud_test_button.clicked.connect(self.test_cloud)
        revoke.clicked.connect(self.revoke_cloud)
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

    def _oauth_store(self, provider_id: str) -> SecretStore:
        return SecretStore(self.data_path / f"oauth-{provider_id}.dpapi")

    def connect_cloud(self) -> None:
        provider_id = str(self.cloud_provider.currentData())
        client_id = self.cloud_client_id.text().strip()
        if not client_id:
            QMessageBox.information(
                self,
                "雲端連接器",
                "請先填入服務商後台建立的 OAuth Client ID。",
            )
            return
        scopes = [
            line.strip()
            for line in self.cloud_scopes.toPlainText().splitlines()
            if line.strip()
        ]
        self.cloud_status.setText("等待瀏覽器授權，請勿關閉墨寒……")
        worker = OAuthWorker(
            provider_id,
            client_id,
            self.cloud_client_secret.text().strip(),
            scopes,
        )
        worker.signals.done.connect(self._cloud_connected)
        worker.signals.failed.connect(self._cloud_failed)
        self.thread_pool.start(worker)

    def _cloud_connected(
        self,
        provider_id: str,
        token: dict[str, Any],
    ) -> None:
        self._oauth_store(provider_id).save(
            json.dumps(token, ensure_ascii=False)
        )
        provider = PROVIDERS[provider_id]
        self.db.save_connector(
            provider_id,
            provider.display_name,
            True,
            {
                "client_id": token.get("client_id", ""),
                "scopes": self.cloud_scopes.toPlainText().splitlines(),
            },
            last_health="OAuth 已連線",
        )
        self.cloud_client_secret.clear()
        self.cloud_status.setText(f"{provider.display_name} 已安全連線")
        self._register_cloud_tools()
        self.refresh_cloud_connections()

    def _cloud_failed(self, provider_id: str, error: str) -> None:
        self.cloud_status.setText(
            f"{PROVIDERS[provider_id].display_name} 連線失敗：{error}"
        )

    def _cloud_token(self, provider_id: str) -> str:
        raw = self._oauth_store(provider_id).load()
        if not raw:
            raise PermissionError("尚未完成 OAuth 連線")
        payload = json.loads(raw)
        expires_in = int(payload.get("expires_in", 0) or 0)
        obtained_at = int(payload.get("obtained_at", 0) or 0)
        if (
            expires_in
            and obtained_at
            and time.time() >= obtained_at + expires_in - 90
        ):
            payload = refresh_oauth_token(PROVIDERS[provider_id], payload)
            self._oauth_store(provider_id).save(
                json.dumps(payload, ensure_ascii=False)
            )
        token = str(payload.get("access_token", ""))
        if not token:
            raise PermissionError("OAuth 權杖資料不完整")
        return token

    def _register_cloud_tools(self) -> None:
        if any(self._oauth_store(provider_id).load() for provider_id in ("google", "microsoft")):
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
                    "Google 與 Microsoft 均已連線，請明確指定要使用哪個帳戶"
                )
            else:
                raise ValueError(
                    "尚未連線 Google 或 Microsoft，或工具計畫未指定供應商"
                )
        if provider not in {"google", "microsoft"}:
            raise ValueError("此工具目前只支援 google 或 microsoft")
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
            datetime.fromisoformat(start.replace("Z", "+00:00"))
            datetime.fromisoformat(end.replace("Z", "+00:00"))
            return start, end

        range_name = str(
            arguments.get("range")
            or arguments.get("time_range")
            or arguments.get("date_range")
            or ""
        ).casefold().strip()
        now = datetime.now().astimezone()
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
            f"已讀取 {len(rows)} 封郵件摘要",
            {"messages": rows},
        )

    def _action_email_send(self, request: ActionRequest) -> ActionResult:
        provider = self._provider_from_request(request)
        recipient = str(request.arguments.get("to", "")).strip()
        subject = str(request.arguments.get("subject", "")).strip()
        body = str(request.arguments.get("body", "")).strip()
        if (
            not recipient
            or "@" not in recipient
            or not subject
            or not body
        ):
            raise ValueError("收件者、主旨與內容不可留空")
        token = self._cloud_token(provider)
        if provider == "google":
            message = EmailMessage()
            message["To"] = recipient
            message["Subject"] = subject
            message.set_content(body)
            draft = GmailConnector(token).create_draft(message.as_bytes())
            draft_id = str(draft.get("id", ""))
            if not draft_id:
                raise RuntimeError("Gmail 未傳回草稿 ID")
            result = GmailConnector(token).send_draft(draft_id)
            message_id = str(result.get("id", ""))
        else:
            payload = {
                "subject": subject,
                "body": {"contentType": "Text", "content": body},
                "toRecipients": [
                    {"emailAddress": {"address": recipient}}
                ],
            }
            MicrosoftGraphConnector(token).send_message(payload)
            message_id = "microsoft-sent"
        return ActionResult(
            request.request_id,
            True,
            f"郵件已寄給 {recipient}",
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
            f"已讀取 {len(rows)} 個行程",
            {"events": rows},
        )

    def _action_calendar_create(self, request: ActionRequest) -> ActionResult:
        provider = self._provider_from_request(request)
        title = str(request.arguments.get("title", "")).strip()
        start = str(request.arguments.get("start", "")).strip()
        end = str(request.arguments.get("end", "")).strip()
        timezone = str(request.arguments.get("timezone", "Asia/Taipei"))
        if not title or not start or not end:
            raise ValueError("行程標題、開始與結束時間不可留空")
        start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
        if end_dt <= start_dt:
            raise ValueError("結束時間必須晚於開始時間")
        token = self._cloud_token(provider)
        if provider == "google":
            result = GoogleCalendarConnector(token).create_event(
                {
                    "summary": title,
                    "description": str(
                        request.arguments.get("description", "")
                    ),
                    "start": {"dateTime": start, "timeZone": timezone},
                    "end": {"dateTime": end, "timeZone": timezone},
                }
            )
        else:
            result = MicrosoftGraphConnector(token).create_event(
                {
                    "subject": title,
                    "body": {
                        "contentType": "Text",
                        "content": str(
                            request.arguments.get("description", "")
                        ),
                    },
                    "start": {"dateTime": start, "timeZone": timezone},
                    "end": {"dateTime": end, "timeZone": timezone},
                }
            )
        return ActionResult(
            request.request_id,
            True,
            f"已建立行程：{title}",
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
            rows = (
                connector.search(name, limit)
                if name
                else connector.recent(limit)
            )
        else:
            if not name:
                raise ValueError("搜尋 OneDrive 時請提供檔案名稱")
            rows = MicrosoftGraphConnector(token).search_drive(name)
        return ActionResult(
            request.request_id,
            True,
            f"找到 {len(rows)} 個符合的雲端檔案",
            {"files": rows},
        )

    def _action_cloud_file_write(self, request: ActionRequest) -> ActionResult:
        provider = self._provider_from_request(request)
        raw_path = str(request.arguments.get("path", ""))
        path = self.toolbox._allowed_path(raw_path, must_exist=True)
        if not path.is_file():
            raise ValueError("只能上傳白名單內的單一檔案")
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
            f"已上傳：{path.name}",
            {"file": result, "source": str(path)},
        )

    def test_cloud(self) -> None:
        provider_id = str(self.cloud_provider.currentData())
        try:
            token = self._cloud_token(provider_id)
        except Exception as exc:
            self.cloud_status.setText(f"測試失敗：{exc}")
            return
        self._cloud_test_generation += 1
        generation = self._cloud_test_generation
        self.cloud_test_button.setEnabled(False)
        self.cloud_test_button.setText("測試中…")
        self.cloud_status.setText(
            "正在分別檢查 Gmail、Google Calendar 與 Google Drive……"
            if provider_id == "google"
            else "正在檢查選取的服務……"
        )
        worker = CloudHealthWorker(provider_id, token)
        worker.setAutoDelete(False)
        self._cloud_test_worker = worker
        worker.signals.done.connect(
            lambda result_provider, results,
            request_generation=generation: self._cloud_test_done(
                result_provider,
                results,
                request_generation,
            )
        )
        self.cloud_test_timeout.start()
        self.thread_pool.start(worker)

    def _cloud_test_done(
        self,
        provider_id: str,
        results: dict[str, Any],
        generation: int,
    ) -> None:
        if generation != self._cloud_test_generation:
            return
        self.cloud_test_timeout.stop()
        self._cloud_test_worker = None
        self.cloud_test_button.setEnabled(True)
        self.cloud_test_button.setText("測試選取服務")
        lines = [
            f"{name}：{'正常' if value.get('ok') else '失敗'}"
            f"（{value.get('detail', '')}）"
            for name, value in results.items()
        ]
        all_ok = bool(results) and all(
            bool(value.get("ok")) for value in results.values()
        )
        row = self.db.connector(provider_id)
        configuration = json.loads(row["configuration"]) if row else {}
        health = ("全部正常" if all_ok else "部分功能異常") + "｜" + "；".join(lines)
        self.db.save_connector(
            provider_id,
            PROVIDERS[provider_id].display_name,
            True,
            configuration,
            last_health=health,
        )
        self.cloud_status.setText("\n".join(lines))
        self.refresh_cloud_connections()
        title = "Google 三項服務測試" if provider_id == "google" else "雲端服務測試"
        if all_ok:
            QMessageBox.information(self, title, "\n".join(lines))
        else:
            QMessageBox.warning(
                self,
                title,
                "\n".join(lines)
                + "\n\n失敗項目通常代表該 API 尚未啟用、OAuth 範圍不足，"
                "或網路暫時無法連線。",
            )

    def _cloud_test_timed_out(self) -> None:
        self.cloud_test_timeout.stop()
        self._cloud_test_generation += 1
        self._cloud_test_worker = None
        if hasattr(self, "cloud_test_button"):
            self.cloud_test_button.setEnabled(True)
            self.cloud_test_button.setText("測試選取服務")
        self.cloud_status.setText(
            "雲端測試超過 35 秒，已停止等待；請查看個別服務的 API 與網路狀態。"
        )
        self.db.audit_event(
            "cloud_health_timeout",
            {"timeout_seconds": 35},
        )

    def revoke_cloud(self) -> None:
        provider_id = str(self.cloud_provider.currentData())
        if QMessageBox.question(
            self,
            "撤銷雲端服務",
            f"確定移除 {PROVIDERS[provider_id].display_name} 的本機權杖？",
        ) != QMessageBox.Yes:
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
        self.cloud_status.setText("本機權杖已移除")

    def refresh_cloud_connections(self) -> None:
        self.cloud_connections.clear()
        for provider_id, provider in PROVIDERS.items():
            row = self.db.connector(provider_id)
            enabled = bool(row["enabled"]) if row else False
            health = str(row["last_health"] or "尚未測試") if row else "未設定"
            self.cloud_connections.addItem(
                f"{'已啟用' if enabled else '未啟用'}｜"
                f"{provider.display_name}｜{health}"
            )

    def _home_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        form = QFormLayout(content)
        scroll.setWidget(content)
        self.ha_enabled = QCheckBox("啟用 Home Assistant 整合")
        self.ha_url = QLineEdit()
        self.ha_url.setPlaceholderText("例如：http://homeassistant.local:8123")
        self.ha_token = QLineEdit()
        self.ha_token.setEchoMode(QLineEdit.Password)
        self.ha_token.setPlaceholderText(
            "已加密保存（留空不變）"
            if self.ha_secret.load()
            else "貼上 Home Assistant 長期存取權杖"
        )
        self.ha_tls = QCheckBox("驗證 HTTPS 憑證")
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
        save = QPushButton("保存連線設定")
        test = QPushButton("測試連線")
        load = QPushButton("讀取裝置")
        buttons_layout.addWidget(save)
        buttons_layout.addWidget(test)
        buttons_layout.addWidget(load)
        self.ha_status = QLabel("尚未測試")
        self.ha_entities = QListWidget()
        self.ha_entities.setMinimumHeight(260)
        form.addRow(self.ha_enabled)
        form.addRow("Home Assistant 位址", self.ha_url)
        form.addRow("長期存取權杖", self.ha_token)
        form.addRow("", self.ha_tls)
        form.addRow("", buttons)
        form.addRow("連線狀態", self.ha_status)
        form.addRow("裝置狀態", self.ha_entities)
        warning = QLabel(
            "門鎖、警報與加熱設備永遠套用高風險政策。"
            "墨寒不能因對話內容自行降低安全等級。"
        )
        warning.setWordWrap(True)
        warning.setStyleSheet("color:#8a5a13;")
        form.addRow(warning)
        save.clicked.connect(self.save_home_settings)
        test.clicked.connect(self.test_home_connection)
        load.clicked.connect(self.load_home_entities)
        return scroll

    def save_home_settings(self) -> None:
        url = self.ha_url.text().strip()
        token = self.ha_token.text().strip()
        if self.ha_enabled.isChecked() and not url:
            QMessageBox.information(self, "Home Assistant", "請先填入連線位址。")
            return
        if token:
            self.ha_secret.save(token)
            self.ha_token.clear()
            self.ha_token.setPlaceholderText("已加密保存（留空不變）")
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
        self.ha_status.setText("設定已保存")

    def _home_client(self) -> HomeAssistantClient:
        row = self.db.connector("home_assistant")
        token = self.ha_secret.load()
        if row is None or not bool(row["enabled"]):
            raise PermissionError("Home Assistant 尚未啟用")
        if not token:
            raise PermissionError("尚未保存 Home Assistant 權杖")
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
        except (PermissionError, ValueError):
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
        except Exception as exc:
            self.ha_status.setText(f"連線失敗：{exc}")
            return
        self.ha_status.setText("連線正常" if healthy else "API 回應不正確")

    def load_home_entities(self) -> None:
        self.ha_entities.clear()
        try:
            states = self._home_client().states()
        except Exception as exc:
            self.ha_status.setText(f"讀取失敗：{exc}")
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
            "；".join(issue["message"] for issue in issues[:5])
            if issues
            else "未發現離線或低電量裝置"
        )
        self.ha_status.setText(
            f"已讀取 {self.ha_entities.count()} 個可用項目。{issue_text}"
        )

    def _remote_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        form = QFormLayout(content)
        scroll.setWidget(content)
        self.remote_enabled = QCheckBox("啟用手機／私人網路遠端服務")
        self.remote_host = QComboBox()
        self.remote_host.addItem("僅本機測試（127.0.0.1）", "127.0.0.1")
        self.remote_host.addItem("私人網路／Tailscale（0.0.0.0）", "0.0.0.0")
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
            (self.remote_port_up, "增加連線埠"),
            (self.remote_port_down, "減少連線埠"),
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
        self.remote_trusted = QCheckBox(
            "我確認已使用 Tailscale、Home Assistant Cloud 或其他加密私人網路"
        )
        self.remote_commands = QCheckBox("允許傳送文字指令")
        self.remote_commands.setChecked(True)
        self.remote_screen = QCheckBox("允許查看墨寒程式視窗（不擷取整個桌面）")
        self.remote_files = QCheckBox("允許下載白名單內的非敏感檔案")
        self.camera_enabled = QCheckBox("允許本機攝影機在場偵測")
        self.face_identity = QCheckBox(
            "本機臉部身分辨識（需另裝可稽核的辨識外掛）"
        )
        self.camera_enabled.setChecked(
            bool(self.db.setting("camera_presence_enabled", False))
        )
        self.face_identity.setChecked(False)
        self.face_identity.setEnabled(False)
        self.camera_status = QLabel("攝影機已關閉")
        self.camera_status.setWordWrap(True)
        apply_camera = QPushButton("套用攝影機隱私設定")
        controls = QWidget()
        line = QHBoxLayout(controls)
        line.setContentsMargins(0, 0, 0, 0)
        start = QPushButton("啟動／套用")
        stop = QPushButton("停止遠端服務")
        pair = QPushButton("配對新手機")
        line.addWidget(start)
        line.addWidget(stop)
        line.addWidget(pair)
        self.remote_status = QLabel("遠端功能預設關閉")
        self.remote_status.setWordWrap(True)
        self.device_list = QListWidget()
        revoke = QPushButton("撤銷選取裝置")
        form.addRow(self.remote_enabled)
        form.addRow("監聽範圍", self.remote_host)
        form.addRow("連線埠", port_control)
        form.addRow("", self.remote_trusted)
        form.addRow("", self.remote_commands)
        form.addRow("", self.remote_screen)
        form.addRow("", self.remote_files)
        form.addRow(QLabel("<b>攝影機與身分辨識</b>"))
        form.addRow("", self.camera_enabled)
        form.addRow("", self.face_identity)
        form.addRow("", apply_camera)
        form.addRow("攝影機狀態", self.camera_status)
        camera_note = QLabel(
            "攝影機預設關閉；啟用時必須顯示狀態。畫面不會默默上傳，"
            "也不會辨識未登錄的陌生人。"
        )
        camera_note.setWordWrap(True)
        form.addRow(camera_note)
        form.addRow("", controls)
        form.addRow("服務狀態", self.remote_status)
        form.addRow("已配對裝置", self.device_list)
        form.addRow("", revoke)
        start.clicked.connect(self.start_remote)
        stop.clicked.connect(self.stop_remote)
        pair.clicked.connect(self.pair_device)
        revoke.clicked.connect(self.revoke_device)
        apply_camera.clicked.connect(self.apply_camera_settings)
        self.refresh_devices()
        return scroll

    def apply_camera_settings(self) -> None:
        enabled = self.camera_enabled.isChecked()
        if not enabled:
            self.camera_presence.stop()
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
                "攝影機權限",
                f"安全政策已阻擋：{decision.reason}",
            )
            return
        if QMessageBox.question(
            self,
            "啟用攝影機",
            "墨寒只會在本機分析粗略移動與明暗，不保存影像、"
            "不傳送雲端，也不辨識陌生人。是否啟用？",
        ) != QMessageBox.Yes:
            self.camera_enabled.setChecked(False)
            return
        try:
            self.camera_presence.start()
        except RuntimeError as exc:
            self.camera_enabled.setChecked(False)
            self.camera_status.setText(str(exc))
            return
        self.db.set_setting("camera_presence_enabled", True)
        self.db.set_setting("face_identity_enabled", False)

    def _camera_status_changed(self, status: str) -> None:
        if hasattr(self, "camera_status"):
            self.camera_status.setText(status)

    def _presence_changed(self, present: bool) -> None:
        self.db.set_setting("camera_presence_state", bool(present))
        if hasattr(self, "camera_status"):
            base = self.camera_status.text().split("｜", 1)[0]
            self.camera_status.setText(
                f"{base}｜{'偵測到有人在場' if present else '暫未偵測到在場'}"
            )

    def start_remote(self) -> None:
        self.stop_remote(silent=True)
        if not self.remote_enabled.isChecked():
            self.remote_status.setText("遠端服務未啟用")
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
        )
        folders = [
            str(row["target_value"])
            for row in self.db.allowed_targets("folder")
            if str(row["access_mode"]) in {"read", "write"}
        ]
        self.remote_server = RemoteControlServer(
            config,
            TokenRegistry(self.db),
            status_provider=self._remote_status_payload,
            command_handler=self._queue_remote_command,
            screen_provider=self._screen_bytes,
            allowed_folders=folders,
        )
        try:
            self.remote_server.start()
        except (OSError, PermissionError) as exc:
            self.remote_server = None
            self.remote_status.setText(f"啟動失敗：{exc}")
            return
        self.db.set_setting("remote_port", self.remote_port.value())
        self.db.set_setting("camera_presence_enabled", self.camera_enabled.isChecked())
        self.db.set_setting("face_identity_enabled", self.face_identity.isChecked())
        self.remote_status.setText(
            f"已啟動：http://{host}:{self.remote_port.value()}\n"
            "只有已配對且具備相應權限的裝置可以存取。"
        )
        self.refresh_health()

    def stop_remote(self, _checked=False, *, silent: bool = False) -> None:
        if self.remote_server:
            self.remote_server.stop()
            self.remote_server = None
        if hasattr(self, "remote_status") and not silent:
            self.remote_status.setText("遠端服務已停止，既有權杖未刪除但無法連線。")
        if hasattr(self, "health_summary"):
            self.refresh_health()

    def pair_device(self) -> None:
        name, ok = self._simple_text_dialog("配對新裝置", "裝置名稱")
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
            "一次性配對權杖",
            "請只在可信任裝置輸入下列權杖。關閉視窗後不會再次顯示：\n\n"
            + token,
        )
        self.refresh_devices()

    def _simple_text_dialog(self, title: str, label: str) -> tuple[str, bool]:
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        root = QVBoxLayout(dialog)
        root.addWidget(QLabel(label))
        editor = QLineEdit()
        root.addWidget(editor)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        root.addWidget(buttons)
        accepted = dialog.exec() == QDialog.Accepted
        return editor.text().strip(), accepted

    def refresh_devices(self) -> None:
        self.device_list.clear()
        for row in self.db.paired_devices():
            item = QListWidgetItem(
                f"{'有效' if row['enabled'] else '已撤銷'}｜"
                f"{row['device_name']}｜最後連線：{row['last_seen_at'] or '從未'}"
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
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }

    def _queue_remote_command(self, text: str, device_name: str) -> dict[str, Any]:
        self._remote_commands.put((text, device_name))
        return {"accepted": True, "message": "已送交墨寒並等待本機權限判斷"}

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
                f"[遠端裝置：{device}] {text}"
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
            raise PermissionError("尚無可用的程式視窗畫面")
        return self._screen_cache

    def _security_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        form = QFormLayout(content)
        scroll.setWidget(content)
        stored = self.db.setting("flagship_permissions", {})
        target_heading = QLabel("<b>允許操作的資料夾與程式</b>")
        target_heading.setStyleSheet("color:#2f6987;font-size:15px;")
        self.target_list = QListWidget()
        self.target_list.setMinimumHeight(130)
        target_buttons = QWidget()
        target_line = QHBoxLayout(target_buttons)
        target_line.setContentsMargins(0, 0, 0, 0)
        add_folder = QPushButton("加入資料夾")
        add_app = QPushButton("加入程式")
        add_web = QPushButton("加入網站")
        remove_target = QPushButton("移除選取項目")
        target_line.addWidget(add_folder)
        target_line.addWidget(add_app)
        target_line.addWidget(add_web)
        target_line.addWidget(remove_target)
        form.addRow(target_heading)
        form.addRow(self.target_list)
        form.addRow("", target_buttons)
        add_folder.clicked.connect(self.add_allowed_folder)
        add_app.clicked.connect(self.add_allowed_app)
        add_web.clicked.connect(self.add_allowed_web)
        remove_target.clicked.connect(self.remove_allowed_target)
        self.refresh_allowed_targets()
        permission_heading = QLabel("<b>能力權限</b>")
        permission_heading.setStyleSheet("color:#2f6987;font-size:15px;")
        form.addRow(permission_heading)
        for capability, label in CORE_PERMISSION_LABELS.items():
            combo = QComboBox()
            combo.addItems(["禁止", "每次詢問", "允許"])
            risk = self.policy.evaluate(
                ActionRequest(capability, label)
            ).risk
            default = (
                "允許"
                if risk.value == 1
                else "每次詢問"
                if risk.value < 4
                else "禁止"
            )
            combo.setCurrentText(str(stored.get(capability, default)))
            if risk.value >= 3:
                combo.setToolTip("即使選擇允許，高風險政策仍會要求確認。")
            self._permission_controls[capability] = combo
            form.addRow(f"{label}（{RISK_NAMES[risk]}）", combo)
        save = QPushButton("保存安全權限")
        save.clicked.connect(self.save_security)
        note = QLabel(
            "付款、購買、密碼匯出、停用安全防護、任意 PowerShell／管理員命令"
            "永遠禁止自動執行，無法由此頁解除。"
        )
        note.setWordWrap(True)
        note.setStyleSheet("color:#8a5a13;")
        form.addRow(note)
        form.addRow("", save)
        return scroll

    def refresh_allowed_targets(self) -> None:
        self.target_list.clear()
        for row in self.db.allowed_targets():
            kind = {
                "folder": "資料夾",
                "app": "程式",
                "web": "網站",
            }.get(str(row["target_type"]), str(row["target_type"]))
            item = QListWidgetItem(
                f"{kind}｜{row['display_name']}｜{row['target_value']}｜"
                f"{row['access_mode']}"
            )
            item.setData(Qt.UserRole, int(row["id"]))
            self.target_list.addItem(item)

    def add_allowed_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            "選擇允許墨寒操作的資料夾",
        )
        if not path:
            return
        mode, ok = self._simple_text_dialog(
            "資料夾權限",
            "輸入 read（只讀）或 write（可建立、移動與重新命名）",
        )
        if not ok:
            return
        access_mode = "write" if mode.casefold() == "write" else "read"
        self.db.add_allowed_target(
            "folder",
            Path(path).name or path,
            path,
            access_mode,
        )
        self.refresh_allowed_targets()
        self._configure_executor()

    def add_allowed_app(self) -> None:
        path, _filter = QFileDialog.getOpenFileName(
            self,
            "選擇允許墨寒啟動的程式",
            "",
            "Windows 程式 (*.exe);;所有檔案 (*)",
        )
        if not path:
            return
        name, ok = self._simple_text_dialog(
            "程式別名",
            "日後對墨寒說的程式名稱",
        )
        if not ok or not name:
            return
        self.db.add_allowed_target(
            "app",
            name,
            path,
            "control",
        )
        self.refresh_allowed_targets()
        self._configure_executor()

    def add_allowed_web(self) -> None:
        url, ok = self._simple_text_dialog(
            "加入允許網站",
            "輸入完整 HTTPS 網址（可限制到指定路徑）",
        )
        if not ok or not url:
            return
        from urllib.parse import urlparse

        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc:
            QMessageBox.information(
                self,
                "網站白名單",
                "公開網站只接受完整 HTTPS 網址。",
            )
            return
        self.db.add_allowed_target(
            "web",
            parsed.hostname or url,
            url.rstrip("/"),
            "control",
        )
        self.refresh_allowed_targets()
        self._configure_executor()

    def remove_allowed_target(self) -> None:
        item = self.target_list.currentItem()
        if item is None:
            return
        if QMessageBox.question(
            self,
            "移除允許項目",
            "確定撤銷墨寒對此項目的存取權？",
        ) != QMessageBox.Yes:
            return
        self.db.remove_allowed_target(int(item.data(Qt.UserRole)))
        self.refresh_allowed_targets()
        self._configure_executor()

    def save_security(self) -> None:
        values = {
            key: combo.currentText()
            for key, combo in self._permission_controls.items()
        }
        self.db.set_setting("flagship_permissions", values)
        self._configure_executor()
        self.speak_requested.emit(
            "安全權限已保存。妾會守住這條界線。",
            "happy",
        )

    def _audit_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        top = QHBoxLayout()
        refresh = QPushButton("重新整理")
        top.addWidget(refresh)
        top.addStretch()
        self.audit_view = QTextBrowser()
        self.audit_view.setOpenExternalLinks(False)
        layout.addLayout(top)
        layout.addWidget(self.audit_view, 1)
        refresh.clicked.connect(self.refresh_audit)
        self.refresh_audit()
        return page

    def refresh_audit(self) -> None:
        if not hasattr(self, "audit_view"):
            return
        lines = []
        for row in self.db.audit_rows(200):
            try:
                payload = json.loads(row["payload"])
                summary = json.dumps(payload, ensure_ascii=False)[:500]
            except json.JSONDecodeError:
                summary = str(row["payload"])[:500]
            lines.append(
                f"<p><b>{row['created_at']}｜{row['event_type']}</b><br>"
                f"{summary}</p>"
            )
        self.audit_view.setHtml("".join(lines) or "<p>尚無工具操作紀錄。</p>")

    def _confirm_action(
        self,
        request: ActionRequest,
        decision: PolicyDecision,
        index: int,
    ) -> bool:
        title = (
            "高風險操作二次確認"
            if decision.confirmation_count > 1 and index > 1
            else "墨寒請求執行工具"
        )
        detail = json.dumps(
            request.arguments,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
        answer = QMessageBox.question(
            self,
            title,
            f"風險：{RISK_NAMES[decision.risk]}\n"
            f"來源：{request.source}\n"
            f"操作：{request.description}\n\n"
            f"參數預覽：\n{detail}\n\n是否允許？",
        )
        return answer == QMessageBox.Yes

    def emergency_stop(self) -> None:
        if self.planner_busy:
            self._planner_generation += 1
            self._planner_reset()
        self.executor.cancellations.cancel()
        self.stop_remote(silent=True)
        self.db.audit_event(
            "emergency_stop",
            {"at": datetime.now().isoformat(timespec="seconds")},
        )
        self.emergency_stop_requested.emit()
        self.speak_requested.emit("已停手。所有工具與遠端連線均已中止。", "worried")
        QMessageBox.information(
            self,
            "緊急停止",
            "所有進行中的工具任務與遠端服務均已停止。",
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

    def close_services(self) -> None:
        self._closed = True
        for timer in (
            getattr(self, "planner_timeout", None),
            getattr(self, "cloud_test_timeout", None),
            getattr(self, "remote_poll", None),
            getattr(self, "screen_timer", None),
            getattr(self, "workflow_timer", None),
        ):
            if timer is not None:
                timer.stop()
        self.stop_remote(silent=True)
        self.camera_presence.close()
        self.thread_pool.clear()
        self.thread_pool.waitForDone(1500)

    def closeEvent(self, event) -> None:
        self.close_services()
        super().closeEvent(event)
