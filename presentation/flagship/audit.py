from __future__ import annotations

lazy import html
import json

lazy from PySide6.QtWidgets import (
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

lazy from domain.flagship_action_models import (
    RISK_NAMES,
    ActionRequest,
    PolicyDecision,
)
lazy from domain.time_utils import local_wall_time

__all__ = ("FlagshipAuditMixin",)


class FlagshipAuditMixin:
    def _audit_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        top = QHBoxLayout()
        refresh = QPushButton(self._t("重新整理"))
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
            # 稽核 payload 含外部來源內容——郵件寄件者、主旨、bodyPreview、
            # 行事曆資料、Home Assistant attributes。json.dumps 會跳脫引號與
            # 反斜線，但**不會跳脫 < > &**，所以一封主旨帶 HTML 標籤的郵件會
            # 在墨寒自己的稽核畫面裡被渲染。QTextBrowser 沒有 JS，但會載入
            # 遠端圖片：一個 <img src="http://…"> 就足以讓外部得知使用者何時
            # 查看稽核紀錄並取得其 IP。稽核畫面正是用來檢查有沒有出事的地方，
            # 它自己不能成為注入點。
            lines.append(
                "<p><b>{stamp}｜{event}</b><br>{summary}</p>".format(
                    stamp=html.escape(str(row["created_at"])),
                    event=html.escape(str(row["event_type"])),
                    summary=html.escape(summary),
                )
            )
        self.audit_view.setHtml("".join(lines) or self._t("<p>尚無工具操作紀錄。</p>"))

    def _confirm_action(
        self,
        request: ActionRequest,
        decision: PolicyDecision,
        index: int,
    ) -> bool:
        title = (
            self._t("高風險操作二次確認")
            if decision.confirmation_count > 1 and index > 1
            else self._t("墨寒請求執行工具")
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
            self._t(
                "風險：{risk}\n來源：{source}\n操作：{description}\n\n"
                "參數預覽：\n{detail}\n\n是否允許？",
                risk=self._t(RISK_NAMES[decision.risk]),
                source=request.source,
                description=request.description,
                detail=detail,
            ),
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
            {"at": local_wall_time().isoformat(timespec="seconds")},
        )
        self.emergency_stop_requested.emit()
        self.speak_requested.emit(
            self._t("已停手。所有工具與遠端連線均已中止。"),
            "worried",
        )
        QMessageBox.information(
            self,
            self._t("緊急停止"),
            self._t("所有進行中的工具任務與遠端服務均已停止。"),
        )
