from __future__ import annotations

import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "docs" / "media"
PNG_FILES = {
    "mohan-hero.png": (1600, 900),
    "first-run-wizard.png": None,
    "voice-modes.png": None,
    "expressions.png": None,
    "tasks-and-ideas.png": None,
    "long-term-memory.png": None,
    "security-permissions.png": None,
}


def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()[:24]
    assert data[:8] == b"\x89PNG\r\n\x1a\n", f"invalid PNG: {path.name}"
    return struct.unpack(">II", data[16:24])


def main() -> int:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for filename, expected_size in PNG_FILES.items():
        path = MEDIA / filename
        assert path.is_file(), f"missing README image: {filename}"
        width, height = png_size(path)
        assert width >= 600 and height >= 400, (
            f"README image is too small: {filename} ({width}x{height})"
        )
        if expected_size:
            assert (width, height) == expected_size, (
                f"unexpected {filename} size: {width}x{height}"
            )
        assert f"docs/media/{filename}" in readme, (
            f"README does not reference {filename}"
        )

    video = MEDIA / "mohan-demo.mp4"
    assert video.is_file(), "missing 30–60 second demonstration video"
    size = video.stat().st_size
    assert 100_000 <= size <= 20 * 1024 * 1024, (
        f"unexpected demonstration video size: {size} bytes"
    )
    header = video.read_bytes()[:32]
    assert b"ftyp" in header, "demonstration video is not an MP4 container"
    assert "docs/media/mohan-demo.mp4" in readme

    security = (ROOT / "SECURITY.md").read_text(encoding="utf-8").lower()
    assert "private vulnerability reporting" in security
    assert "api key" in security and "oauth" in security
    assert "請勿" in security and "公開" in security

    required_community_files = (
        ROOT / "CODE_OF_CONDUCT.md",
        ROOT / ".github" / "ISSUE_TEMPLATE" / "bug_report.yml",
        ROOT / ".github" / "ISSUE_TEMPLATE" / "feature_request.yml",
        ROOT / ".github" / "ISSUE_TEMPLATE" / "config.yml",
    )
    for path in required_community_files:
        assert path.is_file(), f"missing community file: {path.relative_to(ROOT)}"

    print("README_MEDIA_AND_COMMUNITY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
