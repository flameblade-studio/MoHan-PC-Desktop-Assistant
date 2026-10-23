from __future__ import annotations

lazy import sqlite3
lazy import threading
lazy from pathlib import Path
lazy from types import SimpleNamespace
lazy from urllib.error import URLError

lazy import pytest

MIN_BACKUP_NAME_PARTS = 4


def test_home_assistant_redirect_handler_rejects_cross_origin() -> None:
    from integrations.home_assistant import _SameOriginRedirectHandler

    handler = _SameOriginRedirectHandler(("https", "homeassistant.example", 443))
    with pytest.raises(URLError, match="跨 origin"):
        handler.redirect_request(
            SimpleNamespace(full_url="https://homeassistant.example/api"),
            None,
            302,
            "redirect",
            {},
            "https://evil.example/collect",
        )


def test_bounded_http_read_rejects_body_without_trusting_content_length() -> None:
    from integrations.cloud_connectors import (
        MAX_RESPONSE_BYTES,
        _read_bounded_json,
    )

    class Response:
        headers = {}

        def read(self, limit: int) -> bytes:
            assert limit == MAX_RESPONSE_BYTES + 1
            return b"x" * (MAX_RESPONSE_BYTES + 1)

    with pytest.raises(ValueError, match="exceeds"):
        _read_bounded_json(Response())


def test_remote_handle_revalidation_rejects_opened_file_outside_root(
    tmp_path: Path,
) -> None:
    from integrations.remote_control import RemoteControlServer

    inside = tmp_path / "inside.txt"
    outside = tmp_path / "outside.txt"
    inside.write_text("inside", encoding="utf-8")
    outside.write_text("outside", encoding="utf-8")
    server = object.__new__(RemoteControlServer)
    server.allowed_folders = [tmp_path]
    server._allowed_folders_lock = threading.Lock()
    with outside.open("rb") as handle:
        assert not server._opened_file_is_allowed(
            tmp_path.parent / "outside.txt", handle
        )
    with inside.open("rb") as handle:
        assert server._opened_file_is_allowed(inside, handle)


def test_windows_toolbox_revalidates_handle_identity(tmp_path: Path) -> None:
    from infrastructure.flagship_windows_toolbox import WindowsToolbox

    inside = tmp_path / "inside.txt"
    outside = tmp_path.parent / f"{tmp_path.name}-outside.txt"
    inside.write_text("inside", encoding="utf-8")
    outside.write_text("outside", encoding="utf-8")
    toolbox = WindowsToolbox(allowed_folders=[str(tmp_path)])
    with outside.open("rb") as handle:
        assert not toolbox._opened_file_is_allowed(outside, handle)
    with inside.open("rb") as handle:
        assert toolbox._opened_file_is_allowed(inside, handle)


def test_updater_partial_file_is_exclusive(tmp_path: Path) -> None:
    from infrastructure.updater import InstallerAsset, UpdateManager

    partial = tmp_path / ".mohan-update-fixed.part"
    partial.write_bytes(b"original")

    class Response:
        headers = {}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def geturl(self):
            return "https://github.com/example/release.exe"

        def read(self, _size):
            return b"replacement"

    manager = UpdateManager(
        "example/repository",
        "1.0.0",
        tmp_path,
        opener=lambda *_args, **_kwargs: Response(),
    )
    asset = InstallerAsset("exe", "release.exe", "https://github.com/example/release.exe", "0" * 64, 11)
    received, _digest, failure = manager._download_to_partial(asset, partial, None)
    assert received == 0
    assert failure == "安裝程式下載失敗。"
    assert partial.read_bytes() == b"original"


def test_backup_uses_unpredictable_filename_and_rejects_reparse_manifest(
    tmp_path: Path,
) -> None:
    from infrastructure.backup_manager import BackupManager

    database_path = tmp_path / "mohan.db"
    connection = sqlite3.connect(database_path)
    connection.execute("CREATE TABLE sample(value TEXT)")
    connection.execute("INSERT INTO sample VALUES ('ok')")
    connection.commit()
    db = SimpleNamespace(conn=connection, path=database_path)
    backup_dir = tmp_path / "backups"
    target = BackupManager(db, backup_dir).create("test")
    assert target.name.startswith("mohan-")
    assert target.name.endswith(".db")
    assert len(target.stem.split("-")) >= MIN_BACKUP_NAME_PARTS
    assert BackupManager(db, backup_dir).verify(target)
    connection.close()


def test_pack_installation_copies_the_validated_snapshot(tmp_path: Path, monkeypatch) -> None:
    from domain import outfit_pack

    source = tmp_path / "source.mohan-outfit"
    source.write_bytes(b"validated")
    store = tmp_path / "store"

    def inspect_and_replace(_snapshot):
        source.write_bytes(b"replacement")
        return SimpleNamespace(pack_id="fixture")

    monkeypatch.setattr(outfit_pack, "inspect_outfit_pack", inspect_and_replace)
    monkeypatch.setattr(outfit_pack, "official_pack_id_reservations_complete", lambda: True)
    monkeypatch.setattr(outfit_pack, "official_pack_ids", lambda: frozenset())
    outfit_pack.install_outfit_pack(source, store)
    assert (store / "packages" / "fixture.mohan-outfit").read_bytes() == b"validated"


def test_remote_audit_redaction_never_keeps_command_text() -> None:
    from application.flagship_action_runtime import redact_audit_payload

    secret = "Bearer remote-secret-123"
    redacted = redact_audit_payload({"device": "tablet", "text": secret})
    assert secret not in repr(redacted)
    assert "redacted str" in repr(redacted)
