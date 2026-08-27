from __future__ import annotations

lazy import random
lazy import time
lazy from collections import deque
lazy from collections.abc import Callable
lazy from dataclasses import dataclass
lazy from enum import StrEnum

BACK_DEPTH_TWO_THIRDS = 2


class SpeechLifecycle(StrEnum):
    IDLE = "idle"
    STARTING = "starting"
    SPEAKING = "speaking"
    ENDING = "ending"


class SemanticEmotion(StrEnum):
    NEUTRAL = "neutral"
    ATTENTIVE = "attentive"
    GENTLE = "gentle"
    HAPPY = "happy"
    SAD = "sad"
    WORRIED = "worried"
    ANGRY = "angry"
    REMINDER = "reminder"
    SAFETY = "safety"


class GazeTarget(StrEnum):
    USER = "user"
    NEAR_USER = "near_user"
    AWAY = "away"
    DOWN = "down"


class BreathStyle(StrEnum):
    CALM = "calm"
    SPEAKING = "speaking"
    HELD = "held"
    SETTLING = "settling"


class TransitionStyle(StrEnum):
    HOLD = "hold"
    SOFT = "soft"
    TURN_AWAY = "turn_away"
    TURN_BACK = "turn_back"
    SAFETY = "safety"


# Behavior-director thresholds.
PRIORITY_COOLDOWN_THRESHOLD = 90
ANGER_LEVEL_1_THRESHOLD = 0.55
ANGER_LEVEL_2_THRESHOLD = 0.86
AWAY_SECONDS_THRESHOLD = 30


@dataclass(frozen=True, slots=True)
class BehaviorInput:
    speech: SpeechLifecycle
    emotion: SemanticEmotion
    emotion_intensity: float
    conversation_turn: int
    user_in_gaze: bool
    user_present: bool
    away_seconds: float
    current_pose: str
    previous_action: str
    proactive_performance_disabled: bool = False

    def __post_init__(self) -> None:
        if not 0.0 <= self.emotion_intensity <= 1.0:
            raise ValueError("Emotion intensity must be within 0..1.")
        if self.conversation_turn < 0 or self.away_seconds < 0:
            raise ValueError("Conversation turn and away time must be non-negative.")
        if not self.current_pose.strip():
            raise ValueError("Current pose must not be empty.")


@dataclass(frozen=True, slots=True)
class BodyPerformancePlan:
    pose: str
    view: str
    face: str
    left_hand: str
    right_hand: str
    gaze: GazeTarget
    breath: BreathStyle
    transition: TransitionStyle
    hold_ms: int

    def __post_init__(self) -> None:
        if self.hold_ms < 0:
            raise ValueError("A performance hold must not be negative.")
        if not all(
            value.strip()
            for value in (
                self.pose,
                self.view,
                self.face,
                self.left_hand,
                self.right_hand,
            )
        ):
            raise ValueError("Every atomic performance layer must be explicit.")
        if self.pose == "back-full" and self.gaze is not GazeTarget.AWAY:
            raise ValueError("A full back view cannot gaze at the user.")
        if self.pose.startswith("back-") and (
            self.left_hand != "relaxed" or self.right_hand != "relaxed"
        ):
            raise ValueError("Back-facing plans require conflict-free relaxed hands.")


@dataclass(frozen=True, slots=True)
class _Candidate:
    pose: str
    view: str
    face: str
    left_hand: str
    right_hand: str
    gaze: GazeTarget
    breath: BreathStyle
    transition: TransitionStyle
    minimum_hold_ms: int
    speech_safe: bool
    action: str

    def plan(self, hold_ms: int) -> BodyPerformancePlan:
        return BodyPerformancePlan(
            self.pose,
            self.view,
            self.face,
            self.left_hand,
            self.right_hand,
            self.gaze,
            self.breath,
            self.transition,
            hold_ms,
        )


_SPEECH_ACTIVE = frozenset({SpeechLifecycle.STARTING, SpeechLifecycle.SPEAKING})
_BACK_DEPTH = frozendict({
    "front-crossed": 0,
    "left-cheek-rest": 0,
    "left-neutral": 1,
    "right-neutral": 1,
    "back-two-thirds-left": 2,
    "back-two-thirds-right": 2,
    "back-full": 3,
})
# The canonical view for each pose, mirroring the candidate constructors.
# _disabled_plan previously hard-coded "left-030" for every non-front pose,
# rendering e.g. right-neutral from the opposite side's camera.
_POSE_VIEWS = frozendict({
    "front-crossed": "front-000",
    "left-cheek-rest": "left-030",
    "left-neutral": "left-045",
    "right-neutral": "right-045",
    "back-two-thirds-left": "back-left-120",
    "back-two-thirds-right": "back-right-120",
    "back-full": "back-180",
})


class BehaviorDirector:
    """Deterministic, local-only director for constrained natural variation."""

    def __init__(
        self,
        *,
        clock: Callable[[], float] | None = None,
        rng: random.Random | None = None,
        seed: int | None = None,
        cooldown_ms: int = 2_400,
    ) -> None:
        if rng is not None and seed is not None:
            raise ValueError("Inject either rng or seed, not both.")
        if cooldown_ms < 0:
            raise ValueError("Cooldown must not be negative.")
        self._clock = clock or time.monotonic
        self._rng = rng or random.Random(seed)
        self._cooldown_ms = cooldown_ms
        self._active: BodyPerformancePlan | None = None
        self._active_priority = -1
        self._hold_until_ms = 0
        self._last_change_ms = -cooldown_ms
        self._last_action = ""
        self._recent: deque[str] = deque(maxlen=3)
        self._back_depth = 0
        self._back_side = "left"

    def direct(self, context: BehaviorInput) -> BodyPerformancePlan:
        now = round(self._clock() * 1000)
        if (
            context.previous_action
            and context.previous_action != self._last_action
            and context.previous_action not in self._recent
        ):
            self._recent.append(context.previous_action)
        if context.proactive_performance_disabled:
            plan = self._disabled_plan(context)
            self._remember(plan, "disabled-neutral", 100, now)
            self._back_depth = 0
            return plan

        priority = self._priority(context)
        speech_requires_safe = (
            context.speech in _SPEECH_ACTIVE
            and self._active is not None
            and not self._is_speech_safe(self._active)
        )
        if (
            self._active is not None
            and now < self._hold_until_ms
            and priority <= self._active_priority
            and not speech_requires_safe
        ):
            return self._active

        candidate = self._candidate(context, now)
        if context.speech in _SPEECH_ACTIVE and not candidate.speech_safe:
            candidate = self._speech_safe_candidate(context)
        if (
            priority < PRIORITY_COOLDOWN_THRESHOLD
            and now - self._last_change_ms < self._cooldown_ms
            and self._active is not None
            and not speech_requires_safe
        ):
            return self._active

        hold_ms = self._variable_hold(candidate.minimum_hold_ms)
        plan = candidate.plan(hold_ms)
        if not self._transition_is_safe(self._active, plan):
            candidate = self._safe_intermediate(context)
            hold_ms = self._variable_hold(candidate.minimum_hold_ms)
            plan = candidate.plan(hold_ms)
        self._remember(plan, candidate.action, priority, now)
        if candidate.action.startswith(("anger-", "recover-")):
            self._back_depth = _BACK_DEPTH.get(plan.pose, 0)
        elif context.speech in _SPEECH_ACTIVE:
            # A speech-safe replacement does not mean she actually turned
            # around: the coordinator refuses deep pose jumps and keeps the
            # rear pose on screen through speech.  Keep the recovery debt so
            # the post-speech gradient still runs; zeroing it here left the
            # coordinator stranded in back-full with every later candidate
            # rejected as an unsafe jump.
            pass
        else:
            self._back_depth = 0
        if plan.pose.endswith("-right") or plan.pose == "right-neutral":
            # "right-neutral" does not end with "-right"; without its own
            # case the side memory stayed "left" and an anger escalation
            # that began on her right side swept across the front to the
            # left rear mid-sequence.
            self._back_side = "right"
        elif plan.pose.endswith("-left") or plan.pose == "left-neutral":
            self._back_side = "left"
        return plan

    def _candidate(self, context: BehaviorInput, now: int) -> _Candidate:
        if context.emotion is SemanticEmotion.SAFETY:
            return self._safety_candidate(context)
        if context.emotion is SemanticEmotion.REMINDER:
            return self._reminder_candidate(context)
        if context.emotion is SemanticEmotion.ANGRY:
            return self._anger_candidate(context)
        if self._back_depth:
            return self._recovery_candidate(context)
        if context.speech in _SPEECH_ACTIVE:
            return self._speech_safe_candidate(context)
        return self._ambient_candidate(context, now)

    @staticmethod
    def _priority(context: BehaviorInput) -> int:
        if context.emotion is SemanticEmotion.SAFETY:
            return 100
        if context.emotion is SemanticEmotion.REMINDER:
            return 92
        if context.speech in _SPEECH_ACTIVE:
            return 80
        if context.emotion is SemanticEmotion.ANGRY:
            return 70 + round(context.emotion_intensity * 10)
        return 40

    def _anger_candidate(self, context: BehaviorInput) -> _Candidate:
        target = 1 if context.emotion_intensity < ANGER_LEVEL_1_THRESHOLD else (
            2 if context.emotion_intensity < ANGER_LEVEL_2_THRESHOLD else 3
        )
        if context.speech in _SPEECH_ACTIVE:
            target = min(target, 1)
        next_depth = min(target, self._back_depth + 1)
        if next_depth <= self._back_depth and self._active is not None:
            return self._candidate_from_plan(self._active, "anger-hold")
        if next_depth == 1:
            side = self._choose_side("anger-side")
            speaking = context.speech in _SPEECH_ACTIVE
            return _Candidate(
                f"{side}-neutral",
                f"{side}-045",
                "displeased-speaking" if speaking else (
                    "hurt-controlled" if target >= BACK_DEPTH_TWO_THIRDS else "displeased"
                ),
                "relaxed",
                "relaxed",
                GazeTarget.NEAR_USER,
                BreathStyle.SPEAKING if speaking else BreathStyle.HELD,
                TransitionStyle.TURN_AWAY,
                2_200,
                True,
                f"anger-side-{side}",
            )
        if next_depth == BACK_DEPTH_TWO_THIRDS:
            return _Candidate(
                f"back-two-thirds-{self._back_side}",
                f"back-{self._back_side}-120",
                "hurt-withdrawn",
                "relaxed",
                "relaxed",
                GazeTarget.AWAY,
                BreathStyle.HELD,
                TransitionStyle.TURN_AWAY,
                3_000,
                False,
                "anger-two-thirds",
            )
        return _Candidate(
            "back-full",
            "back-180",
            "hidden",
            "relaxed",
            "relaxed",
            GazeTarget.AWAY,
            BreathStyle.HELD,
            TransitionStyle.TURN_AWAY,
            3_800,
            False,
            "anger-full-back",
        )

    def _recovery_candidate(self, context: BehaviorInput) -> _Candidate:
        next_depth = max(0, self._back_depth - 1)
        # While she is speaking, a recovery step is part of the spoken turn:
        # breathe like speech, not like a silent settle.
        recovery_breath = (
            BreathStyle.SPEAKING
            if context.speech in _SPEECH_ACTIVE
            else BreathStyle.SETTLING
        )
        if next_depth == BACK_DEPTH_TWO_THIRDS:
            return _Candidate(
                f"back-two-thirds-{self._back_side}",
                f"back-{self._back_side}-120",
                "settling",
                "relaxed",
                "relaxed",
                GazeTarget.AWAY,
                recovery_breath,
                TransitionStyle.TURN_BACK,
                2_600,
                False,
                "recover-two-thirds",
            )
        if next_depth == 1:
            return _Candidate(
                f"{self._back_side}-neutral",
                f"{self._back_side}-045",
                "settling",
                "relaxed",
                "relaxed",
                GazeTarget.NEAR_USER,
                recovery_breath,
                TransitionStyle.TURN_BACK,
                2_200,
                True,
                "recover-side",
            )
        # The final step must actually face front.  Echoing current_pose here
        # returned the previous recover-side pose (depth 1, still in
        # _BACK_DEPTH), which wrote the debt back and locked the recovery
        # gradient into an endless side-neutral loop.
        return _Candidate(
            "front-crossed",
            "front-000",
            "neutral",
            "relaxed",
            "relaxed",
            GazeTarget.USER if context.user_present else GazeTarget.DOWN,
            BreathStyle.CALM,
            TransitionStyle.TURN_BACK,
            2_000,
            True,
            "recover-front",
        )

    def _speech_safe_candidate(self, context: BehaviorInput) -> _Candidate:
        choices = (
            _Candidate(
                "front-crossed", "front-000", "speaking", "relaxed", "relaxed",
                GazeTarget.USER, BreathStyle.SPEAKING, TransitionStyle.SOFT,
                1_400, True, "speech-front",
            ),
            _Candidate(
                "left-neutral", "left-030", "speaking", "relaxed", "relaxed",
                GazeTarget.NEAR_USER, BreathStyle.SPEAKING, TransitionStyle.SOFT,
                1_400, True, "speech-left",
            ),
            _Candidate(
                "right-neutral", "right-030", "speaking", "relaxed", "relaxed",
                GazeTarget.NEAR_USER, BreathStyle.SPEAKING, TransitionStyle.SOFT,
                1_400, True, "speech-right",
            ),
        )
        return self._choose(choices, offset=context.conversation_turn)

    def _ambient_candidate(self, context: BehaviorInput, now: int) -> _Candidate:
        del now
        if not context.user_present or context.away_seconds >= AWAY_SECONDS_THRESHOLD:
            return _Candidate(
                "front-crossed", "front-000", "idle", "relaxed", "relaxed",
                GazeTarget.DOWN, BreathStyle.CALM, TransitionStyle.SOFT,
                2_600, True, "ambient-wait",
            )
        face = {
            SemanticEmotion.HAPPY: "gentle-smile",
            SemanticEmotion.GENTLE: "gentle-smile",
            SemanticEmotion.ATTENTIVE: "attentive",
            SemanticEmotion.WORRIED: "worried",
            SemanticEmotion.SAD: "soft-concern",
        }.get(context.emotion, "neutral")
        gaze = GazeTarget.USER if context.user_in_gaze else GazeTarget.NEAR_USER
        choices = (
            _Candidate(
                "front-crossed", "front-000", face, "relaxed", "relaxed",
                gaze, BreathStyle.CALM, TransitionStyle.SOFT,
                2_200, True, "ambient-front",
            ),
            _Candidate(
                "left-neutral", "left-030", face, "relaxed", "relaxed",
                gaze, BreathStyle.CALM, TransitionStyle.SOFT,
                2_200, True, "ambient-left",
            ),
            _Candidate(
                "right-neutral", "right-030", face, "relaxed", "relaxed",
                gaze, BreathStyle.CALM, TransitionStyle.SOFT,
                2_200, True, "ambient-right",
            ),
            # A cheek-rest pose adds a thoughtful, lively variation to idle
            # time.  It is not speech-safe, so the director will substitute a
            # safe pose the moment speech begins.
            _Candidate(
                "left-cheek-rest", "left-030", "cheek", "relaxed", "relaxed",
                GazeTarget.NEAR_USER, BreathStyle.CALM, TransitionStyle.SOFT,
                2_600, False, "ambient-cheek-rest",
            ),
        )
        return self._choose(choices, offset=context.conversation_turn)

    @staticmethod
    def _safety_candidate(context: BehaviorInput) -> _Candidate:
        return _Candidate(
            "front-crossed", "front-000",
            "protective-speaking" if context.speech in _SPEECH_ACTIVE else "protective",
            "open", "open", GazeTarget.USER,
            BreathStyle.SPEAKING if context.speech in _SPEECH_ACTIVE else BreathStyle.CALM,
            TransitionStyle.SAFETY, 2_800, True, "safety",
        )

    @staticmethod
    def _reminder_candidate(context: BehaviorInput) -> _Candidate:
        return _Candidate(
            "front-crossed", "front-000",
            "reminder-speaking" if context.speech in _SPEECH_ACTIVE else "reminder",
            "open", "relaxed", GazeTarget.USER,
            BreathStyle.SPEAKING if context.speech in _SPEECH_ACTIVE else BreathStyle.CALM,
            TransitionStyle.SOFT, 2_400, True, "reminder",
        )

    def _safe_intermediate(self, context: BehaviorInput) -> _Candidate:
        """One recovery-gradient step toward the front from the active depth.

        The previous fixed side-neutral (depth 1) fallback was itself an
        unsafe jump when the active pose was back-full (depth 3), and the
        speech branch jumped straight to front (depth 0).  Stepping exactly
        one depth level keeps every emitted transition within the safety
        contract this method exists to uphold, and the recover- action keeps
        the back-depth bookkeeping truthful.
        """
        active_depth = (
            _BACK_DEPTH.get(self._active.pose, 0)
            if self._active is not None
            else 0
        )
        step = max(0, active_depth - 1)
        step_breath = (
            BreathStyle.SPEAKING
            if context.speech in _SPEECH_ACTIVE
            else BreathStyle.SETTLING
        )
        if step == BACK_DEPTH_TWO_THIRDS:
            return _Candidate(
                f"back-two-thirds-{self._back_side}",
                f"back-{self._back_side}-120",
                "settling", "relaxed", "relaxed", GazeTarget.AWAY,
                step_breath, TransitionStyle.TURN_BACK, 2_600,
                False, "recover-two-thirds",
            )
        if step == 1:
            return _Candidate(
                f"{self._back_side}-neutral", f"{self._back_side}-045",
                "settling", "relaxed", "relaxed", GazeTarget.NEAR_USER,
                step_breath, TransitionStyle.SOFT, 2_000, True,
                "recover-side",
            )
        if context.speech in _SPEECH_ACTIVE:
            return self._speech_safe_candidate(context)
        return _Candidate(
            "front-crossed", "front-000", "neutral", "relaxed", "relaxed",
            GazeTarget.USER if context.user_present else GazeTarget.DOWN,
            BreathStyle.CALM, TransitionStyle.TURN_BACK, 2_000, True,
            "recover-front",
        )

    @staticmethod
    def _disabled_plan(context: BehaviorInput) -> BodyPerformancePlan:
        pose = context.current_pose
        default_view = "right-030" if "right" in pose else "left-030"
        # Rear poses must not gaze at the user (BodyPerformancePlan raises
        # on that combination).  The previous USER/DOWN gaze made direct()
        # throw on every frame while she was turned away with performances
        # disabled, freezing the screen on her back permanently.
        rear = _BACK_DEPTH.get(pose, 0) >= BACK_DEPTH_TWO_THIRDS
        return BodyPerformancePlan(
            pose,
            _POSE_VIEWS.get(pose, default_view),
            "neutral",
            "relaxed",
            "relaxed",
            GazeTarget.AWAY
            if rear
            else (GazeTarget.USER if context.user_present else GazeTarget.DOWN),
            BreathStyle.CALM,
            TransitionStyle.HOLD,
            0,
        )

    def _choose(
        self,
        choices: tuple[_Candidate, ...],
        *,
        offset: int = 0,
    ) -> _Candidate:
        eligible = tuple(choice for choice in choices if choice.action not in self._recent)
        pool = eligible or choices
        return pool[(self._rng.randrange(len(pool)) + offset) % len(pool)]

    def _choose_side(self, prefix: str) -> str:
        choices = tuple(
            side for side in ("left", "right")
            if f"{prefix}-{side}" not in self._recent
        ) or ("left", "right")
        return choices[self._rng.randrange(len(choices))]

    def _variable_hold(self, minimum_ms: int) -> int:
        return minimum_ms + self._rng.randrange(0, 601, 100)

    @staticmethod
    def _is_speech_safe(plan: BodyPerformancePlan) -> bool:
        return plan.pose in {"front-crossed", "left-neutral", "right-neutral"}

    @staticmethod
    def _transition_is_safe(
        previous: BodyPerformancePlan | None,
        next_plan: BodyPerformancePlan,
    ) -> bool:
        if previous is None:
            return _BACK_DEPTH.get(next_plan.pose, 0) <= 1
        previous_depth = _BACK_DEPTH.get(previous.pose, 0)
        next_depth = _BACK_DEPTH.get(next_plan.pose, 0)
        return abs(previous_depth - next_depth) <= 1

    @staticmethod
    def _candidate_from_plan(
        plan: BodyPerformancePlan,
        action: str,
    ) -> _Candidate:
        return _Candidate(
            plan.pose, plan.view, plan.face, plan.left_hand, plan.right_hand,
            plan.gaze, plan.breath, TransitionStyle.HOLD,
            max(1_800, plan.hold_ms), BehaviorDirector._is_speech_safe(plan), action,
        )

    def _remember(
        self,
        plan: BodyPerformancePlan,
        action: str,
        priority: int,
        now: int,
    ) -> None:
        changed = self._active != plan
        self._active = plan
        self._active_priority = priority
        self._hold_until_ms = now + plan.hold_ms
        self._last_action = action
        if changed:
            self._last_change_ms = now
            self._recent.append(action)
