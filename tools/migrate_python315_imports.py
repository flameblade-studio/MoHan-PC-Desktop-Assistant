from __future__ import annotations

lazy import argparse
lazy import ast
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = frozenset({
    ".git",
    ".ruff_cache",
    ".venv",
    ".venv315",
    "_python315",
    "__pycache__",
    ".qt315-compat-full",
    ".qt315-compat-verify",
    ".qt315-compat-verify2",
    ".qt315-compat-windows",
    "build",
    "build-temp",
    "dist",
    "release-artifacts",
    "tmp",
})
GENERATED_TREES = (("native", "mohan_accel", "target"),)

# CPython 3.15rc1 exposes ``concurrent.futures.ThreadPoolExecutor`` through a
# lazy module attribute that ``asyncio`` calls without resolving.  These exact
# imports form the one documented compatibility boundary; every other
# top-level import remains subject to PEP 810 migration.
EAGER_IMPORT_EXCEPTIONS = frozendict({
    "application/service_container.py": frozenset({
        (
            "from",
            "integrations.speech",
            (
                "OpenAITTS",
                "SpeechListener",
                "SpeechListenerProviders",
                "UnavailableSystemTTS",
                "WindowsTTS",
                "female_windows_voices_for_language",
                "preferred_windows_voice",
                "windows_voices",
            ),
        ),
    }),
    "application/background_agents.py": frozenset({
        ("from", "domain.python315_concurrency", ("Future", "ThreadPoolExecutor")),
    }),
    "domain/python315_concurrency.py": frozenset({
        ("import", "", ("concurrent.futures",)),
        ("from", "concurrent.futures", ("Future", "as_completed")),
        ("from", "concurrent.futures.thread", ("ThreadPoolExecutor",)),
    }),
    "infrastructure/concurrency_tools.py": frozenset({
        ("from", "domain.python315_concurrency", ("ThreadPoolExecutor",)),
    }),
    "integrations/realtime_voice.py": frozenset({
        (
            "from",
            "integrations.realtime_contracts",
            (
                "_REALTIME_MESSAGES",
                "MAX_ASSISTANT_RESPONSE_CHARACTERS",
                "RealtimeSessionConfig",
                "RealtimeVoiceRequest",
                "_AudioSession",
                "_realtime_message",
            ),
        ),
    }),
    "integrations/speech.py": frozenset({
        (
            "from",
            "integrations.speech_audio",
            (
                "WavePlaybackBoundary",
                "_CancellableWavePlayback",
                "_play_cancellable_wave_bytes",
                "_SpeechCancelled",
                "_SpeechPlaybackUnavailable",
                "abort_raw_output_stream",
                "apply_wav_volume",
                "emit_wave_viseme_cues",
                "play_pcm16_stream_with_visemes_impl",
                "play_wave_with_visemes_impl",
            ),
        ),
        (
            "from",
            "integrations.speech_recognition",
            (
                "RecordingLimits",
                "SpeechEndpointDetector",
                "SpeechTranscriptionLocale",
                "TranscriptionHttpBoundary",
                "TranscriptionRequest",
                "transcribe_wav_bytes_impl",
                "transcription_http_error_message",
            ),
        ),
        (
            "from",
            "integrations.speech_unavailable",
            ("UnavailableSystemTTS",),
        ),
        (
            "from",
            "integrations.speech_voice_catalog",
            (
                "WindowsVoiceInfo",
                "_is_allowed_companion_voice",
                "female_windows_voices_for_language",
                "is_known_male_windows_voice",
                "preferred_windows_voice",
                "windows_voice_catalog",
                "windows_voices",
            ),
        ),
    }),
    "presentation/flagship/cloud_health.py": frozenset({
        (
            "from",
            "domain.python315_concurrency",
            ("ThreadPoolExecutor", "as_completed"),
        ),
    }),
    "presentation/dashboard_conversation.py": frozenset({
        ("from", "PySide6.QtCore", ("QTimer",)),
    }),
    "presentation/preview_app.py": frozenset({
        (
            "from",
            "application.preview_app",
            (
                "PreviewRuntime",
                "parse_preview_arguments",
                "validate_preview_runtime",
            ),
        ),
    }),
    "presentation/ui_localization.py": frozenset({
        (
            "from",
            "presentation.ui_localization_en",
            ("ENGLISH_UI_TEXT",),
        ),
        (
            "from",
            "presentation.ui_localization_ja",
            ("JAPANESE_UI",),
        ),
    }),
    "tests/test_native_concurrency.py": frozenset({
        ("import", "", ("asyncio",)),
    }),
    "tests/test_remote_concurrency.py": frozenset({
        ("from", "domain.python315_concurrency", ("ThreadPoolExecutor",)),
    }),
    "tools/benchmark_native_integrated.py": frozenset({
        ("import", "", ("asyncio",)),
        ("from", "domain.python315_concurrency", ("ThreadPoolExecutor",)),
    }),
    "tools/diagnose_google_services.py": frozenset({
        (
            "from",
            "domain.python315_concurrency",
            ("Future", "ThreadPoolExecutor", "as_completed"),
        ),
    }),
})

ImportSignature = tuple[str, str, tuple[str, ...]]


def _import_signature(node: ast.Import | ast.ImportFrom) -> ImportSignature:
    kind = "import" if isinstance(node, ast.Import) else "from"
    module = "" if isinstance(node, ast.Import) else (node.module or "")
    names = tuple(alias.name for alias in node.names)
    return kind, module, names


def _relative_key(path: Path) -> str | None:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return None


def _compatibility_alias_target(tree: ast.Module) -> str | None:
    """Return the target of one exact module-identity compatibility facade."""

    imports = {
        **{
            alias.asname or alias.name.partition(".")[0]: (
                alias.name,
                bool(getattr(node, "is_lazy", False)),
            )
            for alias in node.names
        }
        for node in tree.body
        if isinstance(node, ast.Import)
    }
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        value = node.value
        if not (
            isinstance(target, ast.Subscript)
            and isinstance(target.value, ast.Attribute)
            and isinstance(target.value.value, ast.Name)
            and imports.get(target.value.value.id, (None, False))[0] == "sys"
            and target.value.attr == "modules"
            and isinstance(target.slice, ast.Name)
            and target.slice.id == "__name__"
        ):
            continue
        if (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Attribute)
            and isinstance(value.func.value, ast.Name)
            and imports.get(value.func.value.id, (None, False))[0] == "importlib"
            and value.func.attr == "import_module"
            and len(value.args) == 1
            and not value.keywords
            and isinstance(value.args[0], ast.Constant)
            and isinstance(value.args[0].value, str)
        ):
            return value.args[0].value
        if isinstance(value, ast.Name):
            module_name, is_lazy = imports.get(value.id, (None, False))
            if is_lazy and isinstance(module_name, str) and "." in module_name:
                return module_name
    return None


def _compatibility_alias_eager_imports(
    tree: ast.Module,
) -> frozenset[ImportSignature]:
    target = _compatibility_alias_target(tree)
    if target is None:
        return frozenset()
    return frozenset({
        ("import", "", ("importlib",)),
        ("import", "", ("sys",)),
    })


def _named_compatibility_facade_eager_imports(
    tree: ast.Module,
) -> frozenset[ImportSignature]:
    """Keep named facade exports concrete under Python 3.15rc1."""

    docstring = ast.get_docstring(tree, clean=False) or ""
    if not docstring.startswith("Compatibility facade"):
        return frozenset()
    return frozenset(
        _import_signature(node)
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        and node.module != "__future__"
    )


def _normalize_compatibility_alias(path: Path) -> bool:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    target = _compatibility_alias_target(tree)
    if target is None or "lazy import importlib" in source:
        return False
    lazy_module_lines = [
        node
        for node in tree.body
        if isinstance(node, ast.Import)
        and bool(getattr(node, "is_lazy", False))
        and any(alias.name == target for alias in node.names)
    ]
    if len(lazy_module_lines) != 1:
        return False
    node = lazy_module_lines[0]
    alias = next(alias for alias in node.names if alias.name == target)
    if alias.asname is None:
        return False
    lines = source.splitlines(keepends=True)
    lines[node.lineno - 1] = "import importlib\n"
    for index, line in enumerate(lines):
        if line.strip() == "lazy import sys":
            lines[index] = "import sys\n"
        if line.strip() == f"sys.modules[__name__] = {alias.asname}":
            lines[index] = (
                "sys.modules[__name__] = "
                f'importlib.import_module("{target}")\n'
            )
    path.write_text("".join(lines), encoding="utf-8", newline="")
    return True


class ImportInventory(ast.NodeVisitor):
    def __init__(
        self,
        allowed_eager: frozenset[ImportSignature],
        configured_eager: frozenset[ImportSignature],
    ) -> None:
        self.eligible: list[int] = []
        self.restricted: list[tuple[int, str]] = []
        self.exceptions: list[int] = []
        self.configured_exceptions: list[int] = []
        self._restriction: str | None = None
        self._allowed_eager = allowed_eager
        self._configured_eager = configured_eager

    def _visit_restricted(self, node: ast.AST, reason: str) -> None:
        previous = self._restriction
        self._restriction = reason
        self.generic_visit(node)
        self._restriction = previous

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_restricted(node, "function")

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_restricted(node, "function")

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._visit_restricted(node, "class")

    def visit_Try(self, node: ast.Try) -> None:
        self._visit_restricted(node, "try")

    def visit_TryStar(self, node: ast.TryStar) -> None:
        self._visit_restricted(node, "try")

    def _record(self, node: ast.Import | ast.ImportFrom) -> None:
        if self._restriction is not None:
            self.restricted.append((node.lineno, self._restriction))
            return
        if getattr(node, "is_lazy", False):
            return
        if _import_signature(node) in self._allowed_eager:
            self.exceptions.append(node.lineno)
            if _import_signature(node) in self._configured_eager:
                self.configured_exceptions.append(node.lineno)
            return
        self.eligible.append(node.lineno)

    def visit_Import(self, node: ast.Import) -> None:
        self._record(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module == "__future__":
            return
        if any(alias.name == "*" for alias in node.names):
            self.restricted.append((node.lineno, "star"))
            return
        self._record(node)


def python_files(root: Path = ROOT) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*.py")
        if not _excluded(path.relative_to(root).parts)
    )


def _excluded(parts: tuple[str, ...]) -> bool:
    if any(part in EXCLUDED_PARTS for part in parts):
        return True
    return any(parts[: len(prefix)] == prefix for prefix in GENERATED_TREES)


def inventory(path: Path) -> ImportInventory:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    key = _relative_key(path)
    configured_eager = (
        EAGER_IMPORT_EXCEPTIONS.get(key, frozenset())
        if key is not None
        else frozenset()
    )
    allowed_eager = (
        configured_eager
        | _compatibility_alias_eager_imports(tree)
        | _named_compatibility_facade_eager_imports(tree)
    )
    result = ImportInventory(allowed_eager, configured_eager)
    result.visit(tree)
    return result


def migrate(path: Path) -> int:
    result = inventory(path)
    if not result.eligible:
        return 0
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    for line_number in result.eligible:
        line = lines[line_number - 1]
        indentation = line[: len(line) - len(line.lstrip())]
        lines[line_number - 1] = f"{indentation}lazy {line[len(indentation):]}"
    path.write_text("".join(lines), encoding="utf-8", newline="")
    return len(result.eligible)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Migrate every Python 3.15-eligible module import to PEP 810."
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    files = python_files()
    pending: list[tuple[Path, int]] = []
    restricted: list[tuple[Path, int, str]] = []
    exceptions: list[tuple[Path, int]] = []
    configured_exception_hits: list[tuple[Path, int]] = []
    for path in files:
        result = inventory(path)
        pending.extend((path, line) for line in result.eligible)
        exceptions.extend((path, line) for line in result.exceptions)
        configured_exception_hits.extend(
            (path, line) for line in result.configured_exceptions
        )
        restricted.extend(
            (path, line, reason) for line, reason in result.restricted
        )

    if args.check:
        configured_exception_count = sum(
            len(signatures) for signatures in EAGER_IMPORT_EXCEPTIONS.values()
        )
        unmatched_exceptions = configured_exception_count - len(
            configured_exception_hits
        )
        compatibility_alias_imports = len(exceptions) - len(
            configured_exception_hits
        )
        for path, line in pending:
            print(f"EAGER_ELIGIBLE {path.relative_to(ROOT)}:{line}")
        for path, line, reason in restricted:
            print(
                f"EAGER_RESTRICTED {path.relative_to(ROOT)}:{line} "
                f"reason={reason}"
            )
        for path, line in exceptions:
            print(f"EAGER_EXCEPTION {path.relative_to(ROOT)}:{line}")
        print(
            f"PYTHON315_IMPORT_AUDIT files={len(files)} "
            f"pending={len(pending)} restricted={len(restricted)} "
            f"exceptions={len(exceptions)} "
            f"configured_exceptions={len(configured_exception_hits)} "
            f"compatibility_alias_imports={compatibility_alias_imports} "
            f"unmatched_exceptions={unmatched_exceptions}"
        )
        return 1 if pending or unmatched_exceptions else 0

    aliases = sum(_normalize_compatibility_alias(path) for path in files)
    migrated = sum(migrate(path) for path in files)
    print(
        f"PYTHON315_LAZY_IMPORTS_MIGRATED files={len(files)} "
        f"imports={migrated} compatibility_aliases={aliases} "
        f"restricted={len(restricted)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
