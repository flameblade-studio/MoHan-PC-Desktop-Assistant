from __future__ import annotations

lazy import hashlib
lazy import json
lazy import zipfile
lazy from dataclasses import replace
lazy from pathlib import Path
lazy from types import SimpleNamespace

lazy import pytest

lazy from application.companion_phrasebook import (
    CompanionPhrasebook,
    PHRASEBOOK_SETTING,
)
lazy from application import service_container
lazy from application.character_runtime_bootstrap import ACTIVE_CHARACTER_ENV
lazy from domain.character_pack.validation import compute_package_hash
lazy from domain.character_source import (
    activate_character_engine_profile,
    activate_character_source,
    active_character_engine_profile,
    active_character_source,
)
lazy from domain.character_runtime_data import default_rig_manifest
lazy from domain.constants import (
    CHARACTER_ASSET_PATHS,
    POSE_ATLAS_LAYERED_RELATIVE_ROOT,
    POSE_ATLAS_RELATIVE_ROOT,
)
lazy from domain.outfit_pack_official import (
    official_pack_id_reservations_complete,
    official_pack_ids,
    reserved_official_pack_ids,
    set_official_pack_id_reservations,
)
lazy from infrastructure.character_source_pack import CharacterPackReadError
lazy from infrastructure.db import StudioDB
lazy from tests.character_pack_fixtures import (
    FAKE_CHARACTER_ID,
    build_fake_character_pack,
)


def _json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _fake_character_archive(tmp_path: Path) -> Path:
    source = build_fake_character_pack(tmp_path)
    destination = tmp_path / "flameblade.test-sentinel-distinctive.zip"
    with zipfile.ZipFile(source) as archive:
        payloads = {
            info.filename: archive.read(info)
            for info in archive.infolist()
            if not info.is_dir()
        }
    manifest = json.loads(payloads["manifest.json"].decode("utf-8"))
    updated_paths = set()

    profile_path = next(
        path for path in payloads if path.endswith("/persona/profile.json")
    )
    profile = json.loads(payloads[profile_path].decode("utf-8"))
    profile["defaults"]["user_title"] = "Sentinel Guide"
    profile["legacy_profile_defaults"]["user_title"] = "Sentinel Guide"
    payloads[profile_path] = _json_bytes(profile)
    updated_paths.add(profile_path)
    for path in tuple(payloads):
        if not path.endswith("/persona/zh-TW.json"):
            continue
        persona = json.loads(payloads[path].decode("utf-8"))
        persona["identity"]["default_user_title"] = "Sentinel Guide"
        payloads[path] = _json_bytes(persona)
        updated_paths.add(path)

    dialogue_path = next(
        path for path in payloads if path.endswith("/dialogue/zh-TW.json")
    )
    dialogue = json.loads(payloads[dialogue_path].decode("utf-8"))
    dialogue["line_sets"]["welcome.warm"] = ["SENTINEL-WELCOME-ONLY"]
    dialogue["line_sets"]["interaction.gentle_check_in"] = [
        "SENTINEL-CHECK-IN-ONLY"
    ]
    dialogue["phrasebook"]["wellbeing.rest.initial"] = [
        "SENTINEL-EVENT-LINE-ONLY"
    ]
    dialogue["reminder_lines"]["work"] = "SENTINEL-REMINDER-ONLY"
    payloads[dialogue_path] = _json_bytes(dialogue)
    updated_paths.add(dialogue_path)

    voice_path = next(
        path for path in payloads if path.endswith("/voice/profile.json")
    )
    voice = json.loads(payloads[voice_path].decode("utf-8"))
    voice["defaults"].update(
        {
            "provider": "openai-speech",
            "tts_voice": "sentinel-tts-voice",
            "cloud_voice": "sentinel-cloud-voice",
            "realtime_voice": "sentinel-realtime-voice",
        }
    )
    voice["instructions"]["zh-TW"] = "SENTINEL-VOICE-INSTRUCTIONS-ONLY"
    payloads[voice_path] = _json_bytes(voice)
    updated_paths.add(voice_path)

    for record in manifest["files"]:
        payload = payloads[record["path"]]
        record["bytes"] = len(payload)
        record["sha256"] = hashlib.sha256(payload).hexdigest()
    for component in manifest["components"]:
        if component["path"] in updated_paths:
            component["sha256"] = hashlib.sha256(
                payloads[component["path"]]
            ).hexdigest()
    manifest["package_hash"] = compute_package_hash(manifest)
    payloads["manifest.json"] = _json_bytes(manifest)

    with zipfile.ZipFile(
        destination,
        "x",
        compression=zipfile.ZIP_STORED,
    ) as archive:
        for name in sorted(payloads):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, payloads[name])
    return destination


class _SecretStore:
    def load(self) -> str:
        return ""


def _stub_service_adapters(monkeypatch: pytest.MonkeyPatch) -> None:
    capabilities = SimpleNamespace(
        offline_speech_recognition=False,
        system_local_speech=False,
        verified_female_voice_catalog=False,
    )
    platform = SimpleNamespace(capabilities=capabilities)
    monkeypatch.setattr(
        service_container,
        "list_installed_character_packs",
        lambda *, data_root=None: (),
    )
    monkeypatch.setattr(service_container, "NativeAcceleration", lambda: object())
    monkeypatch.setattr(
        service_container,
        "_initialize_backup_manager",
        lambda *_args: None,
    )
    monkeypatch.setattr(
        service_container,
        "platform_secret_store_factory",
        lambda _platform: lambda _path, _label: _SecretStore(),
    )
    monkeypatch.setattr(
        service_container,
        "SpeechListener",
        lambda *_args, **kwargs: SimpleNamespace(language=kwargs["language"]),
    )
    monkeypatch.setattr(
        service_container,
        "_local_speech_engine",
        lambda *_args, **_kwargs: object(),
    )
    monkeypatch.setattr(
        service_container,
        "OpenAITTS",
        lambda *_args, **_kwargs: object(),
    )
    monkeypatch.setattr(
        service_container,
        "AzureSpeechTTS",
        lambda *_args, **_kwargs: object(),
    )
    monkeypatch.setattr(
        service_container,
        "RealtimeVoiceClient",
        lambda *_args, **_kwargs: object(),
    )
    monkeypatch.setattr(
        service_container,
        "_realtime_speech_output",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        service_container,
        "create_builtin_speech_registry",
        lambda *_args, **_kwargs: object(),
    )
    monkeypatch.setattr(
        service_container,
        "create_cloud_vision_service_factory",
        lambda: object(),
    )
    monkeypatch.setattr(
        service_container,
        "current_platform_services",
        lambda: platform,
    )


def _select_fake_character(
    monkeypatch: pytest.MonkeyPatch,
    archive: Path,
) -> None:
    monkeypatch.setenv(ACTIVE_CHARACTER_ENV, FAKE_CHARACTER_ID)
    monkeypatch.setenv(
        "MOHAN_DEV_CHARACTER_PACK_ARCHIVE",
        str(archive),
    )


def _activate_selected_character_from_environment() -> None:
    source = service_container.create_default_character_source()
    assert source.character_id == FAKE_CHARACTER_ID


@pytest.fixture
def restore_character_runtime():
    previous_source = active_character_source()
    previous_engine_profile = active_character_engine_profile()
    previous_pack_reservations = (
        reserved_official_pack_ids(previous_source)
        - official_pack_ids(previous_source)
    )
    previous_reservations_complete = official_pack_id_reservations_complete()
    try:
        yield
    finally:
        activate_character_source(previous_source)
        activate_character_engine_profile(previous_engine_profile)
        set_official_pack_id_reservations(
            previous_pack_reservations,
            complete=previous_reservations_complete,
        )


def test_new_profile_and_renderer_startup_use_selected_character_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    restore_character_runtime: None,
) -> None:
    archive = _fake_character_archive(tmp_path)
    _stub_service_adapters(monkeypatch)
    _select_fake_character(monkeypatch, archive)
    _activate_selected_character_from_environment()

    services = service_container.create_default_services(
        tmp_path / "data",
        tmp_path / "voice_listener.ps1",
    )
    try:
        db = services.db
        assert db.setting("assistant_name") == "Test Sentinel"
        assert db.setting("user_title") != "主上"
        assert db.setting("wake_word") == "Test Sentinel"
        assert db.setting("persona_prompt") == (
            "You are Test Sentinel, a synthetic test character."
        )

        phrasebook = CompanionPhrasebook.from_setting(
            db.setting(PHRASEBOOK_SETTING)
        )
        assert phrasebook.welcomes["warm"] == ("SENTINEL-WELCOME-ONLY",)
        assert phrasebook.check_ins == ("SENTINEL-CHECK-IN-ONLY",)
        assert phrasebook.scenarios["wellbeing.rest.initial"] == (
            "SENTINEL-EVENT-LINE-ONLY",
        )
        assert db.setting("reminder_message_work") == "SENTINEL-REMINDER-ONLY"
        assert db.setting("tts_voice") == "sentinel-tts-voice"
        assert db.setting("cloud_voice") == "sentinel-cloud-voice"
        assert db.setting("realtime_voice") == "sentinel-realtime-voice"
        assert db.setting("voice_instructions") == (
            "SENTINEL-VOICE-INSTRUCTIONS-ONLY"
        )
        assert db.setting("voice_prompt_v1204_migrated") is True

        with pytest.raises(CharacterPackReadError, match="undeclared_path"):
            services.presentation_ports.face_renderer_factory()
        with pytest.raises(CharacterPackReadError, match="undeclared_path"):
            services.presentation_ports.full_body_renderer_factory()
    finally:
        services.db.close()


def test_saved_profile_overrides_survive_source_default_seeding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    restore_character_runtime: None,
) -> None:
    archive = _fake_character_archive(tmp_path)
    _stub_service_adapters(monkeypatch)
    _select_fake_character(monkeypatch, archive)
    _activate_selected_character_from_environment()
    data_path = tmp_path / "data"
    db = StudioDB(data_path / "mohan.db")
    saved = {
        "assistant_name": "My saved companion",
        "persona_prompt": "My saved persona prompt",
        PHRASEBOOK_SETTING: {
            "version": 2,
            "welcomes": {"warm": ["MY-SAVED-WELCOME"]},
            "check_ins": [],
            "scenarios": {},
        },
        "reminder_message_work": "MY-SAVED-REMINDER",
        "tts_voice": "my-saved-voice",
        "voice_instructions": "MY-SAVED-VOICE-INSTRUCTIONS",
    }
    for key, value in saved.items():
        db.set_setting(key, value)
    db.close()

    services = service_container.create_default_services(
        data_path,
        tmp_path / "voice_listener.ps1",
    )
    try:
        assert {
            key: services.db.setting(key)
            for key in saved
        } == saved
    finally:
        services.db.close()


def test_renderer_factories_bind_source_assets_and_validated_rig(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "renderer-sentinel-assets"
    defaults = SimpleNamespace(
        outfit_pack_id="sentinel.outfit",
        makeup_pack_id="sentinel.makeup",
    )
    runtime_rig = default_rig_manifest()
    source_rig = replace(runtime_rig, character_id="flameblade.renderer-sentinel")
    source = SimpleNamespace(
        character_id="renderer-sentinel",
        assets=SimpleNamespace(
            asset_root=root,
            resolve_path=lambda relative: root / relative,
            resolve_optional_path=lambda relative: root / relative,
        ),
        appearance=SimpleNamespace(
            appearance_defaults=defaults,
            rig_manifest=source_rig,
        ),
    )
    for relative in (
        CHARACTER_ASSET_PATHS["halfbody_layers"],
        CHARACTER_ASSET_PATHS["halfbody_root"],
        CHARACTER_ASSET_PATHS["halfbody_detachable"],
        POSE_ATLAS_LAYERED_RELATIVE_ROOT,
        POSE_ATLAS_RELATIVE_ROOT,
    ):
        (root / relative).mkdir(parents=True, exist_ok=True)

    face_manifest = SimpleNamespace(kind="face")
    full_body_manifest = SimpleNamespace(kind="full_body")
    loaded_roots = []
    constructors = {}
    monkeypatch.setattr(
        service_container,
        "load_layered_face_assets",
        lambda path: loaded_roots.append(("face", path)) or face_manifest,
    )
    monkeypatch.setattr(
        service_container,
        "load_layered_full_body_assets",
        lambda path: loaded_roots.append(("full", path)) or full_body_manifest,
    )
    monkeypatch.setattr(
        service_container,
        "load_full_body_display_placement",
        lambda path: ("placement", path),
    )
    monkeypatch.setattr(
        service_container,
        "ActiveOutfitOverlay",
        lambda *_args, **_kwargs: object(),
    )
    monkeypatch.setattr(
        service_container,
        "LayeredParametricFaceRenderer",
        lambda **kwargs: constructors.setdefault("face", kwargs),
    )
    monkeypatch.setattr(
        service_container,
        "LayeredFullBodyRenderer",
        lambda **kwargs: constructors.setdefault("full", kwargs),
    )

    ports = service_container._create_presentation_ports(source)
    ports.face_renderer_factory()
    ports.full_body_renderer_factory()

    assert loaded_roots == [
        (
            "face",
            root / CHARACTER_ASSET_PATHS["halfbody_layers"],
        ),
        ("full", root / POSE_ATLAS_LAYERED_RELATIVE_ROOT),
    ]
    face = constructors["face"]
    assert face["manifest"] is face_manifest
    assert face["authority_dir"] == root / CHARACTER_ASSET_PATHS["halfbody_root"]
    assert face["detachable_dir"] == root / CHARACTER_ASSET_PATHS[
        "halfbody_detachable"
    ]
    assert face["use_detachable"] is True
    assert face["exasperated_candidate_dir"] is None

    full = constructors["full"]
    assert full["manifest"] is full_body_manifest
    assert full["authority_root"] == root / POSE_ATLAS_RELATIVE_ROOT
    assert full["display_placement"] == (
        "placement",
        root / POSE_ATLAS_RELATIVE_ROOT,
    )


def test_official_pack_reservations_include_every_installed_character(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def character_source(outfit_id: str, makeup_id: str):
        return SimpleNamespace(
            appearance=SimpleNamespace(
                appearance_defaults=SimpleNamespace(
                    outfit_pack_id=outfit_id,
                    makeup_pack_id=makeup_id,
                )
            )
        )

    bundled = character_source("mohan.outfit", "mohan.makeup")
    installed = (
        character_source("installed.one.outfit", "installed.one.makeup"),
        character_source("installed.two.outfit", "installed.two.makeup"),
    )
    selected = character_source("selected.outfit", "selected.makeup")
    observed = {}

    def list_installed(*, data_root=None):
        observed["data_root"] = data_root
        return installed

    monkeypatch.setattr(
        service_container,
        "list_installed_character_packs",
        list_installed,
    )
    monkeypatch.setattr(
        service_container,
        "set_official_pack_id_reservations",
        lambda pack_ids, *, complete=True: observed.update(
            pack_ids=frozenset(pack_ids),
            complete=complete,
        ),
    )

    service_container._reserve_official_pack_id_reservations(
        selected,
        bundled_source=bundled,
        data_root=tmp_path,
    )

    assert observed["data_root"] == tmp_path
    assert observed["pack_ids"] == frozenset(
        {
            "mohan.outfit",
            "mohan.makeup",
            "installed.one.outfit",
            "installed.one.makeup",
            "installed.two.outfit",
            "installed.two.makeup",
            "selected.outfit",
            "selected.makeup",
        }
    )
    assert observed["complete"] is True
