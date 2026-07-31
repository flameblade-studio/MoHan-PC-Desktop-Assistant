from __future__ import annotations

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db import StudioDB
from remote_control import RemoteControlServer, RemoteServerConfig, TokenRegistry


def _server(db: StudioDB, allowed_folder: Path) -> RemoteControlServer:
    return RemoteControlServer(
        RemoteServerConfig(),
        TokenRegistry(db),
        status_provider=lambda: {},
        command_handler=lambda _text, _device: {},
        allowed_folders=[str(allowed_folder)],
    )


def main() -> None:
    with TemporaryDirectory(dir=Path.cwd()) as tmp:
        base = Path(tmp)
        allowed = base / "allowed"
        allowed.mkdir()
        inside = allowed / "notes.txt"
        inside.write_text("safe", encoding="utf-8")
        outside = base / "outside.txt"
        outside.write_text("private", encoding="utf-8")
        protected = allowed / "secret.pem"
        protected.write_text("private key", encoding="utf-8")

        db = StudioDB(base / "profile.db")
        try:
            server = _server(db, allowed)
            assert server._allowed_file(str(inside)) == inside.resolve()

            for blocked in (
                outside,
                allowed / ".." / outside.name,
                allowed / "missing.txt",
                protected,
            ):
                try:
                    server._allowed_file(str(blocked))
                except (FileNotFoundError, PermissionError):
                    pass
                else:
                    raise AssertionError(f"unsafe remote path was accepted: {blocked}")

            link = allowed / "outside-link.txt"
            try:
                os.symlink(outside, link)
            except (OSError, NotImplementedError):
                pass
            else:
                try:
                    server._allowed_file(str(link))
                except PermissionError:
                    pass
                else:
                    raise AssertionError("symlink escape was accepted")
        finally:
            db.close()

    print("REMOTE_FILE_ACCESS_OK")


if __name__ == "__main__":
    main()
