#!/usr/bin/env python3
"""Negative tests: blank and exact-SHA tampering must fail closed."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
VALIDATOR = HERE / "validate_owner_exact_sha_declaration.py"
BLANK = HERE / "owner-exact-sha-declaration.blank.json"


def run(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(VALIDATOR), "--declaration", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> int:
    blank = run(BLANK)
    if blank.returncode != 4 or "unsigned, incomplete, or hash-unbound" not in blank.stdout:
        print("FAIL: blank form did not fail closed")
        return 1
    data = json.loads(BLANK.read_text(encoding="utf-8"))
    data["rows"][0]["selected_asset_sha256"] = "0" * 64
    with tempfile.TemporaryDirectory(prefix="mohan-owner-declaration-negative-") as directory:
        tampered_path = Path(directory) / "tampered.json"
        tampered_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tampered = run(tampered_path)
    if tampered.returncode != 4 or "seq01:SELECTED_SHA_MISMATCH_OR_MISSING" not in tampered.stdout:
        print("FAIL: exact-SHA tampering did not fail closed")
        return 1
    print("PASS: blank exit 4; tampered exact SHA exit 4")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
