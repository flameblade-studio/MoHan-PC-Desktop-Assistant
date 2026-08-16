from __future__ import annotations

lazy import argparse
lazy import os
lazy import sys
lazy import tempfile
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy from tools.profile_mohan_tachyon import (
    _artifact_paths,
    _capture_statistics,
    _frame_statistics,
    _quality_violations,
    _sanitize_profile_outputs,
    _sanitize_profile_path,
    _top_frames,
)


def test_capture_statistics_support_current_and_legacy_output() -> None:
    current = _capture_statistics(
        "Captured 1,234 samples in 1.25 seconds\n"
        "Sample rate: 987.65 samples/sec\n"
        "Error rate: 1.75\n"
        "Warning: missed 16 samples from the expected total of 1,250 "
        "(1.28%)",
        1.5,
    )
    assert current == {
        "orchestrator_wall_seconds": 1.5,
        "reported_samples": 1234.0,
        "reported_profile_seconds": 1.25,
        "reported_samples_per_second": 987.65,
        "missed_samples": 16.0,
        "missed_samples_percent": 1.28,
        "sample_read_error_percent": 1.75,
    }

    legacy = _capture_statistics(
        "missed 25 samples while sampling (2.50%)",
        2.0,
    )
    assert legacy["missed_samples"] == 25.0
    assert legacy["missed_samples_percent"] == 2.5
    assert legacy["sample_read_error_percent"] is None


def test_chunked_tachyon_tables_and_aggregates() -> None:
    records: list[dict[str, object]] = [
        {
            "type": "string_table",
            "strings": [
                {"str_id": 1, "value": str(ROOT / "integrations" / "speech.py")},
                {"str_id": 2, "value": "emit_viseme"},
            ],
        },
        {
            "type": "string_table",
            "strings": [
                {
                    "str_id": 3,
                    "value": str(ROOT / "domain" / "expression_system.py"),
                },
                {"str_id": 4, "value": "arbitrate"},
            ],
        },
        {
            "type": "frame_table",
            "frames": [
                {
                    "frame_id": 10,
                    "path_str_id": 1,
                    "func_str_id": 2,
                    "line": 101,
                }
            ],
        },
        {
            "type": "frame_table",
            "frames": [
                {
                    "frame_id": 11,
                    "path_str_id": 3,
                    "func_str_id": 4,
                    "line": 202,
                }
            ],
        },
        {
            "type": "agg",
            "kind": "frame",
            "scope": "final",
            "samples_total": 100,
            "entries": [
                {"frame_id": 10, "self": 60, "cumulative": 80}
            ],
        },
        {
            "type": "agg",
            "kind": "frame",
            "scope": "final",
            "samples_total": 100,
            "entries": [
                {"frame_id": 11, "self": 40, "cumulative": 55}
            ],
        },
        {"type": "end", "samples_total": 100},
    ]

    total_samples, frames = _frame_statistics(records)
    assert total_samples == 100
    assert len(frames) == 2
    assert {frame.path for frame in frames} == {
        "<project>/integrations/speech.py",
        "<project>/domain/expression_system.py",
    }
    assert _top_frames(
        frames,
        total_samples,
        1,
        cumulative=False,
    )[0]["function"] == "emit_viseme"


def test_profile_paths_are_private_and_binary_is_temporary() -> None:
    with tempfile.TemporaryDirectory(prefix="mohan-tachyon-test-") as raw:
        temporary = Path(raw)
        output = temporary / "published"
        artifacts = _artifact_paths("lipsync", output, None)
        artifacts.flamegraph.parent.mkdir(parents=True, exist_ok=True)
        project_path = str(ROOT)
        if os.name == "nt":
            project_path = project_path.swapcase()
        private_values = "\n".join(
            (
                str(Path(project_path) / "integrations" / "speech.py"),
                str(temporary / "tachyon_target.py"),
                str(Path.home() / "private-profile.json"),
                r"Z:\unregistered-runner\private\trace.py",
            )
        )
        for path in (
            artifacts.flamegraph,
            artifacts.jsonl,
            artifacts.pstats,
        ):
            path.write_text(private_values, encoding="utf-8")

        _sanitize_profile_outputs(
            artifacts,
            temporary,
            {"PYTHONPATH": os.environ.get("PYTHONPATH", "")},
        )

        published = artifacts.published_outputs()
        assert artifacts.binary not in published
        assert artifacts.summary not in published
        assert not artifacts.binary.exists()
        for path in published[:3]:
            content = path.read_text(encoding="utf-8")
            assert project_path not in content
            assert str(Path.home()) not in content
            assert "unregistered-runner" not in content
            assert "<project>" in content or "<temporary>" in content

    assert _sanitize_profile_path(str(ROOT / "domain" / "lip_sync.py")) == (
        "<project>/domain/lip_sync.py"
    )


def test_quality_gate_requires_samples_low_error_and_jit() -> None:
    arguments = argparse.Namespace(
        min_samples=20,
        max_sample_read_error_percent=5.0,
        max_missed_samples_percent=5.0,
    )
    passing = _quality_violations(
        arguments,
        100,
        {
            "sample_read_error_percent": 1.0,
            "missed_samples_percent": 0.5,
        },
        {"exit_code": 0, "jit_available": True, "jit_enabled": True},
    )
    assert passing == ()

    failing = _quality_violations(
        arguments,
        10,
        {
            "sample_read_error_percent": 7.0,
            "missed_samples_percent": 8.0,
        },
        {"exit_code": 1, "jit_available": False, "jit_enabled": False},
    )
    assert len(failing) == 6
    assert any("below minimum" in item for item in failing)
    assert any("sample-read error" in item for item in failing)
    assert any("missed samples" in item for item in failing)
    assert any("JIT" in item for item in failing)


def main() -> None:
    test_capture_statistics_support_current_and_legacy_output()
    test_chunked_tachyon_tables_and_aggregates()
    test_profile_paths_are_private_and_binary_is_temporary()
    test_quality_gate_requires_samples_low_error_and_jit()
    print("TACHYON_ENTERPRISE_EVIDENCE_OK")


if __name__ == "__main__":
    main()
