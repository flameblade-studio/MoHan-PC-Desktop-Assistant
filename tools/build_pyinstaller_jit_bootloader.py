"""Build the MoHan PyInstaller bootloader that admits only launcher-sanitized JIT."""

from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import os
lazy import shutil
lazy import subprocess
lazy import sys
lazy import tarfile
lazy import tempfile
lazy from pathlib import Path

PYINSTALLER_VERSION = "6.21.0"
SOURCE_SHA256 = "bb9fab705983e393a2d1cac77d6972513057ad800215fd861dc15ff5272e98fd"
SOURCE_DIRNAME = f"pyinstaller-{PYINSTALLER_VERSION}"
BOOTLOADER_PLATFORM = "Windows-64bit-intel"


def _replace_once(path: Path, anchor: str, replacement: str, marker: str) -> None:
    source = path.read_text(encoding="utf-8")
    if marker in source:
        return
    if source.count(anchor) != 1:
        raise RuntimeError(f"PyInstaller source anchor changed: {path.name}")
    path.write_text(source.replace(anchor, replacement), encoding="utf-8")


def patch_sources(source_root: Path) -> None:
    src = source_root / "bootloader" / "src"
    preconfig = src / "pyi_pyconfig.c"
    if "config.isolated = 0;" not in preconfig.read_text(encoding="utf-8"):
        _replace_once(
            preconfig,
            "    dylib_python->PyPreConfig_InitIsolatedConfig((PyPreConfig *)&config);\n",
            "    dylib_python->PyPreConfig_InitIsolatedConfig((PyPreConfig *)&config);\n\n"
            "    /* MOHAN_JIT_ENV_PRECONFIG: sanitized PYTHON_JIT only. */\n"
            "    config.isolated = 0;\n"
            "    config.use_environment = 1;\n",
            "MOHAN_JIT_ENV_PRECONFIG",
        )

    pep587 = src / "pyi_pyconfig_pep587.c"
    if "config_impl->isolated = 0;" not in pep587.read_text(encoding="utf-8"):
        pep587_anchor = (
            "pyi_pyconfig_pep587_set_runtime_options(PyConfig *config, "
            "const struct PYI_CONTEXT *pyi_ctx, "
            "const struct PyiRuntimeOptions *runtime_options)\n"
            "{\n"
            "    const struct DYLIB_PYTHON *dylib_python = pyi_ctx->dylib_python;\n"
            "    const int version_id = _MAKE_VERSION_ID(dylib_python->version, "
            "pyi_ctx->nogil_enabled);\n\n"
            "    /* *** Common options *** */\n"
            "    /* Macro to avoid manual code repetition. */\n"
            "    #define _IMPL_CASE(PY_VERSION, PY_FLAGS, PYCONFIG_IMPL) \\\n"
            "    case _MAKE_VERSION_ID(PY_VERSION, PY_FLAGS): { \\\n"
            "        PyStatus status; \\\n"
            "        PYCONFIG_IMPL *config_impl = (PYCONFIG_IMPL *)config; \\\n"
        )
        _replace_once(
            pep587,
            pep587_anchor,
            pep587_anchor
            + "        /* MOHAN_JIT_ENV_PEP587: sanitized PYTHON_JIT only. */ \\\n"
            "        config_impl->isolated = 0; \\\n"
            "        config_impl->use_environment = 1; \\\n",
            "MOHAN_JIT_ENV_PEP587",
        )

    pep741 = src / "pyi_pyconfig_pep741.c"
    if 'PyInitConfig_SetInt(config, "isolated", 0)' not in pep741.read_text(
        encoding="utf-8"
    ):
        pep741_anchor = (
            "pyi_pyconfig_pep741_set_runtime_options(PyInitConfig *config, "
            "const struct PYI_CONTEXT *pyi_ctx, "
            "const struct PyiRuntimeOptions *runtime_options)\n"
            "{\n"
            "    const struct DYLIB_PYTHON *dylib_python = pyi_ctx->dylib_python;\n"
            "    const char *error_message = NULL;\n"
        )
        _replace_once(
            pep741,
            pep741_anchor,
            pep741_anchor
            + "\n"
            "    /* MOHAN_JIT_ENV_PEP741: Python 3.15 must admit PYTHON_JIT. */\n"
            "    if (dylib_python->PyInitConfig_SetInt(config, \"isolated\", 0) < 0) return -1;\n"
            "    if (dylib_python->PyInitConfig_SetInt(config, \"use_environment\", 1) < 0) return -1;\n",
            "MOHAN_JIT_ENV_PEP741",
        )


def _download_source(cache: Path) -> Path:
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / f"{SOURCE_DIRNAME}.tar.gz"
    if not archive.is_file():
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "download",
                "--no-deps",
                "--no-binary=:all:",
                "--dest",
                str(cache),
                f"pyinstaller=={PYINSTALLER_VERSION}",
            ],
            check=True,
        )
        downloads = tuple(cache.glob(f"[Pp]y[Ii]nstaller-{PYINSTALLER_VERSION}.tar.gz"))
        if len(downloads) != 1:
            raise RuntimeError("Unable to identify the pinned PyInstaller source archive")
        downloads[0].replace(archive)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != SOURCE_SHA256:
        raise RuntimeError(f"PyInstaller source checksum mismatch: {digest}")
    source_root = cache / SOURCE_DIRNAME
    if not source_root.is_dir():
        with tarfile.open(archive, "r:gz") as bundle:
            bundle.extractall(cache, filter="data")
    return source_root


def _source_root(explicit: str) -> Path:
    candidates = tuple(
        path
        for path in (
            Path(explicit) if explicit else None,
            Path(os.environ["MOHAN_PYINSTALLER_SOURCE"])
            if os.environ.get("MOHAN_PYINSTALLER_SOURCE")
            else None,
            Path(tempfile.gettempdir()) / "mohan-pyinstaller-source" / SOURCE_DIRNAME,
        )
        if path is not None
    )
    for candidate in candidates:
        if (candidate / "bootloader" / "wscript").is_file():
            return candidate
    return _download_source(Path(tempfile.gettempdir()) / "mohan-pyinstaller-source")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", default="")
    args = parser.parse_args()
    source_root = _source_root(args.source_root)
    patch_sources(source_root)
    subprocess.run([sys.executable, "waf", "all"], cwd=source_root / "bootloader", check=True)

    import PyInstaller

    built = source_root / "PyInstaller" / "bootloader" / BOOTLOADER_PLATFORM
    installed = Path(PyInstaller.__file__).resolve().parent / "bootloader" / BOOTLOADER_PLATFORM
    for name in ("run.exe", "runw.exe"):
        source = built / name
        if not source.is_file():
            raise FileNotFoundError(source)
        shutil.copy2(source, installed / name)
    print("PYINSTALLER_JIT_BOOTLOADER_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
