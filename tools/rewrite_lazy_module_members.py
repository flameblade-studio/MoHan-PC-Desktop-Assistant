from __future__ import annotations

lazy from pathlib import Path

lazy from migrate_python315_imports import python_files

IMPORT_REPLACEMENTS = frozendict({
    "lazy import urllib.request as urllib_request": (
        "lazy from urllib.request import Request, urlopen"
    ),
    "lazy import urllib.error as urllib_error": (
        "lazy from urllib.error import HTTPError, URLError"
    ),
    "lazy import urllib.parse as urllib_parse": (
        "lazy from urllib.parse import parse_qs, quote, urlencode, urlparse"
    ),
    "lazy import importlib.metadata as importlib_metadata": (
        "lazy from importlib.metadata import Distribution, distribution as metadata_distribution"
    ),
    "lazy import xml.etree.ElementTree as ET": (
        "lazy from xml.etree.ElementTree import parse as parse_xml"
    ),
})
MEMBER_REPLACEMENTS = frozendict({
    "urllib_request.Request": "Request",
    "urllib_request.urlopen": "urlopen",
    "urllib_error.HTTPError": "HTTPError",
    "urllib_error.URLError": "URLError",
    "urllib_parse.parse_qs": "parse_qs",
    "urllib_parse.quote": "quote",
    "urllib_parse.urlencode": "urlencode",
    "urllib_parse.urlparse": "urlparse",
    "importlib_metadata.Distribution": "Distribution",
    "importlib_metadata.distribution": "metadata_distribution",
    "ET.parse": "parse_xml",
})


def main() -> int:
    changed = 0
    for path in python_files():
        if path == Path(__file__).resolve():
            continue
        original = path.read_text(encoding="utf-8")
        updated = original
        for old, new in IMPORT_REPLACEMENTS.items():
            updated = updated.replace(old, new)
        for old, new in MEMBER_REPLACEMENTS.items():
            updated = updated.replace(old, new)
        if updated != original:
            path.write_text(updated, encoding="utf-8", newline="")
            changed += 1
    print(f"PYTHON315_LAZY_MODULE_MEMBERS_REWRITTEN files={changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
