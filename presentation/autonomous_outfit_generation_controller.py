from __future__ import annotations

"""Presentation composition for non-blocking cloud outfit creation."""

lazy import secrets
lazy import shutil
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
    FashionTrendScoutFactory,
    GeneratedOutfitResult,
    OutfitCreationRequest,
    OutfitGenerationPolicy,
    SelfGeneratingWardrobe,
)
lazy from application.wardrobe_service import WardrobeService
lazy from application.wardrobe_storage import WardrobeStorageGuard, WardrobeStoragePolicy
lazy from domain.constants import (
    DEFAULT_WEATHER_CONDITION,
    DEFAULT_WEATHER_TEMPERATURE_C,
)
lazy from domain.outfit_pack import (
    MOOD_TAGS,
    OCCASION_TAGS,
    WEATHER_TAGS,
    OutfitPackError,
)
lazy from infrastructure.db import StudioDBSettingsPort
lazy from integrations.openai_outfit_generator import (
    GeneratedOutfitImageAuditor,
    OpenAIImageEditOptions,
    OpenAIImageEditTransport,
    OpenAIOutfitDraftGenerator,
    OutfitImageGenerationError,
)
lazy from application.presentation_ports import DEFAULT_TEXT_MODEL
lazy import threading
lazy from domain.outfit_generation import OutfitGenerationCancelled

LAST_GENERATED_KEY = "wardrobe_last_generated_at"
LAST_ATTEMPT_KEY = "wardrobe_generation_last_attempt_at"
PENDING_JOB_KEY = "wardrobe_generation_pending_job_id"
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
    cancelled = Signal()


class _GenerationWorker(QRunnable):
    def __init__(
        self,
        wardrobe: SelfGeneratingWardrobe,
        request: OutfitCreationRequest,
        cancel_event: threading.Event,
    ) -> None:
        super().__init__()
        self.wardrobe = wardrobe
        self.request = request
        self.cancel_event = cancel_event
        self.signals = _GenerationSignals()

    def run(self) -> None:
        try:
            result = self.wardrobe.create(
                self.request,
                cancelled=self.cancel_event.is_set,
            )
        except OutfitGenerationCancelled:
            # 使用者停手不是失敗。混在一起回報會讓退避計時器把「使用者按了
            # 緊急停止」記成一次失敗嘗試，接著封鎖他下一次真正想生成的請求。
            self.signals.cancelled.emit()
            return
        except Exception as error:
            # Do not expose API keys, request payloads, or provider response text.
            status = (
                error.public_status
                if isinstance(error, OutfitImageGenerationError)
                else f"failed:{type(error).__name__}"
            )
            self.signals.failed.emit(status)
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
        trend_scout_factory: FashionTrendScoutFactory | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._db = db
        self._settings = StudioDBSettingsPort(db)
        self._secret_store = secret_store
        self._project_root = Path(project_root)
        self._trend_scout_factory = trend_scout_factory
        self._data_root = Path(db.path).parent
        self._pool = QThreadPool.globalInstance()
        self._active_worker: _GenerationWorker | None = None
        # 緊急停止必須觸達這個 worker。它跑在另一個 QThreadPool 裡，stop()
        # 只停 timer 與清參照，對已經在飛的付費呼叫沒有作用。
        self._cancel = threading.Event()
        self._running = False
        self._shutdown = False
        self._wardrobe_service = WardrobeService(self._data_root / "outfits")
        self._wardrobe_runtime = AutonomousWardrobeRuntime(
            self._wardrobe_service,
            self._settings,
            OutfitRevealStateStore(self._settings),
        )
        self._timer = QTimer(self)
        self._timer.setInterval(AUTONOMOUS_CHECK_INTERVAL_MS)
        self._timer.timeout.connect(self.evaluate_automatic)
        # A controller-owned single-shot timer (instead of QTimer.singleShot)
        # so stop() can cancel the initial delayed evaluation outright and no
        # orphaned callback survives this controller's lifetime.
        self._initial_timer = QTimer(self)
        self._initial_timer.setSingleShot(True)
        self._initial_timer.setInterval(INITIAL_AUTONOMOUS_DELAY_MS)
        self._initial_timer.timeout.connect(self.evaluate_automatic)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._shutdown = False
        self._cancel.clear()
        self._timer.start()
        self._initial_timer.start()

    def stop(self) -> None:
        """Detach future UI updates; an in-flight HTTP call remains bounded by timeout.

        ``_active_worker`` is deliberately kept: clearing it here would let a
        stop→start cycle launch a second generation in parallel with the
        still-running worker.  The worker's completion callbacks clear it.
        """
        self._running = False
        self._shutdown = True
        self._timer.stop()
        self._initial_timer.stop()
        self._active_worker = None

    def abort(self) -> None:
        """緊急停止：讓正在執行的生成在下一個視角之前停手。

        stop() 是生命週期收尾，刻意保留 _active_worker；abort() 是使用者
        主動喊停，必須讓 worker 自己察覺。兩者不可混用：abort 之後控制器
        仍然活著，使用者可以再按一次生成。
        """
        self._cancel.set()

    def _cancelled(self) -> None:
        self._active_worker = None
        # 使用者停手不寫入 LAST_ATTEMPT_KEY：那個欄位驅動失敗退避，
        # 把主動停手記成失敗會讓他接下來一小時按不動生成。
        self.status_changed.emit("cancelled-by-user")

    def evaluate_automatic(self) -> None:
        """Generate unattended only when both explicit wardrobe switches allow it."""

        # Both owned timers stop with stop(), yet an already-queued timeout can
        # still be delivered afterwards.  The dashboard closes its DB before
        # that delayed callback may run, so make lifecycle state the first
        # boundary and never touch persistence after stop().
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
            self._db.setting("weather_condition", DEFAULT_WEATHER_CONDITION),
            WEATHER_TAGS,
            DEFAULT_WEATHER_CONDITION,
        )
        mood = _allowed_setting(
            self._db.setting("current_mood", "calm"),
            MOOD_TAGS,
            "calm",
        )
        occasion = _allowed_setting(
            self._wardrobe_occasion(),
            OCCASION_TAGS,
            "everyday",
        )
        try:
            decision = self._wardrobe_runtime.evaluate(
                WardrobeSituation(
                    now,
                    float(
                        self._db.setting(
                            "weather_temperature_c",
                            DEFAULT_WEATHER_TEMPERATURE_C,
                        )
                    ),
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

    def request_generation(self, *, explicit: bool = False) -> None:
        """Start generation; an explicit button click may retry immediately."""

        if self._shutdown:
            # stop() 之後不得再啟動新工作：dashboard 可能已在收尾，資料庫
            # 與檔案系統的後續寫入沒有安全宿主。
            return
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
            if not explicit:
                self.status_changed.emit("cooldown-blocked")
                return
            # A user clicking the charge-labelled button is an intentional
            # retry.  The backoff protects unattended generation only.
        pending_job = str(self._db.setting(PENDING_JOB_KEY, "") or "").strip()
        job_id = pending_job or f"{now:%Y%m%d}-{secrets.token_hex(4)}"
        request = OutfitCreationRequest(
            job_id=job_id,
            language=str(self._db.setting("ui_language", "zh-TW") or "zh-TW"),
            weather=str(
                self._db.setting("weather_condition", DEFAULT_WEATHER_CONDITION)
                or DEFAULT_WEATHER_CONDITION
            ),
            temperature_c=float(
                self._db.setting(
                    "weather_temperature_c", DEFAULT_WEATHER_TEMPERATURE_C
                )
            ),
            mood=str(self._db.setting("current_mood", "calm") or "calm"),
            occasion=self._wardrobe_occasion(),
            creative_direction=(
                "An elegant original Northern-Song-inspired outfit for MoHan, "
                "adapted to the current weather and mood while preserving her "
                "blue-silver sword-spirit identity."
            ),
            requested_at=now,
            last_generated_at=_optional_time(
                self._db.setting(LAST_GENERATED_KEY, "")
            ),
            user_initiated=explicit,
        )
        worker = _GenerationWorker(
            self._create_wardrobe(api_key), request, self._cancel
        )
        worker.signals.completed.connect(self._completed)
        worker.signals.failed.connect(self._failed)
        worker.signals.cancelled.connect(self._cancelled)
        self._active_worker = worker
        self._db.set_setting(PENDING_JOB_KEY, job_id)
        self._db.set_setting(LAST_ATTEMPT_KEY, now.isoformat())
        trend_search = self._trend_search_enabled()
        self.status_changed.emit(
            "generating-with-trend-search" if trend_search else "generating"
        )
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
        trend_search = self._trend_search_enabled()
        trend_scout = (
            self._trend_scout_factory(
                api_key,
                str(self._db.setting("ai_model", DEFAULT_TEXT_MODEL)),
            )
            if trend_search and self._trend_scout_factory is not None
            else _NoTrendScout()
        )
        return SelfGeneratingWardrobe(
            quarantine,
            outfit_store,
            trend_scout,
            OpenAIOutfitDraftGenerator(
                OpenAIImageEditTransport(
                    OpenAIImageEditOptions(
                        api_key,
                        quality=self._outfit_image_quality(),
                    )
                ),
                self._project_root,
                self._data_root / "outfit-generation-cache",
            ),
            GeneratedOutfitImageAuditor(self._project_root),
            OutfitGenerationPolicy(
                enabled=True,
                trend_search_enabled=trend_search,
                install_after_audit=True,
            ),
            WardrobeStorageGuard(outfit_store, quarantine, policy),
        )

    def _outfit_image_quality(self) -> str:
        quality = str(self._db.setting("outfit_image_quality", "medium"))
        return quality if quality in {"low", "medium", "high"} else "medium"

    def _trend_search_enabled(self) -> bool:
        return self._trend_scout_factory is not None and bool(
            self._db.setting("fashion_trend_search_enabled", False)
        )

    def _wardrobe_occasion(self) -> str:
        """Use an explicit occasion, otherwise derive one from the live work mode."""

        explicit = str(self._db.setting("current_occasion", "") or "").lower()
        if explicit in OCCASION_TAGS:
            return explicit
        mode = str(self._db.setting("mode", "") or "")
        return {
            "工作": "work",
            "會議": "formal",
        }.get(mode, "everyday")

    def _completed(self, value: object) -> None:
        self._active_worker = None
        if not self._running:
            return
        if not isinstance(value, GeneratedOutfitResult):
            self._abandon_pending_job()
            self.status_changed.emit("invalid-result")
            return
        if value.status != "installed" or value.installed_pack is None:
            # A completed non-install result has no resumable transaction.
            # Keep its quarantine evidence, but start any later request with a
            # fresh job id. Reusing this id would collide with the preserved
            # quarantine directory and make every retry fail immediately.
            self._abandon_pending_job()
            self.status_changed.emit(value.status)
            return
        completed_job = str(self._db.setting(PENDING_JOB_KEY, "") or "").strip()
        self._db.set_setting(PENDING_JOB_KEY, "")
        if not value.installed_pack.ensembles:
            self.status_changed.emit("activation-failed")
            return
        outfit_id = "/".join(
            (
                value.installed_pack.pack_id,
                value.installed_pack.ensembles[0].ensemble_id,
            )
        )
        now_value = datetime.now(UTC)
        manual_lock_until = _optional_time(
            self._db.setting("wardrobe_manual_lock_until", "")
        )
        if manual_lock_until is not None and manual_lock_until > now_value:
            # Generation may finish hours after it was requested.  Installation
            # is safe, but an autonomous completion must never override the
            # user's current manually locked look.  The new pack remains a
            # candidate after the lock expires or may be selected explicitly.
            now = now_value.isoformat()
            self._settings.write({LAST_GENERATED_KEY: now})
            self._discard_completed_checkpoints(completed_job)
            self.status_changed.emit("installed-manual-lock")
            return
        try:
            self._wardrobe_service.apply(outfit_id)
        except (OSError, ValueError, OutfitPackError):
            self.status_changed.emit("activation-failed")
            return
        now = now_value.isoformat()
        self._settings.write(
            {
                "active_outfit_id": outfit_id,
                "wardrobe_last_changed_at": now,
                LAST_GENERATED_KEY: now,
            }
        )
        OutfitRevealStateStore(self._settings).mark_pending(outfit_id)
        self._discard_completed_checkpoints(completed_job)
        self.status_changed.emit("installed")

    def _abandon_pending_job(self) -> None:
        """Forget a finished unusable job without deleting quarantine evidence."""

        job_id = str(self._db.setting(PENDING_JOB_KEY, "") or "").strip()
        self._db.set_setting(PENDING_JOB_KEY, "")
        self._discard_completed_checkpoints(job_id)

    def _discard_completed_checkpoints(self, job_id: str) -> None:
        """Remove only the exact paid-generation checkpoint after installation."""

        if not job_id or Path(job_id).name != job_id:
            return
        cache_root = (self._data_root / "outfit-generation-cache").resolve()
        job_root = (cache_root / job_id).resolve()
        if job_root.parent != cache_root or not job_root.is_dir():
            return
        try:
            shutil.rmtree(job_root)
        except OSError:
            # The outfit has already been audited/installed at this point.
            # A locked antivirus handle, read-only cache, or transient disk
            # error must not turn that successful transaction into a silent UI
            # failure.  Preserve that exact checkpoint directory for later
            # maintenance instead of misreporting the installed transaction.
            return

    def _failed(self, status: str) -> None:
        self._active_worker = None
        if not self._running:
            return
        self._db.set_setting("wardrobe_generation_last_error", status)
        self.status_changed.emit(status)


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
