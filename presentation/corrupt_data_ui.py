from __future__ import annotations

lazy from collections.abc import Callable
lazy from PySide6.QtWidgets import QMessageBox

__all__ = ("notify_pending_corrupt_data",)


def notify_pending_corrupt_data(
    parent: object,
    db: object,
    translate: Callable[..., str],
) -> None:
    consume = getattr(db, "consume_corrupt_data_notifications", None)
    if not callable(consume):
        return
    messages = consume()
    if messages:
        QMessageBox.warning(
            parent,
            translate("corrupt_data_title", "資料讀取警告"),
            "\n".join(
                translate("corrupt_data_message", message)
                for message in messages
            ),
        )
