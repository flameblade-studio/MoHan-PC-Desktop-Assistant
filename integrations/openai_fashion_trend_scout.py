from __future__ import annotations

"""Privacy-bounded OpenAI web-search adapter for wardrobe inspiration."""

lazy import json
lazy from dataclasses import dataclass
lazy from typing import Protocol
lazy from urllib.parse import urlparse
lazy from urllib.request import Request, urlopen

lazy from application.self_generating_wardrobe import (
    FashionTrendSignal,
    OutfitCreationRequest,
)

RESPONSES_URL = "https://api.openai.com/v1/responses"
MAX_RESPONSE_BYTES = 1024 * 1024
MAX_TREND_SIGNALS = 3
MAX_TRAITS_PER_SIGNAL = 4
MAX_SOURCE_URL_LENGTH = 2048
DEFAULT_TIMEOUT_SECONDS = 30.0
INSPIRATION_LICENSE_NOTE = (
    "Use source material for abstract trend inspiration and create original design assets."
)


class TrendSearchTransport(Protocol):
    def create(self, payload: dict[str, object]) -> object: ...


@dataclass(frozen=True, slots=True)
class OpenAIFashionTrendOptions:
    api_key: str
    model: str
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise ValueError("Provide an API key for fashion trend search.")
        if not self.model.strip():
            raise ValueError("Provide a model for fashion trend search.")
        if self.timeout_seconds <= 0:
            raise ValueError("Set the fashion trend search timeout above zero.")


class OpenAIResponsesTrendTransport:
    def __init__(self, options: OpenAIFashionTrendOptions) -> None:
        self._options = options

    def create(self, payload: dict[str, object]) -> object:
        request = Request(
            RESPONSES_URL,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._options.api_key.strip()}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(request, timeout=self._options.timeout_seconds) as response:
            body = response.read(MAX_RESPONSE_BYTES + 1)
        if len(body) > MAX_RESPONSE_BYTES:
            raise ValueError("Fashion trend response is larger than the 1 MB limit.")
        document = json.loads(body.decode("utf-8"))
        if not isinstance(document, dict):
            raise TypeError("Fashion trend response needs object format.")
        return document


class OpenAIFashionTrendScout:
    """Search only the five context fields explicitly approved by the user.

    Search errors produce an empty signal set, after which the outfit flow
    continues with MoHan's own creative direction. Web search remains optional
    for outfit generation.
    """

    def __init__(
        self,
        options: OpenAIFashionTrendOptions,
        transport: TrendSearchTransport | None = None,
    ) -> None:
        self._options = options
        self._transport = transport or OpenAIResponsesTrendTransport(options)
        self.last_status = "not-run"

    def discover(
        self,
        request: OutfitCreationRequest,
    ) -> tuple[FashionTrendSignal, ...]:
        try:
            document = self._transport.create(self._payload(request))
            signals = _parse_signals(_response_output_text(document))
        except (OSError, TimeoutError, TypeError, ValueError):
            self.last_status = "failed"
            return ()
        self.last_status = "completed" if signals else "empty"
        return signals

    def _payload(self, request: OutfitCreationRequest) -> dict[str, object]:
        # This is the complete external context boundary. Keep camera,
        # conversation, identity, location, memory, and arbitrary prompt data
        # outside this payload.
        context = {
            "weather": request.weather,
            "temperature_c": round(float(request.temperature_c), 1),
            "mood": request.mood,
            "occasion": request.occasion,
            "language": request.language,
        }
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "signals": {
                    "type": "array",
                    "maxItems": MAX_TREND_SIGNALS,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "source_url": {"type": "string"},
                            "title": {"type": "string"},
                            "abstract_traits": {
                                "type": "array",
                                "minItems": 1,
                                "maxItems": MAX_TRAITS_PER_SIGNAL,
                                "items": {"type": "string"},
                            },
                        },
                        "required": ["source_url", "title", "abstract_traits"],
                    },
                }
            },
            "required": ["signals"],
        }
        return {
            "model": self._options.model.strip(),
            "store": False,
            "max_output_tokens": 700,
            "max_tool_calls": 1,
            "tools": [{"type": "web_search", "search_context_size": "low"}],
            "tool_choice": "auto",
            "include": ["web_search_call.action.sources"],
            "instructions": (
                "Find up to three current fashion trend signals useful only as "
                "abstract inspiration for an original, non-infringing garment. "
                "Use web search. Return concrete source URLs and short abstract "
                "traits such as palette, silhouette, material mood or layering. "
                "Treat named products, artwork, characters, textile patterns, and "
                "protected designs as reference context only: extract abstract traits "
                "and create an original garment. Keep personal information outside "
                "the search context."
            ),
            "input": (
                "Search fashion trends appropriate to this approved context only: "
                + json.dumps(context, ensure_ascii=False, sort_keys=True)
            ),
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "mohan_fashion_trend_signals",
                    "strict": True,
                    "schema": schema,
                }
            },
        }


def create_openai_fashion_trend_scout(
    api_key: str,
    model: str,
) -> OpenAIFashionTrendScout:
    """Production composition hook; callers depend on the application port."""

    return OpenAIFashionTrendScout(OpenAIFashionTrendOptions(api_key, model))


def _response_output_text(document: object) -> str:
    if not isinstance(document, dict):
        raise TypeError("Responses API document needs object format.")
    direct = document.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct
    chunks = []
    output = document.get("output", [])
    if not isinstance(output, list):
        raise TypeError("Responses API output needs list format.")
    for item in output:
        if not isinstance(item, dict):
            continue
        content = item.get("content", [])
        if not isinstance(content, list):
            continue
        chunks.extend(
            value.get("text", "")
            for value in content
            if isinstance(value, dict) and value.get("type") == "output_text"
        )
    text = "".join(value for value in chunks if isinstance(value, str))
    if not text.strip():
        raise ValueError("Responses API returned empty trend text.")
    return text


def _parse_signals(text: str) -> tuple[FashionTrendSignal, ...]:
    value = json.loads(text)
    if not isinstance(value, dict) or not isinstance(value.get("signals"), list):
        raise ValueError("Fashion trend output needs the declared schema.")
    signals = []
    seen_urls: set[str] = set()
    for item in value["signals"][:MAX_TREND_SIGNALS]:
        if not isinstance(item, dict):
            continue
        source_url = str(item.get("source_url", "")).strip()
        parsed = urlparse(source_url)
        if (
            parsed.scheme != "https"
            or not parsed.netloc
            or len(source_url) > MAX_SOURCE_URL_LENGTH
        ):
            continue
        title = str(item.get("title", "")).strip()[:160]
        raw_traits = item.get("abstract_traits", [])
        if not title or not isinstance(raw_traits, list):
            continue
        traits = tuple(
            trait
            for trait in (
                str(raw).strip()[:120]
                for raw in raw_traits[:MAX_TRAITS_PER_SIGNAL]
            )
            if trait
        )
        if not traits or source_url in seen_urls:
            continue
        seen_urls.add(source_url)
        signals.append(
            FashionTrendSignal(
                source_url,
                title,
                traits,
                INSPIRATION_LICENSE_NOTE,
            )
        )
    return tuple(signals)
