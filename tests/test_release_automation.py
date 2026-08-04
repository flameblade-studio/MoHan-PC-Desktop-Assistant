from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from PySide6.QtGui import QImage

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.sync_wordpress_download_page import (
    END_MARKER,
    START_MARKER,
    release_block,
    replace_managed_block,
)


def main() -> None:
    current_version = "2.1.0-rc.1"
    version_info = (ROOT / "version_info.py").read_text(encoding="utf-8")
    assert f'FALLBACK_VERSION = "{current_version}"' in version_info

    current_docs = {
        name: (ROOT / name).read_text(encoding="utf-8")
        for name in (
            "README.md",
            "README.zh-CN.md",
            "README.ja.md",
            "QUICKSTART.md",
            "PUBLISHING.md",
            "docs/PYTHON-3.14-MIGRATION.md",
        )
    }
    for name, content in current_docs.items():
        assert current_version in content, f"current release missing from {name}"
    for name in ("README.md", "README.zh-CN.md", "QUICKSTART.md"):
        assert "2.0.14-rc.3.exe" not in current_docs[name]
    assert "RC4" not in current_docs["docs/PYTHON-3.14-MIGRATION.md"]

    build_script = (ROOT / "build.ps1").read_text(encoding="utf-8")
    assert "Python 3.14.x" in build_script
    assert "python = $PythonVersion" in build_script
    for workflow_name in (
        "windows-ci.yml",
        "security-audit.yml",
        "release.yml",
    ):
        workflow = (
            ROOT / ".github" / "workflows" / workflow_name
        ).read_text(encoding="utf-8")
        assert 'python-version: "3.14"' in workflow
        assert 'python-version: "3.12"' not in workflow

    inno_script = (ROOT / "installer" / "mohan.iss").read_text(encoding="utf-8")
    traditional_messages = ROOT / "installer" / "languages" / "ChineseTraditional.isl"
    simplified_messages = ROOT / "installer" / "languages" / "ChineseSimplified.isl"
    assert traditional_messages.is_file()
    assert traditional_messages.stat().st_size > 20_000
    assert simplified_messages.is_file()
    assert simplified_messages.stat().st_size > 20_000
    assert "compiler:Languages\\ChineseTraditional.isl" not in inno_script
    assert "{#TraditionalChineseMessages}" in inno_script
    assert "{#SimplifiedChineseMessages}" in inno_script
    assert 'Name: "chinesetraditional"' in inno_script
    assert 'Name: "chinesesimplified"' in inno_script
    assert 'Name: "english"' in inno_script
    assert 'Name: "japanese"' in inno_script
    assert "japanese.CreateDesktopIcon" in inno_script
    assert "WizardImageFile={#WizardImagePath}" in inno_script
    assert "WizardSmallImageFile={#WizardSmallImagePath}" in inno_script
    assert "DisableWelcomePage=no" in inno_script
    assert inno_script.count(
        'AppUserModelID: "FlamebladeStudio.MoHanDesktopAssistant"'
    ) == 2
    assert inno_script.count('IconFilename: "{#IconPath}"') == 2
    installer_artwork = ROOT / "installer" / "artwork"
    wizard_hero = QImage(str(installer_artwork / "wizard-hero.png"))
    wizard_small = QImage(str(installer_artwork / "wizard-small.png"))
    assert not wizard_hero.isNull()
    assert (wizard_hero.width(), wizard_hero.height()) == (656, 1256)
    assert not wizard_small.isNull()
    assert (wizard_small.width(), wizard_small.height()) == (512, 512)
    checkmark = ROOT / "assets" / "ui" / "checkmark.svg"
    assert checkmark.is_file()
    assert 'stroke="#ffffff"' in checkmark.read_text(encoding="utf-8")

    wix_source = (ROOT / "installer" / "Product.wxs").read_text(encoding="utf-8")
    assert 'Icon="MohanIcon"' in wix_source
    assert 'IconIndex="0"' in wix_source
    localization_policy = (ROOT / "installer" / "LOCALIZATION.md").read_text(
        encoding="utf-8"
    )
    assert 'Language="$(var.ProductLanguage)"' in wix_source
    installer_build = (
        ROOT / "installer" / "build_installers.ps1"
    ).read_text(encoding="utf-8")
    installer_test = (
        ROOT / "installer" / "test_installers.ps1"
    ).read_text(encoding="utf-8")
    for locale, lcid in (
        ("en-US", "1033"),
        ("zh-CN", "2052"),
        ("ja-JP", "1041"),
    ):
        assert locale in installer_build
        assert lcid in installer_build
        assert locale in localization_policy
        assert locale in installer_test
    expected_localization = {
        "zh-TW": ("950", "已安裝較新版本的 MoHan Desktop Assistant。"),
        "zh-CN": ("936", "已安装较新版本的 MoHan Desktop Assistant。"),
        "en-US": ("1252", "A newer version of MoHan Desktop Assistant is already installed."),
        "ja-JP": ("932", "新しいバージョンの MoHan Desktop Assistant が既にインストールされています。"),
    }
    namespace = {"wix": "http://schemas.microsoft.com/wix/2006/localization"}
    for locale, (codepage, message) in expected_localization.items():
        source = ROOT / "installer" / "localization" / f"{locale}.wxl"
        root = ET.parse(source).getroot()
        assert root.attrib["Culture"] == locale
        assert root.attrib["Codepage"] == codepage
        text = root.find("wix:String", namespace)
        assert text is not None
        assert text.attrib["Id"] == "DowngradeErrorMessage"
        assert text.text == message
    assert "torch.exe" in installer_build
    assert "-t language" in installer_build
    assert "foreach ($Transform in $Transforms)" in installer_build
    assert 'Get-Item (Join-Path $ResolvedOutput "*Setup.exe"), $Msi, $Transforms' not in installer_build
    assert "TRANSFORMS=" in installer_test
    assert "Taiwan Traditional Chinese base package" in localization_policy
    assert "MoHan-Desktop-Assistant-<tag>-en-US.mst" in localization_policy
    assert "MoHan-Desktop-Assistant-<tag>-zh-CN.mst" in localization_policy
    assert "MoHan-Desktop-Assistant-<tag>-ja-JP.mst" in localization_policy
    assert "TRANSFORMS=" in localization_policy
    for expression in (
        "proud_front.png",
        "thinking_front.png",
        "shy_cute_front.png",
        "mock_hit_front.png",
        "gentle_smile_front.png",
        "worried_front.png",
    ):
        assert (ROOT / "assets" / "expressions" / expression).is_file(), expression
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
        assert (ROOT / "docs" / "media" / media).is_file(), media

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    japanese_readme = (ROOT / "README.ja.md").read_text(encoding="utf-8")
    assert "日本語" in readme and "README.ja.md" in readme
    assert "日本語の対応範囲" in japanese_readme
    assert "Azure Speech（プレビュー）" in japanese_readme
    assert "墨寒的傲嬌工程小劇場 / MoHan's Tsundere Developer Theatre" in readme
    expression_cards = readme.count(
        'width="33%" align="center"><img src="assets/expressions/'
    )
    support_cards = readme.count(
        'width="33%" align="center"><img src="docs/media/support-'
    )
    assert expression_cards >= 6
    assert support_cards == 3
    assert expression_cards + support_cards >= 9
    for line in (
        "妾才沒有等你的 Star",
        "若再補上測試",
        "你願意送來 PR",
        "未經測試便想合併",
        "全數綠燈",
        "Bug 可以明日再查",
    ):
        assert line in readme

    with tempfile.TemporaryDirectory() as temp:
        artifacts = Path(temp)
        (artifacts / "MoHan-v9-Windows-x64-Setup.exe").write_bytes(b"exe")
        (artifacts / "MoHan-v9-Windows-x64.msi").write_bytes(b"msi")
        (artifacts / "MoHan-v9-Windows-x64.zip").write_bytes(b"zip")
        (artifacts / "MoHan-v9-SBOM.cdx.json").write_text("{}", encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools" / "create_release_metadata.py"),
                "--artifacts",
                str(artifacts),
                "--tag",
                "v2.0.15",
                "--repository",
                "hitoshic1982/MoHan-PC-Desktop-Assistant",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        manifest_path = artifacts / "MoHan-Desktop-Assistant-v2.0.15-update.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["schema"] == 1
        assert {item["kind"] for item in manifest["installers"]} == {"exe", "msi"}
        checksums = (artifacts / "MoHan-Desktop-Assistant-v2.0.15-SHA256.txt").read_text()
        assert manifest_path.name in checksums
        assert "Setup.exe" in checksums and ".msi" in checksums

        block = release_block(manifest, manifest["release_url"])
        assert START_MARKER in block and END_MARKER in block
        assert "SHA256" in block and "Download EXE" in block
        assert "MoHan Desktop Assistant" in block
        assert "墨寒的傲嬌工程小劇場" in block
        assert "Contribute a pull request" in block
        assert "buymeacoffee.com/flameblade_studio" in block
        assert "paypal.com/paypalme/flamebladestudio" in block
        assert 'src="https://raw.githubusercontent.com/' in block
        assert "wp-content/uploads" not in block
        assert block.count('class="mohan-scene"') >= 6
        assert block.count('loading="eager"') == 6
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
        assert "ZIP 可攜版（候選版）" in portable
        assert "Download ZIP" in portable
        initial = "<p>保留的網站內容</p>"
        first = replace_managed_block(initial, block)
        second = replace_managed_block(first, block.replace("2.0.15", "2.0.16"))
        assert second.count(START_MARKER) == 1
        assert second.count(END_MARKER) == 1
        assert "保留的網站內容" in second
        assert "2.0.16" in second

    print("RELEASE_INSTALLER_WEBSITE_AUTOMATION_OK")


if __name__ == "__main__":
    main()
