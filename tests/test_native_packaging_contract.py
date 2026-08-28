from __future__ import annotations

lazy import tomllib
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUST_VERSION = "1.97.1"
MATURIN_VERSION = "1.14.1"
PYO3_VERSION = "0.29.2"
RAYON_VERSION = "1.12.0"
NATIVE_VERIFICATION_INVOCATION_COUNT = 2
LANGUAGE_DOC_COUNT = 4


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_native_toolchain_and_build_inputs_are_immutable() -> None:
    toolchain = tomllib.loads(read("rust-toolchain.toml"))["toolchain"]
    assert toolchain == {
        "channel": RUST_VERSION,
        "profile": "minimal",
        "components": ["clippy", "rustfmt"],
    }
    cargo = tomllib.loads(read("native/mohan_accel/Cargo.toml"))
    assert cargo["package"]["rust-version"] == RUST_VERSION
    assert cargo["dependencies"]["pyo3"] == {
        "version": f"={PYO3_VERSION}",
        "features": ["abi3t-py315"],
    }
    assert cargo["dependencies"]["rayon"] == f"={RAYON_VERSION}"
    assert (ROOT / "native/mohan_accel/Cargo.lock").is_file()
    assert f'name = "pyo3"\nversion = "{PYO3_VERSION}"' in read(
        "native/mohan_accel/Cargo.lock"
    )
    assert f'name = "rayon"\nversion = "{RAYON_VERSION}"' in read(
        "native/mohan_accel/Cargo.lock"
    )
    native_pyproject = tomllib.loads(read("native/mohan_accel/pyproject.toml"))
    assert native_pyproject["build-system"]["requires"] == [
        f"maturin=={MATURIN_VERSION}"
    ]


def test_windows_package_builds_installs_and_collects_native_module() -> None:
    script = read("build.ps1")
    build_call = "tools/build_native_acceleration.py"
    pyinstaller_call = "-m PyInstaller"
    for required in (
        build_call,
        "--output-dir",
        "--evidence",
        "--install",
        'import _mohan_accel',
        "scale_pcm16",
        "alpha_over_rgba",
        "python3t.dll",
        '--add-binary "$Abi3tCompatibilityDll;."',
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
        'Move-Item -LiteralPath $PublicExecutable',
        'tools\\jit_launcher.py',
        '$env:PYTHON_JIT = "0"',
        '$RuntimeExecutable',
        "mohan-native-build-evidence.json",
        "tools/verify_packaged_native_acceleration.py",
    ):
        assert required in script
    assert script.index(build_call) < script.index(pyinstaller_call)
    assert "native-wheels/" in read(".gitignore")
    assert "native-wheels-*/" in read(".gitignore")
    assert '"native-wheels-$NativeBuildId"' in script


def test_python315_jit_bootloader_contract_is_reproducible_and_narrow() -> None:
    builder = read("tools/build_pyinstaller_jit_bootloader.py")
    for required in (
        'PYINSTALLER_VERSION = "6.21.0"',
        "SOURCE_SHA256",
        "MOHAN_JIT_ENV",
        'config.isolated = 0',
        'config.use_environment = 1',
        'PyInitConfig_SetInt(config, \\\"isolated\\\", 0)',
        'PyInitConfig_SetInt(config, \\\"use_environment\\\", 1)',
        'for name in ("run.exe", "runw.exe")',
    ):
        assert required in builder
    launcher = read("tools/jit_launcher.py")
    assert "startswith(PYTHON_ENV_PREFIX)" in launcher
    assert 'environment["PYTHON_JIT"] = "1"' in launcher


def assert_native_workflow_contract(relative: str) -> None:
    workflow = read(relative)
    for required in (
        'FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: "true"',
        'RUSTUP_TOOLCHAIN: "1.97.1"',
        "rustup toolchain install 1.97.1",
        "maturin==1.14.1",
        "tests/test_native_equivalence.py",
        "tests/test_native_rgba_equivalence.py",
        "tools/benchmark_native_rgba.py",
    ):
        assert required in workflow, f"{relative}: {required}"
    assert "maturin-action" not in workflow
    assert "rustup default" not in workflow
    assert "--locked" in read("tools/build_native_acceleration.py")


def test_ci_and_release_share_the_native_build_gate() -> None:
    assert_native_workflow_contract(".github/workflows/windows-ci.yml")
    assert_native_workflow_contract(".github/workflows/release.yml")
    windows = read(".github/workflows/windows-ci.yml")
    assert "tools/build_native_acceleration.py" in windows
    assert "--install" in windows
    release = read(".github/workflows/release.yml")
    for workflow in (windows, release):
        assert ".\\build.ps1" in workflow
        assert "tools/verify_packaged_native_acceleration.py" in workflow
    verifier = read("tools/verify_packaged_native_acceleration.py")
    assert "spec_from_file_location" in verifier
    assert "PACKAGED_NATIVE_ACCELERATION_OK" in verifier


def test_windows_release_verifies_every_distributed_package_form() -> None:
    installer_test = read("installer/test_installers.ps1")
    for required in (
        "tools\\verify_packaged_native_acceleration.py",
        '"exe"',
        '"msi-zh-TW"',
        '"msi-en-US"',
        '"msi-zh-CN"',
        '"msi-ja-JP"',
        "[string]$NativeEvidenceDir",
        "[string]$Python",
        "$ResolvedNativeEvidence",
        "installer-upgrade",
        '"--output"',
        "& $Python @Arguments",
        "Invoke-NativeVerification",
        "Installer omitted layered PoseAtlas v4 assets",
        'if ($LayeredViews.Count -ne 600)',
        "Installer omitted layered half-body expression assets",
        'if ($HalfBodyLayers.Count -ne 75)',
        'foreach ($Authority in @("idle.png", "idle_lean.png", "idle_front.png"))',
    ):
        assert required in installer_test
    assert installer_test.count("Invoke-NativeVerification `") == NATIVE_VERIFICATION_INVOCATION_COUNT

    for relative in (
        ".github/workflows/windows-ci.yml",
        ".github/workflows/release.yml",
    ):
        workflow = read(relative)
        for required in (
            "Expand-Archive",
            '"zip"',
            "-NativeEvidenceDir",
            "-Python $env:MOHAN_JIT_PYTHON",
            "tools/finalize_native_release_evidence.py",
            "tools/generate_native_sbom.py",
            "tools/validate_native_sbom.py",
            "if ($LASTEXITCODE -ne 0)",
        ):
            assert required in workflow, f"{relative}: {required}"

    release = read(".github/workflows/release.yml")
    for release_asset in (
        "$base-Native-Evidence.json",
        "$base-Windows-Native-SBOM.cdx.json",
    ):
        assert release_asset in release


def test_cross_platform_core_builds_the_same_native_contract() -> None:
    workflow = read(".github/workflows/cross-platform-core.yml")
    for required in (
        'FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: "true"',
        'RUSTUP_TOOLCHAIN: "1.97.1"',
        "rustup toolchain install 1.97.1",
        "maturin==1.14.1",
        "tools/build_native_acceleration.py",
        "--install",
        "tests/test_native_equivalence.py",
        "tests/test_native_rgba_equivalence.py",
        "tools/benchmark_native_rgba.py",
    ):
        assert required in workflow
    assert "maturin-action" not in workflow
    assert "rustup default" not in workflow


def test_build_only_inventory_is_not_a_runtime_dependency() -> None:
    policy = tomllib.loads(read("sbom/components.toml"))
    components = {
        str(component["name"]): component
        for component in policy["component"]
    }
    expected = {
        "Rust": RUST_VERSION,
        "Maturin": MATURIN_VERSION,
        "PyO3": PYO3_VERSION,
        "Rayon": RAYON_VERSION,
    }
    for name, version in expected.items():
        component = components[name]
        assert component["version"] == version
        assert component["scope"] == "build"
        assert component["profiles"] == ["windows"]
    runtime = read("requirements-runtime.txt").casefold()
    project = read("pyproject.toml").casefold()
    for forbidden in ("maturin", "pyo3"):
        assert forbidden not in runtime
        assert forbidden not in project

    development = tomllib.loads(read("sbom/development-components.toml"))
    assert development["compiled_component"] == [
        {
            "name": "Rayon",
            "version": RAYON_VERSION,
            "license": "MIT OR Apache-2.0",
            "scope": "compiled",
            "profiles": ["native-build", "packaged-native"],
        }
    ]


def test_governance_does_not_claim_unimplemented_simd_or_zero_copy() -> None:
    for relative in (
        ".github/workflows/windows-ci.yml",
        ".github/workflows/release.yml",
        ".github/workflows/cross-platform-core.yml",
        "sbom/components.toml",
    ):
        content = read(relative).casefold()
        for unsupported in ("simd", "zero-copy", "zero copy"):
            assert unsupported not in content, f"{relative}: {unsupported}"


def test_four_language_docs_state_the_precise_rgba_contract() -> None:
    # Audit ruling (2026-08-27): docs/releases/v4.0.0-draft.md is a frozen
    # historical artifact of the shipped v4.0.0 release, no longer a living
    # document.  Requiring it to track the current RGBA contract wording was
    # a fossil assertion, so it was removed from this list; the living docs
    # below still carry the full four-language contract.
    for relative in (
        "README.md",
        "THIRD_PARTY_NOTICES.md",
        "native/mohan_accel/README.md",
    ):
        content = read(relative)
        assert content.count("Rayon 1.12.0") >= LANGUAGE_DOC_COUNT, relative
        assert content.count("262,144") >= LANGUAGE_DOC_COUNT, relative
        assert content.casefold().count("simd") >= LANGUAGE_DOC_COUNT, relative
    notices = read("THIRD_PARTY_NOTICES.md")
    assert notices.count("| [Rayon]") == LANGUAGE_DOC_COUNT


def main() -> None:
    test_native_toolchain_and_build_inputs_are_immutable()
    test_windows_package_builds_installs_and_collects_native_module()
    test_ci_and_release_share_the_native_build_gate()
    test_cross_platform_core_builds_the_same_native_contract()
    test_build_only_inventory_is_not_a_runtime_dependency()
    test_governance_does_not_claim_unimplemented_simd_or_zero_copy()
    test_four_language_docs_state_the_precise_rgba_contract()
    print("NATIVE_PACKAGING_GOVERNANCE_OK")


if __name__ == "__main__":
    main()
