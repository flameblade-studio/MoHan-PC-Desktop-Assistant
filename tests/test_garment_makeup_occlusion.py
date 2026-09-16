"""Appearance depth remains explicit, typed, and backwards compatible."""
from __future__ import annotations

lazy import io
lazy import zipfile

lazy import pytest
lazy from domain import outfit_pack
lazy from tests.test_outfit_pack import _asset, _png


@pytest.mark.parametrize("flag", [None, False, True])
@pytest.mark.parametrize("slot", ["outerwear", "headwear"])
def test_appearance_depth_declaration_defaults_to_legacy(flag: bool | None, slot: str) -> None:
    payload = _png()
    entry = _asset("assets/appearance.png", payload, slot)
    if flag is not None:
        entry["occludes_makeup"] = flag
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr(entry["path"], payload)
    with zipfile.ZipFile(stream) as archive:
        allowed = outfit_pack.GARMENT_SLOTS if slot == "outerwear" else frozenset({"headwear"})
        parsed = outfit_pack._asset(entry, allowed, archive, set(archive.namelist()))
    assert parsed.occludes_makeup is (flag is True)


@pytest.mark.parametrize("flag", [0, 1, "true", None, [], {}])
def test_garment_depth_rejects_non_boolean_values(flag: object) -> None:
    entry = _asset("assets/cloth.png", _png(), "outerwear")
    entry["occludes_makeup"] = flag
    with pytest.raises(outfit_pack.OutfitPackError, match="boolean"):
        outfit_pack._asset(entry, outfit_pack.GARMENT_SLOTS, None, {entry["path"]})


def test_depth_extension_cannot_be_applied_to_makeup_or_hair() -> None:
    for slot, allowed in (("foundation", outfit_pack.MAKEUP_SLOTS_V2), ("front", outfit_pack.HAIR_SLOTS)):
        entry = _asset("assets/pigment.png", _png(), slot)
        entry["occludes_makeup"] = True
        with pytest.raises(outfit_pack.OutfitPackError, match="garment asset"):
            outfit_pack._asset(entry, allowed, None, {entry["path"]})


def test_depth_extension_keeps_unknown_keys_rejected() -> None:
    entry = _asset("assets/cloth.png", _png(), "outerwear")
    entry.update(occludes_makeup=True, skip_identity_guard=True)
    with pytest.raises(outfit_pack.OutfitPackError, match="asset declaration"):
        outfit_pack._asset(entry, outfit_pack.GARMENT_SLOTS, None, {entry["path"]})
