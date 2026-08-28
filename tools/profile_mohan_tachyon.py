from __future__ import annotations

lazy import argparse
lazy import hashlib
lazy import json
lazy import os
lazy import platform
lazy import re
lazy import subprocess
lazy import sys
lazy import tempfile
lazy import time
lazy from collections.abc import Iterator, Mapping
lazy from dataclasses import dataclass
lazy from datetime import UTC, datetime
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE_TARGETS = ("startup", "lipsync", "expression")
MAX_PERCENT = 100.0
TARGET_SCRIPTS = frozendict(
    {
        "startup": ROOT / "app.py",
        "lipsync": ROOT / "tests" / "test_lipsync_timing.py",
        "expression": ROOT / "tests" / "test_expression_arbiter.py",
    }
)
TARGET_CADENCE_HZ = frozendict(
    {
        "startup": None,
        "lipsync": 50,
        "expression": None,
    }
)
TARGET_REPETITIONS = frozendict(
    {
        "startup": 1,
        "lipsync": 1,
        "expression": 16,
    }
)
TARGET_ALL_THREADS = frozendict(
    {
        "startup": True,
        "lipsync": True,
        "expression": False,
    }
)
TARGET_BLOCKING = frozendict(
    {
        "startup": False,
        "lipsync": False,
        "expression": True,
    }
)
ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
CAPTURE_PATTERN = re.compile(
    r"Captured (?P<samples>[0-9,]+) samples in "
    r"(?P<seconds>[0-9.]+) seconds"
)
RATE_PATTERN = re.compile(r"Sample rate: (?P<rate>[0-9.]+) samples/sec")
MISSED_PATTERN = re.compile(
    r"missed (?P<samples>[0-9,]+) samples.*"
    r"\((?P<percent>[0-9.]+)%\)"
)
ERROR_RATE_PATTERN = re.compile(
    r"Error rate: (?P<percent>[0-9.]+)"
)
WINDOWS_ABSOLUTE_PATH = re.compile(
    r"(?i)(?:^|(?<=[\s\"'(]))[a-z]:[\\/]+"
)
HOME_ABSOLUTE_PATH = re.compile(
    r"(?i)(?:/home/[^/\s\"']+|/Users/[^/\s\"']+)"
)
WINDOWS_PRIVATE_PATH = re.compile(
    r"(?i)(?:^|(?<=[\s\"'(]))[a-z]:[\\/]+[^\r\n\"'<>]*"
)
HOME_PRIVATE_PATH = re.compile(
    r"(?i)(?:/home/|/Users/)[^\r\n\"'<>]*"
)


@dataclass(frozen=True, slots=True)
class ProfileArtifacts:
    binary: Path
    flamegraph: Path
    jsonl: Path
    pstats: Path
    runtime: Path
    summary: Path

    def published_outputs(self) -> tuple[Path, ...]:
        return (
            self.flamegraph,
            self.jsonl,
            self.pstats,
            self.runtime,
        )

    def with_temporary_binary(self, binary: Path) -> ProfileArtifacts:
        return ProfileArtifacts(
            binary=binary,
            flamegraph=self.flamegraph,
            jsonl=self.jsonl,
            pstats=self.pstats,
            runtime=self.runtime,
            summary=self.summary,
        )


@dataclass(frozen=True, slots=True)
class TargetSpec:
    script: Path
    arguments: tuple[str, ...]
    repetitions: int


@dataclass(frozen=True, slots=True)
class FrameStats:
    path: str
    function: str
    line: int
    self_samples: int
    cumulative_samples: int

    def as_json(self, total_samples: int) -> dict[str, object]:
        denominator = max(1, total_samples)
        return {
            "path": self.path,
            "function": self.function,
            "line": self.line,
            "self_samples": self.self_samples,
            "self_percent": round(
                self.self_samples * 100 / denominator,
                4,
            ),
            "cumulative_samples": self.cumulative_samples,
            "cumulative_percent": round(
                self.cumulative_samples * 100 / denominator,
                4,
            ),
        }


@dataclass(frozen=True, slots=True)
class ProfileOutcome:
    target: str
    summary: Path
    violations: tuple[str, ...]


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Capture reproducible MoHan Python 3.15 Tachyon evidence "
            "from one binary sample stream."
        )
    )
    parser.add_argument(
        "--target",
        choices=(*PROFILE_TARGETS, "all"),
        default="startup",
    )
    parser.add_argument("--duration", type=int, default=12)
    parser.add_argument("--rate", default="1khz")
    parser.add_argument(
        "--mode",
        choices=("wall", "cpu", "gil", "exception"),
        default="wall",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "reports" / "tachyon",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Backward-compatible flamegraph path for a single target. "
            "Other evidence files use the same stem."
        ),
    )
    parser.add_argument("--top-frames", type=int, default=20)
    parser.add_argument("--min-samples", type=int, default=20)
    parser.add_argument(
        "--max-sample-read-error-percent",
        "--max-sampling-error-percent",
        "--max-missed-percent",
        dest="max_sample_read_error_percent",
        type=float,
        default=80.0,
    )
    parser.add_argument(
        "--max-missed-samples-percent",
        type=float,
        default=30.0,
    )
    parser.add_argument(
        "--full-session",
        action="store_true",
        help="Profile the normal GUI until it exits.",
    )
    parser.add_argument(
        "--use-user-profile",
        action="store_true",
        help="Use the normal MoHan profile instead of an isolated profile.",
    )
    return parser.parse_args()


def _validate_arguments(args: argparse.Namespace) -> None:
    if sys.version_info[:2] != (3, 15):
        raise SystemExit(
            "Tachyon profiling requires the MoHan Python 3.15 runtime."
        )
    jit = getattr(sys, "_jit", None)
    if jit is None or not jit.is_available():
        raise SystemExit(
            "Tachyon evidence requires a CPython 3.15 build with JIT support."
        )
    if args.duration <= 0:
        raise SystemExit("--duration must be positive.")
    if args.top_frames <= 0 or args.min_samples <= 0:
        raise SystemExit("Frame and sample limits must be positive.")
    if not 0.0 <= args.max_sample_read_error_percent <= MAX_PERCENT:
        raise SystemExit(
            "--max-sample-read-error-percent must be from 0 through 100."
        )
    if not 0.0 <= args.max_missed_samples_percent <= MAX_PERCENT:
        raise SystemExit(
            "--max-missed-samples-percent must be from 0 through 100."
        )
    if args.target == "all" and args.output is not None:
        raise SystemExit("--output is only valid for a single target.")
    if args.full_session and args.target != "startup":
        raise SystemExit(
            "--full-session is only valid with --target startup."
        )


def _targets(selected: str) -> tuple[str, ...]:
    return PROFILE_TARGETS if selected == "all" else (selected,)


def _artifact_paths(
    target: str,
    output_dir: Path,
    legacy_output: Path | None,
) -> ProfileArtifacts:
    if legacy_output is not None:
        flamegraph = legacy_output.resolve()
        stem = flamegraph.stem.removesuffix("-flamegraph")
        base = flamegraph.with_name(stem)
    else:
        directory = output_dir.resolve() / target
        base = directory / f"mohan-tachyon-{target}"
        flamegraph = base.with_name(f"{base.name}-flamegraph.html")
    return ProfileArtifacts(
        binary=base.with_suffix(".profile.bin"),
        flamegraph=flamegraph,
        jsonl=base.with_suffix(".samples.jsonl"),
        pstats=base.with_suffix(".pstats.txt"),
        runtime=base.with_suffix(".runtime.json"),
        summary=base.with_suffix(".summary.json"),
    )


def _target_spec(
    target: str,
    temp_dir: Path,
    full_session: bool,
) -> TargetSpec:
    if target != "startup":
        return TargetSpec(
            TARGET_SCRIPTS[target],
            (),
            TARGET_REPETITIONS[target],
        )
    if full_session:
        return TargetSpec(TARGET_SCRIPTS[target], (), 1)
    smoke_output = temp_dir / "mohan-tachyon-smoke.txt"
    return TargetSpec(
        TARGET_SCRIPTS[target],
        (
            "--smoke-auto-exit",
            f"--smoke-output={smoke_output}",
        ),
        1,
    )


def _runner_source(spec: TargetSpec, runtime_path: Path) -> str:
    script = json.dumps(str(spec.script))
    script_arguments = json.dumps(spec.arguments, ensure_ascii=False)
    repetitions = spec.repetitions
    runtime = json.dumps(str(runtime_path))
    return f"""from __future__ import annotations
import gc
import json
import runpy
import sys
import threading
import time
from pathlib import Path

target = {script}
target_arguments = {script_arguments}
runtime_path = Path({runtime})
sys.argv = [target, *target_arguments]
jit = getattr(sys, "_jit", None)
started_wall = time.perf_counter()
started_cpu = time.process_time()
allocated_before = sys.getallocatedblocks()
gc_before = gc.get_stats()
exit_code = 0
error_type = ""
pending_error = None
try:
    for _iteration in range({repetitions}):
        runpy.run_path(target, run_name="__main__")
except SystemExit as exc:
    exit_code = exc.code if isinstance(exc.code, int) else int(exc.code is not None)
except BaseException as exc:
    exit_code = 1
    error_type = type(exc).__name__
    pending_error = exc
finally:
    evidence = {{
        "schema": "mohan.tachyon.runtime.v1",
        "python": sys.version.split()[0],
        "implementation": sys.implementation.name,
        "jit_available": bool(jit and jit.is_available()),
        "jit_enabled": bool(jit and jit.is_enabled()),
        "wall_seconds": round(time.perf_counter() - started_wall, 6),
        "cpu_seconds": round(time.process_time() - started_cpu, 6),
        "allocated_blocks_before": allocated_before,
        "allocated_blocks_after": sys.getallocatedblocks(),
        "active_threads_at_end": threading.active_count(),
        "gc_before": gc_before,
        "gc_after": gc.get_stats(),
        "exit_code": exit_code,
        "error_type": error_type,
    }}
    runtime_path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\\n",
        encoding="utf-8",
    )
if pending_error is not None:
    raise pending_error
if exit_code:
    raise SystemExit(exit_code)
"""


def _write_runner(
    spec: TargetSpec,
    runtime_path: Path,
    temp_dir: Path,
) -> Path:
    runner = temp_dir / "tachyon_target.py"
    runner.write_text(
        _runner_source(spec, runtime_path),
        encoding="utf-8",
    )
    return runner


def _profile_environment(
    temp_dir: Path,
    use_user_profile: bool,
) -> dict[str, str]:
    environment = os.environ.copy()
    for key in tuple(environment):
        upper = key.upper()
        if any(
            marker in upper
            for marker in ("API_KEY", "TOKEN", "SECRET", "PASSWORD")
        ):
            environment.pop(key, None)
    # Profile what we ship: the runtime now defaults to JIT-off (0xC0000409
    # family, 2026-08-29), and forcing the JIT here both diverged the evidence
    # from the product and made this gate flaky by betting each CI run on a
    # JIT startup crash.  MOHAN_ENABLE_JIT=1 profiles the experiment instead.
    environment["PYTHON_JIT"] = (
        "1" if environment.get("MOHAN_ENABLE_JIT") == "1" else "0"
    )
    environment["PYTHONUTF8"] = "1"
    environment["QT_QPA_PLATFORM"] = "offscreen"
    if not use_user_profile:
        environment["MOHAN_DATA_DIR"] = str(temp_dir / "profile")
    return environment


def _capture_command(
    args: argparse.Namespace,
    target: str,
    artifacts: ProfileArtifacts,
    runner: Path,
) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "profiling.sampling",
        "run",
        "--native",
        "--opcodes",
        "--mode",
        args.mode,
        "--sampling-rate",
        args.rate,
        "--binary",
        "--compression",
        "none",
        "--output",
        str(artifacts.binary),
    ]
    if TARGET_ALL_THREADS[target]:
        command.append("--all-threads")
    if TARGET_BLOCKING[target]:
        command.append("--blocking")
    if not args.full_session:
        command.extend(("--duration", str(args.duration)))
    command.append(str(runner))
    return command


def _strip_ansi(value: str) -> str:
    return ANSI_ESCAPE.sub("", value).replace("\r", "")


def _run_capture(
    command: list[str],
    environment: Mapping[str, str],
) -> tuple[subprocess.CompletedProcess[str], float]:
    started = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=dict(environment),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    elapsed = time.perf_counter() - started
    stdout = _strip_ansi(completed.stdout)
    stderr = _strip_ansi(completed.stderr)
    if stdout:
        print(stdout, end="" if stdout.endswith("\n") else "\n")
    if stderr:
        print(
            stderr,
            end="" if stderr.endswith("\n") else "\n",
            file=sys.stderr,
        )
    return completed, elapsed


def _replay_to_file(
    binary: Path,
    format_flag: str,
    output: Path,
    environment: Mapping[str, str],
) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "profiling.sampling",
            "replay",
            format_flag,
            "--output",
            str(output),
            str(binary),
        ],
        cwd=ROOT,
        env=dict(environment),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode:
        raise RuntimeError(
            _strip_ansi(completed.stderr)
            or f"Tachyon replay failed for {format_flag}."
        )


def _write_pstats(
    binary: Path,
    output: Path,
    environment: Mapping[str, str],
) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "profiling.sampling",
            "replay",
            "--pstats",
            "--sort",
            "sample-pct",
            "--limit",
            "50",
            str(binary),
        ],
        cwd=ROOT,
        env=dict(environment),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode:
        raise RuntimeError(
            _strip_ansi(completed.stderr) or "Tachyon pstats replay failed."
        )
    output.write_text(
        _strip_ansi(completed.stdout),
        encoding="utf-8",
    )


def _replay_profile(
    artifacts: ProfileArtifacts,
    environment: Mapping[str, str],
) -> None:
    _replay_to_file(
        artifacts.binary,
        "--flamegraph",
        artifacts.flamegraph,
        environment,
    )
    _replay_to_file(
        artifacts.binary,
        "--jsonl",
        artifacts.jsonl,
        environment,
    )
    _write_pstats(artifacts.binary, artifacts.pstats, environment)


def _path_replacements(
    temp_dir: Path,
    environment: Mapping[str, str],
) -> tuple[tuple[str, str], ...]:
    replacements: dict[str, str] = {}

    def register(path: Path, label: str) -> None:
        resolved = path.resolve()
        native = str(resolved)
        forward = resolved.as_posix()
        variants = {native, forward}
        if resolved.drive:
            tail = native[len(resolved.drive) :].lstrip("\\/")
            dotted_tail = tail.replace("\\", ".").replace("/", ".")
            variants.add(f"{resolved.drive}\\.{dotted_tail}")
        for variant in variants:
            replacements[variant] = label
            replacements[json.dumps(variant)[1:-1]] = label

    python_path = environment.get("PYTHONPATH", "")
    for entry in python_path.split(os.pathsep):
        if entry and Path(entry).name.casefold() == "site-packages":
            register(Path(entry), "<site-packages>")
    register(Path(sys.base_prefix) / "Lib", "<stdlib>")
    register(temp_dir, "<temporary>")
    register(ROOT, "<project>")
    register(Path(sys.base_prefix), "<python>")
    register(Path.home(), "<user-home>")
    return tuple(
        sorted(
            replacements.items(),
            key=lambda item: len(item[0]),
            reverse=True,
        )
    )


def _sanitize_text_artifact(
    path: Path,
    replacements: tuple[tuple[str, str], ...],
) -> None:
    content = path.read_text(encoding="utf-8")
    for source, replacement in replacements:
        flags = (
            re.IGNORECASE
            if re.prefixmatch(r"^[a-z]:", source, re.IGNORECASE)
            else 0
        )
        content = re.sub(
            re.escape(source),
            lambda _match, value=replacement: value,
            content,
            flags=flags,
        )
    content = WINDOWS_PRIVATE_PATH.sub("<private-path>", content)
    content = HOME_PRIVATE_PATH.sub("<private-path>", content)
    path.write_text(content, encoding="utf-8")


def _sanitize_profile_outputs(
    artifacts: ProfileArtifacts,
    temp_dir: Path,
    environment: Mapping[str, str],
) -> None:
    replacements = _path_replacements(temp_dir, environment)
    for path in (
        artifacts.flamegraph,
        artifacts.jsonl,
        artifacts.pstats,
    ):
        _sanitize_text_artifact(path, replacements)
    _validate_sanitized_outputs(artifacts, replacements)


def _validate_sanitized_outputs(
    artifacts: ProfileArtifacts,
    replacements: tuple[tuple[str, str], ...],
) -> None:
    for path in (
        artifacts.flamegraph,
        artifacts.jsonl,
        artifacts.pstats,
    ):
        content = path.read_text(encoding="utf-8")
        leaked_source = next(
            (source for source, _replacement in replacements if source in content),
            None,
        )
        if leaked_source is not None:
            raise RuntimeError(
                f"Tachyon output {path.name} retains a private path prefix."
            )
        if WINDOWS_ABSOLUTE_PATH.search(content):
            raise RuntimeError(
                f"Tachyon output {path.name} retains a Windows absolute path."
            )
        if HOME_ABSOLUTE_PATH.search(content):
            raise RuntimeError(
                f"Tachyon output {path.name} retains a home-directory path."
            )


def _json_object(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"{context} must be a JSON object.")
    if not all(isinstance(key, str) for key in value):
        raise ValueError(f"{context} contains a non-string key.")
    return value


def _json_object_list(value: object, context: str) -> list[dict[str, object]]:
    if not isinstance(value, list):
        raise TypeError(f"{context} must be a JSON array.")
    return [
        _json_object(item, f"{context}[{index}]")
        for index, item in enumerate(value)
    ]


def _load_json(path: Path) -> dict[str, object]:
    return _json_object(
        json.loads(path.read_text(encoding="utf-8")),
        str(path),
    )


def _load_jsonl(path: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if line.strip():
            records.append(
                _json_object(
                    json.loads(line),
                    f"{path}:{line_number}",
                )
            )
    return records


def _records(
    records: list[dict[str, object]],
    record_type: str,
) -> tuple[dict[str, object], ...]:
    matches = tuple(
        record
        for record in records
        if record.get("type") == record_type
    )
    if not matches:
        raise ValueError(
            f"Tachyon evidence has no {record_type!r} records."
        )
    return matches


def _single_record(
    records: list[dict[str, object]],
    record_type: str,
) -> dict[str, object]:
    matches = _records(records, record_type)
    if len(matches) != 1:
        raise ValueError(
            f"Expected one Tachyon {record_type!r} record, "
            f"found {len(matches)}."
        )
    return matches[0]


def _record_items(
    records: list[dict[str, object]],
    record_type: str,
    item_key: str,
    context: str,
) -> Iterator[dict[str, object]]:
    for record in _records(records, record_type):
        yield from _json_object_list(record.get(item_key), context)


def _sanitize_profile_path(value: str) -> str:
    normalized = value.replace("\\", "/")
    root = ROOT.as_posix()
    if normalized.casefold().startswith(root.casefold()):
        relative = normalized[len(root) :].lstrip("/")
        return f"<project>/{relative}"
    site_marker = "/site-packages/"
    if site_marker in normalized.casefold():
        index = normalized.casefold().index(site_marker)
        return f"<site-packages>/{normalized[index + len(site_marker):]}"
    stdlib_marker = "/lib/"
    if stdlib_marker in normalized.casefold():
        index = normalized.casefold().index(stdlib_marker)
        return f"<stdlib>/{normalized[index + len(stdlib_marker):]}"
    if normalized.startswith("<") or normalized in {"~", ""}:
        return normalized
    return Path(normalized).name


def _frame_metadata(
    records: list[dict[str, object]],
) -> dict[int, tuple[str, str, int]]:
    strings = {
        int(item["str_id"]): str(item["value"])
        for item in _record_items(
            records,
            "string_table",
            "strings",
            "Tachyon string table",
        )
    }
    metadata: dict[int, tuple[str, str, int]] = {}
    for frame in _record_items(
        records,
        "frame_table",
        "frames",
        "Tachyon frame table",
    ):
        frame_id = int(frame["frame_id"])
        if frame_id in metadata:
            raise ValueError(f"Duplicate Tachyon frame id: {frame_id}.")
        metadata[frame_id] = (
            _sanitize_profile_path(
                strings[int(frame["path_str_id"])]
            ),
            strings[int(frame["func_str_id"])],
            int(frame.get("line", 0)),
        )
    return metadata


def _frame_statistics(
    records: list[dict[str, object]],
) -> tuple[int, list[FrameStats]]:
    end = _single_record(records, "end")
    total_samples = int(end["samples_total"])
    aggregates = tuple(
        record
        for record in _records(records, "agg")
        if record.get("kind") == "frame"
        and record.get("scope") == "final"
    )
    if not aggregates:
        raise ValueError("Tachyon has no final frame aggregate.")
    aggregate_totals = {
        int(record["samples_total"]) for record in aggregates
    }
    if aggregate_totals != {total_samples}:
        raise ValueError(
            "Tachyon aggregate and end sample totals disagree."
        )
    metadata = _frame_metadata(records)
    statistics_rows: list[FrameStats] = []
    seen_frames: set[int] = set()
    for aggregate in aggregates:
        for entry in _json_object_list(
            aggregate.get("entries"),
            "Tachyon aggregate entries",
        ):
            frame_id = int(entry["frame_id"])
            if frame_id in seen_frames:
                raise ValueError(
                    f"Duplicate Tachyon aggregate frame id: {frame_id}."
                )
            seen_frames.add(frame_id)
            path, function, line = metadata[frame_id]
            statistics_rows.append(
                FrameStats(
                    path=path,
                    function=function,
                    line=line,
                    self_samples=int(entry["self"]),
                    cumulative_samples=int(entry["cumulative"]),
                )
            )
    return total_samples, statistics_rows


def _top_frames(
    frames: list[FrameStats],
    total_samples: int,
    limit: int,
    *,
    cumulative: bool,
) -> list[dict[str, object]]:
    key = (
        (lambda frame: frame.cumulative_samples)
        if cumulative
        else (lambda frame: frame.self_samples)
    )
    ranked = sorted(frames, key=key, reverse=True)
    return [
        frame.as_json(total_samples)
        for frame in ranked
        if key(frame) > 0
    ][:limit]


def _match_number(
    pattern: re.Pattern[str],
    text: str,
    group: str,
) -> float | None:
    match = pattern.search(text)
    return float(match.group(group).replace(",", "")) if match else None


def _capture_statistics(
    output: str,
    elapsed_seconds: float,
) -> dict[str, object]:
    sample_read_error_percent = _match_number(
        ERROR_RATE_PATTERN,
        output,
        "percent",
    )
    missed_samples_percent = _match_number(
        MISSED_PATTERN,
        output,
        "percent",
    )
    return {
        "orchestrator_wall_seconds": round(elapsed_seconds, 6),
        "reported_samples": _match_number(
            CAPTURE_PATTERN,
            output,
            "samples",
        ),
        "reported_profile_seconds": _match_number(
            CAPTURE_PATTERN,
            output,
            "seconds",
        ),
        "reported_samples_per_second": _match_number(
            RATE_PATTERN,
            output,
            "rate",
        ),
        "missed_samples": _match_number(
            MISSED_PATTERN,
            output,
            "samples",
        ),
        "missed_samples_percent": missed_samples_percent or 0.0,
        "sample_read_error_percent": sample_read_error_percent,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _artifact_evidence(path: Path) -> dict[str, object]:
    return {
        "name": path.name,
        "bytes": path.stat().st_size,
        "sha256": _sha256(path),
    }


def _host_evidence() -> dict[str, object]:
    return {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "python": sys.version.split()[0],
        "implementation": sys.implementation.name,
        "logical_cpu_count": os.cpu_count(),
    }


def _quality_violations(
    args: argparse.Namespace,
    total_samples: int,
    capture: Mapping[str, object],
    runtime: Mapping[str, object],
) -> tuple[str, ...]:
    violations: list[str] = []
    if total_samples < args.min_samples:
        violations.append(
            f"samples {total_samples} below minimum {args.min_samples}"
        )
    sample_read_error_percent = capture.get("sample_read_error_percent")
    if sample_read_error_percent is None:
        violations.append("profiler did not report a sample-read error rate")
    if (
        isinstance(sample_read_error_percent, int | float)
        and sample_read_error_percent > args.max_sample_read_error_percent
    ):
        violations.append(
            f"sample-read error {sample_read_error_percent:.2f}% above "
            f"{args.max_sample_read_error_percent:.2f}%"
        )
    missed_samples_percent = capture.get("missed_samples_percent")
    if (
        isinstance(missed_samples_percent, int | float)
        and missed_samples_percent > args.max_missed_samples_percent
    ):
        violations.append(
            f"missed samples {missed_samples_percent:.2f}% above "
            f"{args.max_missed_samples_percent:.2f}%"
        )
    if runtime.get("exit_code") != 0:
        violations.append(
            f"target exit code was {runtime.get('exit_code')!r}"
        )
    if runtime.get("jit_available") is not True:
        violations.append("target runtime did not expose the CPython JIT")
    # Evidence must match the shipped JIT policy (off by default since the
    # 2026-08-29 0xC0000409 crash; MOHAN_ENABLE_JIT=1 profiles the experiment).
    expect_jit = os.environ.get("MOHAN_ENABLE_JIT") == "1"
    if runtime.get("jit_enabled") is not expect_jit:
        violations.append(
            "target runtime JIT state "
            f"{runtime.get('jit_enabled')!r} does not match the "
            f"shipped policy (expected {expect_jit})"
        )
    return tuple(violations)


def _build_summary(
    args: argparse.Namespace,
    target: str,
    artifacts: ProfileArtifacts,
    capture_output: str,
    capture_elapsed: float,
) -> tuple[dict[str, object], tuple[str, ...]]:
    records = _load_jsonl(artifacts.jsonl)
    total_samples, frames = _frame_statistics(records)
    runtime = _load_json(artifacts.runtime)
    capture = _capture_statistics(capture_output, capture_elapsed)
    violations = _quality_violations(
        args,
        total_samples,
        capture,
        runtime,
    )
    project_frames = [
        frame for frame in frames if frame.path.startswith("<project>/")
    ]
    gc_samples = sum(
        frame.self_samples
        for frame in frames
        if frame.function == "<GC>"
    )
    summary: dict[str, object] = {
        "schema": "mohan.tachyon.evidence.v1",
        "status": "pass" if not violations else "fail",
        "generated_at": datetime.now(UTC).isoformat(),
        "target": target,
        "expected_cadence_hz": TARGET_CADENCE_HZ[target],
        "configuration": {
            "requested_rate": args.rate,
            "mode": args.mode,
            "all_threads": TARGET_ALL_THREADS[target],
            "blocking_stack_reads": TARGET_BLOCKING[target],
            "native_frames": True,
            "opcode_sampling": True,
            "duration_limit_seconds": (
                None if args.full_session else args.duration
            ),
            "workload_repetitions": (
                1 if args.full_session else TARGET_REPETITIONS[target]
            ),
            "isolated_user_profile": not args.use_user_profile,
        },
        "host": _host_evidence(),
        "runtime": runtime,
        "capture": {
            **capture,
            "stored_samples": total_samples,
            "gc_direct_samples": gc_samples,
            "project_direct_samples": sum(
                frame.self_samples for frame in project_frames
            ),
        },
        "top_direct_frames": _top_frames(
            frames,
            total_samples,
            args.top_frames,
            cumulative=False,
        ),
        "top_cumulative_frames": _top_frames(
            frames,
            total_samples,
            args.top_frames,
            cumulative=True,
        ),
        "top_project_direct_frames": _top_frames(
            project_frames,
            total_samples,
            args.top_frames,
            cumulative=False,
        ),
        "artifacts": [
            _artifact_evidence(path)
            for path in artifacts.published_outputs()
        ],
        "quality_gate": {
            "minimum_samples": args.min_samples,
            "maximum_sample_read_error_percent": (
                args.max_sample_read_error_percent
            ),
            "maximum_missed_samples_percent": (
                args.max_missed_samples_percent
            ),
            "violations": list(violations),
        },
    }
    return summary, violations


def _write_json(path: Path, value: Mapping[str, object]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _profile_target(
    args: argparse.Namespace,
    target: str,
) -> ProfileOutcome:
    artifacts = _artifact_paths(
        target,
        args.output_dir,
        args.output,
    )
    artifacts.summary.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=f"mohan-tachyon-{target}-"
    ) as raw_temp_dir:
        temp_dir = Path(raw_temp_dir)
        artifacts = artifacts.with_temporary_binary(
            temp_dir / f"mohan-tachyon-{target}.profile.bin"
        )
        spec = _target_spec(target, temp_dir, args.full_session)
        runner = _write_runner(spec, artifacts.runtime, temp_dir)
        environment = _profile_environment(
            temp_dir,
            args.use_user_profile,
        )
        completed, elapsed = _run_capture(
            _capture_command(args, target, artifacts, runner),
            environment,
        )
        combined_output = _strip_ansi(
            f"{completed.stdout}\n{completed.stderr}"
        )
        if completed.returncode:
            raise RuntimeError(
                f"Tachyon target {target} failed with "
                f"exit code {completed.returncode}."
            )
        if not artifacts.runtime.is_file():
            raise RuntimeError(
                f"Tachyon target {target} did not write runtime evidence."
            )
        _replay_profile(artifacts, environment)
        _sanitize_profile_outputs(artifacts, temp_dir, environment)
    summary, violations = _build_summary(
        args,
        target,
        artifacts,
        combined_output,
        elapsed,
    )
    _write_json(artifacts.summary, summary)
    print(
        "MOHAN_TACHYON_PROFILE_"
        f"{'OK' if not violations else 'FAILED'} "
        f"target={target} summary={artifacts.summary}"
    )
    return ProfileOutcome(target, artifacts.summary, violations)


def _write_suite_summary(
    output_dir: Path,
    outcomes: tuple[ProfileOutcome, ...],
) -> Path:
    path = output_dir.resolve() / "mohan-tachyon-suite-summary.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    output_root = output_dir.resolve()
    summary = {
        "schema": "mohan.tachyon.suite.v1",
        "status": (
            "pass"
            if all(not outcome.violations for outcome in outcomes)
            else "fail"
        ),
        "generated_at": datetime.now(UTC).isoformat(),
        "python": sys.version.split()[0],
        "jit_required": True,
        "targets": [
            {
                "target": outcome.target,
                "summary": _portable_summary_path(
                    outcome.summary,
                    output_root,
                ),
                "sha256": _sha256(outcome.summary),
                "violations": list(outcome.violations),
            }
            for outcome in outcomes
        ],
    }
    _write_json(path, summary)
    return path


def _portable_summary_path(summary: Path, output_root: Path) -> str:
    try:
        return summary.resolve().relative_to(output_root).as_posix()
    except ValueError:
        return summary.name


def main() -> int:
    args = arguments()
    _validate_arguments(args)
    outcomes = tuple(
        _profile_target(args, target)
        for target in _targets(args.target)
    )
    suite = _write_suite_summary(args.output_dir, outcomes)
    print(f"MOHAN_TACHYON_SUITE_EVIDENCE={suite}")
    return int(any(outcome.violations for outcome in outcomes))


if __name__ == "__main__":
    raise SystemExit(main())
