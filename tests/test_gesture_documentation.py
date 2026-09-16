from __future__ import annotations

lazy import re
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GESTURE_DOC = ROOT / "docs" / "GESTURE-INTERACTION.md"
RELEASE_DRAFT = ROOT / "docs" / "releases" / "v4.0.0-draft.md"
LANGUAGE_HEADINGS = ("## 繁體中文", "## 简体中文", "## English", "## 日本語")
LANGUAGE_SECTION_COUNT = 4
GESTURE_IDS = (
    "wave",
    "silence",
    "open-palm",
    "closed-fist",
    "thumbs-up",
    "thumbs-down",
    "point-left",
    "point-right",
)
SUSPICIOUS_MOJIBAKE = tuple(
    chr(codepoint)
    for codepoint in (
        0x875C,
        0x96FF,
        0x929D,
        0x6470,
        0x6498,
        0x977D,
        0xF172,
        0xEF3F,
        0xE6A4,
    )
)


def language_sections(text: str) -> tuple[str, ...]:
    positions = tuple(text.index(heading) for heading in LANGUAGE_HEADINGS)
    assert positions == tuple(sorted(positions))
    return tuple(
        text[start:end]
        for start, end in zip(positions, (*positions[1:], len(text)), strict=True)
    )


def test_gesture_document_has_complete_ordered_four_language_contract() -> None:
    sections = language_sections(GESTURE_DOC.read_text(encoding="utf-8"))
    assert len(sections) == LANGUAGE_SECTION_COUNT
    for section in sections:
        assert "Apache-2.0" in section
        assert "FP32" in section
        assert "7.6 MB" in section
        assert "Windows EXE" in section
        assert "21" in section
        assert "OpenCV Zoo" in section
        for gesture_id in GESTURE_IDS:
            assert f"`{gesture_id}`" in section


def test_every_language_states_safety_privacy_and_release_limits() -> None:
    sections = language_sections(GESTURE_DOC.read_text(encoding="utf-8"))
    required_by_language = (
        (
            "手勢互動的預設狀態為關閉",
            "原始攝影機影像的處理範圍限定於即時記憶體",
            "安全命令流程",
            "完成與發布聲明以相應閘門通過為準",
        ),
        (
            "手势交互的默认状态为关闭",
            "原始摄像头图像的处理范围限定于实时内存",
            "安全命令流程",
            "完成与发布声明以相应关卡通过为准",
        ),
        (
            "Gesture interaction is off by default",
            "Raw camera-image processing is confined to transient memory",
            "safe-command pipeline",
            "completion and release claims begin after",
        ),
        (
            "ジェスチャー操作の既定状態は無効",
            "元のカメラ画像の処理範囲は一時メモリに限定します",
            "安全なコマンド経路",
            "完了と公開の表明は対応する関門を通過した後に成立します",
        ),
    )
    for section, required in zip(sections, required_by_language, strict=True):
        assert all(statement in section for statement in required)
        assert "palm_detection_mediapipe_2023feb.onnx" in section
        assert "handpose_estimation_mediapipe_2023feb.onnx" in section


def test_skeleton_samples_require_explicit_strong_password_encryption() -> None:
    sections = language_sections(GESTURE_DOC.read_text(encoding="utf-8"))
    required_by_language = (
        (
            "一般攜帶檔的內容範圍",
            "骨架樣本在使用者明確勾選敏感資料並設定強密碼時",
            "一般資料庫維持非敏感資料範圍",
        ),
        (
            "普通可移植文件的内容范围",
            "骨架样本在用户明确勾选敏感数据并设置强密码时",
            "普通数据库维持非敏感数据范围",
        ),
        (
            "An ordinary portable profile's content scope",
            "when the user explicitly selects sensitive export and supplies a strong password",
            "the ordinary database retains its non-sensitive-data scope",
        ),
        (
            "通常の可搬プロファイル",
            "利用者が機密データの書き出しを明示的に選択し、強力なパスワードを設定した場合",
            "通常データベースは非機密データ範囲を維持します",
        ),
    )
    for section, required in zip(sections, required_by_language, strict=True):
        assert all(statement in section for statement in required)


def test_release_draft_repeats_skeleton_sample_privacy_boundary() -> None:
    sections = language_sections(RELEASE_DRAFT.read_text(encoding="utf-8"))
    required_by_language = (
        ("一般攜帶檔只含", "骨架樣本不得進一般資料庫或一般攜帶檔", "強密碼加密"),
        (
            "普通可移植文件只含",
            "骨架样本不得进入普通数据库或普通可移植文件",
            "强密码加密",
        ),
        (
            "Ordinary portable profiles contain only",
            "Skeleton samples never enter the ordinary database",
            "strong-password encryption",
        ),
        (
            "通常の可搬プロファイルに含めるのは",
            "骨格サンプルは通常データベース",
            "強力なパスワードで暗号化",
        ),
    )
    for section, required in zip(sections, required_by_language, strict=True):
        assert all(statement in section for statement in required)


def test_files_are_strict_utf8_without_corruption_markers() -> None:
    for path in (GESTURE_DOC, RELEASE_DRAFT, Path(__file__)):
        raw = path.read_bytes()
        text = raw.decode("utf-8", errors="strict")
        assert text.encode("utf-8") == raw
        assert not raw.startswith(bytes((0xEF, 0xBB, 0xBF)))
        assert "\ufffd" not in text
        assert "\x00" not in text
        assert "?" * 2 not in text
        assert not any(marker in text for marker in SUSPICIOUS_MOJIBAKE)

    english = language_sections(GESTURE_DOC.read_text(encoding="utf-8"))[2]
    assert re.search(r"[\u3400-\u9fff]", english) is None


def test_release_draft_keeps_four_language_structure() -> None:
    # Audit ruling (2026-08-27): v4.0.0 shipped. Its draft remains a historical
    # artifact; this gate checks existence and ordered four-language structure
    # through language_sections. Current release guidance lives in current docs.
    sections = language_sections(RELEASE_DRAFT.read_text(encoding="utf-8"))
    assert len(sections) == LANGUAGE_SECTION_COUNT
    assert all(section.strip() for section in sections)


if __name__ == "__main__":
    test_gesture_document_has_complete_ordered_four_language_contract()
    test_every_language_states_safety_privacy_and_release_limits()
    test_skeleton_samples_require_explicit_strong_password_encryption()
    test_release_draft_repeats_skeleton_sample_privacy_boundary()
    test_files_are_strict_utf8_without_corruption_markers()
    test_release_draft_keeps_four_language_structure()
    print("GESTURE_DOCUMENTATION_OK")
