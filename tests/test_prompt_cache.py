from __future__ import annotations

lazy import io
lazy import json
lazy import sys
lazy from pathlib import Path
lazy from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from domain.expression_system import INTERNAL_EMOTION_INSTRUCTION
lazy from integrations.ai_client import (
    STABLE_PROMPT_CACHE_BREAKPOINT,
    ActionPlannerWorker,
    AIWorker,
    AIWorkerRequest,
)
lazy from domain.language_support import response_language_instruction
lazy from domain.prompt_cache import (
    InMemoryPromptTokenEvidence,
    PromptCacheTelemetry,
    PromptCacheTokenEvidence,
    exact_input_token_count_request,
    explicit_prompt_cache_eligible,
    explicit_prompt_cache_key,
    parse_prompt_cache_telemetry,
    prompt_cache_cost_report,
    prompt_cache_prefix_fingerprint,
)

lazy from integrations.ai_client import REQUEST_TIMEOUT_SECONDS
EXACT_TOKEN_COUNT = 1024
SHORT_TOKEN_COUNT = 1023
CACHE_KEY_MAX_LENGTH = 64
EXPECTED_BASELINE_COST_UNITS = 1024.0
EXPECTED_ACTUAL_COST_UNITS = 1280.0
EXPECTED_NET_SAVINGS_UNITS = -256.0
EXPECTED_CACHE_HIT_ACTUAL_COST = 102.4
EXPECTED_CACHE_HIT_NET_SAVINGS = 921.6
EXPECTED_UNCACHED_TOKEN_COUNT = 400
EXPECTED_MIXED_ACTUAL_COST = 830.0
EXPECTED_MIXED_NET_SAVINGS = 1570.0


class Response(io.BytesIO):
    pass


class FakeTokenCounter:
    def __init__(self, result: int | Exception) -> None:
        self.result = result
        self.requests: list[dict] = []

    def count_input_tokens(self, request: dict) -> int:
        self.requests.append(request)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def verified_evidence(
    *,
    model: str = "gpt-5.6-luna",
    stable_instructions: str,
    breakpoint_text: str,
    tokens: int = 1024,
) -> PromptCacheTokenEvidence:
    evidence = InMemoryPromptTokenEvidence(FakeTokenCounter(tokens)).evidence_for(
        model,
        stable_instructions,
        breakpoint_text,
    )
    assert evidence is not None
    return evidence


def response(*, cached: int = 0, written: int = 0) -> Response:
    return Response(
        json.dumps(
            {
                "output_text": "同一語意的回答",
                "usage": {
                    "input_tokens": 2400,
                    "input_tokens_details": {
                        "cached_tokens": cached,
                        "cache_write_tokens": written,
                    },
                },
            }
        ).encode("utf-8")
    )


def captured_worker_payload(request: AIWorkerRequest) -> tuple[dict, list[str]]:
    payloads: list[dict] = []
    answers: list[str] = []

    def open_request(http_request, *, timeout: int):
        assert timeout == REQUEST_TIMEOUT_SECONDS
        payloads.append(json.loads(http_request.data.decode("utf-8")))
        return response(cached=1800, written=200)

    worker = AIWorker(request)
    worker.signals.done.connect(answers.append)
    with patch("integrations.ai_client.urlopen", open_request):
        worker.run()
    assert len(payloads) == 1
    return payloads[0], answers


def assert_gpt_56_uses_explicit_stable_prefix_only() -> None:
    private_name = "PRIVATE-NAME-FIXTURE"
    private_memory = "PRIVATE-MEMORY-FIXTURE"
    payload, answers = captured_worker_payload(
        AIWorkerRequest(
            "動態使用者輸入",
            "工作",
            history=({"role": "user", "content": "動態對話"},),
            api_key="not-a-real-key",
            memories=private_memory,
            model="gpt-5.6-luna",
            persona=f"穩定角色規則。{private_name}。" * 1200,
            user_title=private_name,
            prompt_cache_token_evidence=verified_evidence(
                stable_instructions=(
                    response_language_instruction("zh-TW")
                    + "\n\n## 內部表情控制\n"
                    + INTERNAL_EMOTION_INSTRUCTION
                ),
                breakpoint_text=STABLE_PROMPT_CACHE_BREAKPOINT,
            ),
        )
    )
    assert answers == ["同一語意的回答"]
    assert payload["store"] is False
    assert payload["prompt_cache_options"] == {"mode": "explicit"}
    assert "prompt_cache_retention" not in payload
    assert "ttl" not in payload["prompt_cache_options"]
    assert payload["prompt_cache_key"].startswith("mohan:chat:v1:")
    assert private_name not in payload["prompt_cache_key"]
    assert private_memory not in payload["prompt_cache_key"]
    assert [message["role"] for message in payload["input"]] == [
        "developer",
        "developer",
        "user",
    ]
    stable = payload["input"][0]["content"][0]
    dynamic = payload["input"][1]["content"][0]["text"]
    user = payload["input"][2]["content"][0]["text"]
    assert stable["prompt_cache_breakpoint"] == {"mode": "explicit"}
    assert "穩定前綴" in stable["text"]
    assert private_name not in stable["text"]
    assert private_memory not in stable["text"]
    assert private_name not in payload["instructions"]
    assert private_memory not in payload["instructions"]
    assert private_name in dynamic and private_memory in dynamic
    assert "動態對話" in user and "動態使用者輸入" in user


def assert_non_gpt_56_keeps_legacy_request_shape() -> None:
    payload, answers = captured_worker_payload(
        AIWorkerRequest(
            "hello",
            "工作",
            api_key="not-a-real-key",
            model="gpt-5.5",
            persona="legacy persona",
        )
    )
    assert answers == ["同一語意的回答"]
    assert isinstance(payload["instructions"], str)
    assert isinstance(payload["input"], str)
    assert not any(key.startswith("prompt_cache") for key in payload)
    assert payload["store"] is False


def assert_unverified_or_short_prefix_never_creates_cache_write() -> None:
    for evidence in (
        None,
        PromptCacheTokenEvidence("wrong-prefix", 4096),
        PromptCacheTokenEvidence("wrong-prefix", 1023),
    ):
        payload, answers = captured_worker_payload(
            AIWorkerRequest(
                "動態輸入",
                "工作",
                api_key="not-a-real-key",
                model="gpt-5.6-luna",
                persona="有意義但未證明達門檻的固定規則。" * 100,
                prompt_cache_token_evidence=evidence,
            )
        )
        assert answers == ["同一語意的回答"]
        assert not any(key.startswith("prompt_cache") for key in payload)
        assert isinstance(payload["instructions"], str)
        assert isinstance(payload["input"], str)
    stable = "stable instructions"
    breakpoint = "stable breakpoint"
    evidence = verified_evidence(
        stable_instructions=stable,
        breakpoint_text=breakpoint,
    )
    assert explicit_prompt_cache_eligible(
        "gpt-5.6-luna", stable, breakpoint, evidence
    )
    assert not explicit_prompt_cache_eligible(
        "gpt-5.5", stable, breakpoint, evidence
    )
    forged = PromptCacheTokenEvidence(
        prompt_cache_prefix_fingerprint("gpt-5.6-luna", stable, breakpoint),
        4096,
    )
    assert not explicit_prompt_cache_eligible(
        "gpt-5.6-luna", stable, breakpoint, forged
    )


def assert_exact_count_evidence_is_injected_counted_once_and_fail_closed() -> None:
    stable = "stable instructions"
    breakpoint = "stable breakpoint"
    counter = FakeTokenCounter(1024)
    evidence_cache = InMemoryPromptTokenEvidence(counter)
    first = evidence_cache.evidence_for("gpt-5.6-luna", stable, breakpoint)
    second = evidence_cache.evidence_for("gpt-5.6-luna", stable, breakpoint)
    assert first == second
    assert first is not None and first.exact_tokens == EXACT_TOKEN_COUNT
    assert len(counter.requests) == 1
    assert counter.requests[0] == exact_input_token_count_request(
        "gpt-5.6-luna", stable, breakpoint
    )
    assert "prompt_cache_options" not in counter.requests[0]
    assert "prompt_cache_key" not in counter.requests[0]

    failed_counter = FakeTokenCounter(OSError("token endpoint unavailable"))
    failed_cache = InMemoryPromptTokenEvidence(failed_counter)
    assert failed_cache.evidence_for("gpt-5.6-luna", stable, breakpoint) is None
    assert failed_cache.evidence_for("gpt-5.6-luna", stable, breakpoint) is None
    assert len(failed_counter.requests) == 1

    short_counter = FakeTokenCounter(1023)
    short_cache = InMemoryPromptTokenEvidence(short_counter)
    short = short_cache.evidence_for("gpt-5.6-luna", stable, breakpoint)
    assert short is not None and short.exact_tokens == SHORT_TOKEN_COUNT
    assert not explicit_prompt_cache_eligible(
        "gpt-5.6-luna", stable, breakpoint, short
    )


def assert_cache_key_is_stable_private_and_prefix_specific() -> None:
    first = explicit_prompt_cache_key("stable prefix")
    assert first == explicit_prompt_cache_key("stable prefix")
    assert first != explicit_prompt_cache_key("changed prefix")
    assert "stable prefix" not in first
    assert len(first) <= CACHE_KEY_MAX_LENGTH


def assert_usage_is_numeric_only_and_malformed_usage_degrades_to_zero() -> None:
    telemetry = parse_prompt_cache_telemetry(
        {
            "usage": {
                "input_tokens": 2400,
                "input_tokens_details": {
                    "cached_tokens": 1800,
                    "cache_write_tokens": 200,
                    "content": "must never be retained",
                },
            }
        }
    )
    assert telemetry == PromptCacheTelemetry(2400, 1800, 200)
    assert not hasattr(telemetry, "content")
    assert parse_prompt_cache_telemetry({"usage": "invalid"}) == (
        PromptCacheTelemetry(0, 0, 0)
    )


def assert_telemetry_failure_never_changes_answer() -> None:
    answers: list[str] = []

    def broken_sink(_telemetry: PromptCacheTelemetry) -> None:
        raise RuntimeError("telemetry unavailable")

    worker = AIWorker(
        AIWorkerRequest(
            "hello",
            "工作",
            api_key="not-a-real-key",
            model="gpt-5.6-sol",
            persona="stable rules " * 1500,
            prompt_cache_telemetry=broken_sink,
            prompt_cache_token_evidence=PromptCacheTokenEvidence(
                "unmatched-prefix",
                1024,
            ),
        )
    )
    worker.signals.done.connect(answers.append)
    with patch("integrations.ai_client.urlopen", lambda *_args, **_kwargs: response(cached=1024)):
        worker.run()
    assert answers == ["同一語意的回答"]


def assert_action_planner_remains_uncached() -> None:
    payloads: list[dict] = []
    planner = ActionPlannerWorker(
        "開啟記事本",
        api_key="not-a-real-key",
        model="gpt-5.6-luna",
        available_targets="notepad",
    )

    def open_request(http_request, *, timeout: int):
        assert timeout == REQUEST_TIMEOUT_SECONDS
        payloads.append(json.loads(http_request.data.decode("utf-8")))
        return Response(
            json.dumps(
                {
                    "output": [
                        {
                            "type": "function_call",
                            "name": "propose_action_plan",
                            "arguments": '{"title":"plan","steps":[]}',
                        }
                    ]
                }
            ).encode("utf-8")
        )

    with patch("integrations.ai_client.urlopen", open_request):
        planner.run()
    assert len(payloads) == 1
    assert not any(key.startswith("prompt_cache") for key in payloads[0])
    assert payloads[0]["store"] is False


def assert_cost_report_proves_write_loss_and_later_net_savings() -> None:
    first_write = prompt_cache_cost_report(PromptCacheTelemetry(1024, 0, 1024))
    assert first_write.baseline_cost_units == EXPECTED_BASELINE_COST_UNITS
    assert first_write.actual_cost_units == EXPECTED_ACTUAL_COST_UNITS
    assert first_write.net_savings_units == EXPECTED_NET_SAVINGS_UNITS
    cache_hit = prompt_cache_cost_report(PromptCacheTelemetry(1024, 1024, 0))
    assert cache_hit.actual_cost_units == EXPECTED_CACHE_HIT_ACTUAL_COST
    assert cache_hit.net_savings_units == EXPECTED_CACHE_HIT_NET_SAVINGS
    cumulative_savings = (
        first_write.net_savings_units + cache_hit.net_savings_units
    )
    assert cumulative_savings > 0.0
    mixed = prompt_cache_cost_report(PromptCacheTelemetry(2400, 1800, 200))
    assert mixed.uncached_tokens == EXPECTED_UNCACHED_TOKEN_COUNT
    assert mixed.actual_cost_units == EXPECTED_MIXED_ACTUAL_COST
    assert mixed.net_savings_units == EXPECTED_MIXED_NET_SAVINGS
    invalid = prompt_cache_cost_report(PromptCacheTelemetry(10, 9, 9))
    assert invalid.cached_tokens == 0
    assert invalid.cache_write_tokens == 0
    assert invalid.actual_cost_units == invalid.baseline_cost_units


def run() -> None:
    assert_gpt_56_uses_explicit_stable_prefix_only()
    assert_non_gpt_56_keeps_legacy_request_shape()
    assert_unverified_or_short_prefix_never_creates_cache_write()
    assert_exact_count_evidence_is_injected_counted_once_and_fail_closed()
    assert_cache_key_is_stable_private_and_prefix_specific()
    assert_usage_is_numeric_only_and_malformed_usage_degrades_to_zero()
    assert_telemetry_failure_never_changes_answer()
    assert_action_planner_remains_uncached()
    assert_cost_report_proves_write_loss_and_later_net_savings()
    print("PROMPT_CACHE_OK")


if __name__ == "__main__":
    run()
