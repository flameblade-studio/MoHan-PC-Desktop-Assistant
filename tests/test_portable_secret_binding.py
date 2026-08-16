from __future__ import annotations

lazy import sys
lazy from dataclasses import dataclass
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from infrastructure.portable_secret_binding import (
    PortableSecretBindingError,
    bind_dashboard_portable_secrets,
    bind_portable_secret_stores,
)
lazy from infrastructure.portable_secrets import (
    PORTABLE_SECRETS_FORMAT,
    PORTABLE_SECRETS_VERSION,
    SECRET_IDS,
    PortableSecretsError,
)


class MemoryStore:
    def __init__(
        self,
        value: str = "",
        *,
        fail_on: frozenset[str] = frozenset(),
        mutate_before_failure: bool = False,
    ) -> None:
        self.value = value
        self.fail_on = fail_on
        self.mutate_before_failure = mutate_before_failure

    def load(self) -> str:
        return self.value

    def save(self, value: str) -> None:
        if value in self.fail_on:
            if self.mutate_before_failure:
                self.value = value
            raise RuntimeError("PRIVATE-STORE-DETAIL")
        self.value = value

    def clear(self) -> None:
        self.value = ""


class MemoryFactory:
    def __init__(self) -> None:
        self.stores: dict[Path, MemoryStore] = {}

    def __call__(self, path: Path, description: str = "") -> MemoryStore:
        del description
        store = MemoryStore()
        self.stores[path] = store
        return store


@dataclass(slots=True)
class FakeDashboardDependencies:
    secret_store: MemoryStore
    azure_secret_store: MemoryStore | None
    azure_hd_secret_store: MemoryStore | None
    secret_store_factory: MemoryFactory | None


def payload(secrets: dict[str, str]) -> dict[str, object]:
    return {
        "format": PORTABLE_SECRETS_FORMAT,
        "version": PORTABLE_SECRETS_VERSION,
        "secrets": secrets,
    }


def complete_stores() -> dict[str, MemoryStore]:
    return {secret_id: MemoryStore() for secret_id in SECRET_IDS}


def expect_binding_error(operation) -> str:
    try:
        operation()
    except PortableSecretBindingError as exc:
        message = str(exc)
        assert "PRIVATE" not in message
        return message
    raise AssertionError("invalid binding unexpectedly succeeded")


def assert_complete_dashboard_mapping() -> None:
    with TemporaryDirectory() as temp:
        root = Path(temp)
        factory = MemoryFactory()
        dependencies = FakeDashboardDependencies(
            MemoryStore("openai-value"),
            MemoryStore("azure-value"),
            MemoryStore("dragon-value"),
            factory,
        )
        binding = bind_dashboard_portable_secrets(dependencies, root)
        assert binding.store_ids() == SECRET_IDS
        expected_paths = {
            root / "home-assistant-token.dpapi",
            root / "oauth-google.dpapi",
            root / "oauth-microsoft.dpapi",
            root / "oauth-github.dpapi",
            root / "face-identities.dpapi",
            root / "gesture-templates.dpapi",
        }
        assert set(factory.stores) == expected_paths
        factory.stores[root / "face-identities.dpapi"].value = "protected-face-data"
        factory.stores[root / "gesture-templates.dpapi"].value = (
            "synthetic-protected-gesture-data"
        )
        collected = binding.collect()
        assert collected["secrets"] == {
            "azure_dragon_hd": "dragon-value",
            "azure_speech": "azure-value",
            "face_identities": "protected-face-data",
            "gesture_templates": "synthetic-protected-gesture-data",
            "openai": "openai-value",
        }


def assert_empty_values_are_excluded() -> None:
    binding = bind_portable_secret_stores(complete_stores())
    assert binding.collect() == payload({})


def assert_apply_rollback_is_preserved() -> None:
    stores = complete_stores()
    stores["openai"].value = "old-openai"
    stores["azure_speech"] = MemoryStore(
        "old-azure",
        fail_on=frozenset({"new-azure"}),
        mutate_before_failure=True,
    )
    binding = bind_portable_secret_stores(stores)
    try:
        binding.apply(
            payload({"openai": "new-openai", "azure_speech": "new-azure"})
        )
    except PortableSecretsError as exc:
        assert "PRIVATE" not in str(exc)
    else:
        raise AssertionError("failed apply must be reported")
    assert stores["openai"].value == "old-openai"
    assert stores["azure_speech"].value == "old-azure"


def assert_unknown_missing_and_duplicate_stores_fail_closed() -> None:
    missing = complete_stores()
    missing.pop("oauth_github")
    expect_binding_error(lambda: bind_portable_secret_stores(missing))

    unknown = complete_stores()
    unknown["unknown"] = MemoryStore()
    expect_binding_error(lambda: bind_portable_secret_stores(unknown))

    duplicate = complete_stores()
    duplicate["oauth_github"] = duplicate["oauth_google"]
    expect_binding_error(lambda: bind_portable_secret_stores(duplicate))

    gesture_shared = complete_stores()
    gesture_shared["gesture_templates"] = gesture_shared["face_identities"]
    expect_binding_error(lambda: bind_portable_secret_stores(gesture_shared))


def assert_incomplete_dashboard_boundaries_fail_closed() -> None:
    cases = (
        FakeDashboardDependencies(MemoryStore(), None, MemoryStore(), MemoryFactory()),
        FakeDashboardDependencies(MemoryStore(), MemoryStore(), None, MemoryFactory()),
        FakeDashboardDependencies(MemoryStore(), MemoryStore(), MemoryStore(), None),
    )
    for dependencies in cases:
        expect_binding_error(
            lambda dependencies=dependencies: bind_dashboard_portable_secrets(
                dependencies, Path("unused")
            )
        )


def assert_factory_duplicates_and_failures_are_rejected() -> None:
    shared = MemoryStore()

    def duplicate_factory(path: Path, description: str = "") -> MemoryStore:
        del path, description
        return shared

    dependencies = FakeDashboardDependencies(
        MemoryStore(), MemoryStore(), MemoryStore(), duplicate_factory
    )
    expect_binding_error(
        lambda: bind_dashboard_portable_secrets(dependencies, Path("unused"))
    )

    def failing_factory(path: Path, description: str = "") -> MemoryStore:
        del path, description
        raise RuntimeError("PRIVATE-FACTORY-DETAIL")

    dependencies.secret_store_factory = failing_factory
    message = expect_binding_error(
        lambda: bind_dashboard_portable_secrets(dependencies, Path("unused"))
    )
    assert "PRIVATE-FACTORY-DETAIL" not in message


def run() -> None:
    assert_complete_dashboard_mapping()
    assert_empty_values_are_excluded()
    assert_apply_rollback_is_preserved()
    assert_unknown_missing_and_duplicate_stores_fail_closed()
    assert_incomplete_dashboard_boundaries_fail_closed()
    assert_factory_duplicates_and_failures_are_rejected()
    print("PORTABLE_SECRET_BINDING_OK")


if __name__ == "__main__":
    run()
