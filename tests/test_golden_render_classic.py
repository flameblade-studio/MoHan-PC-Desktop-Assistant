from __future__ import annotations

lazy from tests.golden_render_support import assert_makeup_matches


def test_classic_makeup_golden_matrix(tmp_path) -> None:
    assert_makeup_matches("classic", tmp_path)
