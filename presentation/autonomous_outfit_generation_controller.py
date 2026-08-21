from __future__ import annotations

"""Presentation composition for non-blocking cloud outfit creation."""

lazy import secrets
lazy from datetime import UTC, datetime, timedelta
lazy from pathlib import Path

lazy from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal

lazy from application.outfit_reveal import OutfitRevealStateStore
lazy from application.autonomous_wardrobe_runtime import (
    AutonomousWardrobeRuntime,
    WardrobeSituation,
)
lazy from application.self_generating_wardrobe import (
    FashionTrendSignal,
    GeneratedOutfitResult,
    OutfitCreationRequest,
    OutfitGenerationPolicy,
    SelfGeneratingWardrobe,
)
lazy from application.wardrobe_service import WardrobeService
lazy from application.wardrobe_storage import WardrobeStorageGuard, WardrobeStoragePolicy
lazy from domain.outfit_pack import MOOD_TAGS, OCCASION_TAGS, WEATHER_TAGS
lazy from infrastructure.db import StudioDBSettingsPort
lazy from integrations.openai_outfit_generator import (
    GeneratedOutfitImageAuditor,
    OpenAIImageEditOptions,
    OpenAIImageEditTransport,
    OpenAIOutfitDraftGenerator,
)

LAST_GENERATED_KEY = "wardrobe_last_generated_at"
LAST_ATTEMPT_KEY = "wardrobe_generation_last_attempt_at"
FAILED_ATTEMPT_BACKOFF = timedelta(hours=24)
INITIAL_AUTONOMOUS_DELAY_MS = 30_000
AUTONOMOUS_CHECK_INTERVAL_MS = 60 * 60 * 1000


class _NoTrendScout:
    def discover(self, request: OutfitCreationRequest) -> tuple[FashionTrendSignal, ...]:
        del request
        return ()


class _GenerationSignals(QObject):
    completed = Signal(object)
    failed = Signal(str)


class _GenerationWorker(QRunnable):
    def __init__(
        self,
        wardrobe: SelfGeneratingWardrobe,
        request: OutfitCreationRequest,
    ) -> None:
        super().__init__()
        self.wardrobe = wardrobe
        self.request = request
        self.signals = _GenerationSignals()

    def run(self) -> None:
        try:
            result = self.wardrobe.create(self.request)
        except Exception as error:
            # Do not expose API keys, request payloads, or provider response text.
            self.signals.failed.emit(type(error).__name__)
            return
        self.signals.completed.emit(result)


class AutonomousOutfitGenerationController(QObject):
    """Run one explicit, opt-in 31-view generation job outside the UI thread."""

    status_changed = Signal(str)

    def __init__(
        self,
        *,
        db,
        secret_store,
        project_root: Path,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._db = db
        self._settings = StudioDBSettingsPort(db)
        self._secret_store = secret_store
        self._project_root = Path(project_root)
        self._data_root = Path(db.path).parent
        self._pool = QThreadPool.globalInstance()
        self._active_worker: _GenerationWorker | None = None
        self._running = False
        self._wardrobe_service = WardrobeService(self._data_root / "outfits")
        self._wardrobe_runtime = AutonomousWardrobeRuntime(
            self._wardrobe_service,
            self._settings,
            OutfitRevealStateStore(self._settings),
        )
        self._timer = QTimer(self)
        self._timer.setInterval(AUTONOMOUS_CHECK_INTERVAL_MS)
        self._timer.timeout.connect(self.evaluate_automatic)

    def start(self) -> None:
        self._running = True
        self._timer.start()
        QTimer.singleShot(INITIAL_AUTONOMOUS_DELAY_MS, self.evaluate_automatic)

    def stop(self) -> None:
        """Detach future UI updates; an in-flight HTTP call remains bounded by timeout."""
        self._running = False
        self._timer.stop()
        self._active_worker = None

    def evaluate_automatic(self) -> None:
        """Generate unattended only when both explicit wardrobe switches allow it."""

        # QTimer.singleShot cannot be cancelled.  The dashboard closes its DB
        # before that delayed callback may run, so make lifecycle state the
        # first boundary and never touch persistence after stop().
        if not self._running:
            return
        if not bool(self._db.setting("autonomous_wardrobe_enabled", True)):
            self.status_changed.emit("automatic-selection-disabled")
            return
        self._evaluate_installed_outfits()
        self.request_generation()

    def _evaluate_installed_outfits(self) -> None:
        """Select among official, user-authored, and cloud packs without mutation."""

        now = datetime.now(UTC)
        weather = _allowed_setting(
            self._db.setting("weather_condition", "indoor"),
            WEATHER_TAGS,
            "indoor",
        )
        mood = _allowed_setting(
            self._db.setting("current_mood", "calm"),
            MOOD_TAGS,
            "calm",
        )
        occasion = _allowed_setting(
            self._db.setting("current_occasion", "everyday"),
            OCCASION_TAGS,
            "everyday",
        )
        try:
            decision = self._wardrobe_runtime.evaluate(
                WardrobeSituation(
                    now,
                    float(self._db.setting("weather_temperature_c", 24.0)),
                    weather,
                    mood,
                    occasion,
                )
            )
        except (OSError, TypeError, ValueError):
            self.status_changed.emit("automatic-selection-failed")
            return
        if decision.changed:
            self.status_changed.emit("outfit-selected")

    def request_generation(self) -> None:
        if self._active_worker is not None:
            self.status_changed.emit("already-generating")
            return
        if not bool(self._db.setting("self_outfit_generation_enabled", False)):
            self.status_changed.emit("not-enabled")
            return
        api_key = str(self._secret_store.load() or "").strip()
        if not api_key:
            self.status_changed.emit("api-key-unavailable")
            return
        now = datetime.now(UTC)
        last_attempt = _optional_time(self._db.setting(LAST_ATTEMPT_KEY, ""))
        if last_attempt is not None and now - last_attempt < FAILED_ATTEMPT_BACKOFF:
            return
        request = OutfitCreationRequest(
            job_id=f"{now:%Y%m%d}-{secrets.token_hex(4)}",
            language=str(self._db.setting("ui_language", "zh-TW") or "zh-TW"),
            weather=str(self._db.setting("weather_condition", "indoor") or "indoor"),
            temperature_c=float(self._db.setting("weather_temperature_c", 24.0)),
            mood=str(self._db.setting("current_mood", "calm") or "calm"),
            occasion=str(self._db.setting("current_occasion", "everyday") or "everyday"),
            creative_direction=(
                "An elegant original Northern-Song-inspired outfit for MoHan, "
                "adapted to the current weather and mood while preserving her "
                "blue-silver sword-spirit identity."
            ),
            requested_at=now,
            last_generated_at=_optional_time(
                self._db.setting(LAST_GENERATED_KEY, "")
            ),
        )
        worker = _GenerationWorker(self._create_wardrobe(api_key), request)
        worker.signals.completed.connect(self._completed)
        worker.signals.failed.connect(self._failed)
        self._active_worker = worker
        self._db.set_setting(LAST_ATTEMPT_KEY, now.isoformat())
        self.status_changed.emit("generating")
        self._pool.start(worker)

    def _create_wardrobe(self, api_key: str) -> SelfGeneratingWardrobe:
        outfit_store = self._data_root / "outfits"
        quarantine = self._data_root / "outfit-quarantine"
        policy = WardrobeStoragePolicy(
            max_installed_packages=max(
                1, int(self._db.setting("generated_outfit_limit", 16))
            ),
            max_total_bytes=max(
                1, int(self._db.setting("generated_outfit_storage_gb", 6))
            ) * 1024 * 1024 * 1024,
        )
        return SelfGeneratingWardrobe(
            quarantine,
            outfit_store,
            _NoTrendScout(),
            OpenAIOutfitDraftGenerator(
                OpenAIImageEditTransport(OpenAIImageEditOptions(api_key)),
                self._project_root,
            ),
            GeneratedOutfitImageAuditor(self._project_root),
            OutfitGenerationPolicy(enabled=True, install_after_audit=True),
            WardrobeStorageGuard(outfit_store, quarantine, policy),
        )

    def _completed(self, value: object) -> None:
        self._active_worker = None
        if not self._running:
            return
        if not isinstance(value, GeneratedOutfitResult):
            self.status_changed.emit("invalid-result")
            return
        if value.status != "installed" or value.installed_pack is None:
            self.status_changed.emit(value.status)
            return
        outfit_id = f"{value.installed_pack.pack_id}/autonomous-look"
        self._wardrobe_service.apply(outfit_id)
        now = datetime.now(UTC).isoformat()
        self._settings.write(
            {
                "active_outfit_id": outfit_id,
                "wardrobe_last_changed_at": now,
                LAST_GENERATED_KEY: now,
            }
        )
        OutfitRevealStateStore(self._settings).mark_pending(outfit_id)
        self.status_changed.emit("installed")

    def _failed(self, error_type: str) -> None:
        self._active_worker = None
        if not self._running:
            return
        self.status_changed.emit(f"failed:{error_type}")


def _optional_time(value: object) -> datetime | None:
    if not str(value or "").strip():
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(UTC)


def _allowed_setting(value: object, allowed: frozenset[str], fallback: str) -> str:
    normalized = str(value or "").strip().lower()
    return normalized if normalized in allowed else fallback
