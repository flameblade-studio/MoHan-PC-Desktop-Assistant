from __future__ import annotations

lazy import json
lazy import math
lazy from dataclasses import dataclass
lazy from operator import itemgetter
lazy from uuid import uuid4

lazy from domain.contracts import SecretStorePort
lazy from domain.vision_domain import (
    IdentityObservation,
    IdentityState,
    cosine_similarity,
)


@dataclass(frozen=True, slots=True)
class FaceProfile:
    profile_id: str
    display_name: str
    embeddings: tuple[tuple[float, ...], ...]


class FaceIdentityDataError(ValueError):
    """Report unusable protected identity data without exposing its contents."""


class FaceIdentityStore:
    """Persist encrypted face embeddings; raw enrollment images never leave memory."""

    def __init__(self, secret_store: SecretStorePort) -> None:
        self._secret_store = secret_store

    def profiles(self) -> tuple[FaceProfile, ...]:
        try:
            raw = self._secret_store.load()
        except (OSError, RuntimeError, ValueError, TypeError):
            raise FaceIdentityDataError(
                "protected face identity data is unavailable"
            ) from None
        if not raw:
            return ()
        try:
            payload = json.loads(raw)
            return self._parse_profiles(payload)
        except FaceIdentityDataError:
            raise
        except (KeyError, TypeError, ValueError, OverflowError, json.JSONDecodeError):
            raise FaceIdentityDataError(
                "protected face identity data is invalid"
            ) from None

    def enroll(
        self,
        display_name: str,
        embeddings: tuple[tuple[float, ...], ...],
    ) -> FaceProfile:
        name = display_name.strip()
        if not name:
            raise ValueError("display name must not be empty")
        validated = self._validate_embeddings(embeddings)
        profile = FaceProfile(uuid4().hex, name, validated)
        self._write((*self.profiles(), profile))
        return profile

    def delete(self, profile_id: str) -> bool:
        current = self.profiles()
        remaining = tuple(item for item in current if item.profile_id != profile_id)
        if len(current) == len(remaining):
            return False
        self._write(remaining)
        return True

    def clear(self) -> None:
        self._secret_store.clear()

    def identify(
        self,
        embedding: tuple[float, ...],
        *,
        threshold: float = 0.50,
        ambiguity_margin: float = 0.04,
    ) -> IdentityObservation:
        if not self._valid_embedding(embedding):
            return IdentityObservation(IdentityState.UNKNOWN)
        try:
            profiles = self.profiles()
        except FaceIdentityDataError:
            return IdentityObservation(IdentityState.UNKNOWN)
        if any(len(sample) != len(embedding) for profile in profiles for sample in profile.embeddings):
            return IdentityObservation(IdentityState.UNKNOWN)
        scores = sorted(
            ((
                max(cosine_similarity(embedding, sample) for sample in profile.embeddings),
                profile,
            ) for profile in profiles),
            key=itemgetter(0),
        )
        if not scores or scores[-1][0] < threshold:
            return IdentityObservation(IdentityState.UNKNOWN)
        best_score, best_profile = scores[-1]
        if len(scores) > 1 and best_score - scores[-2][0] < ambiguity_margin:
            return IdentityObservation(IdentityState.UNKNOWN, confidence=best_score)
        return IdentityObservation(
            IdentityState.RECOGNIZED,
            best_profile.profile_id,
            best_profile.display_name,
            best_score,
        )

    @classmethod
    def _parse_profiles(cls, payload: object) -> tuple[FaceProfile, ...]:
        if not isinstance(payload, dict):
            raise FaceIdentityDataError("protected face identity data is invalid")
        version = payload.get("version", 1)
        items = payload.get("profiles", ())
        if version != 1 or not isinstance(items, (list, tuple)):
            raise FaceIdentityDataError("protected face identity data is invalid")
        profiles: list[FaceProfile] = []
        dimensions: set[int] = set()
        for item in items:
            if not isinstance(item, dict):
                raise FaceIdentityDataError("protected face identity data is invalid")
            profile_id = item.get("profile_id")
            display_name = item.get("display_name")
            if not isinstance(profile_id, str) or not profile_id.strip():
                raise FaceIdentityDataError("protected face identity data is invalid")
            if not isinstance(display_name, str) or not display_name.strip():
                raise FaceIdentityDataError("protected face identity data is invalid")
            embeddings = cls._validate_embeddings(item.get("embeddings"))
            dimensions.add(len(embeddings[0]))
            profiles.append(FaceProfile(profile_id, display_name, embeddings))
        if len(dimensions) > 1:
            raise FaceIdentityDataError("protected face identity data is invalid")
        return tuple(profiles)

    @classmethod
    def _validate_embeddings(cls, value: object) -> tuple[tuple[float, ...], ...]:
        if not isinstance(value, (list, tuple)) or len(value) < 3:
            raise ValueError("at least three non-empty face samples are required")
        embeddings: list[tuple[float, ...]] = []
        for sample in value:
            if not isinstance(sample, (list, tuple)):
                raise TypeError("face samples must be numeric vectors")
            if not cls._valid_embedding(sample):
                raise ValueError("face samples must contain finite numeric values")
            embedding = tuple(float(component) for component in sample)
            embeddings.append(embedding)
        if len({len(embedding) for embedding in embeddings}) != 1:
            raise ValueError("face samples must use one vector dimension")
        return tuple(embeddings)

    @staticmethod
    def _valid_embedding(embedding: object) -> bool:
        return (
            isinstance(embedding, (list, tuple))
            and bool(embedding)
            and all(
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(float(value))
                for value in embedding
            )
        )

    def _write(self, profiles: tuple[FaceProfile, ...]) -> None:
        if not profiles:
            self._secret_store.clear()
            return
        payload = {
            "version": 1,
            "profiles": [
                {
                    "profile_id": profile.profile_id,
                    "display_name": profile.display_name,
                    "embeddings": profile.embeddings,
                }
                for profile in profiles
            ],
        }
        self._secret_store.save(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
