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
            raise ValueError("Interaction user title must not be empty.")
        if self.wall_time is not None and self.wall_time.tzinfo is None:
            raise ValueError("Interaction wall time must be timezone-aware.")
        if self.variation_index < 0:
            raise ValueError("Interaction variation index must not be negative.")

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
    welcome = {
        WelcomeStyle.WARM: {
            "zh-TW": (f"歡迎回來，{user_title}。", f"{user_title}，您回來了。", f"又見到您了，{user_title}。"),
            "zh-CN": (f"欢迎回来，{user_title}。", f"{user_title}，您回来了。", f"又见到您了，{user_title}。"),
            "en": (f"Welcome back, {user_title}.", f"You're back, {user_title}.", f"It is good to see you again, {user_title}."),
            "ja": (f"お帰りなさい、{user_title}。", f"{user_title}、戻られたのですね。", f"またお会いできましたね、{user_title}。"),
        },
        WelcomeStyle.CEREMONIAL: {
            "zh-TW": (f"歡迎歸來，{user_title}。", f"許久不見，{user_title}。", f"您終於回來了，{user_title}。"),
            "zh-CN": (f"欢迎归来，{user_title}。", f"许久不见，{user_title}。", f"您终于回来了，{user_title}。"),
            "en": (f"Welcome home, {user_title}.", f"It has been a while, {user_title}.", f"You are finally back, {user_title}."),
            "ja": (f"お帰りなさいませ、{user_title}。", f"お久しぶりです、{user_title}。", f"ようやくお戻りですね、{user_title}。"),
        },
        WelcomeStyle.GENERAL: {
            "zh-TW": (f"歡迎回來，{user_title}。今天過得還好嗎？", f"{user_title}，您回來了。要不要先歇一會兒？", f"又見面了，{user_title}。方才一切還順利嗎？"),
            "zh-CN": (f"欢迎回来，{user_title}。今天过得还好吗？", f"{user_title}，您回来了。要不要先歇一会儿？", f"又见面了，{user_title}。刚才一切还顺利吗？"),
            "en": (f"Welcome back, {user_title}. How has your day been?", f"You're back, {user_title}. Would you like a moment to rest?", f"Good to see you again, {user_title}. Did everything go well?"),
            "ja": (f"お帰りなさい、{user_title}。今日はどんな一日でしたか？", f"{user_title}、お帰りなさい。少し休みませんか？", f"またお会いできましたね、{user_title}。先ほどは順調でしたか？"),
        },
        WelcomeStyle.MORNING: {
            "zh-TW": (f"早安，{user_title}。", f"新的一天開始了，{user_title}。", f"早晨好，{user_title}。今天也請多指教。"),
            "zh-CN": (f"早上好，{user_title}。", f"新的一天开始了，{user_title}。", f"早晨好，{user_title}。今天也请多指教。"),
            "en": (f"Good morning, {user_title}.", f"A new day begins, {user_title}.", f"Morning, {user_title}. I look forward to today with you."),
            "ja": (f"おはようございます、{user_title}。", f"新しい一日が始まりましたね、{user_title}。", f"朝ですね、{user_title}。今日もよろしくお願いします。"),
        },
        WelcomeStyle.LATE_NIGHT: {
            "zh-TW": (f"歡迎回來，{user_title}。夜深了，先喘口氣吧。", f"{user_title}，這麼晚才回來，辛苦了。", f"夜已深了，{user_title}。別忘了讓自己休息。"),
            "zh-CN": (f"欢迎回来，{user_title}。夜深了，先喘口气吧。", f"{user_title}，这么晚才回来，辛苦了。", f"夜已深了，{user_title}。别忘了让自己休息。"),
            "en": (f"Welcome back, {user_title}. It is late; take a breath.", f"You're back late, {user_title}. It has been a long day.", f"It is late, {user_title}. Please remember to rest."),
            "ja": (f"お帰りなさい、{user_title}。夜も遅いですから、ひと息ついてください。", f"こんな時間までお疲れさまです、{user_title}。", f"夜も更けました、{user_title}。休むことも忘れないでください。"),
        },
        WelcomeStyle.WITH_DRINK: {
            "zh-TW": (f"歡迎回來，{user_title}。有記得補充水分，很好。", f"{user_title}帶了飲品回來呢。", f"又見面了，{user_title}。先慢慢喝一口吧。"),
            "zh-CN": (f"欢迎回来，{user_title}。有记得补充水分，很好。", f"{user_title}带了饮品回来呢。", f"又见面了，{user_title}。先慢慢喝一口吧。"),
            "en": (f"Welcome back, {user_title}. I am glad you remembered a drink.", f"You brought a drink back, {user_title}.", f"Good to see you, {user_title}. Take a slow sip first."),
            "ja": (f"お帰りなさい、{user_title}。飲み物も忘れていませんね。", f"飲み物を持って戻られたのですね、{user_title}。", f"また会えましたね、{user_title}。まずはゆっくり一口どうぞ。"),
        },
        WelcomeStyle.WITH_BOOK: {
            "zh-TW": (f"歡迎回來，{user_title}。您帶了書呢。", f"{user_title}又帶著故事回來了。", f"那本書看起來很有意思，{user_title}。"),
            "zh-CN": (f"欢迎回来，{user_title}。您带了书呢。", f"{user_title}又带着故事回来了。", f"那本书看起来很有意思，{user_title}。"),
            "en": (f"Welcome back, {user_title}. You brought a book.", f"You have returned with another story, {user_title}.", f"That book looks interesting, {user_title}."),
            "ja": (f"お帰りなさい、{user_title}。本をお持ちですね。", f"また物語を連れて戻られましたね、{user_title}。", f"その本は面白そうですね、{user_title}。"),
        },
    }
    return {
        InteractionKind.WELCOME_BACK: welcome[style],
        InteractionKind.LIGHTING_CARE: {
            "zh-TW": f"{user_title}，房間似乎變暗了。若還要看螢幕，記得留一盞柔光，也讓眼睛歇一歇。",
            "zh-CN": f"{user_title}，房间似乎变暗了。若还要看屏幕，记得留一盏柔光，也让眼睛歇一歇。",
            "en": f"{user_title}, the room seems dimmer. If you are staying at the screen, keep a soft light on and rest your eyes.",
            "ja": f"{user_title}、部屋が少し暗くなったようです。画面を見続けるなら、柔らかい灯りをつけて、目も休ませてください。",
        },
        InteractionKind.GENTLE_CHECK_IN: {
            "zh-TW": (
                f"{user_title}，忙到現在，還順利嗎？",
                f"{user_title}，安靜了好一會兒。想和我聊聊嗎？",
                f"{user_title}，若累了就停一會兒，墨寒陪著您。",
            ),
            "zh-CN": (
                f"{user_title}，忙到现在，还顺利吗？",
                f"{user_title}，安静了好一会儿。想和我聊聊吗？",
                f"{user_title}，若累了就停一会儿，墨寒陪着您。",
            ),
            "en": (
                f"{user_title}, has everything been going smoothly?",
                f"It has been quiet for a while, {user_title}. Would you like to talk?",
                f"If you are tired, pause for a moment, {user_title}. I am here with you.",
            ),
            "ja": (
                f"{user_title}、ここまで順調ですか？",
                f"しばらく静かでしたね、{user_title}。少し話しませんか？",
                f"疲れたならひと息ついてください、{user_title}。墨寒がおそばにいます。",
            ),
        },
    }


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
            raise TypeError("Interaction context cannot be mixed with legacy options.")
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
    normalized = str(language).strip().lower()
    if normalized.startswith(("zh-cn", "zh-hans")):
        return "zh-CN"
    if normalized.startswith("en"):
        return "en"
    return "ja" if normalized.startswith("ja") else "zh-TW"


def _phrase_choices(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        text = value.strip()
        return (text,) if text else ()
    if isinstance(value, Sequence):
        return tuple(text for item in value if (text := str(item).strip()))
    return ()
