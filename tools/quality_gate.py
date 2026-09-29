from __future__ import annotations

lazy import os
lazy import re
lazy import shutil
lazy import subprocess
lazy import sys
lazy import time
lazy import uuid
lazy from dataclasses import dataclass
lazy from itertools import batched
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
VULTURE_WHITELIST = TOOLS / "vulture_whitelist.py"
PYTHON_SOURCE_EXCLUSIONS = frozenset({
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".quality-tmp",
    ".ruff_cache",
    ".test-tmp",
    ".venv",
    ".venv315",
    "__pycache__",
    "artifacts",
    "assets",
    "build",
    "dist",
    "target",
})
COMPILE_EXCLUDE_PATTERN = (
    r"(^|[\\/])(?:\.git|\.mypy_cache|\.pytest_cache|\.quality-tmp|"
    r"\.ruff_cache|\.venv(?:315)?|__pycache__|artifacts|assets|build|dist|target)"
    r"([\\/]|$)"
)
VULTURE_EXCLUDE_PATTERN = (
    "**/.git/**,**/.mypy_cache/**,**/.pytest_cache/**,**/.quality-tmp/**,"
    "**/.ruff_cache/**,**/.venv/**,**/.venv315/**,**/__pycache__/**,"
    "**/artifacts/**,**/assets/**,**/build/**,**/dist/**,**/target/**"
)
PINNED_REQUIREMENT = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9_.-]*==[^\s;]+(?:\s*;\s*[^\s].*)?$"
)
CARGO_AUDIT_VERSION = "0.22.2"


@dataclass(frozen=True, slots=True)
class Stage:
    name: str
    command: tuple[str, ...]
    action: str = "command"


def _python() -> str:
    return sys.executable


def _cli(name: str) -> str:
    executable_suffix = ".exe" if os.name == "nt" else ""
    scripts_directory = Path(sys.prefix) / ("Scripts" if os.name == "nt" else "bin")
    environment_executable = scripts_directory / f"{name}{executable_suffix}"
    if environment_executable.is_file():
        return str(environment_executable)
    return shutil.which(name) or name


def _stages() -> tuple[Stage, ...]:
    python = _python()
    return (
        Stage(
            "Python 3.15 runtime",
            (
                python,
                "-c",
                "import sys; assert sys.version_info[:2] == (3, 15), "
                "f'Python 3.15 required, found {sys.version.split()[0]}'",
            ),
        ),
        Stage(
            "compileall",
            (
                python,
                "-m",
                "compileall",
                "-q",
                "-x",
                COMPILE_EXCLUDE_PATTERN,
                "app.py",
                "version_info.py",
                "application",
                "domain",
                "infrastructure",
                "integrations",
                "presentation",
                "tools",
                "tests",
            ),
        ),
        Stage("ruff", (python, "-m", "ruff", "check", ".")),
        Stage("requirements exact pins", (python, "tools/quality_gate.py", "--check-pins"), "pins"),
        Stage(
            "pyright (lazy-import-normalized source copy)",
            (
                _cli("pyright"),
                "--project",
                "<temporary>/pyrightconfig.json",
                "--pythonpath",
                python,
            ),
            "pyright",
        ),
        Stage(
            "deptry",
            (
                _cli("deptry"),
                "application",
                "domain",
                "infrastructure",
                "integrations",
                "presentation",
                "--json-output",
                ".quality-tmp/deptry.json",
                "--no-ansi",
            ),
        ),
        Stage(
            "layered imports and cycle detection",
            (python, "tools/check_layered_imports.py"),
        ),
        Stage(
            "lazy import hygiene (non-destructive)",
            (python, "tools/quality_gate.py", "--check-lazy-imports"),
            "lazy-imports",
        ),
        Stage(
            "vulture",
            (
                _cli("vulture"),
                ".",
                str(VULTURE_WHITELIST),
                "--min-confidence",
                "80",
                "--exclude",
                VULTURE_EXCLUDE_PATTERN,
            ),
        ),
        Stage(
            "four-language documentation",
            (python, "tools/check_four_language_docs.py"),
        ),
        Stage(
            "public release audit",
            (python, "tools/audit_public_release.py"),
        ),
        Stage(
            "Python dependency licenses",
            (
                python,
                "tools/check_python_licenses.py",
                "--output",
                ".quality-tmp/python-license-inventory.json",
            ),
        ),
        Stage("pip-audit", (python, "-m", "pip_audit")),
        Stage(
            "cargo audit",
            (
                "cargo",
                "audit",
                "--file",
                "native/mohan_accel/Cargo.lock",
            ),
            "cargo-audit",
        ),
        Stage(
            "Qt wheel parity",
            (python, "tools/qt315_wheel_lock.py"),
        ),
        Stage(
            "full regression suite (aggregate)",
            (python, "tests/run_all.py", "--aggregate"),
        ),
    )


def _check_pins(root: Path = ROOT) -> int:
    failures: list[str] = []
    requirement_files = sorted(root.glob("requirements*.txt"))
    if not requirement_files:
        print("No requirements*.txt files were found.", file=sys.stderr)
        return 1

    for path in requirement_files:
        for number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            line = raw_line.split("#", maxsplit=1)[0].strip()
            if not line or line.startswith(("-r ", "--requirement ", "--")):
                continue
            if PINNED_REQUIREMENT.fullmatch(line):
                continue
            failures.append(f"{path.relative_to(root)}:{number}: {raw_line.strip()}")

    if failures:
        print("Unpinned or unsupported requirement entries:", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        return 1
    print(f"REQUIREMENTS_PINNED_OK files={len(requirement_files)}")
    return 0


def _source_files(root: Path, suffixes: tuple[str, ...] = (".py",)) -> tuple[Path, ...]:
    sources: list[Path] = []
    for current, directories, filenames in os.walk(root):
        directories[:] = sorted(
            directory
            for directory in directories
            if directory not in PYTHON_SOURCE_EXCLUSIONS
            and not directory.startswith(".")
        )
        current_path = Path(current)
        sources.extend(
            current_path / filename
            for filename in filenames
            if filename.endswith(suffixes)
        )
    return tuple(sorted(sources))


def _create_temporary_directory(root: Path, prefix: str) -> Path:
    temporary_parent = root / ".quality-tmp"
    temporary_parent.mkdir(parents=True, exist_ok=True)
    temporary_root = temporary_parent / f"{prefix}{uuid.uuid4().hex}"
    temporary_root.mkdir()
    return temporary_root


def _remove_temporary_tree(
    temporary_root: Path,
    files: list[Path],
    directories: set[Path],
) -> None:
    for path in reversed(files):
        if path.exists():
            path.unlink()
    for path in sorted(directories, key=lambda item: len(item.parts), reverse=True):
        if path.exists():
            path.rmdir()
    if temporary_root.exists():
        temporary_root.rmdir()


def _copy_python_sources(
    root: Path,
    temporary_root: Path,
    *,
    normalize_lazy_imports: bool,
) -> tuple[list[Path], set[Path]]:
    sources = _source_files(root, (".py", ".pyi"))
    copied_files: list[Path] = []
    created_directories: set[Path] = set()
    for source in sources:
        relative = source.relative_to(root)
        copied = temporary_root / relative
        missing_parents: list[Path] = []
        parent = copied.parent
        while parent != temporary_root and not parent.exists():
            missing_parents.append(parent)
            parent = parent.parent
        for directory in reversed(missing_parents):
            directory.mkdir()
            created_directories.add(directory)
        source_bytes = source.read_bytes()
        if normalize_lazy_imports:
            source_bytes = re.sub(
                rb"(?m)^(\s*)lazy (from|import) ",
                rb"\1\2 ",
                source_bytes,
            )
        copied.write_bytes(source_bytes)
        copied_files.append(copied)
    return copied_files, created_directories


def _check_lazy_imports(root: Path = ROOT) -> int:
    sources = _source_files(root)
    findings: list[str] = []
    temporary_root = _create_temporary_directory(root, "quality-gate-lazy-")
    copied_files: list[Path] = []
    created_directories: set[Path] = set()
    try:
        for source in sources:
            relative = source.relative_to(root)
            copied = temporary_root / relative
            missing_parents: list[Path] = []
            parent = copied.parent
            while parent != temporary_root and not parent.exists():
                missing_parents.append(parent)
                parent = parent.parent
            for directory in reversed(missing_parents):
                directory.mkdir()
                created_directories.add(directory)
            copied.write_bytes(source.read_bytes())
            copied_files.append(copied)

        pruner = TOOLS / "prune_unused_lazy_imports.py"
        copies = tuple(
            (copied, copied.relative_to(temporary_root).as_posix())
            for copied in copied_files
        )
        for chunk in batched(copies, 100, strict=False):
            completed = subprocess.run(
                [
                    sys.executable,
                    str(pruner),
                    *(str(copied) for copied, _relative in chunk),
                ],
                cwd=root,
                check=False,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                text=True,
            )
            if completed.returncode:
                detail = completed.stderr.strip() or completed.stdout.strip()
                print(
                    f"Lazy-import checker failed with exit {completed.returncode}: "
                    f"{detail}",
                    file=sys.stderr,
                )
                return completed.returncode
            for copied, relative in chunk:
                output_line = next(
                    (
                        line
                        for line in completed.stdout.splitlines()
                        if line.startswith(f"{copied}: removed ")
                    ),
                    "",
                )
                match = re.search(
                    r"removed ([1-9][0-9]*) unused lazy imports$",
                    output_line,
                )
                if match:
                    findings.append(f"{relative}: {match.group(1)} import(s)")
    except OSError as error:
        print(f"Could not check lazy imports in temporary copies: {error}", file=sys.stderr)
        return 1
    finally:
        _remove_temporary_tree(temporary_root, copied_files, created_directories)

    if findings:
        print("Unused generated lazy imports found:", file=sys.stderr)
        for finding in findings:
            print(f"  {finding}", file=sys.stderr)
        return 1
    print(f"LAZY_IMPORTS_OK files={len(sources)}")
    return 0


def _run_pyright(root: Path) -> int:
    config = root / "pyrightconfig.json"
    if not config.is_file():
        print("pyrightconfig.json is required.", file=sys.stderr)
        return 2
    temporary_root = _create_temporary_directory(root, "quality-gate-pyright-")
    copied_files: list[Path] = []
    created_directories: set[Path] = set()
    try:
        copied_files, created_directories = _copy_python_sources(
            root,
            temporary_root,
            normalize_lazy_imports=True,
        )
        config_copy = temporary_root / "pyrightconfig.json"
        config_copy.write_bytes(config.read_bytes())
        copied_files.append(config_copy)
        command = (
            _cli("pyright"),
            "--project",
            str(config_copy),
            "--pythonpath",
            sys.executable,
        )
        print(
            f"Normalized Python files: {len(copied_files) - 1}; "
            "only temporary copies are passed to Pyright.",
            flush=True,
        )
        return _run_command(Stage("pyright", command), temporary_root)
    except OSError as error:
        print(f"Could not prepare temporary Pyright source tree: {error}", file=sys.stderr)
        return 1
    finally:
        _remove_temporary_tree(temporary_root, copied_files, created_directories)


def _format_command(command: tuple[str, ...]) -> str:
    return subprocess.list2cmdline(list(command))


def _run_command(stage: Stage, root: Path) -> int:
    try:
        completed = subprocess.run(stage.command, cwd=root, check=False)
    except OSError as error:
        print(f"Could not start command: {error}", file=sys.stderr)
        return 127
    return completed.returncode


def _cargo_audit_installed() -> bool:
    return shutil.which("cargo-audit") is not None


def _run_action(stage: Stage, root: Path) -> int:
    if stage.action == "pins":
        return _check_pins(root)
    if stage.action == "lazy-imports":
        (root / ".quality-tmp").mkdir(parents=True, exist_ok=True)
        return _check_lazy_imports(root)
    if stage.action == "pyright":
        return _run_pyright(root)
    if stage.action == "cargo-audit" and not _cargo_audit_installed():
        print(
            "cargo-audit is required. Install it with: "
            f"cargo install cargo-audit --version {CARGO_AUDIT_VERSION} --locked",
            file=sys.stderr,
        )
        return 127
    return _run_command(stage, root)


def run_gate(root: Path = ROOT) -> int:
    stages = _stages()
    print(f"QUALITY_GATE_START stages={len(stages)} root={root}", flush=True)
    for index, stage in enumerate(stages, 1):
        print(
            f"[{index}/{len(stages)}] START {stage.name}: "
            f"{_format_command(stage.command)}",
            flush=True,
        )
        started = time.perf_counter()
        exit_code = _run_action(stage, root)
        elapsed = time.perf_counter() - started
        result = "PASS" if exit_code == 0 else "FAIL"
        print(
            f"[{index}/{len(stages)}] {result} {stage.name} "
            f"exit={exit_code} elapsed_seconds={elapsed:.2f}",
            flush=True,
        )
        if exit_code:
            remaining = len(stages) - index
            print(
                f"QUALITY_GATE_FAILED stage={stage.name} "
                f"remaining_stages_skipped={remaining}",
                file=sys.stderr,
                flush=True,
            )
            return exit_code
    print("QUALITY_GATE_OK", flush=True)
    return 0


def main(argv: tuple[str, ...] | None = None) -> int:
    arguments = tuple(sys.argv[1:] if argv is None else argv)
    if arguments == ("--check-pins",):
        return _check_pins()
    if arguments == ("--check-lazy-imports",):
        (ROOT / ".quality-tmp").mkdir(parents=True, exist_ok=True)
        return _check_lazy_imports()
    if arguments:
        print("Usage: python tools/quality_gate.py", file=sys.stderr)
        return 2
    return run_gate()


if __name__ == "__main__":
    raise SystemExit(main())
