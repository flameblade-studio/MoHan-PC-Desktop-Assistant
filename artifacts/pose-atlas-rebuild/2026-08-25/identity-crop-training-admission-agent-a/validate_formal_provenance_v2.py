"""Read-only, fail-closed provenance report; never authorizes training.

SPDX-License-Identifier: MIT
Copyright (c) 2026 Flameblade Studio
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


PROJECT = Path(r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision")
ARTIFACTS = PROJECT / "artifacts/pose-atlas-rebuild/2026-08-25"
CACHE = Path(r"D:\FlamebladeStudio\CodexProjects\.third-party-cache")
ALLOWLIST = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "CC0-1.0", "CC-BY"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def check(path: Path, expected: str, tokens: tuple[str, ...] = ()) -> dict:
    item = {"path": str(path), "expected_sha256": expected, "exists": path.is_file()}
    if not item["exists"]:
        return item | {"sha256": None, "hash_match": False, "text_match": False}
    actual = sha256(path)
    text_match = True
    if tokens:
        text = path.read_text(encoding="utf-8", errors="replace")
        text_match = all(token in text for token in tokens)
    return item | {"sha256": actual, "hash_match": actual == expected, "text_match": text_match}


def files_pass(items: list[dict]) -> bool:
    return all(x["exists"] and x["hash_match"] and x["text_match"] for x in items)


def main() -> int:
    approval_path = ARTIFACTS / "mohan-authority-only-identity-training-manifest-agent-b/human-training-approval.json"
    approval_file = check(approval_path, "33640655E47FCF6AE17E23F4CA4C0AC79B761CED6D80AA5E8C1738321BA3D6CD")
    approval = json.loads(approval_path.read_text(encoding="utf-8")) if approval_file["exists"] else {}
    artwork_pass = (
        files_pass([approval_file])
        and approval.get("status") == "PASS"
        and approval.get("garment_excluded") is True
        and approval.get("horizontal_mirror_used") is False
    )

    flux = CACHE / "huggingface/hub/models--black-forest-labs--FLUX.1-schnell/snapshots/741f7c3ce8b383c54771c7003378a50191e9efe9"
    flux_files = [
        check(flux / "README.md", "66F915FF73552215A78F83852312EDA079AF1F5A08A258B6B6733350101C58AA", ("license: apache-2.0", "commercial purposes")),
        check(flux / "model_index.json", "24946DF21FF25E210486B5F6B14208983A90C9C73F8D48CFA724C0E4E03F7201"),
    ]
    flux_pass = files_pass(flux_files) and "Apache-2.0" in ALLOWLIST

    trainer = ARTIFACTS / "flux-nf4-cached-single-step-agent-a/cached_single_step.py"
    trainer_license = CACHE / "diffusers-source-a949d3dd/LICENSE"
    trainer_files = [
        check(trainer, "437EE06299627BECA0E58486F584918164FD26566501EF387CABFBD0D9B603FF"),
        check(trainer_license, "E28423074EF718E6580A2C15459CDBF08D01EABAF0218754AD1B65DB0C1F4CB6", ("Apache License", "Version 2.0")),
    ]
    trainer_text = trainer.read_text(encoding="utf-8", errors="replace") if trainer.is_file() else ""
    derivation_bound = all(token in trainer_text for token in (
        "SPDX-License-Identifier: Apache-2.0",
        "a949d3dd906528363d2b61f7f0b38abaed4169ca",
        "Flameblade Studio",
    ))
    trainer_pass = files_pass(trainer_files) and derivation_bound

    bi = CACHE / "huggingface/hub/models--ZhengPeng7--BiRefNet_HR-matting/snapshots/5d6b6f8adcb5b417c871b1d84ceaae9871355b7f"
    birefnet_files = [
        check(bi / "birefnet.py", "2A45B4E0ECE72D7C4212BCA1A988E7D7E52BFE9F98EC59C58B8809C8A8B7A831"),
        check(bi / "BiRefNet_config.py", "E7B8C2A74F6CEA6A59553D517F71D47F2C1D90E670A13416AF17C25FE2F3DC52"),
        check(bi / "config.json", "D0B779EE9A76BF079673C5852C346F439591F016CA0D778A87BBD1DCBE24398A"),
        check(bi / "model.safetensors", "A5A4DE698739EA5E0E8BBAB28E1B293DDE95092B87A442D566CBC585C53CEF55"),
        check(PROJECT / "third_party_licenses/BiRefNet-LICENSE.txt", "92A7089E0915FC32BC40067560B398F1E6A7A5958ABD7D04EDA393629A5ACEFB", ("MIT License", "Permission is hereby granted")),
        check(ARTIFACTS / "license-audit-agent-a/BiRefNet_HR-matting-5d6b6f8.MODEL_CARD.md", "834BA4551D22697900286F26909064338C1E04DD44A8FEB43E2992C0D644334B", ("license: mit",)),
    ]
    birefnet_pass = files_pass(birefnet_files) and "MIT" in ALLOWLIST

    root = ARTIFACTS / "identity-crop-training-admission-agent-a"
    shim_files = [
        check(root / "probe_flux_stack_first_party_shims.py", "FC9B927034D9A2CA6BFC51AEA253A012FC9AB7E590AED332527F4573FE354C41", ("SPDX-License-Identifier: MIT",)),
        check(root / "FIRST-PARTY-TQDM-SHIM-SYMBOLS.json", "841016D24D53EDD2E1AFBF74940C78B1E7639D4BE6FB1806E65512BAD6CE0F89"),
        check(root / "OFFLINE-EMPTY-CA.pem", "D98FDDDAE8276A15BC99F4DE04ADF0AC1649C65223220DA6C535BB727511C0F6"),
        check(root / "probe_dynamic_training_first_party_shims.py", "B5A2BBEF4DE33298C76785F9C806DE89361A86D7FF791D31E7C996CE9613A97F", ("SPDX-License-Identifier: MIT",)),
        check(root / "FIRST-PARTY-SHIM-DYNAMIC-TRAINING-EVIDENCE.json", "4FBB77DA5A73EF6A3095BC8A39F819C424DF9911F711F7D855B98A1289A1BA2F"),
    ]
    shim_evidence = json.loads((root / "FIRST-PARTY-SHIM-DYNAMIC-TRAINING-EVIDENCE.json").read_text(encoding="utf-8"))
    shims_pass = files_pass(shim_files) and shim_evidence.get("probe_exit_code") == 0

    components = {
        "human_artwork_visual_admission": {
            "status": "PASS" if artwork_pass else "FAIL",
            "reason": None if artwork_pass else f"persisted visual-review status is {approval.get('status', 'MISSING')!r}, expected 'PASS'",
            "authorization_boundary": "This file is only a visual gate and never grants permission or starts training.",
            "files": [approval_file],
        },
        "flux_schnell": {"status": "PASS" if flux_pass else "FAIL", "license": "Apache-2.0", "files": flux_files},
        "trainer": {
            "status": "PASS" if trainer_pass else "FAIL",
            "license": "Apache-2.0 candidate",
            "reason": None if trainer_pass else "executable trainer lacks exact SPDX, upstream commit, and local-modification binding",
            "derivation_binding_present": derivation_bound,
            "files": trainer_files,
        },
        "birefnet": {"status": "PASS" if birefnet_pass else "FAIL", "license": "MIT", "files": birefnet_files},
        "first_party_shims": {
            "status": "PASS_COMPONENT_ONLY" if shims_pass else "FAIL",
            "license": "MIT",
            "boundary": "tiny dynamic compatibility only; formal FLUX training remains untested",
            "files": shim_files,
        },
    }
    blockers = [name for name, item in components.items() if not item["status"].startswith("PASS")]
    report = {
        "schema": "mohan.formal_training_provenance.v2",
        "decision": "PASS" if not blockers else "FAIL_CLOSED",
        "exit_code": 0 if not blockers else 4,
        "allowlist": sorted(ALLOWLIST),
        "model_loaded": False,
        "weights_read": False,
        "training_claimed": False,
        "training_authorized_by_this_report": False,
        "components": components,
        "blocking_components": blockers,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
