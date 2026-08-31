"""Add accepted view fragments to an immutable vault, then try exact-600."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

from assemble_exact600_staging import VIEWS, validate_fragment


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fragment", type=Path, action="append", required=True)
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--exact600-output", type=Path, required=True)
    args = parser.parse_args()
    vault = args.vault.resolve()
    exact600_output = args.exact600_output.resolve()

    incoming: dict[str, tuple[Path, str]] = {}
    for raw_path in args.fragment:
        path = raw_path.resolve()
        fragment, _ = validate_fragment(path)
        view = str(fragment["view_id"])
        if view not in VIEWS or view in incoming:
            raise ValueError(f"invalid or duplicate incoming view: {view}")
        incoming[view] = (path, sha256(path))

    # Preflight the whole batch before writing any fragment.
    for view, (_, incoming_hash) in incoming.items():
        target = vault / f"{view}.manifest-fragment.json"
        lock = vault / f"{view}.manifest-fragment.sha256"
        if target.exists() != lock.exists():
            raise ValueError(f"incomplete vault entry: {view}")
        if target.exists():
            locked_hash = lock.read_text(encoding="ascii").strip().lower()
            actual_hash = sha256(target).lower()
            if actual_hash != locked_hash:
                raise ValueError(f"vault fragment hash drifted: {view}")
            if incoming_hash.lower() != locked_hash:
                raise FileExistsError(f"refusing to replace accepted view: {view}")

    vault.mkdir(parents=True, exist_ok=True)
    added: list[str] = []
    idempotent: list[str] = []
    for view, (source, incoming_hash) in incoming.items():
        target = vault / f"{view}.manifest-fragment.json"
        lock = vault / f"{view}.manifest-fragment.sha256"
        if target.exists():
            idempotent.append(view)
            continue
        fragment_temp = vault / f".{target.name}.{uuid.uuid4().hex}.tmp"
        lock_temp = vault / f".{lock.name}.{uuid.uuid4().hex}.tmp"
        try:
            fragment_temp.write_bytes(source.read_bytes())
            if sha256(fragment_temp).lower() != incoming_hash.lower():
                raise ValueError(f"fragment copy hash mismatch: {view}")
            lock_temp.write_text(incoming_hash.lower() + "\n", encoding="ascii")
            os.replace(fragment_temp, target)
            os.replace(lock_temp, lock)
            added.append(view)
        finally:
            fragment_temp.unlink(missing_ok=True)
            lock_temp.unlink(missing_ok=True)

    assembler = Path(__file__).with_name("assemble_exact600_staging.py")
    completed = subprocess.run(
        [
            sys.executable,
            str(assembler),
            "--fragments-root",
            str(vault),
            "--output-dir",
            str(exact600_output),
        ],
        text=True,
        capture_output=True,
    )
    status = {
        "added": added,
        "idempotent": idempotent,
        "vault_views": len(tuple(vault.glob("*.manifest-fragment.json"))),
        "exact600_exit_code": completed.returncode,
        "exact600_created": exact600_output.is_dir(),
    }
    print(json.dumps(status, ensure_ascii=False))
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    return 0 if completed.returncode == 0 else 3


if __name__ == "__main__":
    raise SystemExit(main())
