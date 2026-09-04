from __future__ import annotations

lazy import hashlib
lazy import json
lazy import re
lazy import struct
lazy import subprocess
lazy import sys
lazy import tempfile
lazy from pathlib import Path
lazy from xml.etree.ElementTree import parse as parse_xml

lazy from PySide6.QtGui import QImage

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy from domain.version_info import FALLBACK_VERSION
lazy from domain.constants import POSE_ATLAS_GENERATION
lazy from tools.sync_wordpress_download_page import (
    END_MARKER,
    START_MARKER,
    release_block,
    replace_managed_block,
)

MIN_LANGUAGE_FILE_SIZE = 20_000
EXPECTED_OCCURRENCE_COUNT = 2
MIN_EXPRESSION_CARD_COUNT = 6
SUPPORT_CARD_COUNT = 3
MIN_TOTAL_CARD_COUNT = 9
SCENE_COUNT = 6

VERSION = FALLBACK_VERSION
VERSION_PREFIX, CANDIDATE_NUMBER = VERSION.rsplit(".", maxsplit=1)
NEXT_VERSION = f"{VERSION_PREFIX}.{int(CANDIDATE_NUMBER) + 1}"
TAG = f"v{VERSION}"
PREFIX = f"MoHan-Desktop-Assistant-{TAG}"
REPOSITORY = "flameblade-studio/MoHan-PC-Desktop-Assistant"


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def assert_contains(content: str, expected: tuple[str, ...]) -> None:
    for value in expected:
        assert value in content, value


def assert_image(path: Path, size: tuple[int, int]) -> None:
    image = QImage(str(path))
    assert not image.isNull(), path
    assert (image.width(), image.height()) == size


def test_version_runtime_and_evidence_policy() -> None:
    assert f'FALLBACK_VERSION = "{VERSION}"' in read("domain/version_info.py")
    package_version = VERSION.replace("-rc.", "rc")
    for metadata in ("pyproject.toml", "sbom/preview.pyproject.toml"):
        assert f'version = "{package_version}"' in read(metadata)
    current_docs = {
        name: read(name)
        for name in (
            "README.md",
            "QUICKSTART.md",
            "PUBLISHING.md",
            "CITATION.cff",
        )
    }
    assert VERSION in current_docs["README.md"], (
        "README.md must identify the current source release version"
    )
    assert "Latest formal release:" in current_docs["README.md"]
    for name in ("README.md", "QUICKSTART.md"):
        assert "2.0.14-rc.3.exe" not in current_docs[name]
    assert_contains(
        read("docs/PYTHON-3.15-MIGRATION.md"),
        ("PEP 810", "PEP 799", "Python 3.15.0rc1"),
    )

    build_script = read("build.ps1")
    assert_contains(
        build_script,
        (
            "True:False",
            "running with the JIT off",
            "jit_supported = $true",
            "jit_default = $false",
            "Python 3.15.0rc1",
            "import azure.cognitiveservices.speech, cryptography, cv2, numpy, opencc, sounddevice, websocket",
            "import PySide6.QtCore, PySide6.QtGui, PySide6.QtMultimedia, PySide6.QtWidgets",
            "packaging dependencies are incomplete",
            "platform.python_version()",
            "python = $PythonVersion",
            '--add-data "LICENSE;."',
            '--add-data "THIRD_PARTY_NOTICES.md;."',
            "tools/build_native_acceleration.py",
            "--install",
            '--hidden-import "_mohan_accel"',
            '--hidden-import "PySide6.QtCore"',
            '--hidden-import "PySide6.QtGui"',
            '--hidden-import "PySide6.QtMultimedia"',
            '--hidden-import "PySide6.QtWidgets"',
            '--hidden-import "azure.cognitiveservices.speech"',
            '--hidden-import "sounddevice"',
            '--hidden-import "websocket"',
            '--collect-all "sounddevice"',
            "tools.audit_speech_runtime_chain",
            "speech runtime chain or PortAudio dependency is incomplete",
            '--collect-all "opencc"',
            '$env:PYTHON_JIT = "1"',
            "tools/build_pyinstaller_jit_bootloader.py",
            '.qt315-compat-full\\Lib\\site-packages',
            "6.11.1+mohan.py315.",
            "tools\\jit_launcher.py",
            "Move-Item -LiteralPath $PublicExecutable",
            '$env:PYTHON_JIT = "0"',
        ),
    )
    launcher = read("tools/jit_launcher.py")
    assert 'environment["PYTHON_JIT"] = "1"' in launcher
    assert "RUNTIME_SUFFIX = \"-runtime.exe\"" in launcher
    for workflow_name in ("windows-ci.yml", "release.yml"):
        workflow = read(f".github/workflows/{workflow_name}")
        assert 'python-version: "3.15.0-rc.1"' in workflow
        assert 'python-version: "3.12"' not in workflow
        assert 'FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: "true"' in workflow
        assert "rustup toolchain install 1.97.1" in workflow
        assert 'RUSTUP_TOOLCHAIN: "1.97.1"' in workflow
        assert "rustup default" not in workflow
        assert "maturin==1.14.1" in workflow

    security_audit = read(".github/workflows/security-audit.yml")
    assert_contains(
        security_audit,
        (
            'python-version: "3.14.7"',
            "isolated audit tooling",
            'FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: "true"',
        ),
    )
    release = read(".github/workflows/release.yml")
    assert release.count('python-version: "3.14.7"') == 1
    assert "from version_info import FALLBACK_VERSION" not in release
    assert_contains(
        release,
        (
            "domain/version_info.py",
            "Expected exactly one literal FALLBACK_VERSION in domain/version_info.py",
            'source_version="${source_versions[0]}"',
            "PACKAGED_JIT_DEFAULT_OK",
            "tools/profile_mohan_tachyon.py",
            "tools/validate_release_sboms.py",
            "--spec-version 1.7",
            "--output-reproducible",
            "SBOM-Validation.json",
            "Performance-Evidence.zip",
            "Performance-Summary.json",
            "tools/verify_packaged_native_acceleration.py",
            "tests/test_native_equivalence.py",
            "tests/test_native_rgba_equivalence.py",
        ),
    )


# SHA-256 of the canonical bare half-body sprite (generation-2 base, pinned
# 2026-09-02).  Marketing art is no longer drawn from it directly: the composed
# portrait below is rendered over it by tools/render_marketing_portraits.py.
CANONICAL_HALF_BODY_SHA256 = (
    "e99cc462979d963247db30e73efcceffe408c5b4046db69611325a6920647825"
)
# docs/media/portraits/idle_front.png: generation-2 composite (official pack +
# classic makeup) that installer artwork and the taskbar icon derive from, 2026-09-04.
MARKETING_IDLE_PORTRAIT_SHA256 = (
    "c36995554580949a344c026ec4cffceea92fb6abc195b7fdbc54ba33c7c12afd"
)
# installer/artwork/wizard-hero.png: built from the generation-2 composite, 2026-09-04.
WIZARD_HERO_SHA256 = (
    "41957e25f03220ee444530d31e783b42632f53fffac39394ebb4eb4ede3d9063"
)
# installer/artwork/wizard-small.png: built from the generation-2 composite, 2026-09-04.
WIZARD_SMALL_SHA256 = (
    "94137ee32cde15b6963cc5426a288fb604d0007c563e34c68ce0a7cdf7c282c5"
)
# assets/mohan-taskbar-icon.png: built from the generation-2 composite, 2026-09-04.
TASKBAR_ICON_PNG_SHA256 = (
    "a979d2ae8af72bd6f174b59a2b8b23b7def8d204b7f006bd9947ef41f3dabcd5"
)
# assets/mohan-halfbody.ico: built from the generation-2 composite, 2026-09-04.
WINDOWS_ICON_SHA256 = (
    "404722fba2b808c83e098746d032b52bf21ae40c355ea88941e516b4ffcad24a"
)
# The README expression cards and the canonical idle portrait, rendered composed.
MARKETING_PORTRAITS = (
    "proud_front.png",
    "thinking_front.png",
    "shy_cute_front.png",
    "mock_hit_front.png",
    "gentle_smile_front.png",
    "worried_front.png",
    "idle_front.png",
)
PORTRAIT_SIZE = (1254, 1254)
MEDIA_PROVENANCE_PATH = ROOT / "docs/media/MEDIA-PROVENANCE.json"
README_MEDIA_PATTERN = re.compile(
    r"docs/media/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*"
)
README_AUTO_MEDIA_SHA256 = {
    "docs/media/expressions.png": (
        "c0d8b96c47f1516444f46519a55fe69fd1063f2cf027540e8ff8422620fd04a2"
    ),
    "docs/media/first-run-wizard.png": (
        "8d4f5c1912a4947d6d315fa0bf617d1ce6cdb8ca73aa8e0ccea7d4c2e0bcf927"
    ),
    "docs/media/long-term-memory.png": (
        "31d8f213dc76c0fa8b9888aaf284b63ba7ef3022a4b3fc4cebb5a04091ca2073"
    ),
    "docs/media/mohan-demo.mp4": (
        "f3a3614447e7f743111845c0e33de118a659070c738fea5704c31041002cb9bd"
    ),
    "docs/media/mohan-hero.png": (
        "169d69f63bdc5aba1a3d1ddc80fd6113e62fb0aa969aa865932baa0a998590cb"
    ),
    "docs/media/portraits/gentle_smile_front.png": (
        "92c85c914e60f5acea002368f12ee2759665a53dbdb26784c80b703c71bda5c2"
    ),
    "docs/media/portraits/mock_hit_front.png": (
        "e38163e1fce62ee4e21215f5c32c36787b3e1099ed52256503f6693294e38f5f"
    ),
    "docs/media/portraits/proud_front.png": (
        "5c5c0454d783f22c4ea0e7bd5b3e4b9787679d74cb490d0451b522dd621c340a"
    ),
    "docs/media/portraits/shy_cute_front.png": (
        "76cbd9ae93c41fdc64a0d6b7c094e751daa72262249a223816c5c56449c0efe1"
    ),
    "docs/media/portraits/thinking_front.png": (
        "0d36ddca24d571e905c439ebaaa789993cdc6f1968e2c2ff6bc7cafd328837bd"
    ),
    "docs/media/portraits/worried_front.png": (
        "cff573b6b4071ac70efb7a2ce44b848938615011140f22cfaf5737904c6379c5"
    ),
    "docs/media/security-permissions.png": (
        "37c6f232c6257387370c6581fb98025f1324a8c675cfaa7a1ebf68556fc7f5a2"
    ),
    "docs/media/support-mock-hit.png": (
        "809490a94b627b100ec127ec352b3a7f073345bc051374685a349e0bc16cec64"
    ),
    "docs/media/support-proud.png": (
        "63303ac49ab5a42fced7d1b9b54939f0b5bd2c098442439514f741c9cb252115"
    ),
    "docs/media/support-shy-aligned.png": (
        "8910511e5586f9a936a6a175da9199e8586222efe2278ca94089d77dd7665996"
    ),
    "docs/media/tasks-and-ideas.png": (
        "042402392dfdce1725b100d4ec34ef75d717658d769200353070d913d79ee482"
    ),
    "docs/media/voice-modes.png": (
        "5b563792cf056d2a99692cd5d58bf3bb5550b834c39fdde30bad9164d1def571"
    ),
}


def _readme_media_references() -> set[str]:
    return set(README_MEDIA_PATTERN.findall(read("README.md")))


def _assert_media_provenance(manifest: dict[str, object]) -> None:
    assert manifest.get("schema_version") == 1
    assert manifest.get(
        "generation_source"
    ) == "domain/constants.py:POSE_ATLAS_GENERATION"
    entries = manifest.get("entries")
    assert isinstance(entries, dict)
    references = _readme_media_references()
    assert set(entries) == references, (
        "README media provenance mismatch: "
        f"missing={sorted(references - set(entries))}, "
        f"unexpected={sorted(set(entries) - references)}"
    )

    stale: list[str] = []
    auto_entries: set[str] = set()
    for relative, metadata in sorted(entries.items()):
        assert isinstance(relative, str)
        assert isinstance(metadata, dict), relative
        path = ROOT / relative
        assert path.is_file(), f"missing README media file: {relative}"
        generator = metadata.get("generator")
        assert isinstance(generator, str) and generator.strip(), relative
        generation = metadata.get("generation")
        assert isinstance(generation, int) and not isinstance(generation, bool), relative
        digest = metadata.get("sha256")
        assert isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest), relative
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, relative
        auto_regenerable = metadata.get("auto_regenerable")
        assert isinstance(auto_regenerable, bool), relative
        if auto_regenerable:
            auto_entries.add(relative)
            if generation != POSE_ATLAS_GENERATION:
                stale.append(relative)
        else:
            reason = metadata.get("reason")
            assert isinstance(reason, str) and reason.strip(), relative

    assert auto_entries == set(README_AUTO_MEDIA_SHA256)
    for relative, expected in README_AUTO_MEDIA_SHA256.items():
        assert entries[relative]["sha256"] == expected, relative
    if stale:
        raise AssertionError(
            "README media entries behind "
            f"POSE_ATLAS_GENERATION={POSE_ATLAS_GENERATION}: "
            + ", ".join(stale)
        )


def test_readme_media_provenance() -> None:
    manifest = json.loads(MEDIA_PROVENANCE_PATH.read_text(encoding="utf-8"))
    _assert_media_provenance(manifest)


def test_readme_media_provenance_rejects_stale_auto_generation() -> None:
    manifest = json.loads(MEDIA_PROVENANCE_PATH.read_text(encoding="utf-8"))
    entries = manifest["entries"]
    target = "docs/media/mohan-hero.png"
    original_generation = entries[target]["generation"]
    entries[target]["generation"] = 1
    try:
        _assert_media_provenance(manifest)
    except AssertionError as error:
        message = str(error)
        assert target in message
        assert f"POSE_ATLAS_GENERATION={POSE_ATLAS_GENERATION}" in message
    else:
        raise AssertionError("stale auto-regenerable media was accepted")
    finally:
        entries[target]["generation"] = original_generation


def test_readme_media_generation_tools_use_runtime_composition() -> None:
    renderer = read("tools/render_marketing_portraits.py")
    capture = read("tools/capture_readme_media.py")
    recorder = read("tools/record_demo_video.py")
    assert_contains(
        renderer,
        (
            "ActiveOutfitOverlay(",
            "--crop-alpha",
            "--content-size",
            "--content-offset",
        ),
    )
    assert_contains(
        capture,
        (
            "ActiveOutfitOverlay",
            "grab_widget_image",
            'render_portrait(overlay, "idle_front")',
            'render_portrait(overlay, "attentive_front")',
            'compose_expression_showcase(output_dir / "expressions.png", overlay)',
            "render_all(",
        ),
    )
    assert_contains(
        recorder,
        (
            'os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")',
            '"Microsoft Yating"',
            "synthesize_windows_speech_to_wave",
            "grab_widget_image",
            'f"frame-{frame_index:06d}.png"',
            '"-framerate"',
            '"libx264"',
            '"-ac"',
            '"-ar"',
        ),
    )


def test_inno_setup_and_artwork_contract() -> None:
    inno_script = read("installer/mohan.iss")
    for language in ("ChineseTraditional", "ChineseSimplified"):
        messages = ROOT / "installer" / "languages" / f"{language}.isl"
        assert messages.is_file() and messages.stat().st_size > MIN_LANGUAGE_FILE_SIZE
    assert "compiler:Languages\\ChineseTraditional.isl" not in inno_script
    assert_contains(
        inno_script,
        (
            "{#TraditionalChineseMessages}",
            "{#SimplifiedChineseMessages}",
            'Name: "chinesetraditional"',
            'Name: "chinesesimplified"',
            'Name: "english"',
            'Name: "japanese"',
            "japanese.CreateDesktopIcon",
            "WizardImageFile={#WizardImagePath}",
            "WizardSmallImageFile={#WizardSmallImagePath}",
            "DisableWelcomePage=no",
            'Type: files; Name: "{app}\\MoHan-Desktop-Assistant-*.exe"',
        ),
    )
    assert inno_script.count(
        'AppUserModelID: "FlamebladeStudio.MoHanDesktopAssistant"'
    ) == EXPECTED_OCCURRENCE_COUNT
    installed_icon = 'IconFilename: "{app}\\{#ExecutableName}"'
    assert inno_script.count(installed_icon) == EXPECTED_OCCURRENCE_COUNT
    assert 'IconFilename: "{#IconPath}"' not in inno_script
    installer_test = read("installer/test_installers.ps1")
    assert 'MOHAN_ALLOW_INSTALLER_MUTATION -ne "1"' in installer_test
    assert '"/MERGETASKS=!desktopicon"' in installer_test
    for required in (
        "MSI $Variant shortcut target escaped the install directory",
        "MSI $Variant shortcut has an invalid Shell Link header",
        "MSI $Variant shortcut contains an independent icon location",
        "MSI $Variant shortcut icon escaped the installed MoHan executable",
        "MSI $Variant uninstaller left the Start menu shortcut behind",
    ):
        assert required in installer_test

    canonical = ROOT / "assets/expressions/idle_front.png"
    assert_image(canonical, PORTRAIT_SIZE)
    assert hashlib.sha256(canonical.read_bytes()).hexdigest() == CANONICAL_HALF_BODY_SHA256
    portrait = ROOT / "docs/media/portraits/idle_front.png"
    assert_image(portrait, PORTRAIT_SIZE)
    assert hashlib.sha256(portrait.read_bytes()).hexdigest() == MARKETING_IDLE_PORTRAIT_SHA256
    for consumer in ("infrastructure/face_assets.py", "tools/build_installer_artwork.py"):
        content = read(consumer)
        assert "idle_front.png" in content
        assert "mohan-hero-rain-canonical.webp" not in content
    artwork_builder = read("tools/build_installer_artwork.py")
    assert '"--source"' in artwork_builder
    assert "docs/media/portraits/idle_front.png" in artwork_builder
    portrait_renderer = read("tools/render_marketing_portraits.py")
    assert "ActiveOutfitOverlay(" in portrait_renderer
    assert "TemporaryDirectory(" in portrait_renderer
    artwork = ROOT / "installer/artwork"
    assert_image(artwork / "wizard-hero.png", (656, 1256))
    assert hashlib.sha256((artwork / "wizard-hero.png").read_bytes()).hexdigest() == WIZARD_HERO_SHA256
    assert_image(artwork / "wizard-small.png", (512, 512))
    assert hashlib.sha256((artwork / "wizard-small.png").read_bytes()).hexdigest() == WIZARD_SMALL_SHA256
    checkmark = ROOT / "assets/ui/checkmark.svg"
    assert checkmark.is_file()
    assert 'stroke="#ffffff"' in checkmark.read_text(encoding="utf-8")


def test_windows_taskbar_icon_contract() -> None:
    canonical = ROOT / "assets/expressions/idle_front.png"
    png_icon = ROOT / "assets/mohan-taskbar-icon.png"
    windows_icon = ROOT / "assets/mohan-halfbody.ico"
    assert hashlib.sha256(canonical.read_bytes()).hexdigest() == CANONICAL_HALF_BODY_SHA256
    portrait = ROOT / "docs/media/portraits/idle_front.png"
    assert hashlib.sha256(portrait.read_bytes()).hexdigest() == MARKETING_IDLE_PORTRAIT_SHA256
    assert_image(png_icon, (1024, 1024))
    assert hashlib.sha256(png_icon.read_bytes()).hexdigest() == TASKBAR_ICON_PNG_SHA256
    assert hashlib.sha256(windows_icon.read_bytes()).hexdigest() == WINDOWS_ICON_SHA256

    content = windows_icon.read_bytes()
    reserved, image_type, count = struct.unpack_from("<HHH", content)
    assert (reserved, image_type, count) == (0, 1, 10)
    entries: list[tuple[int, int, int, bool]] = []
    for index in range(count):
        entry_offset = 6 + (16 * index)
        width_byte, height_byte, _colors, _reserved = struct.unpack_from(
            "<BBBB",
            content,
            entry_offset,
        )
        width = width_byte or 256
        height = height_byte or 256
        planes, bits, payload_size, payload_offset = struct.unpack_from(
            "<HHII",
            content,
            entry_offset + 4,
        )
        payload_end = payload_offset + payload_size
        assert payload_end <= len(content)
        is_png = content[payload_offset : payload_offset + 8] == (
            b"\x89PNG\r\n\x1a\n"
        )
        assert width == height
        entries.append((width, planes, bits, is_png))
    assert entries == [
        (size, 1, 32, False)
        for size in (256, 128, 96, 64, 48, 40, 32, 24, 20, 16)
    ]

    icon_builder = read("tools/build_app_icon.ps1")
    assert "assets\\expressions\\idle_front.png" in icon_builder
    assert "[string]$Source" in icon_builder
    assert "docs\\media\\portraits\\idle_front.png" in icon_builder
    assert "assets\\mohan.png" not in icon_builder
    assert "icon:auto-resize=256,128,96,64,48,40,32,24,20,16" in icon_builder
    assert not (ROOT / "assets/mohan.png").exists()
    assert not (ROOT / "assets/mohan.ico").exists()
    assert not (
        ROOT / "assets/onboarding/mohan-hero-rain-canonical.webp"
    ).exists()

    dashboard_owner = read("presentation/dashboard_shell.py")
    dashboard_setup = dashboard_owner.split(
        "def _configure_dashboard_window(self) -> None:",
        maxsplit=1,
    )[1].split("\n    def ", maxsplit=1)[0]
    character_owner = read("presentation/companion_visual_dynamics.py")
    assert "QIcon(str(resource_path(APP_ICON_PATH)))" not in (
        dashboard_owner + character_owner
    )
    assert dashboard_setup.index("self.setWindowFlags(") < dashboard_setup.index(
        "self.setWindowIcon(application_icon())"
    )
    character_setup = character_owner.split(
        "def _configure_character_window(self) -> None:",
        maxsplit=1,
    )[1].split("\n    def ", maxsplit=1)[0]
    assert character_setup.index("self.setWindowFlags(") < character_setup.index(
        "self.setWindowIcon(application_icon())"
    )


def test_wix_source_and_localization_contract() -> None:
    wix_source = read("installer/Product.wxs")
    assert_contains(
        wix_source,
        (
            '<Property Id="ARPPRODUCTICON" Value="MohanIcon" />',
            '<Icon Id="MohanIcon" SourceFile="$(var.IconPath)" />',
            'Key="System.AppUserModel.ID"',
            'Value="FlamebladeStudio.MoHanDesktopAssistant"',
            'Language="$(var.ProductLanguage)"',
            'xmlns="http://wixtoolset.org/schemas/v4/wxs"',
            '<Files Directory="INSTALLFOLDER"',
        ),
    )
    shortcut = wix_source.split(
        '<Shortcut Id="ApplicationStartMenuShortcut"',
        maxsplit=1,
    )[1].split("</Shortcut>", maxsplit=1)[0]
    assert 'Icon="' not in shortcut
    assert 'IconIndex="' not in shortcut
    installer_build = read("installer/build_installers.ps1")
    installer_test = read("installer/test_installers.ps1")
    policy = read("installer/LOCALIZATION.md")
    assert '"LICENSE", "THIRD_PARTY_NOTICES.md"' in installer_test
    assert "EXE shortcut target escaped the installed application directory" in (
        installer_test
    )
    assert "EXE shortcut icon does not use the installed MoHan half-body icon" in (
        installer_test
    )
    for locale, lcid in (("en-US", "1033"), ("zh-CN", "2052"), ("ja-JP", "1041")):
        assert_contains(installer_build, (locale, lcid))
        assert locale in policy
        assert locale in installer_test
    expected = {
        "zh-TW": ("950", "已安裝較新版本的 MoHan Desktop Assistant。"),
        "zh-CN": ("936", "已安装较新版本的 MoHan Desktop Assistant。"),
        "en-US": ("1252", "A newer version of MoHan Desktop Assistant is already installed."),
        "ja-JP": ("932", "新しいバージョンの MoHan Desktop Assistant が既にインストールされています。"),
    }
    namespace = {"wix": "http://wixtoolset.org/schemas/v4/wxl"}
    for locale, (codepage, message) in expected.items():
        root = parse_xml(ROOT / f"installer/localization/{locale}.wxl").getroot()
        assert root.attrib["Culture"] == locale
        assert root.attrib["Codepage"] == codepage
        text = root.find("wix:String", namespace)
        assert text is not None
        assert text.attrib == {"Id": "DowngradeErrorMessage", "Value": message}
    assert_contains(
        installer_build,
        (
            "-acceptEula wix7",
            "$Wix msi transform",
            "-t language",
            "-sice ICE91",
            "foreach ($Transform in $Transforms)",
        ),
    )
    assert (
        'Get-Item (Join-Path $ResolvedOutput "*Setup.exe"), $Msi, $Transforms'
        not in installer_build
    )
    for obsolete in ("heat.exe", "candle.exe", "light.exe", "torch.exe"):
        assert obsolete not in installer_build.lower()
    assert "TRANSFORMS=" in installer_test
    assert_contains(
        policy,
        (
            "Taiwan Traditional Chinese base package",
            "MoHan-Desktop-Assistant-<tag>-en-US.mst",
            "MoHan-Desktop-Assistant-<tag>-zh-CN.mst",
            "MoHan-Desktop-Assistant-<tag>-ja-JP.mst",
            "TRANSFORMS=",
            "WiX Toolset 7.0.0",
        ),
    )


def test_packaging_tools_and_public_media() -> None:
    packaging_tools = read("tools/install_windows_packaging_tools.ps1")
    assert_contains(
        packaging_tools,
        (
            "jrsoftware/issrc",
            "gh release verify-asset",
            "Get-AuthenticodeSignature",
            "Pyrsys B\\.V\\.",
            'InnoVersion = "7.0.2"',
            "gh release verify-asset $InnoTag $InnoDownload --repo jrsoftware/issrc",
            'WixVersion = "7.0.0"',
        ),
    )
    for workflow_name in ("windows-ci.yml", "release.yml"):
        workflow = read(f".github/workflows/{workflow_name}")
        assert_contains(
            workflow,
            (
                "install_windows_packaging_tools.ps1",
                '-InnoVersion "7.0.2"',
                '-WixVersion "7.0.0"',
            ),
        )
        toolchain_step = workflow.split(
            "install_windows_packaging_tools.ps1",
            maxsplit=1,
        )[0].rsplit("- name:", maxsplit=1)[-1]
        assert "GH_TOKEN: ${{ github.token }}" in toolchain_step
        assert "choco install wixtoolset" not in workflow
    assert 'GITHUB_ACTIONS -eq "true" -and -not $env:GH_TOKEN' in packaging_tools
    for expression in MARKETING_PORTRAITS:
        # The bare runtime sprite the portrait is composed over, and the
        # composed portrait the README cards embed.
        assert (ROOT / "assets/expressions" / expression).is_file(), expression
        assert_image(ROOT / "docs/media/portraits" / expression, PORTRAIT_SIZE)
    for media in (
        "mohan-hero.png",
        "first-run-wizard.png",
        "voice-modes.png",
        "expressions.png",
        "tasks-and-ideas.png",
        "long-term-memory.png",
        "security-permissions.png",
        "mohan-demo.mp4",
    ):
        assert (ROOT / "docs/media" / media).is_file(), media


def test_readme_language_and_contribution_contract() -> None:
    readme = read("README.md")
    assert "日本語" in readme
    assert "日本語の対応範囲" in readme
    assert "Azure Speech（プレビュー）" in readme
    assert "墨寒的傲嬌工程小劇場 / MoHan's Tsundere Developer Theatre" in readme
    expression_cards = readme.count(
        'width="33%" align="center"><img src="docs/media/portraits/'
    )
    assert 'src="assets/expressions/' not in readme
    support_cards = readme.count(
        'width="33%" align="center" valign="top"><img src="docs/media/support-'
    )
    assert expression_cards >= MIN_EXPRESSION_CARD_COUNT
    assert support_cards == SUPPORT_CARD_COUNT
    assert expression_cards + support_cards >= MIN_TOTAL_CARD_COUNT
    assert_contains(
        readme,
        (
            "妾才沒有等你的 Star",
            "若再補上測試",
            "你願意送來 PR",
            "未經測試便想合併",
            "全數綠燈",
            "Bug 可以明日再查",
        ),
    )


def metadata_command(artifacts: Path, tag: str = TAG) -> list[str]:
    return [
        sys.executable,
        str(ROOT / "tools/create_release_metadata.py"),
        "--artifacts",
        str(artifacts),
        "--tag",
        tag,
        "--repository",
        REPOSITORY,
    ]


def run_metadata(artifacts: Path, tag: str = TAG) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        metadata_command(artifacts, tag),
        check=False,
        capture_output=True,
        text=True,
    )


def seed_release_artifacts(artifacts: Path) -> None:
    payloads = {
        "Windows-x64-Setup.exe": b"exe",
        "Windows-x64.msi": b"msi",
        "Windows-x64.zip": b"zip",
        "macOS-arm64-Preview.dmg": b"dmg",
        "macOS-x86_64-Preview.dmg": b"intel-dmg",
        "Linux-x86_64-Preview.AppImage": b"appimage",
    }
    for suffix, payload in payloads.items():
        (artifacts / f"{PREFIX}-{suffix}").write_bytes(payload)
    for locale in ("en-US", "zh-CN", "ja-JP"):
        (artifacts / f"{PREFIX}-{locale}.mst").write_bytes(locale.encode("ascii"))
    (artifacts / f"{PREFIX}-SBOM.cdx.json").write_text("{}", encoding="utf-8")


def assert_metadata_rejections(artifacts: Path) -> None:
    intel = artifacts / f"{PREFIX}-macOS-x86_64-Preview.dmg"
    intel.unlink()
    assert run_metadata(artifacts).returncode != 0
    intel.write_bytes(b"intel-dmg")
    assert run_metadata(artifacts, "v2.2.0").returncode != 0

    appimage = artifacts / f"{PREFIX}-Linux-x86_64-Preview.AppImage"
    mismatch = artifacts / (
        "MoHan-Desktop-Assistant-v2.3.0-rc.9-Linux-x86_64-Preview.AppImage"
    )
    appimage.rename(mismatch)
    assert run_metadata(artifacts).returncode != 0
    mismatch.rename(appimage)


def load_and_assert_manifest(artifacts: Path) -> dict[str, object]:
    path = artifacts / f"{PREFIX}-update.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    assert manifest["schema"] == 1
    installers = manifest["installers"]
    assert {
        (item["kind"], item["platform"], item["architecture"])
        for item in installers
    } == {
        ("exe", "windows", "x86_64"),
        ("msi", "windows", "x86_64"),
        ("mst", "windows", "x86_64"),
        ("zip", "windows", "x86_64"),
        ("dmg", "macos", "arm64"),
        ("dmg", "macos", "x86_64"),
        ("appimage", "linux", "x86_64"),
    }
    maturity = {
        (item["kind"], item["architecture"]): item["maturity"]
        for item in installers
        if item["kind"] != "mst"
    }
    assert maturity == {
        ("exe", "x86_64"): "complete",
        ("msi", "x86_64"): "complete",
        ("zip", "x86_64"): "complete",
        ("dmg", "arm64"): "preview",
        ("dmg", "x86_64"): "preview",
        ("appimage", "x86_64"): "preview",
    }
    assert {
        item["locale"] for item in installers if item["kind"] == "mst"
    } == {"en-US", "zh-CN", "ja-JP"}
    return manifest


def assert_checksum_catalog(artifacts: Path) -> None:
    canonical = artifacts / f"{PREFIX}-SHA256SUMS.txt"
    compatibility = artifacts / f"{PREFIX}-SHA256.txt"
    checksums = canonical.read_text(encoding="ascii")
    assert compatibility.read_text(encoding="ascii") == checksums
    assert f"{PREFIX}-update.json" in checksums
    assert f"{PREFIX}-macOS-arm64-Preview.dmg" in checksums
    assert f"{PREFIX}-macOS-x86_64-Preview.dmg" in checksums
    for suffix in ("Setup.exe", ".msi", ".zip", ".dmg", ".AppImage"):
        assert suffix in checksums


def assert_release_website_block(manifest: dict[str, object]) -> None:
    block = release_block(manifest, manifest["release_url"])
    assert START_MARKER in block and END_MARKER in block
    assert_contains(
        block,
        (
            "SHA256",
            "Download EXE",
            "macOS DMG（功能受限 Preview）",
            "Linux AppImage（功能受限 Preview）",
            "not feature parity",
            "MoHan Desktop Assistant",
            "墨寒的傲嬌工程小劇場",
            "Contribute a pull request",
            "ko-fi.com/flamebladestudio",
            'src="https://raw.githubusercontent.com/',
        ),
    )
    assert "buymeacoffee.com" not in block.lower()
    assert "paypal.com/paypalme" not in block.lower()
    assert "wp-content/uploads" not in block
    assert block.count('class="mohan-scene"') >= SCENE_COUNT
    assert block.count('loading="eager"') == SCENE_COUNT

    initial = "<p>保留的網站內容</p>"
    first = replace_managed_block(initial, block)
    second = replace_managed_block(first, block.replace(VERSION, NEXT_VERSION))
    assert second.count(START_MARKER) == 1
    assert second.count(END_MARKER) == 1
    assert "保留的網站內容" in second
    assert NEXT_VERSION in second


def test_portable_website_block() -> None:
    portable = release_block(
        {
            "version": "2.0.14-rc.2",
            "tag": "v2.0.14-rc.2",
            "installers": [
                {
                    "kind": "zip",
                    "url": "https://example.invalid/mohan.zip",
                    "sha256": "0" * 64,
                }
            ],
        },
        "https://example.invalid/release",
    )
    assert "Windows ZIP 免安裝版" in portable
    assert "Download ZIP" in portable


def test_release_metadata_and_website_automation() -> None:
    with tempfile.TemporaryDirectory() as temp:
        artifacts = Path(temp)
        seed_release_artifacts(artifacts)
        result = run_metadata(artifacts)
        assert result.returncode == 0, result.stderr
        assert_metadata_rejections(artifacts)
        manifest = load_and_assert_manifest(artifacts)
        assert_checksum_catalog(artifacts)
        assert_release_website_block(manifest)


def main() -> None:
    test_version_runtime_and_evidence_policy()
    test_inno_setup_and_artwork_contract()
    test_windows_taskbar_icon_contract()
    test_wix_source_and_localization_contract()
    test_packaging_tools_and_public_media()
    test_readme_media_provenance()
    test_readme_media_provenance_rejects_stale_auto_generation()
    test_readme_media_generation_tools_use_runtime_composition()
    test_readme_language_and_contribution_contract()
    test_portable_website_block()
    test_release_metadata_and_website_automation()
    print("RELEASE_INSTALLER_WEBSITE_AUTOMATION_OK")


if __name__ == "__main__":
    main()
