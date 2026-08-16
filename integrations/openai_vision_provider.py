from __future__ import annotations

lazy import base64
lazy import json
lazy import threading
lazy import time
lazy from collections.abc import Callable
lazy from dataclasses import dataclass
lazy from typing import Protocol
lazy from urllib.error import HTTPError, URLError
lazy from urllib.request import Request, urlopen

GPT56_VISION_MODELS = frozenset({
    "gpt-5.6-sol",
    "gpt-5.6-terra",
    "gpt-5.6-luna",
})
SUPPORTED_IMAGE_MEDIA_TYPES = frozenset({
    "image/jpeg",
    "image/png",
    "image/webp",
})


lazy from domain.openai_vision_preferences import VisionDetail
lazy from domain.vision_provider_contracts import (
    ClaimStatus,
    VisionFrameRequest,
    VisionProviderResult,
    VisionResultStatus,
    VisualClaim,
    VisualUnderstanding,
)

__all__ = (
    "GPT56_VISION_MODELS",
    "ClaimStatus",
    "OpenAIVisionLimits",
    "OpenAIVisionProvider",
    "OpenAIVisionRuntime",
    "VisionDetail",
    "VisionFrameRequest",
    "VisionProviderResult",
    "VisionResultStatus",
    "VisualClaim",
    "VisualUnderstanding",
    "create_openai_vision_provider",
)


@dataclass(frozen=True, slots=True)
class OpenAIVisionLimits:
    max_image_bytes: int = 8 * 1024 * 1024
    max_dimension: int = 4_096
    max_pixels: int = 12_000_000
    min_interval_seconds: float = 2.0
    timeout_seconds: float = 20.0
    max_prompt_characters: int = 4_000

    def __post_init__(self) -> None:
        values = (
            self.max_image_bytes,
            self.max_dimension,
            self.max_pixels,
            self.timeout_seconds,
            self.max_prompt_characters,
        )
        if any(value <= 0 for value in values) or self.min_interval_seconds < 0:
            raise ValueError("Vision limits must be positive.")


DEFAULT_VISION_LIMITS = OpenAIVisionLimits()


class ResponsesEndpoint(Protocol):
    def create(self, **request: object) -> object:
        raise NotImplementedError


class ResponsesClient(Protocol):
    responses: ResponsesEndpoint


class _ResponsePayload:
    def __init__(self, output_text: str) -> None:
        self.output_text = output_text


ModelSelector = Callable[[], str]
OriginalDetailPolicy = Callable[[str], bool]
Clock = Callable[[], float]


@dataclass(frozen=True, slots=True)
class OpenAIVisionRuntime:
    limits: OpenAIVisionLimits = DEFAULT_VISION_LIMITS
    original_detail_policy: OriginalDetailPolicy | None = None
    clock: Clock = time.monotonic
    unavailable_status: VisionResultStatus | None = None


DEFAULT_VISION_RUNTIME = OpenAIVisionRuntime()


class VisionServiceError(RuntimeError):
    def __init__(
        self,
        status: VisionResultStatus,
    ) -> None:
        super().__init__(status.value)
        self.status = status


_OUTPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["summary", "claims", "uncertainties"],
    "properties": {
        "summary": {"type": "string", "minLength": 1, "maxLength": 1000},
        "claims": {
            "type": "array",
            "maxItems": 32,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["text", "status", "confidence", "evidence"],
                "properties": {
                    "text": {"type": "string", "minLength": 1, "maxLength": 500},
                    "status": {
                        "type": "string",
                        "enum": [status.value for status in ClaimStatus],
                    },
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "evidence": {"type": "string", "maxLength": 500},
                },
            },
        },
        "uncertainties": {
            "type": "array",
            "maxItems": 16,
            "items": {"type": "string", "minLength": 1, "maxLength": 500},
        },
    },
}


class OpenAIVisionProvider:
    """Privacy-bounded Responses API adapter for occasional single-frame analysis."""

    def __init__(
        self,
        client: ResponsesClient | None,
        *,
        credential_available: bool,
        model_selector: ModelSelector,
        runtime: OpenAIVisionRuntime = DEFAULT_VISION_RUNTIME,
    ) -> None:
        self._client = client
        self._credential_available = credential_available
        self._model_selector = model_selector
        self._limits = runtime.limits
        self._original_detail_policy = (
            runtime.original_detail_policy or GPT56_VISION_MODELS.__contains__
        )
        self._clock = runtime.clock
        self._unavailable_status = runtime.unavailable_status
        self._lock = threading.Lock()
        self._cancelled_through = -1
        self._active_operation: int | None = None
        self._last_request_at: float | None = None

    def cancel(self, operation_id: int) -> None:
        if operation_id < 0:
            return
        with self._lock:
            self._cancelled_through = max(
                self._cancelled_through,
                operation_id,
            )

    def analyze(self, request: VisionFrameRequest) -> VisionProviderResult:
        model = (request.model or self._model_selector()).strip()
        preflight = self._validate(request, model) or self._availability_status()
        if preflight is not None:
            return self._result(request, model, preflight)
        if not self._begin(request.operation_id):
            return self._result(request, model, self._blocked_status(request.operation_id))
        try:
            if self._is_cancelled(request.operation_id):
                return self._result(
                    request,
                    model,
                    VisionResultStatus("cancelled"),
                )
            response = self._client.responses.create(  # type: ignore[union-attr]
                model=model,
                store=False,
                timeout=self._limits.timeout_seconds,
                input=[{
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": _vision_prompt(request.prompt)},
                        {
                            "type": "input_image",
                            "image_url": _data_url(request.image_bytes, request.media_type),
                            "detail": request.detail.value,
                        },
                    ],
                }],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "mohan_visual_understanding",
                        "strict": True,
                        "schema": _OUTPUT_SCHEMA,
                    }
                },
            )
            if self._is_cancelled(request.operation_id):
                return self._result(
                    request,
                    model,
                    VisionResultStatus("cancelled"),
                )
            understanding = _parse_response(response)
            return VisionProviderResult(
                request.operation_id,
                VisionResultStatus("success"),
                model,
                request.detail,
                understanding,
            )
        except (ConnectionError, OSError, RuntimeError, TypeError, ValueError) as error:
            return self._result(request, model, _classify_error(error))
        finally:
            self._finish(request.operation_id)

    def _validate(
        self,
        request: VisionFrameRequest,
        model: str,
    ) -> VisionResultStatus | None:
        limits = self._limits
        invalid = bool(
            request.operation_id < 0
            or not model
            or request.media_type not in SUPPORTED_IMAGE_MEDIA_TYPES
            or not request.image_bytes
            or len(request.image_bytes) > limits.max_image_bytes
            or not request.prompt.strip()
            or len(request.prompt.strip()) > limits.max_prompt_characters
            or (
                request.detail is VisionDetail.ORIGINAL
                and not self._original_detail_policy(model)
            )
        )
        invalid_dimensions = bool(
            request.width <= 0
            or request.height <= 0
            or request.width > limits.max_dimension
            or request.height > limits.max_dimension
            or request.width * request.height > limits.max_pixels
        )
        return (
            VisionResultStatus("invalid_input")
            if invalid or invalid_dimensions
            else None
        )

    def _availability_status(
        self,
    ) -> VisionResultStatus | None:
        if not self._credential_available:
            return VisionResultStatus("key_missing")
        if self._client is None:
            return (
                self._unavailable_status
                or VisionResultStatus("transport_unavailable")
            )
        return None

    def _begin(self, operation_id: int) -> bool:
        with self._lock:
            if (
                operation_id <= self._cancelled_through
                or self._active_operation is not None
            ):
                return False
            now = self._clock()
            if (
                self._last_request_at is not None
                and now - self._last_request_at < self._limits.min_interval_seconds
            ):
                return False
            self._last_request_at = now
            self._active_operation = operation_id
            return True

    def _blocked_status(
        self,
        operation_id: int,
    ) -> VisionResultStatus:
        with self._lock:
            return (
                VisionResultStatus("cancelled")
                if operation_id <= self._cancelled_through
                else VisionResultStatus("rate_limited")
            )

    def _is_cancelled(self, operation_id: int) -> bool:
        with self._lock:
            return operation_id <= self._cancelled_through

    def _finish(self, operation_id: int) -> None:
        with self._lock:
            if self._active_operation == operation_id:
                self._active_operation = None

    @staticmethod
    def _result(
        request: VisionFrameRequest,
        model: str,
        status: VisionResultStatus,
    ) -> VisionProviderResult:
        return VisionProviderResult(request.operation_id, status, model, request.detail)


def create_openai_vision_provider(
    api_key: str,
    *,
    model_selector: ModelSelector,
    limits: OpenAIVisionLimits = DEFAULT_VISION_LIMITS,
    original_detail_policy: OriginalDetailPolicy | None = None,
) -> OpenAIVisionProvider:
    """Create a Python 3.15-compatible Responses API adapter without a request."""

    key = api_key.strip()
    if not key:
        return OpenAIVisionProvider(
            None,
            credential_available=False,
            model_selector=model_selector,
            runtime=OpenAIVisionRuntime(limits, original_detail_policy),
        )
    return OpenAIVisionProvider(
        _HttpResponsesClient(key, limits.timeout_seconds),
        credential_available=True,
        model_selector=model_selector,
        runtime=OpenAIVisionRuntime(limits, original_detail_policy),
    )


class _HttpResponsesEndpoint:
    def __init__(self, api_key: str, timeout_seconds: float) -> None:
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    def create(self, **request: object) -> object:
        try:
            timeout = float(request.pop("timeout", self._timeout_seconds))
            payload = json.dumps(request, ensure_ascii=False).encode("utf-8")
            api_request = Request(
                "https://api.openai.com/v1/responses",
                data=payload,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urlopen(api_request, timeout=timeout) as response:
                document = json.load(response)
            return _ResponsePayload(_response_output_text(document))
        except HTTPError as error:
            raise VisionServiceError(_classify_http_status(error.code)) from None
        except URLError as error:
            reason = error.reason
            status = (
                VisionResultStatus("timed_out")
                if isinstance(reason, TimeoutError)
                else VisionResultStatus("network_unavailable")
            )
            raise VisionServiceError(status) from None


class _HttpResponsesClient:
    def __init__(self, api_key: str, timeout_seconds: float) -> None:
        self.responses = _HttpResponsesEndpoint(api_key, timeout_seconds)


def _response_output_text(document: object) -> str:
    if not isinstance(document, dict):
        raise TypeError("Responses API document must be an object.")
    direct = document.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct
    chunks = [
        *(
            content.get("text", "")
            for content in item.get("content", [])
            if isinstance(content, dict) and content.get("type") == "output_text"
        )
        for item in document.get("output", [])
        if isinstance(item, dict)
    ]
    return "".join(chunk for chunk in chunks if isinstance(chunk, str))


def _data_url(image_bytes: bytes, media_type: str) -> str:
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{media_type};base64,{encoded}"


def _vision_prompt(user_prompt: str) -> str:
    return (
        "Analyze only what is visible in this single image. Separate direct visual "
        "observations from inferences and uncertainty. Never identify a person, infer "
        "sensitive traits, or present an inference as fact. "
        + user_prompt.strip()
    )


def _parse_response(response: object) -> VisualUnderstanding:
    output_text = getattr(response, "output_text", None)
    if not isinstance(output_text, str) or not output_text.strip():
        raise ValueError("Vision response has no structured output.")
    value = json.loads(output_text)
    if not isinstance(value, dict):
        raise TypeError("Vision response must be an object.")
    summary = value.get("summary")
    claims = value.get("claims")
    uncertainties = value.get("uncertainties")
    if not isinstance(summary, str) or not isinstance(claims, list) or not isinstance(uncertainties, list):
        raise TypeError("Vision response fields have invalid types.")
    parsed_claims = tuple(_parse_claim(claim) for claim in claims)
    if not all(isinstance(item, str) for item in uncertainties):
        raise TypeError("Vision uncertainties must be strings.")
    return VisualUnderstanding(summary, parsed_claims, tuple(uncertainties))


def _parse_claim(value: object) -> VisualClaim:
    if not isinstance(value, dict):
        raise TypeError("Vision claim must be an object.")
    text = value.get("text")
    status = value.get("status")
    confidence = value.get("confidence")
    evidence = value.get("evidence")
    if (
        not isinstance(text, str)
        or not isinstance(status, str)
        or not isinstance(confidence, (int, float))
        or isinstance(confidence, bool)
        or not isinstance(evidence, str)
    ):
        raise TypeError("Vision claim fields have invalid types.")
    return VisualClaim(text, ClaimStatus(status), float(confidence), evidence)


def _classify_error(
    error: Exception,
) -> VisionResultStatus:
    if isinstance(error, VisionServiceError):
        return error.status
    name = type(error).__name__
    if isinstance(error, TimeoutError) or name in {"APITimeoutError", "ReadTimeout"}:
        return VisionResultStatus("timed_out")
    if isinstance(error, ConnectionError) or name in {"APIConnectionError", "ConnectError"}:
        return VisionResultStatus("network_unavailable")
    if name == "RateLimitError":
        return VisionResultStatus("rate_limited")
    if isinstance(error, (json.JSONDecodeError, TypeError, ValueError)):
        return VisionResultStatus("invalid_response")
    return VisionResultStatus("service_unavailable")


def _classify_http_status(
    status_code: int,
) -> VisionResultStatus:
    if status_code in {401, 403}:
        return VisionResultStatus("authentication_failed")
    if status_code == 429:
        return VisionResultStatus("rate_limited")
    return VisionResultStatus("service_unavailable")
