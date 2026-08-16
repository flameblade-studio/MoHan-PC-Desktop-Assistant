from __future__ import annotations

lazy import json
lazy import sqlite3
lazy import sys
lazy import time
lazy from pathlib import Path
lazy from urllib.error import HTTPError
lazy from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from infrastructure.secret_store import SecretStore
lazy from integrations.ai_client import ActionPlannerWorker
lazy from safe_error import sanitize_error


def main(data_path_text: str) -> int:
    data_path = Path(data_path_text).resolve()
    key = SecretStore(data_path / "openai-key.dpapi").load().strip()
    if not key:
        print("KEY=missing")
        return 2
    print(f"KEY=present,length={len(key)}")

    connection = sqlite3.connect(
        f"{(data_path / 'mohan.db').as_uri()}?mode=ro",
        uri=True,
    )
    try:
        row = connection.execute(
            "SELECT value FROM settings WHERE key='ai_model'"
        ).fetchone()
        model = json.loads(row[0]) if row else "gpt-5.6-luna"
    finally:
        connection.close()
    print(f"MODEL={model}")

    model_request = Request(
        f"https://api.openai.com/v1/models/{model}",
        headers={"Authorization": f"Bearer {key}"},
    )
    started = time.monotonic()
    try:
        with urlopen(model_request, timeout=15) as response:
            payload = json.load(response)
        print(
            f"MODEL_CHECK=ok,id={payload.get('id')},"
            f"elapsed={time.monotonic() - started:.2f}s"
        )
    except HTTPError as exc:
        error = sanitize_error(exc, http_status=exc.code)
        print(
            f"MODEL_CHECK=failed,{error},"
            f"elapsed={time.monotonic() - started:.2f}s"
        )
        return 3
    except Exception as exc:  # noqa: BLE001 -- external errors become finite metadata
        error = sanitize_error(exc)
        print(
            f"MODEL_CHECK=failed,{error},"
            f"elapsed={time.monotonic() - started:.2f}s"
        )
        return 4

    plans: list[dict] = []
    errors: list[str] = []
    worker = ActionPlannerWorker(
        "請執行：搜尋最近七天的 Gmail 郵件，最多三封，只讀取。",
        api_key=key,
        model=str(model),
        available_targets="（目前沒有本機白名單目標）",
        source="diagnostic",
    )
    worker.signals.done.connect(plans.append)
    worker.signals.failed.connect(errors.append)
    started = time.monotonic()
    worker.run()
    elapsed = time.monotonic() - started
    if errors:
        error = sanitize_error(errors[0])
        print(f"PLANNER=failed,{error},elapsed={elapsed:.2f}s")
        return 5
    if not plans:
        print(f"PLANNER=no_signal,elapsed={elapsed:.2f}s")
        return 6
    steps = plans[0].get("steps", [])
    capabilities = [
        step.get("capability")
        for step in steps
        if isinstance(step, dict)
    ]
    print(
        f"PLANNER=ok,elapsed={elapsed:.2f}s,"
        f"capabilities={capabilities}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
