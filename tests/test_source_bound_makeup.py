"""Synthetic checks for source-bound built-in makeup edits."""

from __future__ import annotations

lazy import copy
lazy import json
lazy import zipfile
lazy from io import BytesIO
lazy from pathlib import Path
lazy from types import SimpleNamespace

lazy import numpy as np
lazy import pytest
lazy from PIL import Image

lazy from tools.art_pipeline.source_bound_makeup import (
    BUILTIN_PACK_TARGET,
    apply_makeup_updates,
    resolve_runtime_makeup_members,
)
lazy from tools.art_pipeline.source_bound_material_guard import MaterialGuardError
lazy from tools.art_pipeline.source_bound_stage import digest

VIEW = "yaw-060-pitch+00"
OTHER_VIEW = "yaw-045-pitch+00"
CHEEKS = f"assets/mohan-signature-classic-{VIEW}-cheeks.png"
EYES = f"assets/mohan-signature-classic-{VIEW}-eyes.png"
LIPS = f"assets/mohan-signature-classic-{VIEW}-lips.png"
FOUNDATION = f"assets/classic-closed-{VIEW}-foundation.png"
HALF_EYES = f"assets/classic-half-{VIEW}-eyes.png"
RAW_NATIVE = f"assets/pose-atlas/v5-base/{VIEW}.png"


def png(pixels: np.ndarray, mode: str = "RGBA") -> bytes:
    stream = BytesIO()
    Image.fromarray(pixels, mode).save(stream, format="PNG")
    return stream.getvalue()


def rgba() -> np.ndarray:
    pixels = np.zeros((3, 4, 4), dtype=np.uint8)
    pixels[1, 1:3] = [20, 40, 60, 255]
    return pixels


def layer(path: str, slot: str, payload: bytes) -> dict:
    return {
        "path": path,
        "slot": slot,
        "sha256": digest(payload),
        "width": 4,
        "height": 3,
        "anchor": [0, 0],
        "z_order": 0,
    }


def pack_bytes(*, shared: bool = False) -> tuple[bytes, dict[str, bytes]]:
    base = png(rgba())
    empty = png(np.zeros((3, 4, 4), dtype=np.uint8))
    members = {
        CHEEKS: base,
        EYES: base,
        LIPS: base,
        FOUNDATION: base,
        HALF_EYES: base,
        "assets/light.png": base,
        "assets/other.png": empty,
    }
    classic = {
        "id": "classic",
        "poses": {VIEW: [
            layer(CHEEKS, "cheeks", base),
            layer(EYES, "eyes", base),
            layer(LIPS, "lips", base),
            layer(FOUNDATION, "foundation", base),
        ], OTHER_VIEW: [layer(CHEEKS if shared else "assets/other.png", "cheeks", empty)]},
        "eye_states": {"half": {VIEW: [layer(HALF_EYES, "eyes", base)]}},
    }
    manifest = {
        "id": "mohan.makeup.builtin",
        "format": "mohan-outfit-pack",
        "version": 2,
        "makeup": [{
            "id": "mohan-signature",
            "variants": [
                classic,
                {"id": "light", "poses": {VIEW: [layer("assets/light.png", "cheeks", base)]}},
            ],
        }],
    }
    stream = BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        for path, payload in members.items():
            archive.writestr(path, payload)
        archive.writestr("metadata.txt", b"preserve exactly")
    return stream.getvalue(), members


def write_input(root: Path, relative: str, payload: bytes) -> dict[str, str]:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return {"source": relative, "target": relative, "sha256": digest(payload)}


def setup_request(tmp_path: Path, *, shared: bool = False):
    pack, members = pack_bytes(shared=shared)
    candidate_pixels = rgba()
    candidate_pixels[1, 1, :3] = [90, 80, 70]
    candidate = png(candidate_pixels)
    mask_pixels = np.zeros((3, 4), dtype=np.uint8)
    mask_pixels[1, 1] = 255
    candidate_pin = write_input(tmp_path, "scratchpad/candidate.png", candidate)
    mask_pin = write_input(tmp_path, "scratchpad/authored-mask.png", png(mask_pixels, "L"))
    manifest = {
        "view_id": VIEW,
        "makeup": "classic",
        "files": [{
            "source": BUILTIN_PACK_TARGET,
            "target": BUILTIN_PACK_TARGET,
            "sha256": digest(pack),
        }],
        "makeup_updates": [{
            **candidate_pin,
            "target": CHEEKS,
            "allowed_change_mask": mask_pin,
        }],
    }
    return manifest, {BUILTIN_PACK_TARGET: pack}, members, candidate


def test_no_updates_are_a_noop_without_requiring_a_pack(tmp_path: Path) -> None:
    files = {"unchanged": b"value"}

    assert apply_makeup_updates(tmp_path, {}, files) == {}
    assert files == {"unchanged": b"value"}


def test_rebuilds_only_selected_member_and_reports_hashes(tmp_path: Path) -> None:
    manifest, files, original_members, candidate = setup_request(tmp_path)
    before_pack = files[BUILTIN_PACK_TARGET]

    report = apply_makeup_updates(tmp_path, manifest, files)

    assert report["sha256_before"] == digest(before_pack)
    assert report["sha256_after"] == digest(files[BUILTIN_PACK_TARGET])
    assert report["members"][CHEEKS] == {
        "changed_pixels": 1,
        "changed_bbox_xyxy": [1, 1, 2, 2],
        "slot": "cheeks",
        "source": "scratchpad/candidate.png",
        "sha256_before": digest(original_members[CHEEKS]),
        "sha256_after": digest(candidate),
        "allowed_change_mask": {
            "source": "scratchpad/authored-mask.png",
            "sha256": manifest["makeup_updates"][0]["allowed_change_mask"]["sha256"],
        },
    }
    with zipfile.ZipFile(BytesIO(files[BUILTIN_PACK_TARGET])) as archive:
        assert archive.read(CHEEKS) == candidate
        assert archive.read(EYES) == original_members[EYES]
        assert archive.read("metadata.txt") == b"preserve exactly"
        rebuilt_manifest = json.loads(archive.read("manifest.json"))
    original_manifest = json.loads(zipfile.ZipFile(BytesIO(before_pack)).read("manifest.json"))
    expected_manifest = copy.deepcopy(original_manifest)
    expected_manifest["makeup"][0]["variants"][0]["poses"][VIEW][0]["sha256"] = digest(candidate)
    assert rebuilt_manifest == expected_manifest


def test_current_view_eye_state_member_is_editable(tmp_path: Path) -> None:
    manifest, files, _, _ = setup_request(tmp_path)
    manifest["makeup_updates"][0]["target"] = HALF_EYES

    report = apply_makeup_updates(tmp_path, manifest, files)

    assert report["members"][HALF_EYES]["slot"] == "eyes"


@pytest.mark.parametrize("target", [FOUNDATION, "assets/light.png", "assets/other.png", RAW_NATIVE])
def test_rejects_foundation_inactive_other_view_and_raw_native(
    tmp_path: Path, target: str,
) -> None:
    manifest, files, _, _ = setup_request(tmp_path)
    manifest["makeup_updates"][0]["target"] = target

    with pytest.raises(ValueError, match="outside the selected variant"):
        apply_makeup_updates(tmp_path, manifest, files)


def test_rejects_duplicate_and_cross_view_shared_members(tmp_path: Path) -> None:
    manifest, files, _, _ = setup_request(tmp_path)
    manifest["makeup_updates"].append(copy.deepcopy(manifest["makeup_updates"][0]))
    with pytest.raises(ValueError, match="Repeated makeup member"):
        apply_makeup_updates(tmp_path, manifest, files)

    manifest, files, _, _ = setup_request(tmp_path, shared=True)
    with pytest.raises(ValueError, match="shared"):
        apply_makeup_updates(tmp_path, manifest, files)


def test_requires_pack_bytes_to_match_the_canonical_manifest_pin(tmp_path: Path) -> None:
    manifest, files, _, _ = setup_request(tmp_path)
    manifest["files"][0]["source"] = "scratchpad/copied-pack.mohan-outfit"
    with pytest.raises(ValueError, match="canonical source pin"):
        apply_makeup_updates(tmp_path, manifest, files)

    manifest, files, _, _ = setup_request(tmp_path)
    files[BUILTIN_PACK_TARGET] += b"drift"
    with pytest.raises(ValueError, match="bytes changed"):
        apply_makeup_updates(tmp_path, manifest, files)


def test_rejects_alpha_change_even_inside_mask(tmp_path: Path) -> None:
    manifest, files, _, _ = setup_request(tmp_path)
    changed = rgba()
    changed[1, 1, 3] = 128
    manifest["makeup_updates"][0].update(
        write_input(tmp_path, "scratchpad/alpha-change.png", png(changed)),
    )
    manifest["makeup_updates"][0]["target"] = CHEEKS

    with pytest.raises(MaterialGuardError, match="alpha must exactly match"):
        apply_makeup_updates(tmp_path, manifest, files)


def test_rejects_rgb_change_in_transparent_original_pixel(tmp_path: Path) -> None:
    manifest, files, _, _ = setup_request(tmp_path)
    changed = rgba()
    changed[0, 0, 0] = 1
    manifest["makeup_updates"][0].update(
        write_input(tmp_path, "scratchpad/transparent-rgb.png", png(changed)),
    )
    manifest["makeup_updates"][0]["target"] = CHEEKS
    mask = np.zeros((3, 4), dtype=np.uint8)
    mask[0, 0] = 255
    manifest["makeup_updates"][0]["allowed_change_mask"] = write_input(
        tmp_path, "scratchpad/transparent-mask.png", png(mask, "L"),
    )

    with pytest.raises(MaterialGuardError, match="visible original alpha"):
        apply_makeup_updates(tmp_path, manifest, files)


def test_rejects_change_outside_authored_mask(tmp_path: Path) -> None:
    manifest, files, _, _ = setup_request(tmp_path)
    wrong_mask = np.zeros((3, 4), dtype=np.uint8)
    wrong_mask[1, 2] = 255
    manifest["makeup_updates"][0]["allowed_change_mask"] = write_input(
        tmp_path, "scratchpad/wrong-mask.png", png(wrong_mask, "L"),
    )

    with pytest.raises(MaterialGuardError, match="outside the allowed-change mask"):
        apply_makeup_updates(tmp_path, manifest, files)


def test_rejects_new_archive_member_and_non_authored_candidate(tmp_path: Path) -> None:
    manifest, files, _, _ = setup_request(tmp_path)
    manifest["makeup_updates"][0]["target"] = "assets/new-slot.png"
    with pytest.raises(ValueError, match="outside the selected variant"):
        apply_makeup_updates(tmp_path, manifest, files)

    manifest, files, _, _ = setup_request(tmp_path)
    manifest["makeup_updates"][0]["source"] = RAW_NATIVE
    with pytest.raises(ValueError, match="authored scratchpad PNG"):
        apply_makeup_updates(tmp_path, manifest, files)


def test_product_resolver_binds_rest_and_eye_state_member_hashes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from domain import outfit_pack

    output = tmp_path / "preview"
    expected_pack = output / BUILTIN_PACK_TARGET
    base_asset = SimpleNamespace(path=CHEEKS, sha256="a" * 64)
    state_asset = SimpleNamespace(path=HALF_EYES, sha256="b" * 64)
    variant = SimpleNamespace(
        variant_id="classic",
        poses={VIEW: (base_asset,)},
        eye_states={"half": {VIEW: (state_asset,)}},
    )
    item = SimpleNamespace(category="makeup", item_id="mohan-signature", variants=(variant,))
    selection = SimpleNamespace(
        effective_pack_id="mohan.makeup.builtin",
        effective_item_id="mohan-signature",
        effective_variant_id="classic",
    )
    monkeypatch.setattr(outfit_pack, "resolve_active_selection", lambda *_: selection)
    monkeypatch.setattr(outfit_pack, "installed_pack_path", lambda *_: expected_pack)
    monkeypatch.setattr(outfit_pack, "inspect_outfit_pack", lambda *_: SimpleNamespace(items=(item,)))
    monkeypatch.setattr(
        outfit_pack,
        "resolve_variant_for_view",
        lambda selected, view: SimpleNamespace(assets=selected.poses[view]),
    )
    request = {
        "view_id": VIEW,
        "makeup": "classic",
        "makeup_updates": [{"target": HALF_EYES, "sha256": "b" * 64}],
    }

    assert resolve_runtime_makeup_members(tmp_path / "store", request, output) == {
        CHEEKS: "a" * 64,
        HALF_EYES: "b" * 64,
    }

    request["makeup_updates"][0]["sha256"] = "c" * 64
    with pytest.raises(ValueError, match="did not select"):
        resolve_runtime_makeup_members(tmp_path / "store", request, output)
