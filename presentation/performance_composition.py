from __future__ import annotations

lazy from collections.abc import Callable

lazy from application.body_pose_renderer import BodyPoseFrame
lazy from application.performance_app_bridge import PerformanceAppBridge
lazy from application.performance_runtime import BodyRenderRequest
lazy from domain.character_pose import default_pose_registry


class ExistingCharacterRenderer:
    """Expose the proven character image as the legacy fallback frame."""

    def __init__(self, frame_source: Callable[[int], BodyPoseFrame]) -> None:
        self._frame_source = frame_source
        self._generation = 0
        self.current_frame = frame_source(0)

    def begin_transition(self) -> int:
        self._generation += 1
        return self._generation

    def render(self, generation: int, *_args: object) -> BodyPoseFrame:
        if generation != self._generation:
            return self.current_frame
        self.current_frame = self._frame_source(generation)
        return self.current_frame


def create_performance_app_bridge(
    frame_source: Callable[[int], BodyPoseFrame],
    publish: Callable[[object], None],
) -> PerformanceAppBridge:
    registry = default_pose_registry()
    renderer = ExistingCharacterRenderer(frame_source)

    def render_request(frame, selected_registry):
        pose = selected_registry.get(frame.pose)
        if pose is None:
            return None
        return BodyRenderRequest(None, pose, pose)  # type: ignore[arg-type]

    return PerformanceAppBridge(
        registry,
        renderer,  # type: ignore[arg-type]
        render_request,
        publish,
        seed=315,
        minimum_render_interval_seconds=0.05,
    )
