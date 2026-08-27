from __future__ import annotations

lazy import sys
lazy from collections.abc import Callable

lazy from PySide6.QtCore import QObject, QRunnable, Signal

lazy from domain.safe_error import sanitize_error
lazy from integrations.cloud_connectors import PROVIDERS, OAuthPKCEFlow

__all__ = ("OAuthSignals", "OAuthWorker", "configure_oauth_flow_factory")


class OAuthSignals(QObject):
    done = Signal(str, object)
    failed = Signal(str, str)


OAuthFlowFactory = Callable[..., object]


class OAuthWorker(QRunnable):
    flow_factory: OAuthFlowFactory = staticmethod(OAuthPKCEFlow)

    def __init__(
        self,
        provider_id: str,
        client_id: str,
        client_secret: str,
        scopes: list[str],
    ):
        super().__init__()
        self.provider_id = provider_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.scopes = scopes
        self.signals = OAuthSignals()
        self._abandoned = False

    def abandon(self) -> None:
        """Mark the in-flight browser flow as unwanted during shutdown.

        The PKCE flow has no cancellation API: ``authorize()`` blocks on a
        local loopback listener until the browser answers or its own timeout
        expires.  Abandoning suppresses both completion callbacks so closing
        the window can stop waiting; the parked worker thread is reclaimed by
        process exit.
        """

        self._abandoned = True

    def run(self) -> None:
        try:
            token = _active_oauth_flow_factory()(
                PROVIDERS[self.provider_id],
                self.client_id,
                client_secret=self.client_secret,
                scopes=self.scopes,
            ).authorize()
            if self._abandoned:
                return
            if self.client_secret:
                token["client_secret"] = self.client_secret
            self.signals.done.emit(self.provider_id, token)
        except Exception as exc:
            if self._abandoned:
                return
            self.signals.failed.emit(self.provider_id, str(sanitize_error(exc)))


def configure_oauth_flow_factory(factory: OAuthFlowFactory) -> None:
    """Install the compatibility boundary used by the legacy public module."""
    OAuthWorker.flow_factory = staticmethod(factory)


def _active_oauth_flow_factory() -> OAuthFlowFactory:
    """Honor the legacy module's patch point without importing it."""
    configured = OAuthWorker.flow_factory
    if configured is not OAuthPKCEFlow:
        return configured
    compatibility = sys.modules.get("flagship_ui")
    return getattr(compatibility, "OAuthPKCEFlow", configured)
