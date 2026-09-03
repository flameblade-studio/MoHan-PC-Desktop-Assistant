from __future__ import annotations

lazy import json
lazy import subprocess
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

lazy import pytest
lazy from tools import traffic_report


DATA_DIR = Path(__file__).parent / "data"
EXPECTED_API_CALLS = 6
EXPECTED_RELEASE_DOWNLOADS = 9
EXPECTED_VIEW_COUNT = 120


def _load_fixture(name: str) -> dict[str, object]:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def _fixture_api(
    bundle: dict[str, object],
    calls: list[tuple[str, bool]],
):
    def api_call(endpoint: str, *, paginate: bool = False) -> object:
        calls.append((endpoint, paginate))
        if endpoint.endswith("/traffic/views"):
            return bundle["views"]
        if endpoint.endswith("/traffic/clones"):
            return bundle["clones"]
        if endpoint.endswith("/traffic/popular/paths"):
            return bundle["popular_paths"]
        if endpoint.endswith("/traffic/popular/referrers"):
            return bundle["popular_referrers"]
        if endpoint.endswith("/releases?per_page=100"):
            return bundle["releases"]
        if endpoint.startswith("repos/"):
            return bundle["repository"]
        raise AssertionError(f"unexpected API endpoint: {endpoint}")

    return api_call


def _snapshot(name: str, month: str) -> dict[str, object]:
    calls: list[tuple[str, bool]] = []
    snapshot = traffic_report.collect_snapshot(
        _fixture_api(_load_fixture(name), calls),
        month=month,
        collected_at="2026-09-03T01:02:03+00:00",
    )
    assert calls[-1][1] is True
    return snapshot


def test_collects_all_required_metrics_and_preserves_raw_payloads() -> None:
    fixture = _load_fixture("traffic_report-current.json")
    calls: list[tuple[str, bool]] = []
    snapshot = traffic_report.collect_snapshot(
        _fixture_api(fixture, calls),
        month="2026-09",
        collected_at="2026-09-03T01:02:03+00:00",
    )
    summary = snapshot["metrics"]["summary"]
    assert summary == {
        "views": EXPECTED_VIEW_COUNT,
        "unique_visitors": 24,
        "clones": 80,
        "unique_cloners": 12,
        "release_downloads": EXPECTED_RELEASE_DOWNLOADS,
        "stars": 7,
        "forks": 3,
        "watchers": 4,
        "google_uniques": 8,
        "ironman_uniques": 5,
    }
    assert snapshot["raw"]["views"] == fixture["views"]
    assert snapshot["metrics"]["release_downloads_total"] == EXPECTED_RELEASE_DOWNLOADS
    assert len(calls) == EXPECTED_API_CALLS
    assert calls[-1][0].endswith("/releases?per_page=100")


def test_render_has_four_languages_correct_comparison_and_release_rows() -> None:
    current = _snapshot("traffic_report-current.json", "2026-09")
    previous = _snapshot("traffic_report-previous.json", "2026-08")
    report = traffic_report.render_report(current, previous)
    for heading in traffic_report.LANGUAGE_HEADINGS:
        assert f"## {heading}" in report
    assert "| Unique visitors | 24 | 18 | +6 | 21 |" in report
    assert "| Google | 20 | 8 |" in report
    assert "| ithelp.ithome.com.tw | 12 | 5 |" in report
    assert "| v1.2.0 | 2 | 7 | 6 | +1 |" in report
    assert "| v1.0.0 | 0 | — | 0 | — |" in report
    assert "Owner input required" in report
    assert "Issue #129" in report


def test_writes_markdown_and_raw_json_together() -> None:
    current = _snapshot("traffic_report-current.json", "2026-09")
    previous = _snapshot("traffic_report-previous.json", "2026-08")
    with TemporaryDirectory(prefix="mohan-traffic-report-test-") as raw_dir:
        report_path, raw_path = traffic_report.write_outputs(
            current,
            previous,
            Path(raw_dir),
        )
        assert report_path.name == "traffic-2026-09.md"
        assert raw_path.name == "traffic-2026-09.json"
        assert report_path.stat().st_size > 0
        saved = json.loads(raw_path.read_text(encoding="utf-8"))
        assert saved["raw"]["views"]["count"] == EXPECTED_VIEW_COUNT
        assert "traffic-2026-09.json" in report_path.read_text(encoding="utf-8")


def test_missing_required_api_data_fails_closed() -> None:
    fixture = _load_fixture("traffic_report-current.json")
    del fixture["clones"]["uniques"]
    with pytest.raises(traffic_report.TrafficReportError, match="uniques"):
        traffic_report.collect_snapshot(
            _fixture_api(fixture, []),
            month="2026-09",
            collected_at="2026-09-03T01:02:03+00:00",
        )


def test_gh_api_failure_is_explicit_and_does_not_call_the_network(
    monkeypatch,
) -> None:
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args,
            returncode=1,
            stdout="",
            stderr="HTTP 403: Resource not accessible by integration",
        )

    monkeypatch.setattr(traffic_report.subprocess, "run", fake_run)
    with pytest.raises(traffic_report.TrafficReportError, match="exit 1"):
        traffic_report.gh_api("repos/example/project/traffic/views")


def test_main_does_not_create_outputs_when_collection_fails(
    monkeypatch,
    capsys,
) -> None:
    def fail(*args, **kwargs):
        raise traffic_report.TrafficReportError("測試用 API 失敗")

    monkeypatch.setattr(traffic_report, "gh_api", fail)
    with TemporaryDirectory(prefix="mohan-traffic-report-fail-") as raw_dir:
        output_dir = Path(raw_dir) / "reports"
        assert traffic_report.main(
            ["--month", "2026-09", "--output-dir", str(output_dir)]
        ) == 1
        assert not output_dir.exists()
    assert "測試用 API 失敗" in capsys.readouterr().err
