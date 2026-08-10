from __future__ import annotations

lazy import hashlib
lazy import json
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

lazy from tools.sync_wordpress_download_page import (
    END_MARKER,
    START_MARKER,
    release_block,
    replace_managed_block,
)
lazy from version_info import FALLBACK_VERSION

VERSION = FALLBACK_VERSION
VERSION_PREFIX, CANDIDATE_NUMBER = VERSION.rsplit(".", maxsplit=1)
NEXT_VERSION = f"{VERSION_PREFIX}.{int(CANDIDATE_NUMBER) + 1}"
TAG = f"v{VERSION}"
PREFIX = f"MoHan-Desktop-Assistant-{TAG}"
REPOSITORY = "hitoshic1982/MoHan-PC-Desktop-Assistant"


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
    assert f'FALLBACK_VERSION = "{VERSION}"' in read("version_info.py")
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
    for name, content in current_docs.items():
        assert VERSION in content, f"current release missing from {name}"
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
            "True:True",
            "JIT enabled by default",
            "jit_default = $true",
            "Python 3.15.0rc1",
            "platform.python_version()",
            "python = $PythonVersion",
            '--add-data "LICENSE;."',
            '--add-data "THIRD_PARTY_NOTICES.md;."',
        ),
    )
    for workflow_name in ("windows-ci.yml", "release.yml"):
        workflow = read(f".github/workflows/{workflow_name}")
        assert 'python-version: "3.15.0-rc.1"' in workflow
        assert 'python-version: "3.12"' not in workflow
        assert 'FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: "true"' in workflow

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
            "Expected exactly one literal FALLBACK_VERSION",
            'source_version="${source_versions[0]}"',
            "PACKAGED_JIT_DEFAULT_OK",
            "tools/profile_mohan_tachyon.py",
            "tools/validate_release_sboms.py",
            "--spec-version 1.7",
            "--output-reproducible",
            "SBOM-Validation.json",
            "Performance-Evidence.zip",
            "Performance-Summary.json",
        ),
    )


def test_inno_setup_and_artwork_contract() -> None:
    inno_script = read("installer/mohan.iss")
    for language in ("ChineseTraditional", "ChineseSimplified"):
        messages = ROOT / "installer" / "languages" / f"{language}.isl"
        assert messages.is_file() and messages.stat().st_size > 20_000
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
        ),
    )
    assert inno_script.count(
        'AppUserModelID: "FlamebladeStudio.MoHanDesktopAssistant"'
    ) == 2
    installed_icon = 'IconFilename: "{app}\\assets\\mohan-halfbody.ico"'
    assert inno_script.count(installed_icon) == 2
    assert 'IconFilename: "{#IconPath}"' not in inno_script

    canonical = ROOT / "assets/onboarding/mohan-hero-rain-canonical.webp"
    assert_image(canonical, (1111, 1416))
    assert hashlib.sha256(canonical.read_bytes()).hexdigest() == (
        "c5dd52425706ee9e2824a8ce99a483947e0a2f55c0658bd6939cb91cc0a509ed"
    )
    assert "mohan-hero-rain-canonical.webp" in read("app.py")
    assert "mohan-hero-rain-canonical.webp" in read(
        "tools/build_installer_artwork.py"
    )
    artwork = ROOT / "installer/artwork"
    assert_image(artwork / "wizard-hero.png", (656, 1256))
    assert_image(artwork / "wizard-small.png", (512, 512))
    checkmark = ROOT / "assets/ui/checkmark.svg"
    assert checkmark.is_file()
    assert 'stroke="#ffffff"' in checkmark.read_text(encoding="utf-8")


def test_windows_taskbar_icon_contract() -> None:
    canonical = ROOT / "docs/media/desktop-character.png"
    png_icon = ROOT / "assets/mohan-taskbar-icon.png"
    windows_icon = ROOT / "assets/mohan-halfbody.ico"
    assert hashlib.sha256(canonical.read_bytes()).hexdigest() == (
        "e58d1bd7fca01baf3d834f167bf301650bc1711d7ddba9851ff35798dd8f5098"
    )
    assert_image(png_icon, (1024, 1024))
    assert hashlib.sha256(png_icon.read_bytes()).hexdigest() == (
        "f9c1cf5fdc8250bddc2aad68076faf38de9121ae60ca20dd3bfbbd30cb2545d2"
    )
    assert hashlib.sha256(windows_icon.read_bytes()).hexdigest() == (
        "8db0306f18f838def968636d6675c31c234f588f9b4c4837ef4de3e5239d43f8"
    )

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
    assert "docs\\media\\desktop-character.png" in icon_builder
    assert "assets\\mohan.png" not in icon_builder
    assert "icon:auto-resize=256,128,96,64,48,40,32,24,20,16" in icon_builder
    assert not (ROOT / "assets/mohan.png").exists()

    app = read("app.py")
    dashboard_setup = app.split(
        "def _configure_dashboard_window(self) -> None:",
        maxsplit=1,
    )[1].split("\n    def ", maxsplit=1)[0]
    assert "QIcon(str(resource_path(APP_ICON_PATH)))" not in app
    assert dashboard_setup.index("self.setWindowFlags(") < dashboard_setup.index(
        "self.setWindowIcon(application_icon())"
    )


def test_wix_source_and_localization_contract() -> None:
    wix_source = read("installer/Product.wxs")
    assert_contains(
        wix_source,
        (
            'Icon="MohanIcon"',
            'IconIndex="0"',
            'Key="System.AppUserModel.ID"',
            'Value="FlamebladeStudio.MoHanDesktopAssistant"',
            'Language="$(var.ProductLanguage)"',
            'xmlns="http://wixtoolset.org/schemas/v4/wxs"',
            '<Files Directory="INSTALLFOLDER"',
        ),
    )
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
    for expression in (
        "proud_front.png",
        "thinking_front.png",
        "shy_cute_front.png",
        "mock_hit_front.png",
        "gentle_smile_front.png",
        "worried_front.png",
    ):
        assert (ROOT / "assets/expressions" / expression).is_file(), expression
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
        'width="33%" align="center"><img src="assets/expressions/'
    )
    support_cards = readme.count(
        'width="33%" align="center" valign="top"><img src="docs/media/support-'
    )
    assert expression_cards >= 6
    assert support_cards == 3
    assert expression_cards + support_cards >= 9
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
    assert block.count('class="mohan-scene"') >= 6
    assert block.count('loading="eager"') == 6

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
    test_readme_language_and_contribution_contract()
    test_portable_website_block()
    test_release_metadata_and_website_automation()
    print("RELEASE_INSTALLER_WEBSITE_AUTOMATION_OK")


if __name__ == "__main__":
    main()
