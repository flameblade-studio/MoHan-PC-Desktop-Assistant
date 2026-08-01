from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

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
    inno_script = (ROOT / "installer" / "mohan.iss").read_text(encoding="utf-8")
    traditional_messages = ROOT / "installer" / "languages" / "ChineseTraditional.isl"
    assert traditional_messages.is_file()
    assert traditional_messages.stat().st_size > 20_000
    assert "compiler:Languages\\ChineseTraditional.isl" not in inno_script
    assert "{#TraditionalChineseMessages}" in inno_script
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
        assert "raw.githubusercontent.com" in block
        assert "wp-content/uploads" not in block
        assert block.count('class="mohan-scene"') >= 6
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
