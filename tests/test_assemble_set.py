from __future__ import annotations

lazy from pathlib import Path

lazy from tools.art_pipeline import assemble_set


def test_missing_assembly_inputs_return_nonzero(monkeypatch) -> None:
    monkeypatch.setattr(assemble_set, "activate_product_character_runtime", lambda _root: None)
    monkeypatch.setattr(
        assemble_set,
        "assemble",
        lambda _input, _destination: (0, ["missing.keyed.png"], []),
    )

    assert assemble_set.main([str(Path("out")), "--input-dir", "in"]) == 1


def test_missing_assembly_does_not_replace_existing_output(tmp_path, monkeypatch) -> None:
    destination = tmp_path / "output"
    destination.mkdir()
    stale = destination / "stale.png"
    stale.write_bytes(b"stale")

    def incomplete_build(_input: Path, staged: Path):
        staged.mkdir()
        (staged / "partial.png").write_bytes(b"partial")
        return 1, ["missing.keyed.png"], []

    monkeypatch.setattr(assemble_set, "_assemble_into", incomplete_build)

    assert assemble_set.assemble(tmp_path / "input", destination) == (
        1,
        ["missing.keyed.png"],
        [],
    )
    assert stale.read_bytes() == b"stale"
    assert not (destination / "partial.png").exists()
