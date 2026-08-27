"""Fail closed when MoHan inputs reference permanently denied dependencies."""

from __future__ import annotations

lazy import argparse
lazy from importlib import util as _importlib_util
lazy import json
lazy import os
lazy from pathlib import Path
lazy import sys
lazy from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = PROJECT_ROOT / "THIRD_PARTY_DENYLIST.json"


def load_policy(path: Path = POLICY_PATH) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "mohan.third-party-denylist.v1":
        raise ValueError("unsupported third-party denylist schema")
    denials = payload.get("permanent_denials")
    if not isinstance(denials, list) or not denials:
        raise ValueError("permanent_denials must be a non-empty list")
    return payload


def denied_aliases(policy: dict[str, object]) -> tuple[str, ...]:
    aliases: list[str] = []
    for denial in policy["permanent_denials"]:  # type: ignore[index]
        aliases.extend(denial["aliases"])  # type: ignore[index]
    return tuple(alias.casefold() for alias in aliases)


def find_denied_references(text: str, aliases: Iterable[str]) -> list[str]:
    folded = text.casefold()
    return sorted({alias for alias in aliases if alias in folded})


def local_residue_paths() -> tuple[Path, ...]:
    local_app_data = Path(os.environ.get("LOCALAPPDATA", ""))
    model_root = PROJECT_ROOT / "tools" / "third_party" / "models"
    shared_huggingface_hub = PROJECT_ROOT.parents[1] / ".third-party-cache" / "huggingface" / "hub"
    return (
        PROJECT_ROOT / "tools" / "third_party" / "InstantMesh" / ".conda" / "Lib" / "site-packages" / "nvdiffrast",
        PROJECT_ROOT / "tools" / "third_party" / "InstantMesh" / ".conda" / "Lib" / "site-packages" / "nvdiffrast-0.3.3.dist-info",
        PROJECT_ROOT / "tools" / "third_party" / "InstantMesh" / ".torch_extensions",
        local_app_data / "torch_extensions" / "torch_extensions" / "Cache" / "py310_cu121" / "nvdiffrast_plugin",
        local_app_data / "Comfy-Desktop",
        Path.home() / ".cache" / "huggingface" / "hub" / "models--sudo-ai--zero123plus-v1.2",
        model_root / "kandinsky-2-2-prior-9fc51ad",
        model_root / "kandinsky-2-2-controlnet-depth-4ecd717",
        model_root / "qwen-image-edit-2509-comfy-apache2",
        shared_huggingface_hub / "models--Qwen--Qwen-Image-Edit-2509",
    )


def find_local_residue() -> list[str]:
    residue: list[str] = []
    for path in local_residue_paths():
        if path.name == ".torch_extensions":
            if path.exists():
                residue.extend(str(candidate) for candidate in path.glob("**/*nvdiffrast*"))
            continue
        if path.exists():
            residue.append(str(path))
    if _importlib_util.find_spec("nvdiffrast") is not None:
        residue.append("importable:nvdiffrast")
    return sorted(set(residue))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", action="append", default=[], type=Path)
    parser.add_argument("--verify-local-absence", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    policy = load_policy()
    aliases = denied_aliases(policy)
    errors: list[str] = []
    for candidate in args.candidate:
        matches = find_denied_references(candidate.read_text(encoding="utf-8"), aliases)
        if matches:
            errors.append(f"{candidate}: denied references: {', '.join(matches)}")
    if args.verify_local_absence:
        errors.extend(f"local residue: {path}" for path in find_local_residue())
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 2
    print("third-party denylist validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
