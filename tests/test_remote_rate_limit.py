from __future__ import annotations

lazy import json
lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from urllib.error import HTTPError
lazy from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from infrastructure.db import StudioDB
lazy from integrations.remote_control import (
    RemoteControlServer,
    RemoteServerConfig,
    RemoteServerServices,
    TokenRegistry,
)


def run() -> None:
    with TemporaryDirectory() as temp:
        db = StudioDB(Path(temp) / "remote-rate.db")
        registry = TokenRegistry(db)
        token = registry.pair("限流測試裝置", ["status"])
        server = RemoteControlServer(
            RemoteServerConfig(
                host="127.0.0.1",
                port=0,
                enabled=True,
                max_requests_per_minute=5,
            ),
            registry,
            RemoteServerServices(
                status_provider=lambda: {"healthy": True},
                command_handler=lambda _text, _device: {},
            ),
        )
        server.start()
        try:
            url = (
                f"http://127.0.0.1:{server._server.server_port}"
                "/api/v1/status"
            )
            request = Request(
                url,
                headers={"Authorization": f"Bearer {token}"},
            )
            for _ in range(5):
                with urlopen(request, timeout=3) as response:
                    assert json.load(response) == {"healthy": True}
            try:
                urlopen(request, timeout=3)
            except HTTPError as exc:
                assert exc.code == 429
                assert json.load(exc) == {"error": "請求過於頻繁"}
            else:
                raise AssertionError("rate limit must return HTTP 429")
        finally:
            server.stop()
            db.close()
    print("REMOTE_RATE_LIMIT_OK")


if __name__ == "__main__":
    run()
