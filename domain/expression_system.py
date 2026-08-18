from __future__ import annotations

lazy import re
lazy import time
lazy from collections import deque
lazy from collections.abc import Callable, Collection
lazy from dataclasses import dataclass

EMOTION_TO_EXPRESSION = frozendict({
    "neutral": "speaking",
    "thinking": "thinking_front",
    "attentive": "attentive_front",
    "determined": "determined_front",
    "gentle": "gentle_smile_front",
    "happy": "happy",
    "proud": "proud_front",
    "relieved": "relieved_front",
    "worried": "worried_front",
    "reminder": "reminder",
    "surprised": "surprised_front",
    "shy": "shy_cute_front",
    "amused": "restrained_amused_front",
    "exasperated": "exasperated_front",
    "scold": "mock_scold",
    "mock_hit": "mock_hit_front",
    "eureka": "eureka_front",
    "protective": "protective_front",
})
EXPRESSION_TO_EMOTION = frozendict({
    expression: emotion
    for emotion, expression in EMOTION_TO_EXPRESSION.items()
})
INTERNAL_EMOTION_INSTRUCTION = (
    "在回覆正文的最後附加一個不可見控制標籤，格式必須是 "
    "[[MOHAN_EMOTION:情緒:強度]]。情緒只能使用："
    + "、".join(EMOTION_TO_EXPRESSION)
    + "；強度為 0.00 至 1.00。標籤不可放入正文、不可解釋、"
    "不可朗讀。一般陳述使用 neutral；只有語意明確時才使用情緒標籤。"
)
_EMOTION_TAG = re.compile(
    r"\[\[\s*MOHAN_EMOTION\s*:\s*([a-z_]+)"
    r"(?:\s*:\s*(0(?:\.\d+)?|1(?:\.0+)?))?\s*\]\]",
    re.IGNORECASE,
)
_ANY_EMOTION_TAG = re.compile(
    r"\[\[\s*MOHAN_EMOTION\b[^\]]*\]\]",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class TaggedReply:
    text: str
    expression: str | None
    emotion: str | None
    intensity: float
    valid_tag: bool


@dataclass(frozen=True, slots=True)
class FaceAnchorProfile:
    pose: str
    offset_x: int
    offset_y: int
    eye_offset_x: int
    eye_offset_y: int
    mouth_offset_x: int
    mouth_offset_y: int
    confidence: float
    score: float


@dataclass(frozen=True, slots=True)
class WaitExpressionCue:
    """One optional, delayed reaction while an AI answer is pending."""

    expression: str
    delay_ms: int
    intensity: float
    reason: str


AI_WAIT_TIMEOUT_MS = 4_200
_COMPLEX_WAIT_DELAY_MS = 1_200
_ATTENTIVE_WAIT_DELAY_MS = 700
_DEEP_THINKING_MARKERS = (
    "分析",
    "比較",
    "評估",
    "規劃",
    "策略",
    "權衡",
    "利弊",
    "風險",
    "優先順序",
    "推理",
    "深入",
    "詳細說明",
    "從長計議",
    "該不該",
    "是否應該",
    "如何取捨",
    "不好回答",
    "難以回答",
    "認真想",
)


def plan_wait_expressions(prompt: str) -> tuple[WaitExpressionCue, ...]:
    """Plan restrained reactions without treating network wait as emotion.

    Routine prompts keep the current pose during a normal response window.
    Analytical prompts may show thinking only after a noticeable delay, while
    a long narrative may receive a neutral attentive pose. Every prompt has
    the same final timeout cue because an unusually long real wait can itself
    justify a thinking reaction.
    """

    compact = "".join(str(prompt or "").split())
    if not compact:
        return ()

    score = 0
    marker_hits = sum(word in compact for word in _DEEP_THINKING_MARKERS)
    score += min(4, marker_hits * 2)
    if len(compact) >= 56:
        score += 1
    if len(compact) >= 110:
        score += 1
    if compact.count("？") + compact.count("?") >= 2:
        score += 1
    if sum(compact.count(mark) for mark in ("。", "；", ";", "\n")) >= 2:
        score += 1

    cues: list[WaitExpressionCue] = []
    if score >= 2:
        cues.append(
            WaitExpressionCue(
                "thinking_front",
                _COMPLEX_WAIT_DELAY_MS,
                0.58,
                "complex_prompt_still_pending",
            )
        )
    elif len(compact) >= 34:
        cues.append(
            WaitExpressionCue(
                "attentive_front",
                _ATTENTIVE_WAIT_DELAY_MS,
                0.38,
                "long_narrative_still_pending",
            )
        )

    cues.append(
        WaitExpressionCue(
            "thinking_front",
            AI_WAIT_TIMEOUT_MS,
            0.5,
            "response_timeout",
        )
    )
    return tuple(cues)


def parse_internal_emotion(value: str) -> TaggedReply:
    """Remove every internal marker and return only a validated final tag."""
    raw = str(value or "")
    matches = list(_EMOTION_TAG.finditer(raw))
    cleaned = _ANY_EMOTION_TAG.sub("", raw).strip()
    if not matches:
        return TaggedReply(cleaned, None, None, 0.5, False)
    emotion = matches[-1].group(1).lower()
    expression = EMOTION_TO_EXPRESSION.get(emotion)
    if expression is None:
        return TaggedReply(cleaned, None, None, 0.5, False)
    intensity_text = matches[-1].group(2)
    intensity = 0.5 if intensity_text is None else float(intensity_text)
    intensity = max(0.0, min(1.0, intensity))
    return TaggedReply(cleaned, expression, emotion, intensity, True)


@dataclass(frozen=True, slots=True)
class ExpressionRule:
    priority: int
    minimum_ms: int
    maximum_ms: int
    cooldown_ms: int


DEFAULT_EXPRESSION_RULE = ExpressionRule(40, 1_600, 3_200, 4_500)
EXPRESSION_RULES = frozendict({
    "thinking_front": ExpressionRule(42, 1_500, 3_600, 9_000),
    "attentive_front": ExpressionRule(38, 1_500, 3_400, 3_000),
    "determined_front": ExpressionRule(66, 1_700, 3_800, 5_000),
    "gentle_smile_front": ExpressionRule(40, 1_700, 3_800, 4_000),
    "happy": ExpressionRule(44, 1_600, 3_600, 4_000),
    "proud_front": ExpressionRule(48, 1_700, 3_800, 5_000),
    "relieved_front": ExpressionRule(52, 1_800, 4_000, 5_000),
    "worried": ExpressionRule(74, 2_000, 4_600, 5_000),
    "worried_front": ExpressionRule(76, 2_000, 4_800, 5_000),
    "reminder": ExpressionRule(92, 2_200, 5_000, 7_000),
    "surprised_front": ExpressionRule(58, 1_400, 3_000, 5_000),
    "shy_front": ExpressionRule(50, 1_800, 4_000, 7_000),
    "shy_cute_front": ExpressionRule(52, 1_800, 4_200, 7_000),
    "caught": ExpressionRule(62, 2_200, 4_200, 9_000),
    "restrained_amused_front": ExpressionRule(44, 1_600, 3_600, 5_000),
    "exasperated_front": ExpressionRule(54, 1_800, 4_000, 6_000),
    "mock_scold": ExpressionRule(82, 2_000, 4_400, 9_000),
    "mock_hit_front": ExpressionRule(86, 2_200, 4_600, 12_000),
    "eureka_front": ExpressionRule(64, 1_700, 3_800, 5_000),
    "protective_front": ExpressionRule(94, 2_300, 5_200, 8_000),
})
SOURCE_PRIORITY_BONUS = frozendict({
    "ambient": -20,
    "ai_wait": -12,
    "fallback": 0,
    "ai_tag": 4,
    "conversation": 4,
    "user_direct": 10,
    "reminder": 18,
    "safety": 25,
})
BASE_EXPRESSIONS = frozenset({"idle", "speaking"})

# The exclusive-favor (主上專屬寵溺) devotion bonus.  When the companion is
# "devoted" (favor >= FAVOR_DEVOTED_THRESHOLD), every user-facing expression
# gains this priority bonus so her fondness for the user outranks competing
# states such as jealousy or drowsiness.  It is a small, bounded nudge — never
# enough to override a safety or reminder cue, but enough to let a devoted
# companion smile at the user even while she is tired or a little jealous.
DEVOTION_PRIORITY_BONUS = 6
FAVOR_DEVOTED_THRESHOLD = 0.7


def devotion_bonus(favor_score: float) -> int:
    """Return the priority bonus granted by the exclusive-favor coefficient.

    ``favor_score`` is in [0, 1].  Below the devoted threshold the bonus is
    zero; at or above it the companion earns ``DEVOTION_PRIORITY_BONUS``.
    """
    if float(favor_score) >= FAVOR_DEVOTED_THRESHOLD:
        return DEVOTION_PRIORITY_BONUS
    return 0


@dataclass(frozen=True, slots=True)
class ExpressionDecision:
    accepted: bool
    expression: str
    reason: str
    hold_ms: int
    priority: int
    generation: int


class ExpressionArbiter:
    """Deterministic expression arbitration independent of the Qt event loop."""

    def __init__(
        self,
        allowed: Collection[str],
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.allowed = frozenset(allowed) | BASE_EXPRESSIONS
        self.clock = clock or time.monotonic
        self.active = "idle"
        self.active_since_ms = self._now_ms()
        self.active_priority = 0
        self.generation = 0
        self.last_started_ms: dict[str, int] = {}
        self.audit: deque[dict[str, object]] = deque(maxlen=256)

    def _now_ms(self) -> int:
        return int(self.clock() * 1000)

    @staticmethod
    def rule(expression: str) -> ExpressionRule:
        return EXPRESSION_RULES.get(expression, DEFAULT_EXPRESSION_RULE)

    @classmethod
    def hold_duration(cls, expression: str, intensity: float = 0.5) -> int:
        rule = cls.rule(expression)
        weight = max(0.0, min(1.0, float(intensity)))
        return round(
            rule.minimum_ms
            + (rule.maximum_ms - rule.minimum_ms) * weight
        )

    def request(
        self,
        expression: str,
        *,
        source: str = "conversation",
        intensity: float = 0.5,
        force: bool = False,
        now_ms: int | None = None,
        favor_score: float = 0.0,
    ) -> ExpressionDecision:
        now = self._now_ms() if now_ms is None else int(now_ms)
        expression = str(expression)
        rule = self.rule(expression)
        priority = (
            rule.priority
            + SOURCE_PRIORITY_BONUS.get(source, 0)
            + devotion_bonus(favor_score)
        )
        hold_ms = self.hold_duration(expression, intensity)
        rejection = self._rejection_reason(
            expression,
            rule,
            priority,
            now,
            force,
        )
        accepted = rejection is None
        if accepted:
            self._activate(expression, priority, now)

        decision = ExpressionDecision(
            accepted,
            expression,
            rejection or "accepted",
            hold_ms,
            priority,
            self.generation,
        )
        self._record(decision, source, intensity, now)
        return decision

    def _rejection_reason(
        self,
        expression: str,
        rule: ExpressionRule,
        priority: int,
        now: int,
        force: bool,
    ) -> str | None:
        reason = None
        if expression not in self.allowed:
            reason = "unknown_expression"
        elif not force and expression == self.active:
            reason = "duplicate_active"
        elif not force and expression not in BASE_EXPRESSIONS:
            reason = self._timing_rejection(expression, rule, priority, now)
        return reason

    def _timing_rejection(
        self,
        expression: str,
        rule: ExpressionRule,
        priority: int,
        now: int,
    ) -> str | None:
        last_started = self.last_started_ms.get(expression)
        if last_started is not None and now - last_started < rule.cooldown_ms:
            return "cooldown"
        active_age = now - self.active_since_ms
        minimum_hold_active = (
            self.active not in BASE_EXPRESSIONS
            and active_age < self.rule(self.active).minimum_ms
            and priority <= self.active_priority
        )
        return "minimum_hold" if minimum_hold_active else None

    def _activate(self, expression: str, priority: int, now: int) -> None:
        self.generation += 1
        self.active = expression
        self.active_since_ms = now
        self.active_priority = priority
        if expression not in BASE_EXPRESSIONS:
            self.last_started_ms[expression] = now

    def _record(
        self,
        decision: ExpressionDecision,
        source: str,
        intensity: float,
        now: int,
    ) -> None:
        self.audit.append(
            {
                "time_ms": now,
                "expression": decision.expression,
                "source": source,
                "intensity": round(float(intensity), 3),
                "accepted": decision.accepted,
                "reason": decision.reason,
                "generation": self.generation,
            }
        )
