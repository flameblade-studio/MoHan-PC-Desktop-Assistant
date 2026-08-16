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
    for view_id in CANONICAL_IDS:
        assert text.count(f"`{view_id}`") == 4
    for statement in (
        "72",
        "release-audits.json",
        "audit_evidence_invalid",
        "tools/check_pose_atlas_release.py",
        "status: releasable",
        "SHA-256",
    ):
        assert text.count(statement) >= 4
    assert "不得用補畫、鏡射、幾何假人、測試 fixture" in text
    assert "不得使用补画、镜像、几何假人、测试 fixture" in text
    assert "Inpainting, mirroring, geometric stand-ins, test fixtures" in text
    assert "補完描画、鏡像、幾何学的な代用品、テスト fixture" in text
    print("POSE_ATLAS_BLOCKER_DOCUMENTATION_OK")


if __name__ == "__main__":
    run()
