from __future__ import annotations

lazy import time
lazy from collections.abc import Mapping, Sequence
lazy from dataclasses import dataclass
lazy from datetime import UTC, datetime
lazy from enum import StrEnum

lazy from application.background_agents import is_quiet_time
lazy from application.visual_perception import (
    LightingState,
    PresenceState,
    VisualObservation,
)
lazy from domain.character_pack.character_data_models import canonical_character_locale
lazy from domain.character_source import active_character_data

_DIALOGUES = active_character_data().dialogues

LATE_NIGHT_HOUR = 23
LATE_NIGHT_END_HOUR = 5
MORNING_END_HOUR = 10


class InteractionKind(StrEnum):
    WELCOME_BACK = "welcome_back"
    LIGHTING_CARE = "lighting_care"
    GENTLE_CHECK_IN = "gentle_check_in"


class WelcomeStyle(StrEnum):
    WARM = "warm"
    GENERAL = "general"
    CEREMONIAL = "ceremonial"
    MORNING = "morning"
    LATE_NIGHT = "late_night"
    WITH_DRINK = "with_drink"
    WITH_BOOK = "with_book"


@dataclass(frozen=True, slots=True)
class ProactiveInteraction:
    kind: InteractionKind
    expression: str
    style: WelcomeStyle = WelcomeStyle.WARM


@dataclass(frozen=True, slots=True)
class WelcomeTimingRules:
    minimum_away_seconds: float = 60.0
    brief_max_seconds: float = 30.0 * 60.0
    long_away_seconds: float = 4.0 * 60.0 * 60.0

    def __post_init__(self) -> None:
        if not (
            1.0 <= self.minimum_away_seconds
            < self.brief_max_seconds
            < self.long_away_seconds
        ):
            raise ValueError(
                "welcome timing must satisfy minimum < brief maximum < long-away threshold"
            )


@dataclass(frozen=True, slots=True)
class InteractionTextContext:
    """All presentation inputs for one localized proactive line."""

    user_title: str
    wall_time: datetime | None = None
    activities: tuple[str, ...] = ()
    custom_welcome: Mapping[WelcomeStyle | str, str | Sequence[str]] | None = None
    custom_check_ins: str | Sequence[str] | None = None
    variation_index: int = 0

    def __post_init__(self) -> None:
        if not self.user_title.strip():
            raise ValueError("Interaction user title requires content.")
        if self.wall_time is not None and self.wall_time.tzinfo is None:
            raise ValueError("Interaction wall time must be timezone-aware.")
        if self.variation_index < 0:
            raise ValueError("Interaction variation index accepts zero or greater.")

    @property
    def local_time(self) -> datetime:
        return self.wall_time or datetime.now(UTC).astimezone()


class MultisensoryInteractionArbiter:
    """Choose rare, explainable interactions from local sensory state."""

    _MODE_COOLDOWN_SECONDS = frozendict(
        {"quiet": float("inf"), "balanced": 30.0 * 60.0, "active": 10.0 * 60.0}
    )

    def __init__(
        self,
        *,
        timing: WelcomeTimingRules | None = None,
        minimum_away_seconds: float | None = None,
        conversation_silence_seconds: float = 45.0 * 60.0,
        clock=time.monotonic,
    ) -> None:
        if timing is not None and minimum_away_seconds is not None:
            raise ValueError("provide timing or minimum_away_seconds, not both")
        self._timing = timing or WelcomeTimingRules(
            minimum_away_seconds=(
                60.0 if minimum_away_seconds is None else float(minimum_away_seconds)
            )
        )
        self._clock = clock
        self._conversation_silence_seconds = max(
            10.0 * 60.0,
            float(conversation_silence_seconds),
        )
        self._last_presence = PresenceState.UNKNOWN
        self._away_since: float | None = None
        self._last_delivery = float("-inf")
        self._last_lighting = LightingState.COMFORTABLE
        self._last_human_interaction = self._clock()

    def consider(
        self,
        observation: VisualObservation,
        *,
        proactive_mode: str,
        wall_time: datetime,
        busy: bool,
        recognized_user: bool = False,
    ) -> ProactiveInteraction | None:
        mode = self._mode_key(proactive_mode)
        now = self._clock()
        previous_presence = self._last_presence
        previous_lighting = self._last_lighting
        self._remember(observation, now)
        if busy or is_quiet_time(wall_time) or mode == "quiet":
            return None
        if now - self._last_delivery < self._MODE_COOLDOWN_SECONDS[mode]:
            return None
        interaction = self._welcome_back(
            observation, previous_presence=previous_presence, now=now
        ) or self._lighting_care(observation, previous_lighting=previous_lighting)
        if interaction is None and recognized_user:
            interaction = self._gentle_check_in(observation, now=now)
        if interaction is not None:
            self._last_delivery = now
        return interaction

    def reset(self) -> None:
        self._last_presence = PresenceState.UNKNOWN
        self._away_since = None
        self._last_delivery = float("-inf")
        self._last_lighting = LightingState.COMFORTABLE
        self._last_human_interaction = self._clock()

    def note_human_interaction(self) -> None:
        self._last_human_interaction = self._clock()

    def _remember(self, observation: VisualObservation, now: float) -> None:
        if observation.presence is PresenceState.AWAY and self._last_presence is not PresenceState.AWAY:
            self._away_since = now
        self._last_presence = observation.presence
        self._last_lighting = observation.lighting

    def _welcome_back(
        self,
        observation: VisualObservation,
        *,
        previous_presence: PresenceState,
        now: float,
    ) -> ProactiveInteraction | None:
        away_duration = 0.0 if self._away_since is None else now - self._away_since
        if (
            observation.presence is PresenceState.PRESENT
            and previous_presence is PresenceState.AWAY
            and away_duration >= self._timing.minimum_away_seconds
        ):
            self._away_since = None
            return ProactiveInteraction(
                InteractionKind.WELCOME_BACK,
                "happy",
                self._welcome_style(away_duration),
            )
        return None

    def _welcome_style(self, away_duration: float) -> WelcomeStyle:
        if away_duration >= self._timing.long_away_seconds:
            return WelcomeStyle.CEREMONIAL
        if away_duration <= self._timing.brief_max_seconds:
            return WelcomeStyle.WARM
        return WelcomeStyle.GENERAL

    @staticmethod
    def _lighting_care(
        observation: VisualObservation,
        *,
        previous_lighting: LightingState,
    ) -> ProactiveInteraction | None:
        if (
            observation.presence is PresenceState.PRESENT
            and observation.lighting is LightingState.DIM
            and previous_lighting in {LightingState.COMFORTABLE, LightingState.BRIGHT}
        ):
            return ProactiveInteraction(InteractionKind.LIGHTING_CARE, "worried")
        return None

    def _gentle_check_in(
        self,
        observation: VisualObservation,
        *,
        now: float,
    ) -> ProactiveInteraction | None:
        if (
            observation.presence is PresenceState.PRESENT
            and now - self._last_human_interaction >= self._conversation_silence_seconds
        ):
            self._last_human_interaction = now
            return ProactiveInteraction(InteractionKind.GENTLE_CHECK_IN, "gentle")
        return None

    @staticmethod
    def _mode_key(value: str) -> str:
        text = str(value).casefold()
        if text.startswith(("安靜", "安静")) or "quiet" in text:
            return "quiet"
        if text.startswith(("積極", "积极")) or "active" in text:
            return "active"
        return "balanced"


def _default_interaction_lines(
    user_title: str,
    style: WelcomeStyle,
) -> dict[InteractionKind, dict[str, str | tuple[str, ...]]]:
    welcome_key = f"welcome.{style.value}"
    welcome = {
        _runtime_locale(locale): tuple(
            line.format(user_title=user_title)
            for line in dialogue.line_sets[welcome_key]
        )
        for locale, dialogue in _DIALOGUES.items()
    }
    lighting = {
        _runtime_locale(locale): dialogue.templates["interaction.lighting_care"].format(
            user_title=user_title,
        )
        for locale, dialogue in _DIALOGUES.items()
    }
    check_in = {
        _runtime_locale(locale): tuple(
            line.format(user_title=user_title)
            for line in dialogue.line_sets["interaction.gentle_check_in"]
        )
        for locale, dialogue in _DIALOGUES.items()
    }
    return {
        InteractionKind.WELCOME_BACK: welcome,
        InteractionKind.LIGHTING_CARE: lighting,
        InteractionKind.GENTLE_CHECK_IN: check_in,
    }


def _runtime_locale(locale: str) -> str:
    return "ja" if locale == "ja-JP" else locale


def interaction_text(
    language: str,
    interaction: ProactiveInteraction,
    context: InteractionTextContext | None = None,
    **legacy: object,
) -> str:
    """Render one line, preserving the pre-v4 keyword-call boundary."""

    context = _interaction_text_context(context, legacy)
    style = _interaction_style(interaction, context)
    choices = _custom_interaction_choices(interaction, style, context)
    if not choices:
        lines = _default_interaction_lines(context.user_title, style)
        choices = _phrase_choices(lines[interaction.kind][_locale(language)])
    return choices[context.variation_index % len(choices)]


def _interaction_text_context(
    context: InteractionTextContext | None,
    legacy: Mapping[str, object],
) -> InteractionTextContext:
    if context is not None:
        if legacy:
            raise TypeError("Choose either interaction context or legacy options.")
        return context
    allowed = {
        "user_title",
        "wall_time",
        "activities",
        "custom_welcome",
        "custom_check_ins",
        "variation_index",
    }
    unknown = set(legacy) - allowed
    if unknown:
        names = ", ".join(sorted(unknown))
        raise TypeError(f"Unsupported interaction options: {names}")
    if "user_title" not in legacy:
        raise TypeError("Interaction user_title is required.")
    wall_time = legacy.get("wall_time")
    if isinstance(wall_time, datetime) and wall_time.tzinfo is None:
        wall_time = wall_time.astimezone()
    return InteractionTextContext(
        user_title=str(legacy["user_title"]),
        wall_time=wall_time if isinstance(wall_time, datetime) else None,
        activities=_string_tuple(legacy.get("activities", ())),
        custom_welcome=_welcome_mapping(legacy.get("custom_welcome")),
        custom_check_ins=_phrase_source(legacy.get("custom_check_ins")),
        variation_index=_variation_index(legacy.get("variation_index", 0)),
    )


def _string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        raise TypeError("Interaction activities must be a sequence of strings.")
    return tuple(str(item) for item in value)


def _welcome_mapping(
    value: object,
) -> Mapping[WelcomeStyle | str, str | Sequence[str]] | None:
    if value is None or isinstance(value, Mapping):
        return value
    raise TypeError("Custom welcome phrases must be a mapping.")


def _phrase_source(value: object) -> str | Sequence[str] | None:
    if value is None or isinstance(value, (str, Sequence)):
        return value
    raise TypeError("Custom check-in phrases must be text or a sequence.")


def _variation_index(value: object) -> int:
    if type(value) is not int:
        raise TypeError("Interaction variation index must be an integer.")
    return value


def _interaction_style(
    interaction: ProactiveInteraction,
    context: InteractionTextContext,
) -> WelcomeStyle:
    if interaction.kind is not InteractionKind.WELCOME_BACK:
        return interaction.style
    if "possible_drinking" in context.activities:
        return WelcomeStyle.WITH_DRINK
    if "possible_reading" in context.activities:
        return WelcomeStyle.WITH_BOOK
    hour = context.local_time.hour
    if hour >= LATE_NIGHT_HOUR or hour < LATE_NIGHT_END_HOUR:
        return WelcomeStyle.LATE_NIGHT
    return WelcomeStyle.MORNING if hour < MORNING_END_HOUR else interaction.style


def _custom_interaction_choices(
    interaction: ProactiveInteraction,
    style: WelcomeStyle,
    context: InteractionTextContext,
) -> tuple[str, ...]:
    if interaction.kind is InteractionKind.WELCOME_BACK and context.custom_welcome:
        custom = context.custom_welcome.get(
            style,
            context.custom_welcome.get(style.value, ""),
        )
        return _phrase_choices(custom)
    if interaction.kind is InteractionKind.GENTLE_CHECK_IN:
        return _phrase_choices(context.custom_check_ins)
    return ()


def _locale(language: str) -> str:
    return _runtime_locale(canonical_character_locale(language))


def _phrase_choices(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        text = value.strip()
        return (text,) if text else ()
    if isinstance(value, Sequence):
        return tuple(text for item in value if (text := str(item).strip()))
    return ()
