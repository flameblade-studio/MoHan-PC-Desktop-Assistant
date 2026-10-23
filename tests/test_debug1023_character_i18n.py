from __future__ import annotations

lazy from pathlib import Path
lazy from types import SimpleNamespace

lazy import pytest

lazy from application.background_agents import VisibleAppWorker
lazy from application.companion_phrasebook import grouped_phrasebook_categories
lazy from domain.character_pack.character_data import load_mohan_character_data
lazy from domain.app_profile import default_persona_for_language
lazy from domain.service_status_localization import ServiceStatus
lazy from infrastructure.character_source_pack import CharacterPackReader
lazy from integrations.ai_client import AIWorker, AIWorkerRequest
lazy from integrations.realtime_session import RealtimeSessionMethods
lazy from presentation.auxiliary_ui_localization import AuxiliaryText, auxiliary_text
lazy from presentation.companion_platform import reminder_line
lazy from presentation.dashboard_conversation import DashboardConversationMixin
lazy from presentation.flagship_ui_localization import FlagshipTranslator
lazy from presentation.ui_localization import ui_text

ROOT = Path(__file__).resolve().parents[1]
LIN_ROOT = ROOT / "assets" / "characters" / "lin-keyun"


def _lin_data():
    return load_mohan_character_data(LIN_ROOT)


def test_emergency_commands_follow_active_character(monkeypatch: pytest.MonkeyPatch):
    import presentation.dashboard_conversation as dashboard

    lin = _lin_data()
    monkeypatch.setattr(dashboard, "active_character_data", lambda: lin, raising=False)
    called: list[bool] = []
    target = SimpleNamespace(
        _emergency_stop=lambda: called.append(True),
    )

    assert DashboardConversationMixin._handle_emergency_command(
        target,
        f"{lin.personas['zh-TW'].identity.display_name}停手",
    )
    assert called == [True]


def test_phrasebook_and_flagship_catalog_are_role_safe(
    monkeypatch: pytest.MonkeyPatch,
):
    import application.companion_phrasebook as phrasebook

    lin = _lin_data()
    monkeypatch.setattr(phrasebook, "active_character_data", lambda: lin)
    categories = grouped_phrasebook_categories()
    labels = [label for _key, group in categories for _key, label in group]

    assert "林可芸的生日・含蓄暗示" in labels
    assert FlagshipTranslator("en").text("新裝互動") == "Outfit interactions"
    assert (
        FlagshipTranslator("ja-JP").text("新裝初見・來歷")
        == "新しい衣装を初めて見て・由来"
    )


def test_ui_and_auxiliary_identity_follow_active_character(
    monkeypatch: pytest.MonkeyPatch,
):
    import presentation.auxiliary_ui_localization as auxiliary
    import presentation.ui_localization as ui

    lin = _lin_data()
    monkeypatch.setattr(ui, "active_character_data", lambda: lin, raising=False)
    monkeypatch.setattr(auxiliary, "active_character_data", lambda: lin, raising=False)

    assert ui_text("en", "first_run_brand", "") == "Lin Keyun"
    assert (
        auxiliary_text("en", AuxiliaryText.DEFAULT_ASSISTANT_NAME)
        == "Lin Keyun"
    )


def test_dashboard_builtin_reply_uses_current_locale(
    monkeypatch: pytest.MonkeyPatch,
):
    import presentation.dashboard_conversation as dashboard

    replies: list[str] = []
    monkeypatch.setattr(
        dashboard,
        "runtime_dialogue_locale",
        lambda locale: {"dashboard_teasing": f"{locale}-teasing"},
    )
    target = SimpleNamespace(
        ui_language="en",
        _runtime_dialogue=lambda: dashboard.runtime_dialogue_locale("en"),
        _reply=lambda text, _expression: replies.append(text),
    )

    assert DashboardConversationMixin._handle_teasing_command(
        target,
        dashboard.TEASING_COMMAND_MARKERS[0],
    )
    assert replies == ["en-teasing"]


def test_background_worker_uses_requested_character_locale(
    monkeypatch: pytest.MonkeyPatch,
):
    import application.background_agents as background

    lin = _lin_data()
    monkeypatch.setattr(background, "active_character_data", lambda: lin)
    windows = iter(([], [{"title": "Visual Studio Code"}]))
    worker = VisibleAppWorker(
        lambda: next(windows),
        {"Visual Studio Code": ("Visual Studio Code",)},
        language="en",
    )

    assert tuple(worker.poll()) == ()
    observations = tuple(worker.poll())
    assert len(observations) == 1
    assert "Swordmaster" in observations[0].message
    assert "opened Visual Studio Code" in observations[0].message


def test_background_diagnostic_uses_requested_locale(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    import application.background_agents as background

    report = tmp_path / "diagnostics.txt"
    report.write_text("error: one issue\n", encoding="utf-8")
    monkeypatch.setattr(
        background,
        "runtime_dialogue_locale",
        lambda locale: {
            "background_diagnostic": f"{locale}:{'{report_name}'}:{'{issues}'}",
        },
    )

    worker = background.DiagnosticReportWorker(lambda: report, language="en")
    observation = next(iter(worker.poll()))
    assert observation.message == "en:diagnostics.txt:1"


def test_voice_error_uses_current_assistant_name():
    chat: list[tuple[str, str]] = []
    spoken: list[tuple[str, str]] = []
    target = SimpleNamespace(
        assistant_name="林可芸",
        _t=lambda _key, fallback: fallback,
        set_voice_phase=lambda _text: None,
        append_chat=lambda author, text: chat.append((author, text)),
        speak_requested=SimpleNamespace(
            emit=lambda text, state: spoken.append((text, state)),
        ),
    )

    DashboardConversationMixin._voice_error(target, "microphone failed")
    assert chat == [("林可芸", "microphone failed")]
    assert spoken == [("microphone failed", "worried")]


def test_voice_preview_uses_active_character_dialogue(monkeypatch: pytest.MonkeyPatch):
    import presentation.companion_speech_runtime as speech

    lin = _lin_data()
    spoken: list[str] = []
    monkeypatch.setattr(speech, "active_character_data", lambda: lin, raising=False)
    target = SimpleNamespace(
        db=SimpleNamespace(
            setting=lambda key, default="": {
                "ui_language": "en",
                "user_title": "Swordmaster",
            }.get(key, default),
        ),
        speak=lambda text, _expression: spoken.append(text),
    )

    speech.CompanionSpeechRuntimeMixin.preview_voice(target)
    assert spoken == [lin.dialogues["en"].templates["voice.preview"].format(
        user_title="Swordmaster",
    )]


def test_reminder_uses_active_character_dialogue(monkeypatch: pytest.MonkeyPatch):
    import presentation.companion_platform as platform

    lin = _lin_data()
    monkeypatch.setattr(platform, "active_character_data", lambda: lin, raising=False)
    assert reminder_line("en", "work") == lin.dialogues["en"].reminder_lines["work"]


def test_default_persona_uses_active_character_source(monkeypatch: pytest.MonkeyPatch):
    from domain import app_profile

    persona = SimpleNamespace(
        persona_prompt=lambda language: f"lin-persona:{language}",
    )
    monkeypatch.setattr(
        app_profile,
        "active_character_source",
        lambda: SimpleNamespace(persona=persona),
        raising=False,
    )
    assert default_persona_for_language("en-US") == "lin-persona:en"


def test_speech_not_understood_is_character_templated():
    import domain.service_status_localization as status

    template = status._TEXT[ServiceStatus.SPEECH_NOT_UNDERSTOOD]["zh-TW"]
    assert "{self_reference}" in template


def test_character_pack_reader_localizes_identity():
    lin = _lin_data()
    reader = object.__new__(CharacterPackReader)
    reader._character_data = lin
    reader._canonical_name = "林可芸"
    reader._default_user_title = "劍主"

    assert reader.display_name("en") == "Lin Keyun"
    assert reader.default_user_title("ja-JP") == "剣主"


def test_realtime_context_uses_requested_locale():
    result = RealtimeSessionMethods._compose_instructions(
        "Keep the response concise.",
        "",
        "",
        "en",
    )
    assert "long-term memory" in result.lower()
    assert "長期記憶" not in result


def test_offline_notice_normalizes_locale():
    request = AIWorkerRequest(
        user_text="hello",
        mode="companion",
        response_language="ja-JP",
    )
    worker = AIWorker(request)
    emitted: list[str] = []
    worker.signals.done.connect(emitted.append)

    worker._run_request()

    assert emitted
    assert emitted[0].startswith("〔オフラインモード")


def test_voice_listener_constructs_selected_recognizer():
    source = (ROOT / "voice_listener.ps1").read_text(encoding="utf-8")
    assert "SpeechRecognitionEngine]::new($info)" in source
