from __future__ import annotations

lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCUMENT = ROOT / "docs" / "release-evidence" / "V4-POSE-ATLAS-BLOCKER.md"
LANGUAGE_HEADINGS = ("## 繁體中文", "## 简体中文", "## English", "## 日本語")
CANONICAL_IDS = tuple(
    f"yaw{yaw:+04d}-pitch+00" for yaw in range(-180, 180, 15)
)


def run() -> None:
    raw = DOCUMENT.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8")
    assert all(marker not in text for marker in ("�", "\x00"))
    positions = tuple(text.index(heading) for heading in LANGUAGE_HEADINGS)
    assert positions == tuple(sorted(positions))
    assert all(text.count(heading) == 1 for heading in LANGUAGE_HEADINGS)
    assert "historical blocker record (superseded)" in text
    assert "24／24" in text
    assert "assets/pose-atlas/v4/" in text
    assert "release-audits.json" in text
    assert "no longer block publication" in text
    print("POSE_ATLAS_RELEASE_DOCUMENTATION_OK")


if __name__ == "__main__":
    run()
