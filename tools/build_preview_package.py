from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import json
lazy import os
lazy import platform
lazy import re
lazy import shutil
lazy import stat
lazy import subprocess
lazy import sys
lazy import tempfile
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION_PATTERN = re.compile(
    r"^[0-9]+\.[0-9]+\.[0-9]+(?:-rc\.(?:0|[1-9][0-9]*))?$"
)
APPIMAGETOOL_SOURCE_COMMIT = "8c8c91f762b412a19f4e8d2c4b35afb98f2d7c81"
APPIMAGETOOL_ASSET_ID = "324406882"
APPIMAGETOOL_SHA256 = (
    "a6d71e2b6cd66f8e8d16c37ad164658985e0cf5fcaa950c90a482890cb9d13e0"
)
APPIMAGETOOL_URL = (
    "https://github.com/AppImage/appimagetool/releases/download/continuous/"
    "appimagetool-x86_64.AppImage"
)
POSE_ATLAS_ROOT = ROOT / "assets" / "pose-atlas" / "v4"


def _run(command: list[str], *, env: dict[str, str] | None = None) -> None:
    subprocess.run(command, cwd=ROOT, env=env, check=True)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_version(version: str) -> None:
    if not VERSION_PATTERN.fullmatch(version):
        raise ValueError(
            "Preview packages require an N.N.N or N.N.N-rc.N version"
        )


def _release_pose_atlas_root(required: bool) -> Path | None:
    if not required:
        return None
    audit = POSE_ATLAS_ROOT / "release-audits.json"
    if not audit.is_file():
        raise FileNotFoundError(
            "The formal Preview release requires audited PoseAtlas assets: "
            f"{audit}"
        )
    return POSE_ATLAS_ROOT


def _write_build_info(path: Path, version: str, target: str) -> None:
    jit = getattr(sys, "_jit", None)
    if not jit or not jit.is_available() or not jit.is_enabled():
        raise RuntimeError(
            "Preview packages require Python 3.15 with JIT enabled by default"
        )
    path.write_text(
        json.dumps(
            {
                "version": version,
                "repository": "hitoshic1982/MoHan-PC-Desktop-Assistant",
                "python": platform.python_version(),
                "jit_default": True,
                "target": target,
                "maturity": "preview",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _pyinstaller(
    *,
    name: str,
    version: str,
    target: str,
    icon: Path,
    temp_root: Path,
    pose_atlas_root: Path | None,
) -> Path:
    build_info = temp_root / "build-info.json"
    _write_build_info(build_info, version, target)
    dist = temp_root / "dist"
    data_separator = os.pathsep
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        name,
        "--distpath",
        str(dist),
        "--workpath",
        str(temp_root / "build"),
        "--specpath",
        str(temp_root / "spec"),
        "--paths",
        str(ROOT),
        "--icon",
        str(icon),
        "--add-data",
        f"{ROOT / 'installer' / 'artwork' / 'wizard-hero.png'}{data_separator}installer/artwork",
        "--add-data",
        f"{ROOT / 'installer' / 'artwork' / 'wizard-small.png'}{data_separator}installer/artwork",
        "--add-data",
        f"{ROOT / 'LICENSE'}{data_separator}.",
        "--add-data",
        f"{ROOT / 'THIRD_PARTY_NOTICES.md'}{data_separator}.",
        "--add-data",
        f"{build_info}{data_separator}.",
    ]
    if pose_atlas_root is not None:
        command.extend(
            [
                "--add-data",
                f"{pose_atlas_root}{data_separator}assets/pose-atlas/v4",
            ]
        )
    if target == "macos":
        command.extend(
            [
                "--osx-bundle-identifier",
                "tw.com.flamebladestudio.mohan.preview",
            ]
        )
    command.append(str(ROOT / "presentation" / "preview_app.py"))
    _run(command)
    return dist


def _create_icns(temp_root: Path) -> Path:
    source = ROOT / "installer" / "artwork" / "wizard-small.png"
    iconset = temp_root / "MoHanPreview.iconset"
    iconset.mkdir()
    for size in (16, 32, 128, 256, 512):
        _run(
            [
                "sips",
                "-z",
                str(size),
                str(size),
                str(source),
                "--out",
                str(iconset / f"icon_{size}x{size}.png"),
            ]
        )
        doubled = size * 2
        if doubled <= 1024:
            _run(
                [
                    "sips",
                    "-z",
                    str(doubled),
                    str(doubled),
                    str(source),
                    "--out",
                    str(iconset / f"icon_{size}x{size}@2x.png"),
                ]
            )
    destination = temp_root / "MoHanPreview.icns"
    _run(["iconutil", "-c", "icns", str(iconset), "-o", str(destination)])
    return destination


def _preview_notice() -> str:
    return """MoHan Desktop Assistant — macOS/Linux Limited Preview

繁體中文：此預覽包只驗證啟動、四語介面、平台路徑與安全停用邊界；不是 Windows 完整版。
简体中文：此预览包只验证启动、四语界面、平台路径与安全停用边界；不是 Windows 完整版。
English: This limited Preview validates launch, four-language UI, platform paths, and fail-closed boundaries. It is not feature parity with Windows.
日本語：この限定 Preview は起動、四言語画面、保存先、安全な無効化を確認するもので、Windows 完全版と同等ではありません。
Voice, cloud connectors, system tools, autostart, and secret entry remain disabled until verified on real devices.
"""


def build_macos(version: str, output_dir: Path, *, require_pose_atlas: bool) -> Path:
    if sys.platform != "darwin":
        raise RuntimeError("macOS DMG packages must be built on a macOS runner")
    reported_architecture = platform.machine().lower()
    architecture = {
        "aarch64": "arm64",
        "arm64": "arm64",
        "amd64": "x86_64",
        "x86_64": "x86_64",
    }.get(reported_architecture)
    if architecture is None:
        raise RuntimeError(
            f"This verified macOS pipeline supports arm64 and x86_64 only: "
            f"{reported_architecture or 'unknown'}"
        )
    with tempfile.TemporaryDirectory(prefix="mohan-preview-macos-") as raw:
        temp_root = Path(raw)
        pose_atlas_root = _release_pose_atlas_root(require_pose_atlas)
        icon = _create_icns(temp_root)
        dist = _pyinstaller(
            name="MoHan Desktop Assistant Preview",
            version=version,
            target="macos",
            icon=icon,
            temp_root=temp_root,
            pose_atlas_root=pose_atlas_root,
        )
        app = dist / "MoHan Desktop Assistant Preview.app"
        if not app.is_dir():
            raise RuntimeError(f"Expected app bundle was not created: {app}")
        stage = temp_root / "dmg"
        stage.mkdir()
        shutil.copytree(app, stage / app.name)
        os.symlink("/Applications", stage / "Applications")
        (stage / "PREVIEW-NOTICE.txt").write_text(
            _preview_notice(), encoding="utf-8"
        )
        shutil.copy2(ROOT / "LICENSE", stage / "LICENSE.txt")
        shutil.copy2(
            ROOT / "THIRD_PARTY_NOTICES.md",
            stage / "THIRD_PARTY_NOTICES.md",
        )
        output = output_dir / (
            f"MoHan-Desktop-Assistant-v{version}-macOS-{architecture}-Preview.dmg"
        )
        output.unlink(missing_ok=True)
        _run(
            [
                "hdiutil",
                "create",
                "-volname",
                "MoHan Desktop Assistant Preview",
                "-srcfolder",
                str(stage),
                "-format",
                "UDZO",
                "-ov",
                str(output),
            ]
        )
        return output


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8", newline="\n")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def build_linux(
    version: str,
    output_dir: Path,
    appimagetool: Path,
    *,
    require_pose_atlas: bool,
) -> Path:
    if not sys.platform.startswith("linux"):
        raise RuntimeError("Linux AppImage packages must be built on Linux")
    architecture = platform.machine().lower()
    if architecture not in {"x86_64", "amd64"}:
        raise RuntimeError(f"This verified AppImage pipeline is x86_64 only: {architecture}")
    if not appimagetool.is_file():
        raise FileNotFoundError(f"Pinned appimagetool is missing: {appimagetool}")
    actual_hash = _sha256(appimagetool)
    if actual_hash != APPIMAGETOOL_SHA256:
        raise RuntimeError(
            "appimagetool SHA256 mismatch; refusing an unverified build tool"
        )

    with tempfile.TemporaryDirectory(prefix="mohan-preview-linux-") as raw:
        temp_root = Path(raw)
        pose_atlas_root = _release_pose_atlas_root(require_pose_atlas)
        icon = ROOT / "installer" / "artwork" / "wizard-small.png"
        dist = _pyinstaller(
            name="mohan-preview",
            version=version,
            target="linux",
            icon=icon,
            temp_root=temp_root,
            pose_atlas_root=pose_atlas_root,
        )
        bundle = dist / "mohan-preview"
        executable = bundle / "mohan-preview"
        if not executable.is_file():
            raise RuntimeError(f"Expected Linux bundle was not created: {bundle}")

        app_dir = temp_root / "MoHanPreview.AppDir"
        app_dir.mkdir()
        shutil.copytree(bundle, app_dir / "usr" / "lib" / "mohan-preview")
        _write_executable(
            app_dir / "AppRun",
            "#!/bin/sh\n"
            'APPDIR="$(dirname "$(readlink -f "$0")")"\n'
            'exec "$APPDIR/usr/lib/mohan-preview/mohan-preview" "$@"\n',
        )
        desktop = """[Desktop Entry]
Type=Application
Name=MoHan Desktop Assistant Preview
Name[zh_TW]=墨寒桌面陪伴工作助理 Preview
Name[zh_CN]=墨寒桌面陪伴工作助手 Preview
Name[ja]=墨寒デスクトップアシスタント Preview
Comment=Limited cross-platform preview; unsupported capabilities remain disabled
Exec=mohan-preview
Icon=mohan-preview
Categories=Utility;
Terminal=false
X-AppImage-Version=PREVIEW
"""
        (app_dir / "mohan-preview.desktop").write_text(
            desktop, encoding="utf-8", newline="\n"
        )
        shutil.copy2(icon, app_dir / "mohan-preview.png")
        (app_dir / "PREVIEW-NOTICE.txt").write_text(
            _preview_notice(), encoding="utf-8"
        )
        notice_dir = app_dir / "usr" / "share" / "doc" / "mohan-desktop-assistant"
        notice_dir.mkdir(parents=True)
        shutil.copy2(ROOT / "LICENSE", notice_dir / "LICENSE.txt")
        shutil.copy2(
            ROOT / "THIRD_PARTY_NOTICES.md",
            notice_dir / "THIRD_PARTY_NOTICES.md",
        )

        output = output_dir / (
            f"MoHan-Desktop-Assistant-v{version}-Linux-x86_64-Preview.AppImage"
        )
        output.unlink(missing_ok=True)
        environment = os.environ.copy()
        environment.update(
            {
                "ARCH": "x86_64",
                "APPIMAGE_EXTRACT_AND_RUN": "1",
            }
        )
        _run([str(appimagetool), str(app_dir), str(output)], env=environment)
        output.chmod(
            output.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        )
        return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=("macos", "linux"), required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--appimagetool", type=Path)
    parser.add_argument("--require-pose-atlas", action="store_true")
    args = parser.parse_args()
    _validate_version(args.version)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.platform == "macos":
        package = build_macos(
            args.version,
            args.output_dir,
            require_pose_atlas=args.require_pose_atlas,
        )
    else:
        if args.appimagetool is None:
            raise ValueError("--appimagetool is required for Linux packages")
        package = build_linux(
            args.version,
            args.output_dir,
            args.appimagetool,
            require_pose_atlas=args.require_pose_atlas,
        )
    print(package)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
