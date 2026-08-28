from __future__ import annotations

lazy from contextlib import suppress

lazy from PySide6.QtCore import QTimer

__all__ = ("FlagshipLifecycleMixin",)


class FlagshipLifecycleMixin:
    """Idempotent cleanup that also works after partial construction."""

    def close_services(self) -> None:
        if getattr(self, "_closed", False):
            return
        self._closed = True
        self._planner_generation = getattr(self, "_planner_generation", 0) + 1
        self._cloud_test_generation = getattr(self, "_cloud_test_generation", 0) + 1
        self.planner_busy = False
        self._planner_worker = None
        self._cloud_test_worker = None
        self._home_probe_worker = None
        # 進行中的瀏覽器 OAuth 流程沒有取消 API；先標記棄單讓完成回呼
        # 早退，waitForDone 才不會被授權流程逼到上限。仍卡在 authorize()
        # 的執行緒（上限 180 秒）由行程退出回收。
        oauth_worker = getattr(self, "_oauth_worker", None)
        if oauth_worker is not None:
            with suppress(AttributeError, RuntimeError):
                oauth_worker.abandon()
            self._oauth_worker = None

        for timer in self.findChildren(QTimer):
            timer.stop()
        with suppress(AttributeError, RuntimeError):
            self.stop_remote(silent=True)

        for service_name in (
            "cloud_vision_service",
            "camera_presence",
            "vision_controller",
            "multimodal_controller",
            "_gesture_controller",
        ):
            service = getattr(self, service_name, None)
            if service is not None:
                with suppress(AttributeError, RuntimeError):
                    service.close()

        thread_pool = getattr(self, "thread_pool", None)
        if thread_pool is not None:
            with suppress(RuntimeError):
                thread_pool.clear()
                # 上限維持在 3000ms 以下：被棄單的 OAuth 執行緒可能仍在
                # 等待瀏覽器，關窗不應為它久候；殘留執行緒由行程退出回收。
                thread_pool.waitForDone(1500)

    def closeEvent(self, event) -> None:
        self.close_services()
        super().closeEvent(event)
