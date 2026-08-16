from __future__ import annotations

lazy import os
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from urllib.parse import urlencode
lazy from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from infrastructure.db import StudioDB
lazy from integrations.remote_control import (
    RemoteControlServer,
    RemoteServerConfig,
    RemoteServerServices,
    TokenRegistry,
)


def _server(db: StudioDB, allowed_folder: Path) -> RemoteControlServer:
    return RemoteControlServer(
        RemoteServerConfig(
            host="127.0.0.1",
            port=0,
            enabled=True,
            allow_files=True,
        ),
        TokenRegistry(db),
        RemoteServerServices(
            status_provider=dict,
            command_handler=lambda _text, _device: {},
            allowed_folders=(str(allowed_folder),),
        ),
    )


def _create_test_files(base: Path) -> tuple[Path, Path, Path, Path]:
    allowed = base / "allowed"
    allowed.mkdir()
    inside = allowed / "notes.txt"
    inside.write_text("safe", encoding="utf-8")
    outside = base / "outside.txt"
    outside.write_text("private", encoding="utf-8")
    protected = allowed / "secret.pem"
    protected.write_text("private key", encoding="utf-8")
    return allowed, inside, outside, protected


def _assert_download_metadata(
    server: RemoteControlServer,
    inside: Path,
) -> str:
    assert server._allowed_file(str(inside)) == inside.resolve()
    content_type, disposition = server._download_metadata(inside)
    assert content_type == "text/plain; charset=utf-8"
    assert disposition.startswith('attachment; filename="mohan-')
    assert "\r" not in disposition and "\n" not in disposition
    return disposition


def _assert_authenticated_download(
    server: RemoteControlServer,
    inside: Path,
    disposition: str,
) -> None:
    token = server.tokens.pair("測試裝置", ["files"])
    server.start()
    try:
        query = urlencode({"path": str(inside)})
        request = Request(
            f"http://127.0.0.1:{server._server.server_port}/api/v1/file?{query}",
            headers={"Authorization": f"Bearer {token}"},
        )
        with urlopen(request, timeout=3) as response:
            assert response.read() == b"safe"
            assert response.headers["Content-Type"].startswith("text/plain")
            assert response.headers["Content-Disposition"] == disposition
            assert response.headers["X-Content-Type-Options"] == "nosniff"
    finally:
        server.stop()


def _assert_path_rejected(server: RemoteControlServer, path: Path) -> None:
    try:
        server._allowed_file(str(path))
    except (FileNotFoundError, PermissionError):
        return
    raise AssertionError(f"unsafe remote path was accepted: {path}")


def _assert_blocked_paths(
    server: RemoteControlServer,
    allowed: Path,
    outside: Path,
    protected: Path,
) -> None:
    for blocked in (
        outside,
        allowed / ".." / outside.name,
        allowed / "missing.txt",
        protected,
    ):
        _assert_path_rejected(server, blocked)


def _assert_symlink_escape_rejected(
    server: RemoteControlServer,
    allowed: Path,
    outside: Path,
) -> None:
    link = allowed / "outside-link.txt"
    try:
        os.symlink(outside, link)
    except (OSError, NotImplementedError):
        return
    try:
        server._allowed_file(str(link))
    except PermissionError:
        return
    raise AssertionError("symlink escape was accepted")


def _assert_remote_file_policy(base: Path) -> None:
    allowed, inside, outside, protected = _create_test_files(base)
    db = StudioDB(base / "profile.db")
    try:
        server = _server(db, allowed)
        disposition = _assert_download_metadata(server, inside)
        _assert_authenticated_download(server, inside, disposition)
        _assert_blocked_paths(server, allowed, outside, protected)
        _assert_symlink_escape_rejected(server, allowed, outside)
    finally:
        db.close()


def main() -> None:
    with TemporaryDirectory(dir=Path.cwd()) as tmp:
        _assert_remote_file_policy(Path(tmp))

    print("REMOTE_FILE_ACCESS_OK")


if __name__ == "__main__":
    main()
