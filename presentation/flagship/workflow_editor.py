from __future__ import annotations

lazy import json
lazy from typing import Any

lazy from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QTimeEdit,
    QVBoxLayout,
)

lazy from application.workflow_engine import Workflow
lazy from presentation.flagship_ui_localization import FlagshipTranslator

__all__ = ("WorkflowEditor",)

STEP_PART_COUNT = 3


class WorkflowEditor(QDialog):
    def __init__(self, parent=None, *, language: str = "zh-TW"):
        super().__init__(parent)
        self._translator = FlagshipTranslator(language)
        self.language = self._translator.language
        self.setWindowTitle(self._t("新增安全工作流程"))
        self.resize(620, 560)
        root = QVBoxLayout(self)
        form = QFormLayout()
        self.name = QLineEdit()
        self.trigger = QComboBox()
        for canonical, label in (
            ("manual", "手動執行"),
            ("schedule", "每天固定時間"),
            ("work_start", "開始工作時"),
        ):
            self.trigger.addItem(self._t(label), canonical)
        self.at = QTimeEdit()
        self.at.setDisplayFormat("HH:mm")
        self.preview = QCheckBox(self._t("第一次與高風險操作先預覽"))
        self.preview.setChecked(True)
        form.addRow(self._t("流程名稱"), self.name)
        form.addRow(self._t("啟動方式"), self.trigger)
        form.addRow(self._t("執行時間"), self.at)
        form.addRow("", self.preview)
        root.addLayout(form)

        note = QLabel(
            self._t(
                "每行一個步驟，格式：能力｜說明｜參數。\n"
                "範例：open_web｜開啟工作網站｜https://example.com\n"
                "範例：home_control｜開啟書房燈｜light.study,turn_on"
            )
        )
        note.setWordWrap(True)
        note.setStyleSheet("color:#356f8d;")
        self.steps = QTextEdit()
        self.steps.setPlaceholderText(
            self._t("open_web｜開啟工作網站｜https://example.com")
        )
        root.addWidget(note)
        root.addWidget(self.steps, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText(self._t("儲存"))
        buttons.button(QDialogButtonBox.Cancel).setText(self._t("取消"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _t(self, source: str, /, **values: Any) -> str:
        return self._translator.text(source, **values)

    def _trigger_definition(self) -> dict[str, Any]:
        trigger_type = str(self.trigger.currentData())
        if trigger_type == "schedule":
            return {
                "type": "schedule",
                "time": self.at.time().toString("HH:mm"),
                "weekdays": list(range(7)),
            }
        if trigger_type == "work_start":
            return {"type": "work_start"}
        return {"type": "manual"}

    def _home_arguments(
        self,
        capability: str,
        raw_argument: str,
    ) -> dict[str, Any]:
        try:
            entity, service = (value.strip() for value in raw_argument.split(",", 1))
        except ValueError as exc:
            raise ValueError(
                self._t(
                    "{capability} 參數格式必須是 entity_id,service",
                    capability=capability,
                )
            ) from exc
        return {
            "domain": entity.split(".", 1)[0],
            "service": service,
            "data": {"entity_id": entity},
        }

    def _step_arguments(
        self,
        capability: str,
        raw_argument: str,
    ) -> dict[str, Any]:
        simple_keys = {
            "open_web": "url",
            "open_folder": "path",
            "launch_app": "name",
            "home_read": "entity_id",
        }
        if capability in simple_keys:
            return {simple_keys[capability]: raw_argument}
        if capability in {
            "home_control",
            "home_lock",
            "home_alarm",
            "home_heat",
            "home_routine",
        }:
            return self._home_arguments(capability, raw_argument)
        try:
            arguments = json.loads(raw_argument)
        except json.JSONDecodeError as exc:
            raise ValueError(
                self._t(
                    "{capability} 的參數必須是 JSON 物件",
                    capability=capability,
                )
            ) from exc
        if not isinstance(arguments, dict):
            raise TypeError(
                self._t(
                    "{capability} 的參數必須是 JSON 物件",
                    capability=capability,
                )
            )
        return arguments

    def _workflow_steps(self) -> list[dict[str, Any]]:
        steps: list[dict[str, Any]] = []
        for raw_line in self.steps.toPlainText().splitlines():
            line = raw_line.strip()
            if not line:
                continue
            parts = [part.strip() for part in line.split("｜", 2)]
            if len(parts) != STEP_PART_COUNT:
                raise ValueError(self._t("步驟格式不正確：{line}", line=line))
            capability, description, raw_argument = parts
            steps.append({
                "capability": capability,
                "description": description,
                "arguments": self._step_arguments(
                    capability,
                    raw_argument,
                ),
            })
        return steps

    def workflow(self) -> Workflow:
        workflow = Workflow(
            None,
            self.name.text().strip(),
            True,
            self._trigger_definition(),
            self._workflow_steps(),
            self.preview.isChecked(),
        )
        workflow.validate()
        return workflow
