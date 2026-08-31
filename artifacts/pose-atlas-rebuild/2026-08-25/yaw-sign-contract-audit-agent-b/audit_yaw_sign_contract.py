from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


HERE = Path(__file__).resolve().parent
PROJECT = Path(r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision")
BASE = PROJECT / "artifacts" / "pose-atlas-rebuild" / "2026-08-25"
RAW_ROOT = BASE / "ufbx-lod1-extractor-agent-a" / "candidate3-yaw-controls-24"
RAW_MANIFEST = RAW_ROOT / "candidate3-camera-anchor-control-manifest.json"
FORMAL_ROOT = BASE / "candidate3-formal-controls-bundle-agent-a"
FORMAL_MANIFEST = FORMAL_ROOT / "formal-controls-manifest.json"
MAPPING_EVIDENCE = BASE / "allowed-15deg-control-path-audit-agent-a" / "audit.json"
CHARACTER_POSE = PROJECT / "domain" / "character_pose.py"
LAYERED_RENDERER = PROJECT / "infrastructure" / "layered_full_body_renderer.py"
B00 = PROJECT / "artifacts" / "pose-atlas-rebuild" / "2026-08-24" / "mother-views" / "yaw+000-pitch+00.approved-rgba.png"
EXEC82 = Path(r"C:\Users\hitos\.codex\generated_images\01a009be-0db2-7811-a647-3b7ac37528a9\exec-82b460bc-acca-4611-8a56-71194beded59.png")
CANDIDATE_030 = BASE / "yaw030-candidate-v5-physical-ornament-main" / "yaw+030-pitch+00.candidate-v5.physical-ornament.birefnet-rgba.png"
CANDIDATE_045 = BASE / "yaw045-edge-decontam-agent-a" / "yaw+045-pitch+00.candidate-v3.edge-decontaminated-v1.png"
YAW_VALUES = tuple(range(-180, 180, 15))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def font(size: int = 22):
    path = Path(r"C:\Windows\Fonts\msjh.ttc")
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default()


def white_or_gray(path: Path, gray=False) -> Image.Image:
    rgba = Image.open(path).convert("RGBA")
    value = 232 if gray else 255
    return Image.alpha_composite(Image.new("RGBA", rgba.size, (value, value, value, 255)), rgba).convert("RGB")


def panel(image: Image.Image, title: str, note: str, size=(390, 610)) -> Image.Image:
    out = Image.new("RGB", size, "white")
    view = image.convert("RGB")
    view.thumbnail((size[0] - 16, size[1] - 85), Image.Resampling.LANCZOS)
    out.paste(view, ((size[0] - view.width) // 2, 70 + (size[1] - 70 - view.height) // 2))
    draw = ImageDraw.Draw(out)
    draw.text((8, 6), title, fill="black", font=font(23))
    draw.text((8, 36), note, fill=(120, 0, 0), font=font(17))
    draw.rectangle((0, 0, size[0] - 1, size[1] - 1), outline=(20, 20, 20), width=2)
    return out


def view_id(yaw: int) -> str:
    return f"yaw{yaw:+04d}-pitch+00"


def renderer_yaw(formal_yaw: int) -> int:
    value = -formal_yaw
    return -180 if value == 180 else value


def line_evidence(path: Path, needles: list[str]) -> list[dict[str, object]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    result = []
    for needle in needles:
        matches = [{"line": index + 1, "text": text.strip()} for index, text in enumerate(lines) if needle in text]
        result.append({"needle": needle, "matches": matches[:8]})
    return result


def main() -> int:
    required = [RAW_MANIFEST, FORMAL_MANIFEST, MAPPING_EVIDENCE, CHARACTER_POSE, LAYERED_RENDERER, B00, EXEC82, CANDIDATE_030, CANDIDATE_045]
    for yaw in (-45, 45, -30, 30):
        required.append(RAW_ROOT / "controls" / f"{view_id(yaw)}_normal.png")
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        print(json.dumps({"status": "FAIL_MISSING_INPUT", "missing": missing}, indent=2))
        return 2

    raw = json.loads(RAW_MANIFEST.read_text(encoding="utf-8"))
    formal = json.loads(FORMAL_MANIFEST.read_text(encoding="utf-8"))
    allowed = json.loads(MAPPING_EVIDENCE.read_text(encoding="utf-8"))
    if formal.get("mapping_rule") != "source_renderer_yaw=-formal_yaw; +180 canonicalized to -180":
        print(json.dumps({"status": "FAIL_FORMAL_MAPPING_RULE", "value": formal.get("mapping_rule")}))
        return 4
    if allowed["fastest_ready_input"]["mapping_rule"] != formal["mapping_rule"]:
        print(json.dumps({"status": "FAIL_MAPPING_EVIDENCE_DISAGREES"}))
        return 4

    raw_by_yaw = {entry["yaw_degrees"]: entry for entry in raw["views"]}
    formal_by_yaw = {entry["formal_yaw_degrees"]: entry for entry in formal["views"]}
    mapping = []
    for yaw in YAW_VALUES:
        source_yaw = renderer_yaw(yaw)
        entry = formal_by_yaw[yaw]
        expected_source_id = view_id(source_yaw)
        if entry["source_renderer_yaw_degrees"] != source_yaw or entry["source_control_file_id"] != expected_source_id:
            print(json.dumps({"status": "FAIL_VIEW_MAPPING", "formal_yaw": yaw, "entry": entry}, indent=2))
            return 4
        if raw_by_yaw[source_yaw]["view_id"] != expected_source_id:
            print(json.dumps({"status": "FAIL_RAW_CAMERA_ENTRY", "formal_yaw": yaw}))
            return 4
        mapping.append(
            {
                "formal_view_id": view_id(yaw),
                "formal_yaw_degrees": yaw,
                "runtime_lookup_view_id": view_id(yaw),
                "source_renderer_view_id": expected_source_id,
                "source_renderer_yaw_degrees": source_yaw,
                "mirror": False,
            }
        )

    images = [
        panel(white_or_gray(B00), "B00 formal yaw+000", "front anchor"),
        panel(Image.open(EXEC82).convert("RGB"), "exec-82 ornament authority", "confirmed physical side"),
        panel(white_or_gray(CANDIDATE_030, True), "formal candidate yaw+030", "nose/chest face canvas-left"),
        panel(white_or_gray(CANDIDATE_045, True), "formal candidate yaw+045", "nose/chest face canvas-left"),
        panel(Image.open(RAW_ROOT / "controls" / "yaw-030-pitch+00_normal.png"), "renderer yaw-030", "MATCH formal +030 direction"),
        panel(Image.open(RAW_ROOT / "controls" / "yaw+030-pitch+00_normal.png"), "renderer yaw+030", "OPPOSITE formal +030"),
        panel(Image.open(RAW_ROOT / "controls" / "yaw-045-pitch+00_normal.png"), "renderer yaw-045", "MATCH formal +045 direction"),
        panel(Image.open(RAW_ROOT / "controls" / "yaw+045-pitch+00_normal.png"), "renderer yaw+045", "OPPOSITE formal +045"),
    ]
    contact = Image.new("RGB", (1560, 1220), (225, 225, 225))
    for index, item in enumerate(images):
        contact.paste(item, ((index % 4) * 390, (index // 4) * 610))
    contact_path = HERE / "yaw-sign-direction-evidence-contact.png"
    contact.save(contact_path)

    conclusion = {
        "formal_yaw_plus_045_control": "renderer yaw-045-pitch+00",
        "formal_yaw_plus_030_control": "renderer yaw-030-pitch+00",
        "rule": "source_renderer_yaw=-formal_yaw; +180 canonicalized to -180",
        "mirror": "FORBIDDEN_AND_UNNECESSARY",
        "reason": "Runtime consumes the canonical formal view_id unchanged; offline renderer camera rotation has the opposite visual sign. Candidate and control contacts independently agree at +030 and +045.",
    }
    report = {
        "schema": "mohan.pose-atlas.yaw-sign-contract-audit.v1",
        "status": "PASS_SIGN_CONTRACT_RESOLVED",
        "conclusion": conclusion,
        "formal_view_count": len(mapping),
        "mapping_table": mapping,
        "runtime_evidence": {
            "character_pose": {
                "path": str(CHARACTER_POSE),
                "sha256": sha256(CHARACTER_POSE),
                "evidence": line_evidence(CHARACTER_POSE, ['"left-045": -45', '"right-045": 45', "target = _positive_yaw(yaw_degrees)", "def canonical_view_id"]),
                "interpretation": "Runtime canonical +45 means right-045 and does not negate the requested yaw during atlas resolution.",
            },
            "layered_renderer": {
                "path": str(LAYERED_RENDERER),
                "sha256": sha256(LAYERED_RENDERER),
                "evidence": line_evidence(LAYERED_RENDERER, ["view = self._manifest_or_load().view(view_id)", "result = self._outfit_overlay.apply(result, view_id)"]),
                "interpretation": "Runtime renders the already-authored formal view_id exactly; renderer-source sign conversion is a production-time concern only.",
            },
        },
        "production_evidence": {
            "formal_controls_manifest": {"path": str(FORMAL_MANIFEST), "sha256": sha256(FORMAL_MANIFEST), "mapping_rule": formal["mapping_rule"]},
            "allowed_control_audit": {"path": str(MAPPING_EVIDENCE), "sha256": sha256(MAPPING_EVIDENCE), "mapping_rule": allowed["fastest_ready_input"]["mapping_rule"]},
            "raw_renderer_manifest": {"path": str(RAW_MANIFEST), "sha256": sha256(RAW_MANIFEST), "rotation_formula": raw["camera_contract"]["rotation_formula"]},
        },
        "visual_evidence": {
            "contact": str(contact_path),
            "contact_sha256": sha256(contact_path),
            "B00_sha256": sha256(B00),
            "exec82_sha256": sha256(EXEC82),
            "candidate_030_sha256": sha256(CANDIDATE_030),
            "candidate_045_sha256": sha256(CANDIDATE_045),
        },
        "prohibitions": ["no mirroring", "no formal asset modification", "no generation"],
    }
    report_path = HERE / "yaw-sign-contract.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (HERE / "mapping-table.csv").write_text(
        "formal_view_id,formal_yaw_degrees,runtime_lookup_view_id,source_renderer_view_id,source_renderer_yaw_degrees,mirror\n"
        + "\n".join(
            f'{row["formal_view_id"]},{row["formal_yaw_degrees"]},{row["runtime_lookup_view_id"]},{row["source_renderer_view_id"]},{row["source_renderer_yaw_degrees"]},false'
            for row in mapping
        )
        + "\n",
        encoding="utf-8",
    )
    hashes = {path.name: sha256(path) for path in (report_path, HERE / "mapping-table.csv", contact_path)}
    (HERE / "evidence-hashes.json").write_text(json.dumps({"sha256": hashes}, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "conclusion": conclusion, "mapping_rows": len(mapping), "contact": str(contact_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
