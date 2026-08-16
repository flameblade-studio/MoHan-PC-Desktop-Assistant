from __future__ import annotations

lazy import json
lazy import sys
lazy from io import BytesIO
lazy from pathlib import Path
lazy from types import SimpleNamespace
lazy from typing import Self
lazy from unittest.mock import patch
lazy from urllib.error import HTTPError, URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from integrations.openai_vision_provider import (
    GPT56_VISION_MODELS,
    ClaimStatus,
    OpenAIVisionLimits,
    OpenAIVisionProvider,
    OpenAIVisionRuntime,
    VisionDetail,
    VisionFrameRequest,
    VisionResultStatus,
    create_openai_vision_provider,
)


def assert_legacy_sdk_status_migrates_to_transport() -> None:
    assert VisionResultStatus("sdk_unavailable") is (
        VisionResultStatus.TRANSPORT_UNAVAILABLE
    )
    assert VisionResultStatus.SDK_UNAVAILABLE is (
        VisionResultStatus.TRANSPORT_UNAVAILABLE
    )
    assert VisionResultStatus.TRANSPORT_UNAVAILABLE.value == (
        "transport_unavailable"
    )


class FakeResponses:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self.error: Exception | None = None
        self.before_return = None

    def create(self, **request: object) -> object:
        self.calls.append(request)
        if self.error is not None:
            raise self.error
        if callable(self.before_return):
            self.before_return()
        output = {
            "summary": "A person is near a desk.",
            "claims": [
                {
                    "text": "A person is visible.",
                    "status": "observed",
                    "confidence": 0.9,
                    "evidence": "A human figure is visible in the frame.",
                },
                {
                    "text": "The person may be working.",
                    "status": "inferred",
                    "confidence": 0.55,
                    "evidence": "A desk and screen are nearby.",
                },
            ],
            "uncertainties": ["The person's activity cannot be confirmed."],
        }
        return SimpleNamespace(output_text=json.dumps(output))


class FakeClient:
    def __init__(self) -> None:
        self.responses = FakeResponses()


class Clock:
    def __init__(self) -> None:
        self.value = 100.0

    def __call__(self) -> float:
        return self.value


def frame(
    operation_id: int = 1,
    *,
    detail: VisionDetail | None = None,
    model: str | None = None,
    image_bytes: bytes = b"private-image",
) -> VisionFrameRequest:
    selected_detail = VisionDetail.AUTO if detail is None else detail
    return VisionFrameRequest(
        operation_id,
        image_bytes,
        640,
        480,
        "image/jpeg",
        "Describe useful visible context.",
        selected_detail,
        model,
    )


def provider(
    client: FakeClient | None = None,
    *,
    clock: Clock | None = None,
    credential_available: bool = True,
) -> OpenAIVisionProvider:
    return OpenAIVisionProvider(
        client or FakeClient(),
        credential_available=credential_available,
        model_selector=lambda: "gpt-5.6-luna",
        runtime=OpenAIVisionRuntime(
            OpenAIVisionLimits(min_interval_seconds=2.0),
            clock=clock or Clock(),
        ),
    )


def assert_responses_request_is_private_and_typed() -> None:
    client = FakeClient()
    result = provider(client).analyze(frame())
    assert result.succeeded
    assert result.model == "gpt-5.6-luna"
    assert result.understanding is not None
    assert result.understanding.model_reported
    assert not result.understanding.independently_verified
    assert result.understanding.claims[0].status is ClaimStatus.OBSERVED
    assert result.understanding.claims[1].status is ClaimStatus.INFERRED
    request = client.responses.calls[0]
    assert request["store"] is False
    assert request["timeout"] == 20.0
    content = request["input"][0]["content"]  # type: ignore[index]
    assert content[0]["type"] == "input_text"
    assert "present an inference as fact" in content[0]["text"]
    assert content[1]["type"] == "input_image"
    assert content[1]["image_url"].startswith("data:image/jpeg;base64,")
    assert content[1]["detail"] == "auto"
    assert "private-image" not in repr(request)
    assert request["text"]["format"]["strict"] is True  # type: ignore[index]


def assert_models_detail_and_injected_selection() -> None:
    for index, model in enumerate(sorted(GPT56_VISION_MODELS), start=1):
        client = FakeClient()
        result = provider(client).analyze(
            frame(index, model=model, detail=VisionDetail.ORIGINAL)
        )
        assert result.succeeded
        assert client.responses.calls[0]["model"] == model
    custom = provider().analyze(
        frame(8, model="existing-custom-model", detail=VisionDetail.ORIGINAL)
    )
    assert custom.status is VisionResultStatus.INVALID_INPUT
    client = FakeClient()
    enabled = OpenAIVisionProvider(
        client,
        credential_available=True,
        model_selector=lambda: "existing-custom-model",
        runtime=OpenAIVisionRuntime(
            original_detail_policy=lambda model: model == "existing-custom-model"
        ),
    ).analyze(frame(9, detail=VisionDetail.ORIGINAL))
    assert enabled.succeeded


def assert_limits_rate_timeout_cancel_and_errors() -> None:
    clock = Clock()
    client = FakeClient()
    service = provider(client, clock=clock)
    assert service.analyze(frame(1)).succeeded
    assert service.analyze(frame(2)).status is VisionResultStatus.RATE_LIMITED
    clock.value += 2.0
    service.cancel(3)
    assert service.analyze(frame(3)).status is VisionResultStatus.CANCELLED
    clock.value += 2.0
    oversized = frame(4, image_bytes=b"x" * (8 * 1024 * 1024 + 1))
    assert service.analyze(oversized).status is VisionResultStatus.INVALID_INPUT
    assert len(client.responses.calls) == 1

    for error, expected in (
        (TimeoutError("secret frame"), VisionResultStatus.TIMED_OUT),
        (ConnectionError("secret key"), VisionResultStatus.NETWORK_UNAVAILABLE),
        (RuntimeError("secret payload"), VisionResultStatus.SERVICE_UNAVAILABLE),
    ):
        isolated = FakeClient()
        isolated.responses.error = error
        result = provider(isolated).analyze(frame())
        assert result.status is expected
        assert "secret" not in repr(result)


def assert_cancel_during_request_discards_output() -> None:
    client = FakeClient()
    service = provider(client)
    client.responses.before_return = lambda: service.cancel(11)
    result = service.analyze(frame(11))
    assert result.status is VisionResultStatus.CANCELLED
    assert result.understanding is None


def assert_cancelled_and_active_operation_state_is_bounded() -> None:
    service = provider()
    for operation_id in range(10_000):
        service.cancel(operation_id)
    assert not hasattr(service, "_cancelled")
    assert service._cancelled_through == 9_999
    assert service.analyze(frame(0)).status is VisionResultStatus.CANCELLED

    clock = Clock()
    clock.value += 10.0
    fresh = provider(clock=clock)
    assert fresh.analyze(frame(10_000)).succeeded
    assert fresh._active_operation is None


def assert_invalid_remote_output_fails_closed() -> None:
    client = FakeClient()
    client.responses.before_return = None

    def invalid_create(**request: object) -> object:
        client.responses.calls.append(request)
        return SimpleNamespace(output_text='{"summary":"guess","claims":[')

    client.responses.create = invalid_create  # type: ignore[method-assign]
    result = provider(client).analyze(frame())
    assert result.status is VisionResultStatus.INVALID_RESPONSE
    assert result.understanding is None


def assert_missing_key_degrades_without_network() -> None:
    no_key = OpenAIVisionProvider(
        None,
        credential_available=False,
        model_selector=lambda: "gpt-5.6-luna",
    ).analyze(frame())
    assert no_key.status is VisionResultStatus.KEY_MISSING


class HttpResponse(BytesIO):
    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


def assert_http_factory_uses_responses_api_without_sdk() -> None:
    structured = json.dumps({
        "summary": "A person is near a desk.",
        "claims": [{
            "text": "A person is visible.",
            "status": "observed",
            "confidence": 0.9,
            "evidence": "A human figure is visible.",
        }],
        "uncertainties": [],
    })
    response_document = json.dumps({
        "output": [{
            "content": [{"type": "output_text", "text": structured}],
        }],
    }).encode("utf-8")
    captured = []

    def fake_urlopen(request: object, *, timeout: float) -> HttpResponse:
        captured.append((request, timeout))
        return HttpResponse(response_document)

    service = create_openai_vision_provider(
        "not-a-real-key",
        model_selector=lambda: "gpt-5.6-luna",
    )
    with patch("integrations.openai_vision_provider.urlopen", side_effect=fake_urlopen):
        result = service.analyze(frame())
    assert result.succeeded
    assert len(captured) == 1
    request, timeout = captured[0]
    assert request.full_url == "https://api.openai.com/v1/responses"
    assert timeout == 20.0
    payload = json.loads(request.data.decode("utf-8"))
    assert payload["store"] is False
    assert payload["model"] == "gpt-5.6-luna"
    assert "not-a-real-key" not in json.dumps(payload)


def assert_http_errors_are_sanitized() -> None:
    failures = (
        (
            HTTPError(
                "https://api.openai.com/v1/responses",
                401,
                "not-a-real-key private-image",
                {},
                None,
            ),
            VisionResultStatus.AUTHENTICATION_FAILED,
        ),
        (URLError("not-a-real-key private-image"), VisionResultStatus.NETWORK_UNAVAILABLE),
    )
    for error, expected in failures:
        service = create_openai_vision_provider(
            "not-a-real-key",
            model_selector=lambda: "gpt-5.6-luna",
        )
        with patch("integrations.openai_vision_provider.urlopen", side_effect=error):
            result = service.analyze(frame())
        assert result.status is expected
        assert "not-a-real-key" not in repr(result)
        assert "private-image" not in repr(result)


def run() -> None:
    assert_legacy_sdk_status_migrates_to_transport()
    assert_responses_request_is_private_and_typed()
    assert_models_detail_and_injected_selection()
    assert_limits_rate_timeout_cancel_and_errors()
    assert_cancel_during_request_discards_output()
    assert_cancelled_and_active_operation_state_is_bounded()
    assert_invalid_remote_output_fails_closed()
    assert_missing_key_degrades_without_network()
    assert_http_factory_uses_responses_api_without_sdk()
    assert_http_errors_are_sanitized()
    print("OPENAI_VISION_PROVIDER_OK")


if __name__ == "__main__":
    run()
