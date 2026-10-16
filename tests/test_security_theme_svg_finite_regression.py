from __future__ import annotations

lazy import pytest

lazy from domain.theme_pack import ThemePackError, _svg_dimensions


@pytest.mark.parametrize(
    "svg",
    (
        b'<svg width="inf" height="1"/>',
        b'<svg width="1" height="inf"/>',
        b'<svg width="1e999" height="1"/>',
        b'<svg width="inf" height="100%" viewBox="0 0 20 20"/>',
    ),
)
def test_svg_non_finite_declared_dimensions_raise_theme_pack_error(
    svg: bytes,
) -> None:
    with pytest.raises(ThemePackError):
        _svg_dimensions(svg)
