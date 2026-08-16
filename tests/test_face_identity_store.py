from __future__ import annotations

lazy import json
lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from infrastructure.face_identity_store import (
    FaceIdentityDataError,
    FaceIdentityStore,
)
lazy from vision_domain import IdentityState, cosine_similarity


class MemorySecretStore:
    def __init__(self) -> None:
        self.value = ""

    def load(self) -> str:
        return self.value

    def save(self, value: str) -> None:
        self.value = value

    def clear(self) -> None:
        self.value = ""


class BrokenSecretStore(MemorySecretStore):
    def load(self) -> str:
        raise RuntimeError("PRIVATE-CIPHERTEXT-MUST-NOT-LEAK")


def assert_safe_error(store: FaceIdentityStore) -> None:
    try:
        store.profiles()
    except FaceIdentityDataError as exc:
        message = str(exc)
        assert message in {
            "protected face identity data is unavailable",
            "protected face identity data is invalid",
        }
        assert "PRIVATE" not in message
        assert exc.__cause__ is None
    else:
        raise AssertionError("corrupt protected data must raise a safe error")
    assert store.identify((1.0, 0.0, 0.0)).state is IdentityState.UNKNOWN


def assert_corruption_fails_closed() -> None:
    assert_safe_error(FaceIdentityStore(BrokenSecretStore()))
    invalid_payloads: tuple[object, ...] = (
        "{PRIVATE-BROKEN-JSON",
        "[]",
        '{"version":2,"profiles":[]}',
        '{"profiles":"PRIVATE-NOT-A-LIST"}',
        '{"profiles":["PRIVATE-NOT-A-PROFILE"]}',
        '{"profiles":[{"profile_id":"","display_name":"Owner","embeddings":[[1],[1],[1]]}]}',
        '{"profiles":[{"profile_id":"1","display_name":"","embeddings":[[1],[1],[1]]}]}',
        '{"profiles":[{"profile_id":"1","display_name":"Owner","embeddings":[[1],[1]]}]}',
        '{"profiles":[{"profile_id":"1","display_name":"Owner","embeddings":[[1,0],[1],[1,0]]}]}',
        '{"profiles":[{"profile_id":"1","display_name":"Owner","embeddings":[[NaN,0],[1,0],[1,0]]}]}',
        {
            "version": 1,
            "profiles": [
                {"profile_id": "1", "display_name": "Owner", "embeddings": [[1, 0], [1, 0], [1, 0]]},
                {"profile_id": "2", "display_name": "Visitor", "embeddings": [[1, 0, 0], [1, 0, 0], [1, 0, 0]]},
            ],
        },
    )
    for payload in invalid_payloads:
        secret = MemorySecretStore()
        secret.value = payload if isinstance(payload, str) else json.dumps(payload)
        assert_safe_error(FaceIdentityStore(secret))


def assert_invalid_enrollment_is_rejected() -> None:
    identities = FaceIdentityStore(MemorySecretStore())
    for embeddings in (
        ((1.0,), (1.0,)),
        ((1.0, 0.0), (1.0,), (1.0, 0.0)),
        ((float("nan"), 0.0), (1.0, 0.0), (1.0, 0.0)),
        ((float("inf"), 0.0), (1.0, 0.0), (1.0, 0.0)),
        ((True, 0.0), (1.0, 0.0), (1.0, 0.0)),
    ):
        try:
            identities.enroll("Owner", embeddings)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid enrollment vector must be rejected")


def assert_invalid_probe_is_unknown() -> None:
    secret = MemorySecretStore()
    identities = FaceIdentityStore(secret)
    identities.enroll("Owner", ((1.0, 0.0), (0.99, 0.01), (0.98, 0.02)))
    for embedding in ((), (1.0,), (float("nan"), 0.0), (float("inf"), 0.0)):
        assert identities.identify(embedding).state is IdentityState.UNKNOWN
    assert cosine_similarity((float("nan"),), (1.0,)) == 0.0


def run() -> None:
    assert_corruption_fails_closed()
    assert_invalid_enrollment_is_rejected()
    assert_invalid_probe_is_unknown()
    secret = MemorySecretStore()
    identities = FaceIdentityStore(secret)
    assert identities.profiles() == ()
    profile = identities.enroll(
        "Owner",
        ((1.0, 0.0, 0.0), (0.99, 0.01, 0.0), (0.98, 0.02, 0.0)),
    )
    assert "Owner" in secret.value
    match = identities.identify((1.0, 0.0, 0.0))
    assert match.state is IdentityState.RECOGNIZED
    assert match.display_name == "Owner"
    assert identities.identify((0.0, 1.0, 0.0)).state is IdentityState.UNKNOWN
    second = identities.enroll(
        "Visitor",
        ((0.98, 0.02, 0.0), (0.97, 0.03, 0.0), (0.96, 0.04, 0.0)),
    )
    ambiguous = identities.identify((0.99, 0.01, 0.0))
    assert ambiguous.state is IdentityState.UNKNOWN
    assert ambiguous.display_name == ""
    # Version-less v1 payloads predate the explicit version field and remain valid.
    legacy_payload = json.loads(secret.value)
    legacy_payload.pop("version")
    secret.value = json.dumps(legacy_payload)
    assert len(identities.profiles()) == 2
    assert identities.delete(profile.profile_id)
    assert identities.delete(second.profile_id)
    assert identities.profiles() == ()
    assert secret.value == ""


if __name__ == "__main__":
    run()
    print("FACE_IDENTITY_STORE_OK")
