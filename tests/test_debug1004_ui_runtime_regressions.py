from __future__ import annotations

lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from types import SimpleNamespace

lazy import pytest

lazy from infrastructure.db import StudioDB
lazy from presentation.autonomous_outfit_generation_controller import (
    AutonomousOutfitGenerationController,
)
lazy from presentation.companion_face_animation import CompanionFaceAnimationMixin
lazy from presentation.flagship.workflow_editor import WorkflowEditor
lazy from presentation.flagship_ui_localization import FlagshipTranslator
lazy from presentation.ui_localization import ui_text


class _Pool:
    def __init__(self) -> None:
        self.workers: list[object] = []

    def start(self, worker: object) -> None:
        self.workers.append(worker)


def test_abort_without_worker_does_not_cancel_the_next_outfit_job() -> None:
    with TemporaryDirectory(ignore_cleanup_errors=True) as temporary:
        root = Path(temporary)
        db = StudioDB(root / "mohan.db")
        db.set_setting("self_outfit_generation_enabled", True)
        controller = AutonomousOutfitGenerationController(
            db=db,
            secret_store=SimpleNamespace(load=lambda: "memory-test-key"),
            project_root=root,
        )
        controller._running = True
        controller._create_wardrobe = lambda _api_key: object()
        controller._pool = _Pool()

        controller.abort()
        assert controller._cancel.is_set()
        controller.request_generation(explicit=True)

        assert len(controller._pool.workers) == 1
        worker = controller._pool.workers[0]
        assert not worker.cancel_event.is_set()
        db.close()


def test_workflow_editor_parses_the_english_example_it_displays() -> None:
    class _Steps:
        def toPlainText(self) -> str:
            return FlagshipTranslator("en").text(
                "open_web｜開啟工作網站｜https://example.com"
            )

    class _EditorProbe:
        steps = _Steps()
        _step_arguments = WorkflowEditor._step_arguments

        @staticmethod
        def _t(key: str, **values: object) -> str:
            return key.format_map(values)

    example = _EditorProbe.steps.toPlainText()
    parsed = WorkflowEditor._workflow_steps(_EditorProbe())

    assert example == "open_web | Open the work site | https://example.com"
    assert parsed == [
        {
            "capability": "open_web",
            "description": "Open the work site",
            "arguments": {"url": "https://example.com"},
        }
    ]


@pytest.mark.parametrize(
    "language",
    ("zh-TW", "zh-CN", "en", "ja-JP"),
)
def test_caught_reaction_uses_localized_copy_when_available(
    language: str,
    monkeypatch,
) -> None:
    from presentation import companion_face_animation

    monkeypatch.setattr(
        companion_face_animation,
        "QTimer",
        SimpleNamespace(singleShot=lambda *_args: None),
    )

    class _ReactionProbe:
        def __init__(self) -> None:
            self.ui_language = language
            self.bubbles: list[str] = []
            self.translation_calls: list[tuple[str, str]] = []

        def set_state(self, *_args: object, **_kwargs: object) -> None:
            return

        def _t(self, key: str, fallback: str, **values: object) -> str:
            self.translation_calls.append((key, fallback))
            return f"test translation for {self.ui_language}"

        def _show_bubble(self, text: str) -> None:
            self.bubbles.append(text)

        def _schedule_return_to_idle(self, *_args: object) -> None:
            return

        def _hide_bubble_unless_speaking(self) -> None:
            return

    probe = _ReactionProbe()
    CompanionFaceAnimationMixin._show_caught_reaction(probe)

    assert probe.translation_calls == [("caught_glance_dialogue", CAUGHT_GLANCE_LINES["zh-TW"])]
    assert probe.bubbles == [f"test translation for {language}"]


# Owner-approved 2026-10-04 (candidate 2 of 3).
CAUGHT_GLANCE_LINES = {
    "zh-TW": "妾只是望向窗外，才不是在偷看主上。",
    "zh-CN": "妾只是望向窗外，才不是在偷看主上。",
    "en": "I was only looking out the window, not sneaking a glance at you.",
    "ja-JP": "窓の外を見ていただけです。主上を覗いていたわけではありません。",
}


@pytest.mark.parametrize(
    "language",
    ("zh-TW", "zh-CN", "en", "ja-JP"),
)
def test_caught_reaction_shows_the_owner_approved_line(
    language: str,
    monkeypatch,
) -> None:
    from presentation import companion_face_animation

    monkeypatch.setattr(
        companion_face_animation,
        "QTimer",
        SimpleNamespace(singleShot=lambda *_args: None),
    )

    class _PendingReactionProbe:
        def __init__(self) -> None:
            self.ui_language = language
            self.states: list[tuple[str, str]] = []
            self.bubbles: list[str] = []

        def set_state(self, state: str, *, source: str) -> None:
            self.states.append((state, source))

        def _t(self, key: str, fallback: str, **values: object) -> str:
            return ui_text(self.ui_language, key, fallback, **values)

        def _show_bubble(self, text: str) -> None:
            self.bubbles.append(text)

        def _schedule_return_to_idle(self, *_args: object) -> None:
            return

        def _hide_bubble_unless_speaking(self) -> None:
            return

    probe = _PendingReactionProbe()
    CompanionFaceAnimationMixin._show_caught_reaction(probe)

    assert probe.states == [("caught", "user_direct")]
    assert probe.bubbles == [CAUGHT_GLANCE_LINES[language]]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
