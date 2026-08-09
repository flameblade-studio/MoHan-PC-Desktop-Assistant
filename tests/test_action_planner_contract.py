lazy import io
lazy import json
lazy import sys
lazy from pathlib import Path
lazy from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from ai_client import ActionPlannerWorker


def run() -> None:
    plans = []
    worker = ActionPlannerWorker(
        "請幫我開啟工作網站",
        api_key="sk-test",
        model="gpt-5.4-mini",
        available_targets="- web：工作網站＝https://example.com",
    )
    worker.signals.done.connect(plans.append)
    response = io.BytesIO(
        json.dumps(
            {
                "output": [
                    {
                        "type": "function_call",
                        "name": "propose_action_plan",
                        "arguments": json.dumps(
                            {
                                "title": "開啟工作網站",
                                "steps": [
                                    {
                                        "capability": "open_web",
                                        "description": "開啟工作網站",
                                        "arguments_json": json.dumps(
                                            {"url": "https://example.com"}
                                        ),
                                        "reversible": False,
                                    }
                                ],
                            },
                            ensure_ascii=False,
                        ),
                    }
                ]
            },
            ensure_ascii=False,
        ).encode("utf-8")
    )
    with patch(
        "ai_client.urlopen",
        return_value=response,
    ) as mocked:
        worker.run()
    payload = json.loads(mocked.call_args.args[0].data.decode("utf-8"))
    assert payload["store"] is False
    assert payload["tool_choice"]["name"] == "propose_action_plan"
    assert payload["tools"][0]["strict"] is True
    capabilities = payload["tools"][0]["parameters"]["properties"]["steps"][
        "items"
    ]["properties"]["capability"]["enum"]
    assert "arbitrary_shell" not in capabilities
    assert "payment" not in capabilities
    assert plans[0]["steps"][0]["capability"] == "open_web"
    assert plans[0]["steps"][0]["arguments"]["url"] == "https://example.com"

    errors = []
    timeout_worker = ActionPlannerWorker(
        "請幫我讀取郵件",
        api_key="sk-test",
        model="gpt-5.4-mini",
        available_targets="（目前沒有白名單目標）",
    )
    timeout_worker.signals.failed.connect(errors.append)
    with patch(
        "ai_client.urlopen",
        side_effect=TimeoutError("連線等待逾時"),
    ):
        timeout_worker.run()
    assert len(errors) == 1
    assert "TimeoutError" in errors[0]
    assert "連線等待逾時" in errors[0]
    print("ACTION_PLANNER_CONTRACT_OK")


if __name__ == "__main__":
    run()
