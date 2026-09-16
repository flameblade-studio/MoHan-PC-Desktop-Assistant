"""Source and visibility gates for an isolated cross-angle makeup candidate."""

from __future__ import annotations

import json
import zipfile
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from tools.art_pipeline.source_bound_makeup_pack import (
    APPROVAL_SCHEMA,
    SCHEMA,
    SOURCE_PACK_PATH,
    _light_pigment,
    _pigment_replacements,
    _stage_source_pack,
    _validate_layers,
    _verify_preserved_members,
    digest,
    prepare_candidate,
)


def png(size: tuple[int, int], *, alpha: int = 0) -> bytes:
    image = Image.new("RGBA", size, (30, 80, 110, 0))
    if alpha:
        image.putpixel((10, 10), (30, 80, 110, alpha))
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def pin(root: Path, relative: str, payload: bytes, *, nonvisible: bool | None = None) -> dict:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    record = {"path": relative, "sha256": digest(payload)}
    if nonvisible is not None:
        record["nonvisible"] = nonvisible
    return record


def one_view(root: Path, view: str, size: tuple[int, int], *, visible: bool) -> dict:
    source = pin(root, f"scratchpad/{view}-source.png", png(size))
    alpha = 200 if visible else 0
    eye = pin(root, f"scratchpad/{view}-eye.png", png(size, alpha=alpha), nonvisible=not visible)
    cheeks = pin(root, f"scratchpad/{view}-cheeks.png", png(size, alpha=alpha), nonvisible=not visible)
    lips = pin(root, f"scratchpad/{view}-lips.png", png(size, alpha=alpha), nonvisible=not visible)
    return {
        "source": source,
        "eye_motion": "fixed_closed",
        "layers": {
            "rest": {"eyes": eye, "cheeks": cheeks, "lips": lips},
            "half": {"eyes": eye},
            "closed": {"eyes": eye},
        },
    }


def region(*, visible: bool) -> SimpleNamespace:
    return SimpleNamespace(rects=lambda _slot: ((1, 1, 20, 20),) if visible else ())


def test_visible_closed_eyes_require_native_pigment(tmp_path: Path) -> None:
    view = "front-crossed"
    declaration = one_view(tmp_path, view, (1254, 1254), visible=True)
    pigments, _ = _validate_layers(tmp_path, {view: declaration}, {view: region(visible=True)}, (view,))
    assert set(pigments) == {
        (view, "rest", "eyes"), (view, "rest", "cheeks"), (view, "rest", "lips"),
        (view, "half", "eyes"), (view, "closed", "eyes"),
    }

    declaration["eye_motion"] = "animated"
    declaration["layers"]["closed"]["eyes"] = pin(
        tmp_path, "scratchpad/empty-closed.png", png((1254, 1254)), nonvisible=False,
    )
    with pytest.raises(ValueError, match="visibility disagrees"):
        _validate_layers(tmp_path, {view: declaration}, {view: region(visible=True)}, (view,))


def test_nonvisible_back_view_requires_explicit_empty_layers(tmp_path: Path) -> None:
    view = "yaw-180-pitch+00"
    declaration = one_view(tmp_path, view, (1024, 1536), visible=False)
    _validate_layers(tmp_path, {view: declaration}, {view: region(visible=False)}, (view,))

    declaration["layers"]["rest"]["lips"]["nonvisible"] = False
    with pytest.raises(ValueError, match="visibility disagrees"):
        _validate_layers(tmp_path, {view: declaration}, {view: region(visible=False)}, (view,))


def test_light_is_same_color_and_support_at_55_percent_alpha() -> None:
    original = Image.new("RGBA", (2, 1))
    original.putdata([(40, 50, 60, 200), (70, 80, 90, 1)])
    stream = BytesIO()
    original.save(stream, format="PNG")

    with Image.open(BytesIO(_light_pigment(stream.getvalue()))) as light:
        assert light.getpixel((0, 0)) == (40, 50, 60, 110)
        assert light.getpixel((1, 0)) == (70, 80, 90, 1)


def test_replacements_leave_historic_exasperated_and_strength_untouched() -> None:
    classic = {
        "intensity": 1.0,
        "poses": {
            "front-crossed": [{"slot": "eyes", "path": "classic/crossed-eyes.png"}],
            "front-exasperated": [{"slot": "eyes", "path": "classic/old-exasperated-eyes.png"}],
        },
        "eye_states": {},
    }
    light = {
        "intensity": 1.0,
        "poses": {
            "front-crossed": [{"slot": "eyes", "path": "light/crossed-eyes.png"}],
            "front-exasperated": [{"slot": "eyes", "path": "light/old-exasperated-eyes.png"}],
        },
        "eye_states": {},
    }
    pigment = png((1254, 1254), alpha=200)

    replacements = _pigment_replacements(
        {"classic": classic, "light": light}, {("front-crossed", "rest", "eyes"): pigment},
    )

    assert set(replacements) == {"classic/crossed-eyes.png", "light/crossed-eyes.png"}
    assert replacements["classic/crossed-eyes.png"] == pigment
    assert classic["intensity"] == light["intensity"] == 1.0
    with Image.open(BytesIO(replacements["light/crossed-eyes.png"])) as image:
        assert image.getpixel((10, 10)) == (30, 80, 110, 110)


def test_sealing_guard_rejects_out_of_scope_member_drift(tmp_path: Path) -> None:
    view = "front-crossed"
    external = "front-exasperated"
    members = {}
    variants = []
    for variant_id in ("classic", "light"):
        poses = {}
        eye_states = {"half": {}, "closed": {}}
        for pose in (view, external):
            rest_path = f"assets/{variant_id}/{pose}/rest-eyes.png"
            members[rest_path] = png((11, 11), alpha=200)
            poses[pose] = [{"path": rest_path, "slot": "eyes"}]
            for state in eye_states:
                path = f"assets/{variant_id}/{pose}/{state}-eyes.png"
                members[path] = png((11, 11), alpha=200)
                eye_states[state][pose] = [{"path": path, "slot": "eyes"}]
        foundation_path = f"assets/{variant_id}/foundation.png"
        members[foundation_path] = b"independent foundation"
        poses[view].append({"path": foundation_path, "slot": "foundation"})
        variants.append({
            "id": variant_id, "intensity": 1.0,
            "poses": poses, "eye_states": eye_states,
        })
    manifest = {"id": "mohan.makeup.builtin", "makeup": [{"variants": variants}]}
    source = BytesIO()
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        for path, payload in members.items():
            archive.writestr(path, payload)

    output = tmp_path / "scratchpad/candidate.mohan-outfit"
    output.parent.mkdir(parents=True)
    authoring, asset_root, foundation, historic, unchanged = _stage_source_pack(
        source.getvalue(), output, (view,), {(view, "rest", "eyes"): png((11, 11), alpha=100)},
    )

    def seal(*, drift: bool) -> None:
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr("manifest.json", authoring.read_bytes())
            for path in members:
                payload = (asset_root / path).read_bytes()
                if drift and path == f"assets/classic/{external}/rest-eyes.png":
                    payload = b"unexpected historic change"
                archive.writestr(path, payload)

    seal(drift=False)
    _verify_preserved_members(output, (view,), foundation, historic, unchanged)
    seal(drift=True)
    with pytest.raises(ValueError, match="Out-of-scope makeup assets changed"):
        _verify_preserved_members(output, (view,), foundation, historic, unchanged)


def test_missing_view_fails_before_staging_or_writing_candidate(tmp_path: Path) -> None:
    approval_root = "scratchpad/palette"
    reference = b"approved reference pin"
    pin(tmp_path, f"{approval_root}/three-angle-style-reference.png", reference)
    approval = {
        "schema": APPROVAL_SCHEMA,
        "approved_scope": [
            "cross-angle eyes cheeks lips palette", "native per-view layer integration",
            "optional strength and removal",
        ],
        "reference": "three-angle-style-reference.png",
        "sha256": digest(reference),
        "not_authorized_as_replacement_face": True,
    }
    approval_pin = pin(tmp_path, f"{approval_root}/owner-approval.json", json.dumps(approval).encode())
    source_pin = pin(tmp_path, SOURCE_PACK_PATH, b"source pack pin")
    (tmp_path / "assets/makeup-safe-regions.json").write_bytes(b"{}")
    request = {
        "schema": SCHEMA,
        "palette_approval": approval_pin,
        "source_pack": source_pin,
        "views": {},
    }
    request_path = tmp_path / "scratchpad/request.json"
    request_path.write_text(json.dumps(request), encoding="utf-8")
    output = tmp_path / "scratchpad/candidate.mohan-outfit"

    with pytest.raises(ValueError, match="every non-exasperated silhouette"):
        prepare_candidate(
            tmp_path, request_path, output, regions={}, required=("front-crossed",),
        )

    assert not output.exists()
    assert not output.with_suffix(output.suffix + ".receipt.json").exists()
    assert not (output.parent / ".candidate.authoring").exists()
