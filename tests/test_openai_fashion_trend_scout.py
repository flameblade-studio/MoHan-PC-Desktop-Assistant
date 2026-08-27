from __future__ import annotations

lazy import json
lazy from datetime import UTC, datetime
lazy from urllib.error import HTTPError

lazy from application.self_generating_wardrobe import OutfitCreationRequest
lazy from integrations.openai_fashion_trend_scout import (
    INSPIRATION_LICENSE_NOTE,
    OpenAIFashionTrendOptions,
    OpenAIFashionTrendScout,
)


class _RecordingTransport:
    def __init__(self, response: object) -> None:
        self.response = response
        self.payload: dict[str, object] | None = None

    def create(self, payload: dict[str, object]) -> object:
        self.payload = payload
        return self.response


class _FailingTransport:
    def create(self, payload: dict[str, object]) -> object:
        del payload
        raise OSError("offline")


def _request() -> OutfitCreationRequest:
    return OutfitCreationRequest(
        job_id="privacy-test",
        language="zh-TW",
        weather="rain",
        temperature_c=23.26,
        mood="joyful",
        occasion="work",
        creative_direction=(
            "DO-NOT-SEND camera conversation identity location memory secret"
        ),
        requested_at=datetime(2026, 8, 23, tzinfo=UTC),
        accessory_direction="DO-NOT-SEND-ACCESSORY",
    )


def test_search_sends_only_the_five_consent_fields() -> None:
    transport = _RecordingTransport(
        {
            "output_text": json.dumps(
                {
                    "signals": [
                        {
                            "source_url": "https://example.com/fashion",
                            "title": "Layered blue tailoring",
                            "abstract_traits": ["blue-silver", "layered silhouette"],
                        }
                    ]
                }
            )
        }
    )
    scout = OpenAIFashionTrendScout(
        OpenAIFashionTrendOptions("test-key", "gpt-test"), transport
    )

    signals = scout.discover(_request())

    assert transport.payload is not None
    payload_text = json.dumps(transport.payload, ensure_ascii=False)
    assert transport.payload["store"] is False
    assert transport.payload["max_tool_calls"] == 1
    assert transport.payload["tools"] == [
        {"type": "web_search", "search_context_size": "low"}
    ]
    input_text = str(transport.payload["input"])
    approved_context = json.loads(input_text[input_text.index("{") :])
    assert approved_context == {
        "weather": "rain",
        "temperature_c": 23.3,
        "mood": "joyful",
        "occasion": "work",
        "language": "zh-TW",
    }
    for forbidden in (
        "DO-NOT-SEND",
        "camera",
        "conversation",
        "identity",
        "location",
        "memory",
        "ACCESSORY",
    ):
        assert forbidden not in payload_text
    assert len(signals) == 1
    assert signals[0].license_note == INSPIRATION_LICENSE_NOTE
    assert scout.last_status == "completed"


def test_invalid_or_duplicate_sources_are_discarded() -> None:
    transport = _RecordingTransport(
        {
            "output_text": json.dumps(
                {
                    "signals": [
                        {
                            "source_url": "http://insecure.example/fashion",
                            "title": "Insecure",
                            "abstract_traits": ["discard"],
                        },
                        {
                            "source_url": "https://example.com/fashion",
                            "title": "Valid",
                            "abstract_traits": ["clean lines"],
                        },
                        {
                            "source_url": "https://example.com/fashion",
                            "title": "Duplicate",
                            "abstract_traits": ["discard"],
                        },
                    ]
                }
            )
        }
    )
    scout = OpenAIFashionTrendScout(
        OpenAIFashionTrendOptions("test-key", "gpt-test"), transport
    )

    signals = scout.discover(_request())

    assert [signal.title for signal in signals] == ["Valid"]


def test_search_failure_degrades_to_no_trends() -> None:
    scout = OpenAIFashionTrendScout(
        OpenAIFashionTrendOptions("test-key", "gpt-test"),
        _FailingTransport(),
    )

    assert scout.discover(_request()) == ()
    assert scout.last_status == "failed"


def test_provider_failures_and_malformed_documents_degrade_without_detail() -> None:
    failures = (
        TimeoutError("private timeout detail"),
        HTTPError("https://api.openai.com", 401, "secret", None, None),
        HTTPError("https://api.openai.com", 429, "secret", None, None),
        HTTPError("https://api.openai.com", 503, "secret", None, None),
        ValueError("malformed private JSON"),
    )

    class FailureTransport:
        def __init__(self, error: BaseException) -> None:
            self.error = error

        def create(self, payload: dict[str, object]) -> object:
            del payload
            raise self.error

    for error in failures:
        scout = OpenAIFashionTrendScout(
            OpenAIFashionTrendOptions("secret-key", "gpt-test"),
            FailureTransport(error),
        )
        assert scout.discover(_request()) == ()
        assert scout.last_status == "failed"
