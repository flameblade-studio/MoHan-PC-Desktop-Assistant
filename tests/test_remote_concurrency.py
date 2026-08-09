lazy import json
lazy import sys
lazy from concurrent.futures import ThreadPoolExecutor
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from db import StudioDB
lazy from remote_control import (
    RemoteControlServer,
    RemoteServerConfig,
    RemoteServerServices,
    TokenRegistry,
)


def run() -> None:
    with TemporaryDirectory() as tmp:
        db = StudioDB(Path(tmp) / "remote.db")
        registry = TokenRegistry(db)
        token = registry.pair("壓力測試裝置", ["status"])
        server = RemoteControlServer(
            RemoteServerConfig(
                host="127.0.0.1",
                port=0,
                enabled=True,
                max_requests_per_minute=200,
            ),
            registry,
            RemoteServerServices(
                status_provider=lambda: {"healthy": True},
                command_handler=lambda _text, _device: {
                    "accepted": True
                },
            ),
        )
        server.start()
        port = server._server.server_port

        def request_status(_index: int) -> bool:
            request = Request(
                f"http://127.0.0.1:{port}/api/v1/status",
                headers={"Authorization": f"Bearer {token}"},
            )
            with urlopen(request, timeout=5) as response:
                return json.load(response) == {"healthy": True}

        try:
            with ThreadPoolExecutor(max_workers=8) as pool:
                assert all(pool.map(request_status, range(40)))
        finally:
            server.stop()
            db.close()
    print("REMOTE_CONCURRENCY_OK")


if __name__ == "__main__":
    run()
