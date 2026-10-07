from __future__ import annotations

lazy import json
lazy from pathlib import Path

lazy import pytest

lazy from application.background_agents import DiagnosticReportWorker
lazy from domain import sensory_synesthesia
lazy from domain.sensory_synesthesia import WeatherMood, complaint_line
lazy from integrations.ai_client import AIWorker, AIWorkerRequest, offline_reply
lazy from integrations.realtime_session import RealtimeSessionMethods
lazy from integrations.realtime_speech_output import _message
lazy from presentation.companion_face_animation import CompanionFaceAnimationMixin
lazy from presentation.companion_visual_dynamics import CompanionVisualDynamicsMixin
lazy from presentation.dashboard_conversation import (
    EMERGENCY_COMMANDS,
    DashboardConversationMixin,
)
lazy from tools import build_character_inventory

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_PATH = ROOT / "tests/data/persona-dialogue-voice-before.json"
ASSIGNED_PATHS = (
    "application/background_agents.py",
    "domain/sensory_synesthesia.py",
    "integrations/ai_client.py",
    "integrations/realtime_session.py",
    "integrations/realtime_speech_output.py",
    "presentation/companion_core.py",
    "presentation/companion_face_animation.py",
    "presentation/companion_visual_dynamics.py",
    "presentation/dashboard_conversation.py",
)
LOCALES = ("zh-TW", "zh-CN", "en", "ja-JP")


class _Settings:
    def __init__(self, values: dict[str, object]) -> None:
        self.values = values

    def setting(self, key: str, default: object = None) -> object:
        return self.values.get(key, default)


class _StartupProbe(CompanionVisualDynamicsMixin):
    def __init__(self, onboarding_complete: bool) -> None:
        self._visual_startup_complete = False
        self._startup_speech_requested = True
        self._closing = False
        self.db = _Settings(
            {
                "onboarding_complete": onboarding_complete,
                "user_title": "主上",
            }
        )
        self.spoken: list[list[str]] = []

    def _load_expression_assets(self) -> None:
        pass

    def _build_physics_layers(self) -> None:
        pass

    def _build_attention_layers(self) -> None:
        pass

    def _build_mouth_frames(self) -> None:
        pass

    def _update_physics_pose(self, _state: str) -> None:
        pass

    def _apply_physics_visibility(self) -> None:
        pass

    def _render_attention_layers(self, force: bool = False) -> None:
        del force

    def _setup_timers(self) -> None:
        pass

    def _setup_tray(self) -> None:
        pass

    def speak(self, text: str, state: str) -> None:
        self.spoken.append([text, state])


class _FaceProbe(CompanionFaceAnimationMixin):
    def __init__(self) -> None:
        self.states: list[list[str]] = []
        self.bubbles: list[str] = []
        self.returns: list[list[int | str]] = []

    def set_state(self, state: str, source: str = "") -> None:
        self.states.append([state, source])

    def _t(self, _key: str, default: str) -> str:
        return default

    def _show_bubble(self, text: str) -> None:
        self.bubbles.append(text)

    def _schedule_return_to_idle(self, delay: int, state: str) -> None:
        self.returns.append([delay, state])

    def _hide_bubble_unless_speaking(self) -> None:
        pass


def _runtime_snapshot(tmp_path: Path) -> dict[str, object]:
    diagnostic = tmp_path / "baseline-diagnostic.txt"
    diagnostic.write_text("error\nwarning\n", encoding="utf-8", newline="\n")
    observation = next(iter(DiagnosticReportWorker(lambda: diagnostic).poll()))

    startup: dict[str, list[list[str]]] = {}
    for onboarding_complete in (False, True):
        probe = _StartupProbe(onboarding_complete)
        probe._finish_visual_startup()
        startup[str(onboarding_complete).lower()] = probe.spoken

    face = _FaceProbe()
    face._show_caught_reaction()
    samples = (
        "再胡說妾便敲你",
        "妾並未偷看",
        "妾想到了",
        "妾會護著主上",
        "真拿主上沒辦法",
        "妾忍俊不禁",
        "妾在聽",
        "計策已定",
        "真沒想到",
        "妾很擔心",
        "妾提醒主上",
        "主上平安便好",
        "不出妾所料",
        "主上做得很好",
        "妾先分析",
        "plain reply",
    )
    weather: dict[str, dict[str, str]] = {}
    for locale in (*LOCALES, "fallback"):
        weather[locale] = {}
        for mood in WeatherMood:
            weather[locale][mood.value] = complaint_line(locale, mood)
    worker = AIWorker(
        AIWorkerRequest(
            user_text="",
            mode="",
            assistant_name="Aster",
            user_title="Captain",
        )
    )
    return {
        "background_diagnostic": {
            "message": observation.message,
            "expression": observation.expression,
            "priority": observation.priority,
        },
        "weather": weather,
        "ai_personalize": worker._personalize("墨寒會稱呼你為主上。"),
        "offline": {
            locale: offline_reply("", "", locale)
            for locale in LOCALES
        },
        "realtime_compose": RealtimeSessionMethods._compose_instructions(
            "BASE",
            "MEM",
            "RECENT",
        ),
        "realtime_ready": {
            locale: _message(locale, "ready")
            for locale in LOCALES
        },
        "startup": startup,
        "caught": {
            "states": face.states,
            "bubbles": face.bubbles,
            "returns": face.returns,
        },
        "emergency_commands": sorted(EMERGENCY_COMMANDS),
        "reply_expression": {
            sample: DashboardConversationMixin._reply_expression(sample)
            for sample in samples
        },
    }


def test_extracted_runtime_matches_pre_change_snapshot(tmp_path: Path) -> None:
    expected = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    assert _runtime_snapshot(tmp_path) == expected


def test_runtime_dialogue_requires_four_immutable_locales() -> None:
    for locale in LOCALES:
        dialogue = sensory_synesthesia.runtime_dialogue_locale(locale)
        assert dialogue["wave_greetings"]
        assert dialogue["realtime_ready"]
        with pytest.raises(TypeError):
            dialogue["realtime_ready"] = "changed"  # type: ignore[index]


def test_runtime_dialogue_rejects_schema_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalid = tmp_path / "runtime.json"
    invalid.write_text("{}\n", encoding="utf-8", newline="\n")
    sensory_synesthesia._runtime_dialogue_payload.cache_clear()
    monkeypatch.setattr(sensory_synesthesia, "_RUNTIME_DIALOGUE_PATH", invalid)
    with pytest.raises(ValueError, match="top-level shape"):
        sensory_synesthesia._runtime_dialogue_payload()
    sensory_synesthesia._runtime_dialogue_payload.cache_clear()


def test_assigned_sources_have_no_embedded_character_content() -> None:
    for relative in ASSIGNED_PATHS:
        source = (ROOT / relative).read_text(encoding="utf-8")
        assert build_character_inventory._content_evidence(relative, source) == []
