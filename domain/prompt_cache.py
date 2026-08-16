from __future__ import annotations

lazy import hashlib
lazy from collections.abc import Mapping
lazy from dataclasses import dataclass, field
lazy from typing import Any, Protocol

PROMPT_CACHE_SCHEMA = "mohan:chat:v1"
MINIMUM_EXPLICIT_PREFIX_TOKENS = 1_024
CACHE_READ_RATE = 0.10
CACHE_WRITE_RATE = 1.25
_EXACT_COUNT_ATTESTATION = sentinel("EXACT_COUNT_ATTESTATION")


@dataclass(frozen=True, slots=True)
class PromptCacheTelemetry:
    input_tokens: int = 0
    cached_tokens: int = 0
    cache_write_tokens: int = 0


@dataclass(frozen=True, slots=True)
class PromptCacheCostReport:
    input_tokens: int
    cached_tokens: int
    cache_write_tokens: int
    uncached_tokens: int
    baseline_cost_units: float
    actual_cost_units: float
    net_savings_units: float
    net_savings_ratio: float


@dataclass(frozen=True, slots=True)
class PromptCacheTokenEvidence:
    """Exact token evidence bound to one model and rendered stable prefix."""

    prefix_fingerprint: str
    exact_tokens: int
    _attestation: object = field(default=None, repr=False, compare=False)


class PromptTokenCounterPort(Protocol):
    """Boundary for POST /responses/input_tokens implementations."""

    def count_input_tokens(self, request: Mapping[str, Any]) -> int: ...


class InMemoryPromptTokenEvidence:
    """Count each stable-prefix fingerprint once without retaining content."""

    def __init__(self, counter: PromptTokenCounterPort) -> None:
        self._counter = counter
        self._attempted: set[str] = set()
        self._counts: dict[str, int] = {}

    def evidence_for(
        self,
        model: str,
        stable_instructions: str,
        stable_breakpoint_text: str,
    ) -> PromptCacheTokenEvidence | None:
        fingerprint = prompt_cache_prefix_fingerprint(
            model,
            stable_instructions,
            stable_breakpoint_text,
        )
        if fingerprint in self._attempted:
            exact_tokens = self._counts.get(fingerprint)
            return (
                _attested_token_evidence(fingerprint, exact_tokens)
                if exact_tokens is not None
                else None
            )
        self._attempted.add(fingerprint)
        try:
            exact_tokens = self._counter.count_input_tokens(
                exact_input_token_count_request(
                    model,
                    stable_instructions,
                    stable_breakpoint_text,
                )
            )
        except (OSError, RuntimeError, TypeError, ValueError):
            return None
        if type(exact_tokens) is not int or exact_tokens < 0:
            return None
        self._counts[fingerprint] = exact_tokens
        return _attested_token_evidence(fingerprint, exact_tokens)


def supports_explicit_prompt_cache(model: str) -> bool:
    normalized = model.strip().casefold()
    return normalized == "gpt-5.6" or normalized.startswith("gpt-5.6-")


def explicit_prompt_cache_eligible(
    model: str,
    stable_instructions: str,
    stable_breakpoint_text: str,
    evidence: PromptCacheTokenEvidence | None,
) -> bool:
    """Enable writes only when an exact external count proves eligibility."""

    return bool(
        supports_explicit_prompt_cache(model)
        and evidence is not None
        and evidence._attestation is _EXACT_COUNT_ATTESTATION
        and evidence.prefix_fingerprint
        == prompt_cache_prefix_fingerprint(
            model,
            stable_instructions,
            stable_breakpoint_text,
        )
        and type(evidence.exact_tokens) is int
        and evidence.exact_tokens >= MINIMUM_EXPLICIT_PREFIX_TOKENS
    )


def _attested_token_evidence(
    fingerprint: str,
    exact_tokens: int,
) -> PromptCacheTokenEvidence:
    return PromptCacheTokenEvidence(
        fingerprint,
        exact_tokens,
        _EXACT_COUNT_ATTESTATION,
    )


def explicit_prompt_cache_key(stable_prefix: str) -> str:
    """Return a stable routing key without retaining prompt or user content."""

    digest = hashlib.sha256(stable_prefix.encode("utf-8")).hexdigest()[:24]
    return f"{PROMPT_CACHE_SCHEMA}:{digest}"


def prompt_cache_prefix_fingerprint(
    model: str,
    stable_instructions: str,
    stable_breakpoint_text: str,
) -> str:
    """Bind exact token evidence to the complete cacheable request prefix."""

    material = "\0".join(
        (model.strip().casefold(), stable_instructions, stable_breakpoint_text)
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _stable_breakpoint_message(text: str) -> dict[str, Any]:
    return {
        "type": "message",
        "role": "developer",
        "content": [
            {
                "type": "input_text",
                "text": text,
                "prompt_cache_breakpoint": {"mode": "explicit"},
            }
        ],
    }


def exact_input_token_count_request(
    model: str,
    stable_instructions: str,
    stable_breakpoint_text: str,
) -> dict[str, Any]:
    """Render the exact stable Responses prefix for an injected token counter."""

    if not supports_explicit_prompt_cache(model):
        raise ValueError("Exact explicit-cache counting requires GPT-5.6.")
    if not stable_instructions.strip() or not stable_breakpoint_text.strip():
        raise ValueError("Stable developer content must not be empty.")
    return {
        "model": model,
        "instructions": stable_instructions,
        "input": [_stable_breakpoint_message(stable_breakpoint_text)],
    }


def explicit_prompt_cache_request(
    model: str,
    stable_prefix: str,
    stable_breakpoint_text: str,
    dynamic_developer_text: str,
    user_text: str,
) -> dict[str, Any]:
    if not supports_explicit_prompt_cache(model):
        raise ValueError("Explicit prompt caching requires a GPT-5.6 model.")
    if not stable_prefix.strip() or not stable_breakpoint_text.strip():
        raise ValueError("Stable developer content must not be empty.")
    return {
        "prompt_cache_key": explicit_prompt_cache_key(
            stable_prefix + "\n" + stable_breakpoint_text
        ),
        "prompt_cache_options": {"mode": "explicit"},
        "input": [
            _stable_breakpoint_message(stable_breakpoint_text),
            {
                "type": "message",
                "role": "developer",
                "content": [
                    {
                        "type": "input_text",
                        "text": dynamic_developer_text,
                    }
                ],
            },
            {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": user_text}],
            },
        ],
    }


def parse_prompt_cache_telemetry(response: object) -> PromptCacheTelemetry:
    """Extract numeric usage only; malformed telemetry is safely ignored."""

    try:
        if not isinstance(response, dict):
            return PromptCacheTelemetry()
        usage = response.get("usage")
        if not isinstance(usage, dict):
            return PromptCacheTelemetry()
        details = usage.get("input_tokens_details")
        if not isinstance(details, dict):
            details = {}
        return PromptCacheTelemetry(
            _nonnegative_integer(usage.get("input_tokens")),
            _nonnegative_integer(details.get("cached_tokens")),
            _nonnegative_integer(details.get("cache_write_tokens")),
        )
    except (ArithmeticError, TypeError, ValueError):
        return PromptCacheTelemetry()


def prompt_cache_cost_report(
    telemetry: PromptCacheTelemetry,
) -> PromptCacheCostReport:
    """Compare cache billing to the same input charged fully uncached."""

    input_tokens = _nonnegative_integer(telemetry.input_tokens)
    cached_tokens = _nonnegative_integer(telemetry.cached_tokens)
    cache_write_tokens = _nonnegative_integer(telemetry.cache_write_tokens)
    categorized = cached_tokens + cache_write_tokens
    if categorized > input_tokens:
        cached_tokens = 0
        cache_write_tokens = 0
        categorized = 0
    uncached_tokens = input_tokens - categorized
    baseline = float(input_tokens)
    actual = (
        uncached_tokens
        + cached_tokens * CACHE_READ_RATE
        + cache_write_tokens * CACHE_WRITE_RATE
    )
    savings = baseline - actual
    ratio = savings / baseline if baseline else 0.0
    return PromptCacheCostReport(
        input_tokens,
        cached_tokens,
        cache_write_tokens,
        uncached_tokens,
        baseline,
        actual,
        savings,
        ratio,
    )


def _nonnegative_integer(value: object) -> int:
    return value if type(value) is int and value >= 0 else 0
