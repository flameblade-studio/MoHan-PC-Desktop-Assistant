from __future__ import annotations

lazy import math
lazy from dataclasses import dataclass
lazy from enum import StrEnum
lazy from typing import Final


class AppearanceDynamicsError(ValueError):
    """A secondary-motion input or configuration is unsafe."""


class DynamicsMode(StrEnum):
    STATIC = "static"
    REDUCED = "reduced"
    FULL = "full"


class MotionGroup(StrEnum):
    BODY = "body"
    SLEEVE = "sleeve"
    HAIR = "hair"
    ACCESSORY = "accessory"


@dataclass(frozen=True, slots=True)
class MotionTransform:
    offset_x: float = 0.0
    offset_y: float = 0.0
    rotation_degrees: float = 0.0
    scale_y: float = 1.0


IDENTITY_TRANSFORM: Final = MotionTransform()


@dataclass(frozen=True, slots=True)
class DynamicsConfiguration:
    enabled: bool = False
    mode: DynamicsMode = DynamicsMode.FULL
    fixed_step_seconds: float = 1.0 / 60.0
    maximum_dt_seconds: float = 0.1
    maximum_substeps: int = 4
    breathing_hz: float = 0.22
    breathing_pixels: float = 1.2
    breathing_scale: float = 0.0025

    def __post_init__(self) -> None:
        if type(self.enabled) is not bool or not isinstance(self.mode, DynamicsMode):
            raise AppearanceDynamicsError("Dynamics configuration is invalid.")
        finite_positive = (
            self.fixed_step_seconds,
            self.maximum_dt_seconds,
            self.breathing_hz,
        )
        finite_nonnegative = (self.breathing_pixels, self.breathing_scale)
        if not all(math.isfinite(value) and value > 0 for value in finite_positive):
            raise AppearanceDynamicsError("Dynamics timing is invalid.")
        if not all(
            math.isfinite(value) and value >= 0 for value in finite_nonnegative
        ):
            raise AppearanceDynamicsError("Breathing configuration is invalid.")
        if (
            self.fixed_step_seconds > self.maximum_dt_seconds
            or type(self.maximum_substeps) is not int
            or not 1 <= self.maximum_substeps <= 8
            or self.breathing_pixels > 4.0
            or self.breathing_scale > 0.01
        ):
            raise AppearanceDynamicsError("Dynamics limits are invalid.")


DEFAULT_DYNAMICS_CONFIGURATION: Final = DynamicsConfiguration()


@dataclass(frozen=True, slots=True)
class DynamicsInput:
    dt_seconds: float
    motion_x: float = 0.0
    motion_y: float = 0.0
    gravity_x: float = 0.0
    gravity_y: float = 1.0

    def __post_init__(self) -> None:
        values = (
            self.dt_seconds,
            self.motion_x,
            self.motion_y,
            self.gravity_x,
            self.gravity_y,
        )
        if not all(math.isfinite(value) for value in values) or self.dt_seconds < 0:
            raise AppearanceDynamicsError("Dynamics input is invalid.")


@dataclass(frozen=True, slots=True)
class DynamicsFrame:
    tick: int
    transforms: frozendict[MotionGroup, MotionTransform]
    static_fallback: bool

    def for_group(self, group: MotionGroup) -> MotionTransform:
        return self.transforms.get(group, IDENTITY_TRANSFORM)

    def for_slot(self, slot: str) -> MotionTransform:
        group = motion_group_for_slot(slot)
        return IDENTITY_TRANSFORM if group is None else self.for_group(group)


@dataclass(frozen=True, slots=True)
class DynamicsSnapshot:
    accumulator: float
    breathing_phase: float
    tick: int
    states: tuple[tuple[MotionGroup, tuple[float, float, float, float, float, float]], ...]
    last_frame: DynamicsFrame


@dataclass(frozen=True, slots=True)
class _MotionProfile:
    stiffness: float
    damping: float
    inertia_x: float
    inertia_y: float
    gravity_x: float
    gravity_y: float
    rotation_response: float
    maximum_offset: float
    maximum_rotation: float


@dataclass(slots=True)
class _MotionState:
    x: float = 0.0
    y: float = 0.0
    velocity_x: float = 0.0
    velocity_y: float = 0.0
    rotation: float = 0.0
    rotation_velocity: float = 0.0


_PROFILES: Final = frozendict(
    {
        MotionGroup.BODY: _MotionProfile(45.0, 13.0, -0.35, -0.20, 0.05, 0.08, 0.8, 2.0, 1.0),
        MotionGroup.SLEEVE: _MotionProfile(20.0, 7.5, -1.8, -1.0, 0.25, 0.45, 3.5, 8.0, 8.0),
        MotionGroup.HAIR: _MotionProfile(16.0, 6.5, -2.2, -1.1, 0.35, 0.60, 4.2, 10.0, 10.0),
        MotionGroup.ACCESSORY: _MotionProfile(24.0, 8.0, -1.4, -0.8, 0.20, 0.50, 5.0, 7.0, 12.0),
    }
)
_REDUCED_GROUPS: Final = frozenset({MotionGroup.BODY, MotionGroup.HAIR})
_SLEEVE_SLOTS: Final = frozenset({"sleeve", "sleeve-left", "sleeve-right"})
_HAIR_SLOTS: Final = frozenset(
    {"hair", "back", "front", "side-left", "side-right", "bangs", "bun", "ponytail"}
)
_ACCESSORY_SLOTS: Final = frozenset(
    {
        "headwear",
        "weapon",
        "sheath",
        "handheld",
        "jewelry",
        "foreground-effect",
    }
)


def motion_group_for_slot(slot: str) -> MotionGroup | None:
    """Map an existing generic layer slot without requiring pack changes."""

    normalized = str(slot).strip().lower()
    if normalized in _SLEEVE_SLOTS:
        return MotionGroup.SLEEVE
    if normalized in _HAIR_SLOTS:
        return MotionGroup.HAIR
    if normalized in _ACCESSORY_SLOTS:
        return MotionGroup.ACCESSORY
    if normalized in {"body", "garment", "outerwear", "skirt", "trousers"}:
        return MotionGroup.BODY
    return None


class AppearanceDynamics:
    """Deterministic, bounded secondary motion with an explicit static fallback."""

    def __init__(
        self,
        configuration: DynamicsConfiguration = DEFAULT_DYNAMICS_CONFIGURATION,
        *,
        backend_available: bool = True,
    ) -> None:
        if type(backend_available) is not bool:
            raise AppearanceDynamicsError("Dynamics capability is invalid.")
        self._configuration = configuration
        self._backend_available = backend_available
        self._states = {group: _MotionState() for group in MotionGroup}
        self._accumulator = 0.0
        self._breathing_phase = 0.0
        self._tick = 0
        self._last_frame = self._static_frame()

    @property
    def state_count(self) -> int:
        """Expose the fixed allocation size for resource-boundary tests."""

        return len(self._states)

    @property
    def current_frame(self) -> DynamicsFrame:
        return self._last_frame

    def snapshot(self) -> DynamicsSnapshot:
        return DynamicsSnapshot(
            accumulator=self._accumulator,
            breathing_phase=self._breathing_phase,
            tick=self._tick,
            states=tuple(
                (
                    group,
                    (
                        state.x,
                        state.y,
                        state.velocity_x,
                        state.velocity_y,
                        state.rotation,
                        state.rotation_velocity,
                    ),
                )
                for group, state in self._states.items()
            ),
            last_frame=self._last_frame,
        )

    def restore(self, snapshot: DynamicsSnapshot) -> DynamicsFrame:
        if not isinstance(snapshot, DynamicsSnapshot):
            raise AppearanceDynamicsError("Dynamics snapshot is invalid.")
        if tuple(group for group, _values in snapshot.states) != tuple(MotionGroup):
            raise AppearanceDynamicsError("Dynamics snapshot is invalid.")
        self._accumulator = snapshot.accumulator
        self._breathing_phase = snapshot.breathing_phase
        self._tick = snapshot.tick
        for group, values in snapshot.states:
            state = self._states[group]
            (
                state.x,
                state.y,
                state.velocity_x,
                state.velocity_y,
                state.rotation,
                state.rotation_velocity,
            ) = values
        self._last_frame = snapshot.last_frame
        return self._last_frame

    def reset(self) -> DynamicsFrame:
        for state in self._states.values():
            state.x = state.y = state.velocity_x = state.velocity_y = 0.0
            state.rotation = state.rotation_velocity = 0.0
        self._accumulator = 0.0
        self._breathing_phase = 0.0
        self._tick = 0
        self._last_frame = self._static_frame()
        return self._last_frame

    def advance(self, sample: DynamicsInput) -> DynamicsFrame:
        if self._uses_static_fallback:
            self._last_frame = self._static_frame()
            return self._last_frame
        configuration = self._configuration
        accepted_dt = min(sample.dt_seconds, configuration.maximum_dt_seconds)
        maximum_backlog = configuration.fixed_step_seconds * configuration.maximum_substeps
        self._accumulator = min(self._accumulator + accepted_dt, maximum_backlog)
        steps = min(
            int(self._accumulator / configuration.fixed_step_seconds),
            configuration.maximum_substeps,
        )
        for _index in range(steps):
            self._step(sample, configuration.fixed_step_seconds)
        self._accumulator -= steps * configuration.fixed_step_seconds
        if steps:
            self._last_frame = self._dynamic_frame()
        return self._last_frame

    @property
    def _uses_static_fallback(self) -> bool:
        return (
            not self._configuration.enabled
            or not self._backend_available
            or self._configuration.mode is DynamicsMode.STATIC
        )

    def _active_groups(self) -> frozenset[MotionGroup]:
        if self._configuration.mode is DynamicsMode.REDUCED:
            return _REDUCED_GROUPS
        return frozenset(MotionGroup)

    def _step(self, sample: DynamicsInput, dt: float) -> None:
        motion_x = _clamp(sample.motion_x, -1.0, 1.0)
        motion_y = _clamp(sample.motion_y, -1.0, 1.0)
        gravity_x = _clamp(sample.gravity_x, -1.0, 1.0)
        gravity_y = _clamp(sample.gravity_y, -1.0, 1.0)
        active = self._active_groups()
        for group, state in self._states.items():
            if group not in active:
                continue
            profile = _PROFILES[group]
            target_x = motion_x * profile.inertia_x + gravity_x * profile.gravity_x
            target_y = motion_y * profile.inertia_y + gravity_y * profile.gravity_y
            target_rotation = (
                motion_x * profile.rotation_response
                + gravity_x * profile.rotation_response * 0.5
            )
            state.velocity_x += (
                (target_x - state.x) * profile.stiffness
                - state.velocity_x * profile.damping
            ) * dt
            state.velocity_y += (
                (target_y - state.y) * profile.stiffness
                - state.velocity_y * profile.damping
            ) * dt
            state.rotation_velocity += (
                (target_rotation - state.rotation) * profile.stiffness
                - state.rotation_velocity * profile.damping
            ) * dt
            state.x = _clamp(
                state.x + state.velocity_x * dt,
                -profile.maximum_offset,
                profile.maximum_offset,
            )
            state.y = _clamp(
                state.y + state.velocity_y * dt,
                -profile.maximum_offset,
                profile.maximum_offset,
            )
            state.rotation = _clamp(
                state.rotation + state.rotation_velocity * dt,
                -profile.maximum_rotation,
                profile.maximum_rotation,
            )
        self._breathing_phase = (
            self._breathing_phase
            + math.tau * self._configuration.breathing_hz * dt
        ) % math.tau
        self._tick += 1

    def _dynamic_frame(self) -> DynamicsFrame:
        breathing = math.sin(self._breathing_phase)
        active = self._active_groups()
        transforms: dict[MotionGroup, MotionTransform] = {}
        for group, state in self._states.items():
            if group not in active:
                transforms[group] = IDENTITY_TRANSFORM
                continue
            offset_y = state.y
            scale_y = 1.0
            if group is MotionGroup.BODY:
                offset_y += breathing * self._configuration.breathing_pixels
                scale_y += breathing * self._configuration.breathing_scale
            transforms[group] = MotionTransform(
                offset_x=state.x,
                offset_y=offset_y,
                rotation_degrees=state.rotation,
                scale_y=scale_y,
            )
        return DynamicsFrame(self._tick, frozendict(transforms), False)

    def _static_frame(self) -> DynamicsFrame:
        return DynamicsFrame(
            self._tick,
            frozendict({group: IDENTITY_TRANSFORM for group in MotionGroup}),
            True,
        )


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))
