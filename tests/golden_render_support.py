"""Shared assertions for the sharded golden-render matrix."""

from __future__ import annotations

lazy from pathlib import Path
lazy import json

lazy from tools.golden_render import (
    DEFAULT_BASELINE,
    DEFAULT_DIFF,
    MANIFEST_PATH,
    compare_manifest,
    matrix_cells,
    render_matrix,
)


def assert_makeup_matches(makeup: str, tmp_path: Path) -> None:
    expected = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    selected = tuple(cell for cell in matrix_cells() if cell.makeup == makeup)
    output = tmp_path / "current"
    rendered = render_matrix(output, cells=selected)
    repeat_output = tmp_path / "repeat"
    repeated = render_matrix(repeat_output, cells=selected)
    repeat_changes = compare_manifest(
        repeated, rendered, output=repeat_output, baseline_dir=output,
        diff_dir=DEFAULT_DIFF / "repeat" / makeup,
    )
    png_changes = [
        first["id"] for first, second in zip(rendered["cells"], repeated["cells"], strict=True)
        if first["png_sha256"] != second["png_sha256"]
    ]
    assert repeat_changes == [] and png_changes == [], (
        f"同機重複渲染雜湊不一致：RGBA={repeat_changes} PNG={png_changes}"
    )
    expected_subset = {
        **expected,
        "cells": [cell for cell in expected["cells"] if cell["inputs"]["makeup"] == makeup],
    }
    changed = compare_manifest(
        rendered,
        expected_subset,
        output=output,
        baseline_dir=DEFAULT_BASELINE,
        diff_dir=DEFAULT_DIFF,
    )
    assert changed == [], "golden 格子已變更：" + ", ".join(changed)
