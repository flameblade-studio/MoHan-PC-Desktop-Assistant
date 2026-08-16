from __future__ import annotations

lazy from collections.abc import Callable
lazy from pathlib import Path

lazy from application.cloud_vision_ui_bridge import CloudVisionServiceFactoryPort
lazy from application.presentation_ports import (
    DashboardServices,
    PlatformServicePort,
    PresentationPorts,
    bind_dashboard_portable_secrets,
)
lazy from domain.contracts import (
    AzureSpeechEnginePort,
    SecretStoreFactoryPort,
    SecretStorePort,
    SpeechListenerPort,
)
lazy from presentation.profile_transfer_ui import SensitiveProfileCallbacks

__all__ = ("DashboardDependencies", "create_portable_secret_callbacks")


class DashboardDependencies(DashboardServices):
    """Explicit services required to compose the control dashboard."""

    listener: SpeechListenerPort
    secret_store: SecretStorePort
    azure_secret_store: SecretStorePort | None = None
    azure_hd_secret_store: SecretStorePort | None = None
    azure_speech: AzureSpeechEnginePort | None = None
    azure_hd_speech: AzureSpeechEnginePort | None = None
    secret_store_factory: SecretStoreFactoryPort | None = None
    platform_services: PlatformServicePort | None = None
    cloud_vision_service_factory: CloudVisionServiceFactoryPort | None = None
    dense_face_provider_factory: Callable[[], object] | None = None
    presentation_ports: PresentationPorts | None = None


def create_portable_secret_callbacks(
    dependencies: DashboardDependencies,
    data_path: Path,
) -> SensitiveProfileCallbacks | None:
    """Bind optional portable secrets at the composition boundary."""

    try:
        binding = bind_dashboard_portable_secrets(dependencies, data_path)
    except (OSError, RuntimeError, TypeError, ValueError):
        return None
    return SensitiveProfileCallbacks(
        collect=binding.collect,
        restore=binding.apply,
    )
