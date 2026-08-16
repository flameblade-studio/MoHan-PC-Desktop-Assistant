from __future__ import annotations

lazy import time
lazy from collections.abc import Callable
lazy from dataclasses import dataclass
lazy from typing import Protocol

lazy from application.adaptive_character_runtime import AdaptiveCharacterRuntime
lazy from application.character_framing_app_bridge import CharacterFramingAppBridge
lazy from application.framing_orchestrator import FramingOrchestrator
lazy from application.full_body_performance_bridge import FullBodyPerformanceBridge
lazy from application.full_body_render_adapter import FullBodyRenderAdapter
lazy from domain.character_framing import CharacterFramingDirector

DEFAULT_CHARACTER_IMAGE_SIZE = 465


class AdaptiveCharacterRuntimePort(Protocol):
    """Narrow lifecycle used by the desktop composition root."""

    def begin_operation(self) -> int: ...

    def dispatch(self, request: object) -> object: ...

    def cancel(self, generation: int) -> None: ...


@dataclass(frozen=True, slots=True)
class AdaptiveCharacterComposition:
    """Optional v4 services created only after the feature gate opens."""

    runtime: AdaptiveCharacterRuntimePort
    assets: object | None = None


AdaptiveCharacterFactory = Callable[
    [Callable[[object], None]],
    AdaptiveCharacterComposition,
]


class _CallableFramePublisher:
    def __init__(self, publish: Callable[[object], None]) -> None:
        self._publish = publish

    def publish(self, frame: object) -> None:
        self._publish(frame)


def create_adaptive_character_composition(
    stage_frame: Callable[[object], None],
    *,
    image_size: int = DEFAULT_CHARACTER_IMAGE_SIZE,
    assets: object | None = None,
) -> AdaptiveCharacterComposition:
    """Build the optional 2.5D runtime behind one explicit boundary."""

    framing = CharacterFramingAppBridge(
        FramingOrchestrator(CharacterFramingDirector(time.monotonic))
    )
    renderer = FullBodyRenderAdapter(
        image_size,
        image_size,
        _CallableFramePublisher(stage_frame),
    )
    runtime = AdaptiveCharacterRuntime(
        framing,
        FullBodyPerformanceBridge(renderer),
    )
    return AdaptiveCharacterComposition(runtime, assets)
