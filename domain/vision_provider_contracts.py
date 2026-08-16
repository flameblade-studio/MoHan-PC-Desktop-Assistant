"""Provider-neutral contracts shared by cloud-vision adapters and policies."""

from __future__ import annotations

lazy import math
lazy from dataclasses import dataclass
lazy from enum import StrEnum

lazy from domain.openai_vision_preferences import VisionDetail


class ClaimStatus(StrEnum):
    OBSERVED = "observed"
    INFERRED = "inferred"
    UNCERTAIN = "uncertain"


class VisionResultStatus(StrEnum):
    SUCCESS = "success"
    KEY_MISSING = "key_missing"
    AUTHENTICATION_FAILED = "authentication_failed"
    TRANSPORT_UNAVAILABLE = "transport_unavailable"
    SDK_UNAVAILABLE = "transport_unavailable"
    NETWORK_UNAVAILABLE = "network_unavailable"
    RATE_LIMITED = "rate_limited"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"
    INVALID_INPUT = "invalid_input"
    INVALID_RESPONSE = "invalid_response"
    SERVICE_UNAVAILABLE = "service_unavailable"

    @classmethod
    def _missing_(cls, value: object) -> VisionResultStatus | None:
        if value == "sdk_unavailable":
            return cls.TRANSPORT_UNAVAILABLE
        return None


@dataclass(frozen=True, slots=True)
class VisualClaim:
    text: str
    status: ClaimStatus
    confidence: float
    evidence: str

    def __post_init__(self) -> None:
        if not self.text.strip() or len(self.text) > 500:
            raise ValueError("Claim text must contain 1 to 500 characters.")
        if not math.isfinite(self.confidence) or not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Claim confidence must be between zero and one.")
        if len(self.evidence) > 500:
            raise ValueError("Claim evidence exceeds the supported length.")
        if self.status is ClaimStatus.OBSERVED and not self.evidence.strip():
            raise ValueError("Observed claims require visible evidence.")


@dataclass(frozen=True, slots=True)
class VisualUnderstanding:
    summary: str
    claims: tuple[VisualClaim, ...]
    uncertainties: tuple[str, ...]
    model_reported: bool = True
    independently_verified: bool = False

    def __post_init__(self) -> None:
        if not self.summary.strip() or len(self.summary) > 1_000:
            raise ValueError("Summary must contain 1 to 1000 characters.")
        if len(self.claims) > 32 or len(self.uncertainties) > 16:
            raise ValueError("Vision response exceeds the supported item count.")
        if any(not item.strip() or len(item) > 500 for item in self.uncertainties):
            raise ValueError("Uncertainty entries must contain 1 to 500 characters.")
        if not self.model_reported or self.independently_verified:
            raise ValueError("Remote vision output cannot be marked independently verified.")


@dataclass(frozen=True, slots=True)
class VisionProviderResult:
    operation_id: int
    status: VisionResultStatus
    model: str
    detail: VisionDetail
    understanding: VisualUnderstanding | None = None

    @property
    def succeeded(self) -> bool:
        return self.status is VisionResultStatus.SUCCESS


@dataclass(frozen=True, slots=True)
class VisionFrameRequest:
    operation_id: int
    image_bytes: bytes
    width: int
    height: int
    media_type: str
    prompt: str
    detail: VisionDetail = VisionDetail.AUTO
    model: str | None = None


__all__ = (
    "ClaimStatus",
    "VisionFrameRequest",
    "VisionProviderResult",
    "VisionResultStatus",
    "VisualClaim",
    "VisualUnderstanding",
)
