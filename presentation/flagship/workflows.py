from __future__ import annotations

lazy import json

lazy from PySide6.QtCore import Qt
lazy from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

lazy from application.workflow_engine import Workflow, schedule_due
lazy from domain.safe_error_localization import safe_error_message
lazy from domain.time_utils import local_wall_time
lazy from presentation.flagship.workflow_editor import WorkflowEditor

__all__ = ("FlagshipWorkflowMixin",)


class FlagshipWorkflowMixin:
    def _workflow_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        top = QHBoxLayout()
        add = QPushButton(self._t("新增工作流程"))
        run = QPushButton(self._t("執行選取流程"))
        delete = QPushButton(self._t("刪除選取流程"))
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
            trigger_type = str(workflow.trigger.get("type"))
            trigger = {
                "manual": self._t("手動"),
                "schedule": self._t(
                    "每天 {time}",
                    time=workflow.trigger.get("time", ""),
                ),
                "work_start": self._t("開始工作時"),
                "app_start": self._t("程式啟動時"),
            }.get(trigger_type, self._t("未知"))
            item = QListWidgetItem(
                f"{'●' if workflow.enabled else '○'} "
                f"{workflow.name}　｜　{trigger}　｜　"
                + self._t("{count} 步", count=len(workflow.steps))
            )
            item.setData(Qt.UserRole, int(row["id"]))
            self.workflow_list.addItem(item)

    def add_workflow(self) -> None:
        dialog = WorkflowEditor(self, language=self.language)
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
            QMessageBox.warning(
                self,
                self._t("工作流程"),
                safe_error_message(self.language, exc),
            )
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
            QMessageBox.information(
                self,
                self._t("工作流程"),
                self._t("請先選取一個流程。"),
            )
            return
        self.run_workflow(workflow)

    def run_workflow(self, workflow: Workflow) -> None:
        try:
            plan = workflow.to_plan()
        except ValueError as exc:
            QMessageBox.warning(
                self,
                self._t("工作流程"),
                safe_error_message(self.language, exc),
            )
            return
        if workflow.require_preview:
            preview = "\n".join(
                f"{index}. {step.description}"
                for index, step in enumerate(plan.steps, 1)
            )
            if (
                QMessageBox.question(
                    self,
                    self._t("預覽工作流程"),
                    self._t(
                        "{title}\n\n{preview}\n\n是否執行？",
                        title=plan.title,
                        preview=preview,
                    ),
                )
                != QMessageBox.Yes
            ):
                return
        results = self.executor.execute(plan)
        if workflow.workflow_id:
            self.db.mark_workflow_run(workflow.workflow_id)
        message = "\n".join(self._system_text(result.message) for result in results)
        QMessageBox.information(
            self,
            self._t("任務結果"),
            message or self._t("沒有可執行步驟"),
        )
        self.refresh_audit()

    def delete_selected_workflow(self) -> None:
        workflow = self._selected_workflow()
        if workflow is None or workflow.workflow_id is None:
            return
        if (
            QMessageBox.question(
                self,
                self._t("刪除工作流程"),
                self._t("確定刪除「{name}」？", name=workflow.name),
            )
            == QMessageBox.Yes
        ):
            self.db.delete_workflow(workflow.workflow_id)
            self.refresh_workflows()

    def run_due_workflows(self) -> None:
        if self._closed or getattr(self, "_due_workflows_running", False):
            # run_workflow 會開啟模態確認／結果對話框，模態事件迴圈會讓
            # 30 秒計時器的下一次 tick 重入本方法；旗標防止同一批工作流
            # 疊加執行。
            return
        self._due_workflows_running = True
        try:
            now = local_wall_time()
            notified_schedule_errors = getattr(
                self,
                "_notified_schedule_errors",
                set(),
            )
            self._notified_schedule_errors = notified_schedule_errors
            for row in self.db.workflows(enabled_only=True):
                workflow = Workflow.from_row(row)
                workflow_id = workflow.workflow_id
                error_seen = False

                def notify_schedule_error(message: str) -> None:
                    nonlocal error_seen
                    error_seen = True
                    if workflow_id in notified_schedule_errors:
                        return
                    notified_schedule_errors.add(workflow_id)
                    QMessageBox.warning(
                        self,
                        self._t("工作流程"),
                        self._t(message),
                    )

                if schedule_due(
                    workflow,
                    now,
                    row["last_run_at"],
                    notify=notify_schedule_error,
                ):
                    self.run_workflow(workflow)
                if not error_seen:
                    notified_schedule_errors.discard(workflow_id)
        finally:
            self._due_workflows_running = False

    def work_started(self) -> None:
        for row in self.db.workflows(enabled_only=True):
            workflow = Workflow.from_row(row)
            if workflow.trigger.get("type") == "work_start":
                self.run_workflow(workflow)
