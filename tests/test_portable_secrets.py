from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from infrastructure.portable_secrets import (
    MAX_PAYLOAD_BYTES,
    MAX_SECRET_BYTES,
    PORTABLE_SECRETS_FORMAT,
    PORTABLE_SECRETS_VERSION,
    SECRET_IDS,
    PortableSecretsError,
    apply_sensitive_payload,
    collect_sensitive_payload,
    validate_sensitive_payload,
)


class MemoryStore:
    def __init__(
        self,
        value: str = "",
        *,
        fail_load: bool = False,
        fail_save_on: frozenset[str] = frozenset(),
        mutate_before_failure: bool = False,
        fail_clear: bool = False,
    ) -> None:
        self.value = value
        self.fail_load = fail_load
        self.fail_save_on = fail_save_on
        self.mutate_before_failure = mutate_before_failure
        self.fail_clear = fail_clear

    def load(self) -> str:
        if self.fail_load:
            raise RuntimeError("PRIVATE-LOAD-DETAIL")
        return self.value

    def save(self, value: str) -> None:
        if value in self.fail_save_on:
            if self.mutate_before_failure:
                self.value = value
            raise RuntimeError("PRIVATE-SAVE-DETAIL")
        self.value = value

    def clear(self) -> None:
        if self.fail_clear:
            raise RuntimeError("PRIVATE-CLEAR-DETAIL")
        self.value = ""


class BrokenContractStore:
    @property
    def load(self):
        raise RuntimeError("PRIVATE-CONTRACT-DETAIL")


class RollbackFailureStore(MemoryStore):
    def save(self, value: str) -> None:
        if value == "new-openai":
            self.value = value
            raise RuntimeError("PRIVATE-PRIMARY-FAILURE")
        if value == "old-openai":
            raise RuntimeError("PRIVATE-ROLLBACK-FAILURE")
        self.value = value


def payload(secrets: dict[str, object]) -> dict[str, object]:
    return {
        "format": PORTABLE_SECRETS_FORMAT,
        "version": PORTABLE_SECRETS_VERSION,
        "secrets": secrets,
    }


def expect_safe_error(operation) -> str:
    try:
        operation()
    except PortableSecretsError as exc:
        message = str(exc)
        assert "PRIVATE" not in message
        assert "fixture-secret" not in message
        assert exc.__cause__ is None
        return message
    raise AssertionError("operation unexpectedly succeeded")


def assert_collection_schema_and_empty_filter() -> None:
    stores = {secret_id: MemoryStore() for secret_id in SECRET_IDS}
    stores["openai"].value = "fixture-openai"
    stores["face_identities"].value = '{"protected":"embedding-string"}'
    stores["gesture_templates"].value = "synthetic-protected-gesture-templates"
    collected = collect_sensitive_payload(stores)
    assert set(collected) == {"format", "version", "secrets"}
    assert collected["format"] == PORTABLE_SECRETS_FORMAT
    assert collected["version"] == PORTABLE_SECRETS_VERSION
    assert collected["secrets"] == {
        "face_identities": '{"protected":"embedding-string"}',
        "gesture_templates": "synthetic-protected-gesture-templates",
        "openai": "fixture-openai",
    }


def assert_gesture_templates_require_explicit_sensitive_collection() -> None:
    store = MemoryStore("synthetic-protected-gesture-templates")
    assert store.load() == "synthetic-protected-gesture-templates"
    # General profile export never calls this collector. Once the user explicitly
    # enables sensitive export, the typed collector includes this ninth store.
    collected = collect_sensitive_payload({"gesture_templates": store})
    assert collected["secrets"] == {
        "gesture_templates": "synthetic-protected-gesture-templates"
    }


def assert_exact_allowlist_and_types() -> None:
    valid = payload({"openai": "fixture-secret"})
    cases = (
        {**valid, "extra": "fixture-secret"},
        {"format": PORTABLE_SECRETS_FORMAT, "version": PORTABLE_SECRETS_VERSION},
        payload({"unknown": "fixture-secret"}),
        payload({"openai": 123}),
        payload({"openai": ""}),
        {**valid, "version": True},
        {**valid, "format": "unknown-format"},
    )
    for candidate in cases:
        expect_safe_error(lambda candidate=candidate: apply_sensitive_payload(candidate, {}))
    expect_safe_error(
        lambda: collect_sensitive_payload({"unknown": MemoryStore("fixture-secret")})
    )
    detached = validate_sensitive_payload(valid)
    assert detached == valid
    assert detached is not valid
    assert detached["secrets"] is not valid["secrets"]


def assert_size_limits() -> None:
    oversized = "x" * (MAX_SECRET_BYTES + 1)
    expect_safe_error(
        lambda: apply_sensitive_payload(
            payload({"openai": oversized}),
            {"openai": MemoryStore()},
        )
    )
    chunk = "x" * (MAX_SECRET_BYTES - 128)
    oversized_payload = payload(
        {"openai": chunk, "azure_speech": chunk, "azure_dragon_hd": chunk}
    )
    assert len(str(oversized_payload).encode("utf-8")) > MAX_PAYLOAD_BYTES
    expect_safe_error(
        lambda: apply_sensitive_payload(
            oversized_payload,
            {
                "openai": MemoryStore(),
                "azure_speech": MemoryStore(),
                "azure_dragon_hd": MemoryStore(),
            },
        )
    )


def assert_atomic_apply_and_omitted_preservation() -> None:
    stores = {
        "openai": MemoryStore("old-openai"),
        "azure_speech": MemoryStore("old-azure"),
        "oauth_github": MemoryStore("keep-github"),
        "face_identities": MemoryStore("old-protected-embeddings"),
    }
    apply_sensitive_payload(
        payload(
            {
                "openai": "new-openai",
                "azure_speech": "new-azure",
                "face_identities": "new-protected-embeddings",
            }
        ),
        stores,
    )
    assert stores["openai"].value == "new-openai"
    assert stores["azure_speech"].value == "new-azure"
    assert stores["face_identities"].value == "new-protected-embeddings"
    assert stores["oauth_github"].value == "keep-github"


def assert_rollback_includes_partially_written_store() -> None:
    stores = {
        "openai": MemoryStore("old-openai"),
        "azure_speech": MemoryStore(
            "old-azure",
            fail_save_on=frozenset({"new-azure"}),
            mutate_before_failure=True,
        ),
        "oauth_google": MemoryStore("keep-google"),
    }
    message = expect_safe_error(
        lambda: apply_sensitive_payload(
            payload({"openai": "new-openai", "azure_speech": "new-azure"}),
            stores,
        )
    )
    assert "restored" in message
    assert stores["openai"].value == "old-openai"
    assert stores["azure_speech"].value == "old-azure"
    assert stores["oauth_google"].value == "keep-google"


def assert_empty_old_value_uses_clear_on_rollback() -> None:
    stores = {
        "openai": MemoryStore(""),
        "azure_speech": MemoryStore(
            "old-azure",
            fail_save_on=frozenset({"new-azure"}),
        ),
    }
    expect_safe_error(
        lambda: apply_sensitive_payload(
            payload({"openai": "new-openai", "azure_speech": "new-azure"}),
            stores,
        )
    )
    assert stores["openai"].value == ""
    assert stores["azure_speech"].value == "old-azure"


def assert_exception_stores_fail_safely() -> None:
    expect_safe_error(
        lambda: collect_sensitive_payload({"openai": MemoryStore(fail_load=True)})
    )
    expect_safe_error(
        lambda: apply_sensitive_payload(
            payload({"openai": "fixture-secret"}),
            {"openai": MemoryStore(fail_load=True)},
        )
    )
    missing_message = expect_safe_error(
        lambda: apply_sensitive_payload(payload({"openai": "fixture-secret"}), {})
    )
    assert "unavailable" in missing_message
    expect_safe_error(
        lambda: collect_sensitive_payload({"openai": BrokenContractStore()})
    )


def assert_incomplete_rollback_is_explicit() -> None:
    store = RollbackFailureStore("old-openai")
    message = expect_safe_error(
        lambda: apply_sensitive_payload(
            payload({"openai": "new-openai"}),
            {"openai": store},
        )
    )
    assert "rollback was incomplete" in message


def run() -> None:
    assert_collection_schema_and_empty_filter()
    assert_gesture_templates_require_explicit_sensitive_collection()
    assert_exact_allowlist_and_types()
    assert_size_limits()
    assert_atomic_apply_and_omitted_preservation()
    assert_rollback_includes_partially_written_store()
    assert_empty_old_value_uses_clear_on_rollback()
    assert_exception_stores_fail_safely()
    assert_incomplete_rollback_is_explicit()
    print("PORTABLE_SECRETS_OK")


if __name__ == "__main__":
    run()
