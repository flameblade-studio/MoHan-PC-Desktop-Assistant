from __future__ import annotations

import hashlib
import json
from pathlib import Path

path = Path(__file__).with_name("training-env-notices.json")
data = json.loads(path.read_text(encoding="utf-8"))
allow = set(data["allowlist"])
checks = {}
for component in data["components"]:
    key = f"{component['name']}=={component['version']}"
    metadata = Path(component["metadata_path"])
    checks[f"{key}:metadata"] = metadata.is_file() and hashlib.sha256(metadata.read_bytes()).hexdigest().upper() == component["metadata_sha256"]
    checks[f"{key}:license_files"] = bool(component["license_files"]) and all(Path(record["path"]).is_file() and hashlib.sha256(Path(record["path"]).read_bytes()).hexdigest().upper() == record["sha256"] for record in component["license_files"])
    expected = "PASS" if all(item in allow for item in component["normalized_license_evidence"]) else "BLOCK"
    checks[f"{key}:classification"] = component["admission"] == expected
blocked = [component["name"] for component in data["components"] if component["admission"] == "BLOCK"]
checks["summary"] = blocked == data["summary"]["blocked_components"]
checks["formal_gate"] = data["formal_training_admission"] == ("BLOCK" if blocked else "PASS")
probes = data["runtime_probes"]
checks["peft_only_visibility"] = probes == {
    "peft_present": True,
    "datasets_present": False,
    "aiohappyeyeballs_present": False,
    "cuda_available": True,
}
technical_valid = all(checks.values())
print(json.dumps({"checks": checks, "technical_validator_passed": technical_valid, "formal_training_admission": data["formal_training_admission"], "blocked_components": blocked}, ensure_ascii=False, indent=2))
raise SystemExit(4 if not technical_valid or blocked else 0)
