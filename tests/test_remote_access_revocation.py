from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy import pytest
lazy from PySide6.QtCore import Qt
lazy from infrastructure.db import StudioDB
lazy from presentation.flagship import settings_security
lazy from presentation.flagship.settings_security import (
    FlagshipSettingsSecurityMixin,
)
lazy from integrations.remote_control import (
    RemoteControlServer,
    RemoteServerConfig,
    RemoteServerServices,
    TokenRegistry,
)


def test_removing_allowed_folder_revokes_running_remote_downloads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    folder = tmp_path / "shared"
    folder.mkdir()
    allowed_file = folder / "notes.txt"
    allowed_file.write_text("private", encoding="utf-8")
    other_folder = tmp_path / "other-shared"
    other_folder.mkdir()
    other_file = other_folder / "notes.txt"
    other_file.write_text("still allowed", encoding="utf-8")

    db = StudioDB(tmp_path / "profile.db")
    target_id = db.add_allowed_target(
        "folder",
        folder.name,
        str(folder),
        "read",
    )
    db.add_allowed_target(
        "folder",
        other_folder.name,
        str(other_folder),
        "read",
    )
    server = RemoteControlServer(
        RemoteServerConfig(enabled=True, allow_files=True),
        TokenRegistry(db),
        RemoteServerServices(
            status_provider=dict,
            command_handler=lambda _text, _device: {},
            allowed_folders=(str(folder), str(other_folder)),
        ),
    )

    class _TargetItem:
        def data(self, role: int) -> int:
            assert role == Qt.UserRole
            return target_id

    class _TargetList:
        def currentItem(self) -> _TargetItem:
            return _TargetItem()

    class _Settings(FlagshipSettingsSecurityMixin):
        def _t(self, text: str) -> str:
            return text

        def refresh_allowed_targets(self) -> None:
            pass

        def _configure_executor(self) -> None:
            pass

    settings = _Settings()
    settings.db = db
    settings.target_list = _TargetList()

    class _MessageBox:
        Yes = 1

        @staticmethod
        def question(*_args: object) -> int:
            return _MessageBox.Yes

    monkeypatch.setattr(settings_security, "QMessageBox", _MessageBox)
    monkeypatch.setattr(settings_security, "require_qwidget", lambda _widget: object())

    try:
        assert server._allowed_file(str(allowed_file)) == allowed_file.resolve()
        assert server._allowed_file(str(other_file)) == other_file.resolve()
        settings.remote_server = server
        settings.remove_allowed_target()
        with pytest.raises(PermissionError):
            server._allowed_file(str(allowed_file))
        assert server._allowed_file(str(other_file)) == other_file.resolve()
    finally:
        db.close()
