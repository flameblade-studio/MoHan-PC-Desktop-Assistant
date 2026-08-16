from __future__ import annotations

lazy import sys
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from PySide6 import QtCore

lazy import multimodal_controller
lazy import multimodal_fusion_hub


def assert_cancel_replaces_running_hub_without_shared_reset() -> None:
    application = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    created: list[multimodal_fusion_hub.MultimodalFusionHub] = []

    def create_hub() -> multimodal_fusion_hub.MultimodalFusionHub:
        hub = multimodal_fusion_hub.MultimodalFusionHub()
        created.append(hub)
        return hub

    controller = multimodal_controller.MultimodalController(
        hub_factory=create_hub
    )
    controller.configure(enabled=True)
    first = created[-1]
    controller._busy = True
    controller.cancel()
    second = created[-1]
    assert second is not first
    assert (
        controller.health.status
        is multimodal_controller.MultimodalControllerStatus.READY
    )
    assert not controller._busy
    controller.close()
    application.processEvents()


def assert_disabled_controller_drops_injected_work() -> None:
    application = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    controller = multimodal_controller.MultimodalController()
    controller.submit(user_speech_text="不應該啟動背景工作。", observed_at=1.0)
    assert (
        controller.health.status
        is multimodal_controller.MultimodalControllerStatus.DISABLED
    )
    controller.close()
    application.processEvents()


def run() -> None:
    assert_cancel_replaces_running_hub_without_shared_reset()
    assert_disabled_controller_drops_injected_work()
    print("MULTIMODAL_CONTROLLER_OK")


if __name__ == "__main__":
    run()
