from __future__ import annotations

lazy import argparse
lazy import os
lazy import stat
lazy import subprocess
lazy import tempfile
lazy from pathlib import Path

EXPECTED = "PREVIEW_PACKAGE_SMOKE_OK"


def _require_license(path: Path) -> None:
    if not path.is_file() or "MIT License" not in path.read_text(
        encoding="utf-8"
    ):
        raise RuntimeError(f"Packaged MIT license is missing or invalid: {path}")


def _run(
    executable: Path,
    output: Path,
    *,
    expected_version: str,
    environment: dict[str, str],
) -> None:
    jit_output = output.with_name("jit-default.txt")
    result = subprocess.run(
        [
            str(executable),
            f"--preview-smoke-output={output}",
            f"--preview-expected-version={expected_version}",
            f"--jit-status-output={jit_output}",
        ],
        env=environment,
        check=False,
        timeout=90,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Preview smoke process exited with {result.returncode}")
    if not output.is_file() or output.read_text(encoding="utf-8") != EXPECTED:
        raise RuntimeError("Preview smoke marker was not created correctly")
    if (
        not jit_output.is_file()
        or jit_output.read_text(encoding="utf-8") != "PACKAGED_JIT_DEFAULT_OK"
    ):
        raise RuntimeError("Preview package did not enable Python 3.15 JIT by default")


def smoke_macos(package: Path, expected_version: str) -> None:
    with tempfile.TemporaryDirectory(prefix="mohan-preview-mount-") as raw:
        mount = Path(raw) / "mount"
        mount.mkdir()
        subprocess.run(
            [
                "hdiutil",
                "attach",
                str(package),
                "-mountpoint",
                str(mount),
                "-nobrowse",
                "-readonly",
            ],
            check=True,
        )
        try:
            apps = sorted(mount.glob("*.app"))
            if len(apps) != 1:
                raise RuntimeError(f"Expected one app in DMG, found {len(apps)}")
            _require_license(mount / "LICENSE.txt")
            _require_license(apps[0] / "Contents" / "Resources" / "LICENSE")
            if not (mount / "THIRD_PARTY_NOTICES.md").is_file():
                raise RuntimeError("DMG omitted third-party notices")
            executables = [
                path
                for path in (apps[0] / "Contents" / "MacOS").iterdir()
                if path.is_file() and os.access(path, os.X_OK)
            ]
            if len(executables) != 1:
                raise RuntimeError(
                    f"Expected one app executable, found {len(executables)}"
                )
            output = Path(raw) / "smoke.txt"
            environment = os.environ.copy()
            environment["QT_QPA_PLATFORM"] = "offscreen"
            _run(
                executables[0],
                output,
                expected_version=expected_version,
                environment=environment,
            )
        finally:
            subprocess.run(
                ["hdiutil", "detach", str(mount), "-force"],
                check=True,
            )


def smoke_linux(package: Path, expected_version: str) -> None:
    package.chmod(
        package.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
    )
    with tempfile.TemporaryDirectory(prefix="mohan-preview-smoke-") as raw:
        extraction = Path(raw) / "extract"
        extraction.mkdir()
        extracted = subprocess.run(
            [str(package), "--appimage-extract"],
            cwd=extraction,
            check=False,
            capture_output=True,
            text=True,
            timeout=90,
        )
        if extracted.returncode != 0:
            raise RuntimeError(
                "AppImage extraction exited with "
                f"{extracted.returncode}: {extracted.stderr[-1000:]}"
            )
        documentation = (
            extraction
            / "squashfs-root"
            / "usr"
            / "share"
            / "doc"
            / "mohan-desktop-assistant"
        )
        _require_license(documentation / "LICENSE.txt")
        if not (documentation / "THIRD_PARTY_NOTICES.md").is_file():
            raise RuntimeError("AppImage omitted third-party notices")
        output = Path(raw) / "smoke.txt"
        environment = os.environ.copy()
        environment.update(
            {
                "APPIMAGE_EXTRACT_AND_RUN": "1",
                "QT_QPA_PLATFORM": "offscreen",
            }
        )
        _run(
            package,
            output,
            expected_version=expected_version,
            environment=environment,
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=("macos", "linux"), required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--expected-version", required=True)
    args = parser.parse_args()
    package = args.package.resolve()
    if not package.is_file():
        raise FileNotFoundError(package)
    if args.platform == "macos":
        smoke_macos(package, args.expected_version)
    else:
        smoke_linux(package, args.expected_version)
    print(EXPECTED)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
