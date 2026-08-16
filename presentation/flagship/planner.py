from __future__ import annotations

lazy import json
lazy from typing import Any

lazy from PySide6.QtCore import QTimer
lazy from PySide6.QtWidgets import QMessageBox

lazy from application.flagship_action_runtime import parse_plan_json
lazy from domain.safe_error_localization import safe_error_message
lazy from integrations.ai_client import DEFAULT_TEXT_MODEL, ActionPlannerWorker

__all__ = ('FlagshipPlannerMixin',)


class FlagshipPlannerMixin:
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
                "刪除",
                "建立",
                "移動",
                "控制",
                "關閉",
            )
        ):
            QMessageBox.information(
                self,
                self._t("工具任務"),
                self._t("這句話沒有明確要求執行操作，因此不會產生工具計畫。"),
            )
            return
        self.planner_busy = True
        self._planner_generation += 1
        generation = self._planner_generation
        if hasattr(self, "plan_button"):
            self.plan_button.setEnabled(False)
            self.plan_button.setText(self._t("規劃中…"))

        # 確定性的唯讀 Google 操作先走本機安全計畫，不送往 OpenAI 規劃器。
        # 這條快速路徑仍會通過後續權限與確認流程。
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
                lambda payload=local_plan, origin=source, request_generation=generation: (
                    self._planner_done_if_current(
                        payload,
                        origin,
                        request_generation,
                    )
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
            language=self.language,
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
        # 保留工作物件，直到完成或失敗回呼結束，避免 Python 包裝物件過早回收。
        worker.setAutoDelete(False)
        self._planner_worker = worker
        self.thread_pool.start(worker)
    def recognizes_safe_instruction(self, instruction: str) -> bool:
        """Return whether a chat command maps to a deterministic safe plan."""
        return self._known_safe_plan(instruction) is not None
    def _known_safe_plan(
        self,
        instruction: str,
    ) -> dict[str, Any] | None:
        """Return deterministic plans for simple read-only Google requests."""
        plan = self._safe_intents.known_safe_plan(instruction)
        return None if plan is None else plan.to_payload()
    def _planner_targets(self) -> str:
        lines = [
            (
                f"- {row['target_type']}：{row['display_name']}＝"
                f"{row['target_value']}（{row['access_mode']}）"
            )
            for row in self.db.allowed_targets()
        ]
        if hasattr(self, "ha_entities"):
            lines.extend(
                f"- home：{self.ha_entities.item(index).text()}"
                for index in range(min(200, self.ha_entities.count()))
            )
        return "\n".join(lines) or self._t("（目前沒有白名單目標）")
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
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            QMessageBox.warning(
                self,
                self._t("工具計畫"),
                self._t(
                    "計畫驗證失敗：{error}",
                    error=safe_error_message(self.language, exc),
                ),
            )
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
                self._t("工具計畫"),
                self._t("資料不足或並非明確操作要求，因此沒有產生任何步驟。"),
            )
            return
        preview = "\n".join(
            f"{index}. {step.description}" for index, step in enumerate(plan.steps, 1)
        )
        if (
            QMessageBox.question(
                self,
                self._t("執行前計畫預覽"),
                self._t(
                    "{title}\n\n{preview}\n\n每一步仍會依個別權限與風險再次判斷。是否繼續？",
                    title=plan.title,
                    preview=preview,
                ),
            )
            != QMessageBox.Yes
        ):
            return
        results = self.executor.execute(plan)
        QMessageBox.information(
            self,
            self._t("任務結果"),
            "\n".join(self._system_text(result.message) for result in results),
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
        QMessageBox.warning(
            self,
            self._t("工具計畫"),
            self._t(
                "無法產生計畫：{error}",
                error=safe_error_message(self.language, error),
            ),
        )
    def _planner_timed_out(self) -> None:
        if self._closed or not self.planner_busy:
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
            self._t("工具計畫逾時"),
            self._t(
                "等待 OpenAI 安全計畫超過 50 秒，已自動停止等待。"
                "請確認網路、API 金鑰與文字模型後再試一次。"
            ),
        )
    def _planner_reset(self) -> None:
        self.planner_timeout.stop()
        self.planner_busy = False
        self._planner_worker = None
        if hasattr(self, "plan_button"):
            self.plan_button.setEnabled(True)
            self.plan_button.setText(self._t("先產生安全計畫"))
