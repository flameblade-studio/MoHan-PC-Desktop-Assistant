"""Source drift and scope errors must fail before preview output is created."""

from __future__ import annotations

lazy import json
lazy import zipfile
lazy from io import BytesIO

lazy import pytest

lazy from tools.art_pipeline.source_bound_stage import (
    SCHEMA, PinnedFile, digest, read_pinned, rebuild_pack, relative_path, stage_preview,
)

VIEW = "yaw+060-pitch+00"
NATIVE = f"assets/pose-atlas/v5-base/{VIEW}.png"


@pytest.mark.parametrize("path", ["../x", "/x", "C:/x", "a\\b", "a//b", "a/./b"])
def test_portable_path_rejects_escape_and_noncanonical_names(path):
    with pytest.raises(ValueError):
        relative_path(path)


def test_pinned_input_rejects_changed_source(tmp_path):
    (tmp_path / "source").write_bytes(b"changed")
    pin = PinnedFile("source", digest(b"original"), "assets/source")
    with pytest.raises(ValueError, match="changed"):
        read_pinned(tmp_path, pin)


def test_stage_rejects_native_substitution_before_creating_output(tmp_path):
    original = tmp_path / NATIVE
    original.parent.mkdir(parents=True)
    original.write_bytes(b"native")
    substitute = tmp_path / "substitute.png"
    substitute.write_bytes(b"different face")
    native = {"source": NATIVE, "target": NATIVE, "sha256": digest(b"native")}
    manifest = {
        "schema": SCHEMA, "view_id": VIEW, "native": native,
        "files": [{"source": "substitute.png", "target": NATIVE,
                   "sha256": digest(b"different face")}],
    }
    output = tmp_path / "scratchpad/preview"
    with pytest.raises(ValueError, match="Native authority"):
        stage_preview(tmp_path, manifest, output)
    assert not output.exists()
    assert original.read_bytes() == b"native"


def pack_bytes(contents):
    stream = BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        for name, data in contents.items():
            archive.writestr(name, data)
    return stream.getvalue()


def test_rebuild_retains_unaffected_members_and_declaration_properties():
    member = f"assets/hanfu-robe-{VIEW}-outerwear.png"
    manifest = {"garments": [{"path": member, "sha256": digest(b"old"), "z_order": 7}]}
    source = pack_bytes({"manifest.json": json.dumps(manifest), member: b"old", "other": b"fixed"})
    result = rebuild_pack(source, {member: b"new"})
    with zipfile.ZipFile(BytesIO(result)) as archive:
        actual = json.loads(archive.read("manifest.json"))
        assert archive.read("other") == b"fixed"
        assert archive.read(member) == b"new"
    manifest["garments"][0]["sha256"] = digest(b"new")
    assert actual == manifest


def test_rebuild_rejects_undeclared_member():
    source = pack_bytes({"manifest.json": "{}", "undeclared": b"old"})
    with pytest.raises(ValueError, match="existing layer"):
        rebuild_pack(source, {"undeclared": b"new"})


def test_unchanged_pack_remains_byte_identical():
    source = pack_bytes({"manifest.json": "{}", "image": b"same"})
    assert rebuild_pack(source, {}) == source
