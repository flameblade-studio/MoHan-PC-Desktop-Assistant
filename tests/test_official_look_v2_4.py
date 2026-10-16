from __future__ import annotations

lazy from types import SimpleNamespace
lazy from builtins import sentinel

lazy import pytest

lazy from application.character_default_look import resolved_body_pack_for_source
lazy from domain.body_pack import BodyPackMismatchError
lazy from infrastructure import bundled_character_source
lazy from infrastructure.app_resources import resource_path
lazy from infrastructure.bundled_character_source import LegacyMohanCharacterSource


def _mohan_source(*, body_pack_roots=()):
    return LegacyMohanCharacterSource(
        resource_path("."),
        body_pack_roots=body_pack_roots,
    )


def test_mohan_with_verified_body_pack_uses_body_renderer(monkeypatch) -> None:
    verified_body = sentinel("verified_body")

    def resolve(*_args):
        return SimpleNamespace(resolved_body_pack=verified_body)

    monkeypatch.setattr(
        bundled_character_source,
        "resolve_character_body_binding",
        resolve,
    )
    source = _mohan_source()

    assert resolved_body_pack_for_source(source) is verified_body
    assert source.body_pack_fallback_active is False
    assert source.body_pack_resolution_error is None


def test_mohan_without_body_pack_keeps_legacy_renderer_and_retains_diagnostic(caplog) -> None:
    source = _mohan_source()

    with caplog.at_level("WARNING"):
        assert resolved_body_pack_for_source(source) is None

    assert source.body_pack_fallback_active is True
    assert source.body_pack_resolution_error is not None
    assert source.body_pack_resolution_error.code == "body_pack_missing"
    assert "mohan_body_pack_fallback" in caplog.text


def test_mohan_invalid_body_pack_keeps_legacy_renderer(monkeypatch) -> None:
    rejection = BodyPackMismatchError(
        "fingerprint_mismatch",
        "The installed body pack does not match the declared fingerprint.",
        "manifest.json",
    )

    def reject(*_args):
        raise rejection

    monkeypatch.setattr(
        bundled_character_source,
        "resolve_character_body_binding",
        reject,
    )
    source = _mohan_source()

    assert resolved_body_pack_for_source(source) is None
    assert source.body_pack_fallback_active is True
    assert source.body_pack_resolution_error is rejection
    assert source.body_pack_resolution_error.code == "fingerprint_mismatch"


def test_non_bundled_character_sources_remain_fail_closed() -> None:
    source = SimpleNamespace(
        appearance=SimpleNamespace(resolved_body_pack=None),
        manifest=SimpleNamespace(body_pack=object()),
    )

    with pytest.raises(BodyPackMismatchError) as captured:
        resolved_body_pack_for_source(source)

    assert captured.value.code == "body_pack_missing"
