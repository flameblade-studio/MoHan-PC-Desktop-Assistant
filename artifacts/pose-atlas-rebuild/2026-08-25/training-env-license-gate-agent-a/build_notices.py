from __future__ import annotations

import email
import hashlib
import importlib.util
import json
from pathlib import Path

import torch

ENV = Path(r"D:\FlamebladeStudio\CodexProjects\.third-party-cache\mohan-flux-training-py312")
SP = ENV / "Lib" / "site-packages"
OUT = Path(__file__).resolve().parent
ALLOW = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "CC0-1.0", "CC-BY"}
NORMALIZED = {
    "aiohappyeyeballs": ["PSF-2.0"],
    "aiohttp": ["Apache-2.0", "MIT"],
    "aiosignal": ["Apache-2.0"],
    "attrs": ["MIT"],
    "datasets": ["Apache-2.0"],
    "dill": ["BSD-3-Clause"],
    "frozenlist": ["Apache-2.0"],
    "fsspec": ["BSD-3-Clause"],
    "multidict": ["Apache-2.0"],
    "multiprocess": ["BSD-3-Clause"],
    "pandas": ["BSD-3-Clause"],
    "peft": ["Apache-2.0"],
    "pip": ["MIT"],
    "propcache": ["Apache-2.0"],
    "pyarrow": ["Apache-2.0"],
    "python-dateutil": ["Apache-2.0", "BSD-3-Clause"],
    "six": ["MIT"],
    "tzdata": ["Apache-2.0"],
    "xxhash": ["BSD-2-Clause"],
    "yarl": ["Apache-2.0"],
}

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()

rows = []
for dist in sorted(SP.glob("*.dist-info")):
    metadata_path = dist / "METADATA"
    metadata = email.message_from_bytes(metadata_path.read_bytes())
    name = metadata["Name"]
    key = name.casefold()
    evidence = []
    for path in sorted(dist.rglob("*")):
        if path.is_file() and any(token in path.name.upper() for token in ("LICENSE", "LICENCE", "COPYING", "NOTICE")):
            evidence.append({"path": str(path), "sha256": digest(path), "bytes": path.stat().st_size})
    licenses = NORMALIZED.get(key, ["UNKNOWN"])
    admitted = bool(evidence) and all(license_id in ALLOW for license_id in licenses)
    rows.append({
        "name": name,
        "version": metadata["Version"],
        "dist_info": str(dist),
        "metadata_path": str(metadata_path),
        "metadata_sha256": digest(metadata_path),
        "metadata_license": metadata.get("License"),
        "metadata_license_expression": metadata.get("License-Expression"),
        "normalized_license_evidence": licenses,
        "license_files": evidence,
        "admission": "PASS" if admitted else "BLOCK",
        "block_reason": None if admitted else ("LICENSE_OUTSIDE_USER_ALLOWLIST" if licenses != ["UNKNOWN"] else "UNKNOWN_OR_UNMAPPED_LICENSE"),
    })

blocks = [row for row in rows if row["admission"] == "BLOCK"]
payload = {
    "schema": "mohan.training_env_license_gate.v1",
    "environment": str(ENV),
    "python": str(ENV / "Scripts" / "python.exe"),
    "inherits_system_site_packages": True,
    "scope": "packages installed directly into this venv site-packages; inherited base environment remains under its separate SBOM gate",
    "allowlist": sorted(ALLOW),
    "components": rows,
    "summary": {"component_count": len(rows), "pass_count": len(rows) - len(blocks), "block_count": len(blocks), "blocked_components": [row["name"] for row in blocks]},
    "runtime_probes": {
        "peft_present": importlib.util.find_spec("peft") is not None,
        "datasets_present": importlib.util.find_spec("datasets") is not None,
        "aiohappyeyeballs_present": importlib.util.find_spec("aiohappyeyeballs") is not None,
        "cuda_available": torch.cuda.is_available(),
    },
    "formal_training_admission": "PASS" if not blocks else "BLOCK",
    "mutation_performed": False,
}
(OUT / "training-env-notices.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(payload["summary"], ensure_ascii=False))
