from __future__ import annotations

lazy import re
lazy import hashlib
lazy import json
lazy import shutil
lazy import struct
lazy import subprocess
lazy import tempfile
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "docs" / "media"
MIN_IMAGE_WIDTH = 600
MIN_IMAGE_HEIGHT = 400
LANGUAGE_NAV_COUNT = 4
MIN_VIDEO_SIZE_BYTES = 100_000
VIDEO_WIDTH = 1280
VIDEO_HEIGHT = 720
VIDEO_FPS = "10/1"
VIDEO_MIN_DURATION_SECONDS = 30.0
VIDEO_MAX_DURATION_SECONDS = 60.0
VIDEO_AUDIO_SAMPLE_RATE = 22050
VIDEO_AUDIO_CHANNELS = 1
VIDEO_AUDIO_CODEC = "aac"
VIDEO_CODEC = "h264"
VIDEO_GENERATION = 2
VIDEO_GENERATOR = "tools/record_demo_video.py"
VIDEO_STREAM_DURATION_TOLERANCE_SECONDS = 0.1
VIDEO_PROVENANCE_KEY = "docs/media/mohan-demo.mp4"
VIDEO_PROVENANCE_FIELDS = (
    "width",
    "height",
    "fps",
    "duration_seconds",
    "audio_sample_rate",
    "audio_channels",
)
SUPPORT_COLUMN_COUNT = 3
STRATEGIST_CARD_COUNT = 4
PNG_FILES = {
    "mohan-hero.png": (1600, 900),
    "first-run-wizard.png": None,
    "voice-modes.png": None,
    "expressions.png": None,
    "tasks-and-ideas.png": None,
    "long-term-memory.png": None,
    "security-permissions.png": None,
    "support-proud.png": (640, 640),
    "support-shy-aligned.png": (640, 640),
    "support-mock-hit.png": (640, 640),
}
README_BADGES = (
    (
        "Windows CI",
        ("https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/"
        "actions/workflows/windows-ci.yml/badge.svg"),
    ),
    (
        "Cross-platform core CI",
        ("https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/"
        "actions/workflows/cross-platform-core.yml/badge.svg"),
    ),
    (
        "CodeQL",
        ("https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/"
        "actions/workflows/codeql.yml/badge.svg"),
    ),
    (
        "Python Security Audit",
        ("https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/"
        "actions/workflows/security-audit.yml/badge.svg"),
    ),
    (
        "Extended Secret Defense / Gitleaks",
        ("https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/"
        "actions/workflows/secret-defense.yml/badge.svg"),
    ),
    (
        "Latest Published Release",
        ("https://img.shields.io/github/v/release/"
        "flameblade-studio/MoHan-PC-Desktop-Assistant?"
        "include_prereleases&label=published"),
    ),
    ("MIT License", "https://img.shields.io/badge/license-MIT-blue.svg"),
    (
        "Python 3.15",
        ("https://img.shields.io/badge/Python-3.15-3776AB.svg?"
        "logo=python&logoColor=white"),
    ),
    (
        "4 interface languages",
        "https://img.shields.io/badge/interface_languages-4-79648d.svg",
    ),
)
BADGE_WORKFLOWS = (
    "windows-ci.yml",
    "cross-platform-core.yml",
    "codeql.yml",
    "security-audit.yml",
    "secret-defense.yml",
)
TIME_SENSITIVE_CREATOR_AGE_PATTERNS = (
    re.compile(r"我是一位\s*(?:\d{1,3}|[零〇一二三四五六七八九十百兩两]+)\s*[歲岁]"),
    re.compile(
        r"\bI was an?\s+(?:\d{1,3}|[a-z]+(?:-[a-z]+)*)"
        r"(?:-year-old|\s+years?\s+old)\b",
        re.IGNORECASE,
    ),
    re.compile(r"私は\s*(?:\d{1,3}|[零〇一二三四五六七八九十百]+)\s*歳"),
    re.compile(r"[三四五六七八九]十(?:多)?[歲岁]的自己"),
    re.compile(r"\bmy\s+(?:\d+|[a-z]+)-something\s+self\b", re.IGNORECASE),
    re.compile(r"[三四五六七八九]十代の自分"),
)


def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()[:24]
    assert data[:8] == b"\x89PNG\r\n\x1a\n", f"invalid PNG: {path.name}"
    return struct.unpack(">II", data[16:24])


def _assert_readme_images(readme: str) -> None:
    for filename, expected_size in PNG_FILES.items():
        path = MEDIA / filename
        assert path.is_file(), f"missing README image: {filename}"
        width, height = png_size(path)
        assert width >= MIN_IMAGE_WIDTH and height >= MIN_IMAGE_HEIGHT, (
            f"README image is too small: {filename} ({width}x{height})"
        )
        if expected_size:
            assert (width, height) == expected_size, (
                f"unexpected {filename} size: {width}x{height}"
            )
        assert f"docs/media/{filename}" in readme, (
            f"README does not reference {filename}"
        )


def _assert_single_readme_entry_point(readme: str) -> None:
    language_navigation = (
        "[繁體中文](#繁體中文) · [簡體中文](#简体中文) · "
        "[English](#english) · [日本語](#日本語)"
    )
    assert readme.count(language_navigation) == LANGUAGE_NAV_COUNT
    for obsolete_readme in ("README.zh-CN.md", "README.ja.md"):
        assert not (ROOT / obsolete_readme).exists(), (
            f"duplicate README entry point returned: {obsolete_readme}"
        )
        assert obsolete_readme not in readme, (
            f"README links obsolete compatibility entry point: {obsolete_readme}"
        )


def _assert_certification_badges(readme: str) -> None:
    badge_match = re.search(
        r'<p align="center">\s*(.*?)\s*</p>', readme, re.DOTALL
    )
    assert badge_match, "README.md is missing its certification badge block"
    actual_badges = tuple(
        re.findall(r'<img alt="([^"]+)" src="([^"]+)">', badge_match.group(1))
    )
    assert actual_badges == README_BADGES, (
        "README.md certification badges are incomplete, out of order, or stale"
    )
    for filename in PNG_FILES:
        if filename.startswith("support-"):
            continue
        assert f"docs/media/{filename}" in readme, (
            f"README.md does not reference shared current media: {filename}"
        )


def _assert_quality_standard(readme: str) -> None:
    quality_standard = (ROOT / "PUBLISHING.md").read_text(encoding="utf-8")
    for heading in (
        "炎劍開源軟體家族品質標準",
        "炎剑开源软件家族质量标准",
        "Flameblade Open Source Software Family Quality Standard",
        "炎剣オープンソース・ソフトウェア・ファミリー品質基準",
    ):
        assert heading in quality_standard, (
            f"missing shared quality-standard heading: {heading}"
        )
    for declaration in (
        "劍，我已鍛成；餘下的路，就交給你們了。",
        "剑，我已锻成；余下的路，就交给你们了。",
        "I have forged this sword. What comes next is up to you.",
        "この剣は、私が鍛え上げました。あとは皆さんに託します。",
    ):
        assert declaration in quality_standard, (
            f"missing open-source declaration: {declaration}"
        )
    assert "(PUBLISHING.md)" in readme, (
        "README.md does not link to the shared Flameblade quality standard"
    )
    for workflow in BADGE_WORKFLOWS:
        assert (ROOT / ".github" / "workflows" / workflow).is_file(), (
            f"README badge points to missing workflow: {workflow}"
        )


def _assert_timeless_creator_narrative(readme: str) -> None:
    for pattern in TIME_SENSITIVE_CREATOR_AGE_PATTERNS:
        assert not pattern.search(readme), (
            "README.md hard-codes the creator's changing age: "
            f"{pattern.pattern}"
        )


def _assert_demo_video_provenance(
    video: Path,
    provenance_path: Path,
) -> dict[str, object]:
    manifest = json.loads(provenance_path.read_text(encoding="utf-8"))
    entries = manifest.get("entries")
    assert isinstance(entries, dict)
    entry = entries.get(VIDEO_PROVENANCE_KEY)
    assert isinstance(entry, dict), "missing demonstration video provenance entry"
    assert entry.get("generator") == VIDEO_GENERATOR
    assert entry.get("generation") == VIDEO_GENERATION
    assert entry.get("auto_regenerable") is True
    digest = entry.get("sha256")
    assert isinstance(digest, str) and digest == hashlib.sha256(
        video.read_bytes()
    ).hexdigest(), "demonstration video SHA-256 differs from provenance"

    for field in VIDEO_PROVENANCE_FIELDS:
        assert field in entry, f"missing demonstration video provenance field: {field}"
    assert entry["width"] == VIDEO_WIDTH
    assert entry["height"] == VIDEO_HEIGHT
    assert entry["fps"] == VIDEO_FPS
    duration = entry["duration_seconds"]
    assert isinstance(duration, (int, float)) and not isinstance(duration, bool)
    assert VIDEO_MIN_DURATION_SECONDS <= duration <= VIDEO_MAX_DURATION_SECONDS, (
        "provenance duration_seconds must be between 30 and 60 seconds"
    )
    assert entry["audio_sample_rate"] == VIDEO_AUDIO_SAMPLE_RATE
    assert entry["audio_channels"] == VIDEO_AUDIO_CHANNELS
    assert entry["audio_channels"] > 0, "demonstration video provenance has no audio"
    return entry


def _assert_demo_video_live_probe(
    video: Path,
    entry: dict[str, object],
    ffprobe: str,
) -> None:
    probe = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_streams",
            "-show_format",
            str(video),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert probe.returncode == 0, probe.stderr
    metadata = json.loads(probe.stdout)
    streams = metadata.get("streams")
    assert isinstance(streams, list)
    video_stream = next(
        (
            stream
            for stream in streams
            if isinstance(stream, dict) and stream.get("codec_type") == "video"
        ),
        None,
    )
    audio_stream = next(
        (
            stream
            for stream in streams
            if isinstance(stream, dict) and stream.get("codec_type") == "audio"
        ),
        None,
    )
    assert isinstance(video_stream, dict), "demonstration video has no video stream"
    assert isinstance(audio_stream, dict), "demonstration video has no audio stream"
    assert video_stream.get("codec_name") == VIDEO_CODEC
    assert video_stream.get("width") == VIDEO_WIDTH
    assert video_stream.get("height") == VIDEO_HEIGHT
    assert video_stream.get("r_frame_rate") == VIDEO_FPS
    assert int(video_stream["nb_frames"]) == round(
        float(video_stream["duration"]) * int(VIDEO_FPS.split("/", 1)[0])
    )
    assert audio_stream.get("codec_name") == VIDEO_AUDIO_CODEC
    assert int(audio_stream["sample_rate"]) == VIDEO_AUDIO_SAMPLE_RATE
    assert audio_stream.get("channels") == VIDEO_AUDIO_CHANNELS
    assert audio_stream.get("channel_layout") == "mono"
    assert abs(
        float(video_stream["duration"]) - float(audio_stream["duration"])
    ) <= VIDEO_STREAM_DURATION_TOLERANCE_SECONDS
    format_info = metadata.get("format")
    assert isinstance(format_info, dict)
    assert "mp4" in str(format_info.get("format_name", ""))
    live_specs = {
        "width": video_stream.get("width"),
        "height": video_stream.get("height"),
        "fps": video_stream.get("r_frame_rate"),
        "duration_seconds": float(format_info["duration"]),
        "audio_sample_rate": int(audio_stream["sample_rate"]),
        "audio_channels": audio_stream.get("channels"),
    }
    for field, actual in live_specs.items():
        assert actual == entry[field], (
            f"live probe differs from provenance for {field}: "
            f"{actual!r} != {entry[field]!r}"
        )


def _assert_demo_video(readme: str) -> None:
    video = MEDIA / "mohan-demo.mp4"
    assert video.is_file(), "missing 30–60 second demonstration video"
    size = video.stat().st_size
    assert MIN_VIDEO_SIZE_BYTES <= size <= 20 * 1024 * 1024, (
        f"unexpected demonstration video size: {size} bytes"
    )
    header = video.read_bytes()[:32]
    assert b"ftyp" in header, "demonstration video is not an MP4 container"
    assert "docs/media/mohan-demo.mp4" in readme

    provenance_path = ROOT / "docs/media/MEDIA-PROVENANCE.json"
    entry = _assert_demo_video_provenance(video, provenance_path)
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        print("live probe skipped: ffprobe not available", flush=True)
    else:
        _assert_demo_video_live_probe(video, entry, ffprobe)


def test_demo_video_provenance_rejects_out_of_range_duration() -> None:
    video = MEDIA / "mohan-demo.mp4"
    source = ROOT / "docs/media/MEDIA-PROVENANCE.json"
    manifest = json.loads(source.read_text(encoding="utf-8"))
    manifest["entries"][VIDEO_PROVENANCE_KEY]["duration_seconds"] = 70
    with tempfile.TemporaryDirectory(prefix="mohan-media-provenance-") as directory:
        candidate = Path(directory) / "MEDIA-PROVENANCE.json"
        candidate.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=4) + "\n",
            encoding="utf-8",
        )
        try:
            _assert_demo_video_provenance(video, candidate)
        except AssertionError as error:
            assert "duration_seconds" in str(error)
        else:
            raise AssertionError("out-of-range provenance duration was accepted")


def _assert_support_section(readme: str) -> None:
    support_requirements = (
        "## 支持墨寒 / Support MoHan",
        "docs/media/support-proud.png",
        "docs/media/support-shy-aligned.png",
        "docs/media/support-mock-hit.png",
        "請使用儲存庫上方由 GitHub 顯示的 Sponsor 按鈕，或直接前往",
        "请使用仓库上方由 GitHub 显示的 Sponsor 按钮，或直接前往",
        "Use the Sponsor button displayed by GitHub above this repository, or visit",
        "このリポジトリ上部に GitHub が表示する Sponsor ボタンをご利用いただくか、",
        "支持墨寒：Ko-fi 贊助＆裝飾 DLC 下載",
        "支持墨寒：Ko-fi 赞助＆装饰 DLC 下载",
        "Support MoHan: Ko-fi sponsorship & cosmetic DLC downloads",
        "墨寒を支援：Ko-fi スポンサー＆装飾 DLC ダウンロード",
        "https://ko-fi.com/flamebladestudio",
    )
    for requirement in support_requirements:
        assert requirement in readme, f"missing project support content: {requirement}"
    for retired_support in (
        "buymeacoffee.com",
        "paypal.com/paypalme",
    ):
        assert retired_support not in readme.lower(), (
            f"retired support link remains in README: {retired_support}"
        )
    for filename in (
        "support-proud.png",
        "support-shy-aligned.png",
        "support-mock-hit.png",
    ):
        assert f'src="docs/media/{filename}" width="220" height="220"' in readme, (
            f"support portrait lacks fixed aligned dimensions: {filename}"
        )
    assert readme.count('width="33%" align="center" valign="top"') == SUPPORT_COLUMN_COUNT, (
        "support columns must be top-aligned so shorter captions cannot push "
        "the complete image-and-text column downward on GitHub"
    )
    assert readme.count('width="25%" align="center" valign="top"') == STRATEGIST_CARD_COUNT, (
        "all four strategist-theatre cards must be top-aligned so shorter "
        "captions cannot push the first images and text downward on GitHub"
    )


def _assert_github_links(readme: str) -> None:
    github_requirements = (
        "actions/workflows/windows-ci.yml/badge.svg",
        "actions/workflows/codeql.yml/badge.svg",
        "ROADMAP.md",
        "/discussions",
    )
    for requirement in github_requirements:
        assert requirement in readme, f"missing GitHub project link: {requirement}"


def _assert_security_and_community_files() -> None:
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


def main() -> int:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    _assert_single_readme_entry_point(readme)
    _assert_readme_images(readme)
    _assert_certification_badges(readme)
    _assert_quality_standard(readme)
    _assert_timeless_creator_narrative(readme)
    test_demo_video_provenance_rejects_out_of_range_duration()
    _assert_demo_video(readme)
    _assert_support_section(readme)
    _assert_github_links(readme)
    _assert_security_and_community_files()
    print("README_MEDIA_AND_COMMUNITY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
