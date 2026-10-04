from __future__ import annotations

lazy import ast
lazy from pathlib import Path

lazy import pytest

lazy from tools import rewrite_lazy_dotted_imports
lazy from tools.prune_unused_lazy_imports import prune_unused_lazy_imports
lazy from tools.remove_top_level_definitions import remove_definitions


@pytest.mark.parametrize(
    "original",
    (
        "lazy import os; KEEP = 42\n",
        "KEEP = '墨寒'; lazy import os\n",
        "lazy import os, json; KEEP = json.dumps(42)\n",
        "lazy from pathlib import (\n    Path,\n); KEEP = 42\n",
    ),
)
def test_pruner_rejects_shared_physical_lines(tmp_path: Path, original: str) -> None:
    source = tmp_path / "source.py"
    source.write_bytes(original.encode("utf-8"))
    with pytest.raises(RuntimeError, match="shared physical line"):
        prune_unused_lazy_imports(source)
    assert source.read_bytes() == original.encode("utf-8")


@pytest.mark.parametrize(
    ("original", "class_name"),
    (
        ("REMOVE = 1; KEEP = 42\n", None),
        ("KEEP = '墨寒'; REMOVE = 1\n", None),
        ("REMOVE = (\n    1\n); KEEP = 42\n", None),
        ("class Example:\n    REMOVE = 1; KEEP = 42\n", "Example"),
        ("class Example: REMOVE = 1\n", "Example"),
    ),
)
def test_definition_remover_rejects_shared_physical_lines(
    tmp_path: Path, original: str, class_name: str | None,
) -> None:
    source = tmp_path / "source.py"
    source.write_bytes(original.encode("utf-8"))
    with pytest.raises(RuntimeError, match="shared physical line"):
        remove_definitions(source, frozenset({"REMOVE"}), class_name=class_name)
    assert source.read_bytes() == original.encode("utf-8")


def _rewrite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, original: str) -> str:
    source = tmp_path / "source.py"
    source.write_bytes(original.encode("utf-8"))
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1] / "tools"))
    monkeypatch.setattr(rewrite_lazy_dotted_imports, "python_files", lambda: [source])
    assert rewrite_lazy_dotted_imports.main() == 0
    return source.read_bytes().decode("utf-8")


def test_dotted_rewriter_preserves_eager_imports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = 'import urllib.request\nTARGET = "urllib.request.urlopen"\n'
    assert _rewrite(tmp_path, monkeypatch, original) == original


def test_dotted_rewriter_changes_only_bound_expressions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = (
        "lazy import urllib.request\r\n"
        '# urllib.request.urlopen remains the mock target\r\n'
        'TARGET = "urllib.request.urlopen"\r\n'
        "結果 = urllib.request.urlopen\r\n"
        'TEXT = f"urllib.request {urllib.request.__name__}"\r\n'
    )
    expected = (
        "lazy import urllib.request as urllib_request\r\n"
        '# urllib.request.urlopen remains the mock target\r\n'
        'TARGET = "urllib.request.urlopen"\r\n'
        "結果 = urllib_request.urlopen\r\n"
        'TEXT = f"urllib.request {urllib_request.__name__}"\r\n'
    )
    rewritten = _rewrite(tmp_path, monkeypatch, original)
    assert rewritten == expected
    ast.parse(rewritten)
    assert _rewrite(tmp_path, monkeypatch, rewritten) == expected


def test_dotted_rewriter_handles_multiple_lazy_imports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = (
        "lazy import urllib.request, urllib.error\n"
        "def references():\n"
        "    return urllib.request.Request, urllib.error.URLError\n"
    )
    rewritten = _rewrite(tmp_path, monkeypatch, original)
    assert rewritten == (
        "lazy import urllib.request as urllib_request, urllib.error as urllib_error\n"
        "def references():\n"
        "    return urllib_request.Request, urllib_error.URLError\n"
    )


@pytest.mark.parametrize(
    "suffix",
    (
        "urllib_request = 42\nRESULT = urllib.request\n",
        "def reference(urllib):\n    return urllib.request\n",
        "import urllib.parse\nRESULT = urllib.request\n",
        "RESULT = urllib\n",
        "RESULT = urllib.parse\n",
    ),
)
def test_dotted_rewriter_rejects_ambiguous_bindings_atomically(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, suffix: str,
) -> None:
    original = "lazy import urllib.request\n" + suffix
    with pytest.raises(RuntimeError, match="binding"):
        _rewrite(tmp_path, monkeypatch, original)
    assert (tmp_path / "source.py").read_bytes() == original.encode("utf-8")
