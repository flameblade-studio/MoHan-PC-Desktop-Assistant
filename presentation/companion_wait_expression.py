from __future__ import annotations

lazy from domain.character_runtime_data import default_expression_catalog

_EXPRESSION_CATALOG = default_expression_catalog()


def start_ai_wait_expression(
    runtime: object,
    generation: int,
    expression: str,
    intensity: float,
) -> None:
    """Apply a low-priority wait pose only over a neutral visual state."""
    if expression not in _EXPRESSION_CATALOG.ai_wait_expressions:
        return
    if (
        runtime.speech_playing
        or runtime.realtime_mouth_active
        or runtime.realtime.running
        or runtime.state == "speaking"
    ):
        return
    if runtime.state not in _EXPRESSION_CATALOG.ai_wait_current_states:
        return
    if runtime.set_state(
        expression,
        source="ai_wait",
        intensity=intensity,
    ):
        runtime.active_ai_wait_generation = generation
        runtime.active_ai_wait_expression = expression


def finish_ai_wait_expression(runtime: object, generation: int) -> None:
    """Clear only the wait pose owned by this exact request."""
    if generation != runtime.active_ai_wait_generation:
        return
    expression = runtime.active_ai_wait_expression
    runtime.active_ai_wait_generation = 0
    runtime.active_ai_wait_expression = ""
    if (
        runtime.state == expression
        and not runtime.speech_playing
        and not runtime.realtime_mouth_active
    ):
        runtime.set_state("idle", source="ai_wait", force=True)
