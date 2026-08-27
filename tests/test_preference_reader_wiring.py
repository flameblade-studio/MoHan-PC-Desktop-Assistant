from __future__ import annotations

"""Structural wiring contracts for the audit-wave "settings take effect" fixes.

These checks pin the reader side of the typed preference stores without
booting the full Qt companion window:

* the speech runtime consumes the cached typed performance preferences (the
  old ad-hoc reads defaulted every flag to True, contradicting the domain);
* the adaptive-character dispatch consumes the cached framing preferences;
* every settings save refreshes the multisensory arbiter and the caches;
* the voice-volume and weather defaults come from their single constants.
"""

lazy import ast
lazy import sys
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CORE_PATH = ROOT / "presentation" / "companion_core.py"
SPEECH_PATH = ROOT / "presentation" / "companion_speech_runtime.py"
PROACTIVE_PATH = ROOT / "presentation" / "companion_proactive.py"
VOICE_PATH = ROOT / "presentation" / "dashboard_voice.py"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def _method_source(path: Path, class_name: str, method_name: str) -> str:
    tree = ast.parse(_source(path), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if (
                    isinstance(item, ast.FunctionDef)
                    and item.name == method_name
                ):
                    segment = ast.get_source_segment(_source(path), item)
                    assert segment is not None
                    return segment
    raise AssertionError(f"{class_name}.{method_name} not found in {path.name}")


def test_speech_runtime_reads_typed_performance_preferences() -> None:
    source = _method_source(
        SPEECH_PATH,
        "CompanionSpeechRuntimeMixin",
        "_record_speech_performance",
    )
    assert "_current_performance_preferences" in source
    # The retired ad-hoc reads must not come back with their all-True defaults.
    assert "performance_proactive_body_enabled" not in source
    assert "performance_360_view_enabled" not in source


def test_adaptive_dispatch_reads_cached_framing_preferences() -> None:
    core_source = _source(CORE_PATH)
    assert "self._current_framing_preferences()" in core_source
    assert "FramingPreferences()," not in core_source


def test_settings_saved_refreshes_arbiter_and_preference_caches() -> None:
    core_source = _source(CORE_PATH)
    assert (
        "settings_saved.connect(self._refresh_multisensory_config)"
        in core_source
    )
    assert (
        "settings_saved.connect(self._reload_preference_caches)" in core_source
    )


def test_voice_volume_default_is_the_shared_constant() -> None:
    from domain.speech_configuration import DEFAULT_VOICE_VOLUME_PERCENT

    expected_volume_percent = 125
    assert DEFAULT_VOICE_VOLUME_PERCENT == expected_volume_percent
    for path in (CORE_PATH, VOICE_PATH):
        source = _source(path)
        # No reader may keep a private numeric default for the volume.
        assert '"voice_volume_percent", 100' not in source
        assert '"voice_volume_percent", 125' not in source
        assert (
            '"voice_volume_percent", DEFAULT_VOICE_VOLUME_PERCENT' in source
        )


def test_weather_reads_use_the_domain_defaults() -> None:
    for path in (CORE_PATH, PROACTIVE_PATH):
        source = _source(path)
        assert '"weather_temperature_c", 20.0' not in source
        assert '"weather_temperature_c", 24.0' not in source
        assert '"weather_condition", "clear"' not in source
    controller = _source(
        ROOT / "presentation" / "autonomous_outfit_generation_controller.py"
    )
    assert '"weather_condition", "indoor"' not in controller
    assert '"weather_temperature_c", 24.0' not in controller
