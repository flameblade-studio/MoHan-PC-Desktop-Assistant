from __future__ import annotations

lazy import os
lazy import sys
lazy from dataclasses import dataclass
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from PySide6.QtWidgets import QApplication

lazy from application.presentation_ports import (
    ProfileTransferError as ApplicationProfileTransferError,
)
lazy from presentation.dashboard_composition import (
    DashboardDependencies,
    create_portable_secret_callbacks,
)
lazy from infrastructure.db import StudioDB
lazy from infrastructure.portable_secrets import SECRET_IDS
lazy from infrastructure.profile_transfer import (
    ProfileImportResult,
    ProfileManifest,
    ProfileTransferError,
)
lazy from presentation.profile_transfer_ui import PortableProfilePanel


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
            raise RuntimeError("PRIVATE-WIRING-DETAIL")
        self.value = value

    def clear(self) -> None:
        self.value = ""


class MemoryFactory:
    def __init__(self) -> None:
        self.stores: dict[Path, MemoryStore] = {}

    def __call__(self, path: Path, description: str = "") -> MemoryStore:
        del description
        return self.stores.setdefault(path, MemoryStore())


@dataclass(slots=True)
class ListenerProbe:
    pass


def dependencies(factory: MemoryFactory) -> DashboardDependencies:
    return DashboardDependencies(
        listener=ListenerProbe(),
        secret_store=MemoryStore(),
        azure_secret_store=MemoryStore(),
        azure_hd_secret_store=MemoryStore(),
        secret_store_factory=factory,
    )


def _all_stores(
    configured: DashboardDependencies,
    factory: MemoryFactory,
    root: Path,
) -> dict[str, MemoryStore]:
    assert isinstance(configured.secret_store, MemoryStore)
    assert isinstance(configured.azure_secret_store, MemoryStore)
    assert isinstance(configured.azure_hd_secret_store, MemoryStore)
    return {
        "openai": configured.secret_store,
        "azure_speech": configured.azure_secret_store,
        "azure_dragon_hd": configured.azure_hd_secret_store,
        "home_assistant": factory.stores[root / "home-assistant-token.dpapi"],
        "oauth_google": factory.stores[root / "oauth-google.dpapi"],
        "oauth_microsoft": factory.stores[root / "oauth-microsoft.dpapi"],
        "oauth_github": factory.stores[root / "oauth-github.dpapi"],
        "face_identities": factory.stores[root / "face-identities.dpapi"],
        "gesture_templates": factory.stores[root / "gesture-templates.dpapi"],
    }


def assert_nine_store_round_trip_without_real_data(root: Path) -> None:
    factory = MemoryFactory()
    configured = dependencies(factory)
    callbacks = create_portable_secret_callbacks(configured, root)
    assert callbacks is not None
    stores = _all_stores(configured, factory, root)
    assert set(stores) == SECRET_IDS
    for index, secret_id in enumerate(sorted(SECRET_IDS)):
        stores[secret_id].value = f"synthetic-old-{index}"
    collected = callbacks.collect()
    assert set(collected["secrets"]) == SECRET_IDS
    replacement = {
        secret_id: f"synthetic-new-{index}"
        for index, secret_id in enumerate(sorted(SECRET_IDS))
    }
    callbacks.restore({**collected, "secrets": replacement})
    assert {key: store.value for key, store in stores.items()} == replacement


def assert_default_checkbox_does_not_collect(root: Path) -> None:
    database = StudioDB(root / "default-off" / "mohan.db")
    factory = MemoryFactory()
    configured = dependencies(factory)
    callbacks = create_portable_secret_callbacks(configured, database.path.parent)
    assert callbacks is not None
    for store in _all_stores(configured, factory, database.path.parent).values():
        store.load = lambda: (_ for _ in ()).throw(
            AssertionError("default-off flow must not read stores")
        )
    try:
        panel = PortableProfilePanel(
            database,
            sensitive_callbacks=callbacks,
        )
        assert panel.include_sensitive.isChecked() is False
        assert panel._export_sensitive_input() == (None, None)
        panel.deleteLater()
    finally:
        database.close()


def assert_unsafe_composition_fails_closed(root: Path) -> None:
    factory = MemoryFactory()
    configured = dependencies(factory)
    configured = DashboardDependencies(
        listener=configured.listener,
        secret_store=configured.secret_store,
        azure_secret_store=None,
        azure_hd_secret_store=configured.azure_hd_secret_store,
        secret_store_factory=factory,
    )
    assert create_portable_secret_callbacks(configured, root) is None


def assert_sensitive_failure_calls_core_rollback(root: Path) -> None:
    database = StudioDB(root / "rollback" / "mohan.db")
    factory = MemoryFactory()
    configured = dependencies(factory)
    callbacks = create_portable_secret_callbacks(configured, database.path.parent)
    assert callbacks is not None
    stores = _all_stores(configured, factory, database.path.parent)
    stores["openai"].value = "old-openai"
    stores["azure_speech"].value = "old-azure"
    stores["azure_speech"].fail_on = frozenset({"new-azure"})
    stores["azure_speech"].mutate_before_failure = True
    result = ProfileImportResult(
        manifest=ProfileManifest("", "snapshot", "", "", "", frozendict()),
        backup_path=root / "synthetic-backup.db",
        imported_counts=frozendict(),
        sensitive_payload={
            "format": "mohan-portable-secrets",
            "version": 1,
            "secrets": {"openai": "new-openai", "azure_speech": "new-azure"},
        },
    )
    panel = PortableProfilePanel(
        database,
        sensitive_callbacks=callbacks,
    )
    try:
        with (
            patch.object(panel.manager, "restore_import") as restore_import,
        ):
            try:
                panel._restore_sensitive_result(result)
            except ProfileTransferError as exc:
                assert "PRIVATE" not in str(exc)
            else:
                raise AssertionError("sensitive restore failure must surface")
        restore_import.assert_called_once_with(result)
        assert stores["openai"].value == "old-openai"
        assert stores["azure_speech"].value == "old-azure"
    finally:
        panel.deleteLater()
        database.close()


def assert_sensitive_and_rollback_failure_uses_transfer_error(root: Path) -> None:
    database = StudioDB(root / "rollback-failure" / "mohan.db")
    factory = MemoryFactory()
    configured = dependencies(factory)
    callbacks = create_portable_secret_callbacks(configured, database.path.parent)
    assert callbacks is not None
    stores = _all_stores(configured, factory, database.path.parent)
    stores["azure_speech"].fail_on = frozenset({"new-azure"})
    result = ProfileImportResult(
        manifest=ProfileManifest("", "snapshot", "", "", "", frozendict()),
        backup_path=root / "synthetic-backup.db",
        imported_counts=frozendict(),
        sensitive_payload={
            "format": "mohan-portable-secrets",
            "version": 1,
            "secrets": {"azure_speech": "new-azure"},
        },
    )
    panel = PortableProfilePanel(database, sensitive_callbacks=callbacks)
    try:
        with patch.object(
            panel.manager,
            "restore_import",
            side_effect=ProfileTransferError("PRIVATE-ROLLBACK-DETAIL"),
        ):
            try:
                panel._restore_sensitive_result(result)
            except ProfileTransferError as exc:
                assert "PRIVATE" not in str(exc)
                assert "rollback failed" in str(exc)
            else:
                raise AssertionError("rollback failure must surface")
    finally:
        panel.deleteLater()
        database.close()


def run() -> None:
    assert ApplicationProfileTransferError is ProfileTransferError
    application = QApplication.instance() or QApplication([])
    with TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        root = Path(temp)
        assert_nine_store_round_trip_without_real_data(root)
        assert_default_checkbox_does_not_collect(root)
        assert_unsafe_composition_fails_closed(root)
        assert_sensitive_failure_calls_core_rollback(root)
        assert_sensitive_and_rollback_failure_uses_transfer_error(root)
    application.processEvents()
    print("PORTABLE_SECRET_WIRING_OK")


if __name__ == "__main__":
    run()
