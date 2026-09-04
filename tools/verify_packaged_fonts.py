"""Verify the exact font payload emitted by the Windows PyInstaller bundle."""

from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import os
lazy from collections.abc import Sequence
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGED_FONT_ROOT = Path("_internal") / "assets" / "fonts"
LEGACY_PACKAGED_FONT_ROOT = Path("assets") / "fonts"
PACKAGED_FONT_ROOTS = (PACKAGED_FONT_ROOT, LEGACY_PACKAGED_FONT_ROOT)
REQUIRED_FONT_FILES = (
    Path("LXGW-WenKai-TC") / "LXGWWenKaiTC-Regular.ttf",
    Path("LXGW-WenKai-TC") / "OFL.txt",
    Path("Cinzel") / "Cinzel[wght].ttf",
    Path("Cinzel") / "OFL.txt",
)
SUCCESS_MARKER = "PACKAGED_FONTS_OK"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _find_packaged_font_root(package: Path) -> Path:
    """Find the current or legacy PyInstaller data root, fail closed."""

    candidates = tuple(package / relative for relative in PACKAGED_FONT_ROOTS)
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    checked = ", ".join(str(candidate) for candidate in candidates)
    raise RuntimeError(
        "Packaged artifact is missing the governed font directory; "
        f"checked: {checked}"
    )


def _path_sort_key(path: Path, root: Path) -> str:
    """Return a platform-neutral key for deterministic packaged-file order."""

    relative = path.relative_to(root)
    return os.path.normcase(os.path.normpath(str(relative)))


def verify_packaged_fonts(
    package_root: Path,
    *,
    source_root: Path | None = None,
) -> tuple[Path, ...]:
    """Require every governed font and license in a PyInstaller onedir bundle."""

    package = package_root.resolve()
    if not package.is_dir():
        raise FileNotFoundError(f"Packaged application directory not found: {package}")
    source = (
        ROOT / "assets" / "fonts" if source_root is None else source_root
    ).resolve()
    if not source.is_dir():
        raise FileNotFoundError(f"Font source directory not found: {source}")

    packaged_root = _find_packaged_font_root(package)

    packaged: list[Path] = []
    for relative in REQUIRED_FONT_FILES:
        source_path = source / relative
        package_path = packaged_root / relative
        if not source_path.is_file():
            raise FileNotFoundError(f"Governed font source is missing: {source_path}")
        if not package_path.is_file():
            raise RuntimeError(
                "Packaged artifact is missing a governed font file: "
                f"{package_path}"
            )
        if _sha256(package_path) != _sha256(source_path):
            raise RuntimeError(f"Packaged font hash differs from source: {package_path}")
        packaged.append(package_path)
    return tuple(sorted(packaged, key=lambda path: _path_sort_key(path, packaged_root)))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("package_root", type=Path)
    args = parser.parse_args(argv)
    packaged = verify_packaged_fonts(args.package_root)
    print(f"{SUCCESS_MARKER}={packaged[0].parent.parent}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
