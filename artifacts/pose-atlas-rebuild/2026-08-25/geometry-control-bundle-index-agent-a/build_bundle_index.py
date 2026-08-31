from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
CONTROL_DIR = PROJECT / "artifacts/pose-atlas-rebuild/2026-08-25/ufbx-lod1-extractor-agent-a/candidate3-yaw-controls-24"
PART_DIR = PROJECT / "artifacts/pose-atlas-rebuild/2026-08-25/skin-weight-parts-agent-a"
MASK_DIR = PROJECT / "artifacts/pose-atlas-rebuild/2026-08-25/geometry-rigid-soft-masks-agent-a"
CONTROL_MANIFEST = CONTROL_DIR / "candidate3-camera-anchor-control-manifest.json"
TOPOLOGY_QA = CONTROL_DIR / "topology-continuity-qa.json"
PART_QA = PART_DIR / "part-id-mask-qa.json"
MASK_MANIFEST = MASK_DIR / "geometry-rigid-soft-mask-manifest.json"
YAWS = tuple(range(-180, 180, 15))
VIEW_IDS = tuple(f"yaw{yaw:+04d}-pitch+00" for yaw in YAWS)
TYPES = ("silhouette", "depth", "normal", "part_id", "rigid", "soft")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def record(path: Path) -> dict[str, object]:
    image = Image.open(path); image.load()
    if image.size != (1024, 1536): raise ValueError(f"size: {path}")
    return {"path": str(path.relative_to(PROJECT)).replace("\\", "/"), "sha256": digest(path), "bytes": path.stat().st_size, "width": 1024, "height": 1536, "mode": image.mode}


def main() -> int:
    controls = json.loads(CONTROL_MANIFEST.read_text(encoding="utf-8"))
    topology = json.loads(TOPOLOGY_QA.read_text(encoding="utf-8"))
    part_qa = json.loads(PART_QA.read_text(encoding="utf-8"))
    masks = json.loads(MASK_MANIFEST.read_text(encoding="utf-8"))
    if topology["status"] != "PASS_INDEPENDENT_TOPOLOGY_CORRESPONDENCE_GATE": raise ValueError("topology gate")
    gates = topology["circular_gates"]
    if not all(gates[key] for key in ("view_ids_exact_order", "wrap_is_plus_165_to_minus_180_equivalent_plus_15", "no_mirror_transition")): raise ValueError("ring gate")
    control_by = {view["view_id"]: view for view in controls["views"]}
    part_by = {view["view_id"]: view for view in part_qa["views"]}
    mask_by = {view["view_id"]: view for view in masks["views"]}
    if tuple(control_by) != VIEW_IDS or tuple(part_by) != VIEW_IDS or tuple(mask_by) != VIEW_IDS: raise ValueError("source view order")
    views=[]
    for yaw, view_id in zip(YAWS, VIEW_IDS, strict=True):
        control = control_by[view_id]
        paths = {
            "silhouette": CONTROL_DIR / control["controls"]["silhouette"]["path"],
            "depth": CONTROL_DIR / control["controls"]["depth"]["path"],
            "normal": CONTROL_DIR / control["controls"]["normal"]["path"],
            "part_id": PART_DIR / part_by[view_id]["path"],
            "rigid": MASK_DIR / mask_by[view_id]["rigid"]["path"],
            "soft": MASK_DIR / mask_by[view_id]["soft"]["path"],
        }
        assets={kind:record(paths[kind]) for kind in TYPES}
        if assets["normal"]["mode"] != "RGB" or any(assets[kind]["mode"] != "L" for kind in TYPES if kind != "normal"): raise ValueError(f"mode: {view_id}")
        for kind in ("silhouette", "depth", "normal"):
            if assets[kind]["sha256"] != control["controls"][kind]["sha256"]: raise ValueError(f"control hash: {view_id} {kind}")
        if assets["part_id"]["sha256"] != part_by[view_id]["sha256"]: raise ValueError(f"part hash: {view_id}")
        if assets["rigid"]["sha256"] != mask_by[view_id]["rigid"]["sha256"] or assets["soft"]["sha256"] != mask_by[view_id]["soft"]["sha256"]: raise ValueError(f"mask hash: {view_id}")
        views.append({"view_id":view_id,"yaw_degrees":yaw,"pitch_degrees":0,"assets":assets})
    payload={
        "schema":"mohan.pose-atlas.geometry-control-bundle-index.v1",
        "status":"CANDIDATE_GEOMETRY_CONTROLS_ONLY",
        "notice":"GEOMETRY CONTROL ONLY - NOT FINAL ART",
        "formal_layer_manifest":False,
        "clothing_baked_into_body":False,
        "canvas":{"width":1024,"height":1536},
        "view_order":list(VIEW_IDS),
        "ring":{"yaw_step_degrees":15,"wrap_from":"yaw+165-pitch+00","wrap_to":"yaw-180-pitch+00","wrap_equivalent_positive_step_degrees":15,"no_mirror_transition":True,"topology_evidence_status":topology["status"]},
        "asset_types":list(TYPES),
        "provenance":{
            "candidate3_control_manifest":{"path":str(CONTROL_MANIFEST.relative_to(PROJECT)).replace("\\","/"),"sha256":digest(CONTROL_MANIFEST)},
            "topology_continuity":{"path":str(TOPOLOGY_QA.relative_to(PROJECT)).replace("\\","/"),"sha256":digest(TOPOLOGY_QA)},
            "skin_weight_part_qa":{"path":str(PART_QA.relative_to(PROJECT)).replace("\\","/"),"sha256":digest(PART_QA)},
            "rigid_soft_manifest":{"path":str(MASK_MANIFEST.relative_to(PROJECT)).replace("\\","/"),"sha256":digest(MASK_MANIFEST)}
        },
        "views":views,
        "forbidden_claims":["formal layer_manifest", "final art", "clothing segmentation", "hair segmentation", "facial-feature segmentation", "identity consistency", "600 layered PNG completion"]
    }
    (HERE/"geometry-control-bundle-index.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"PASS_BUILD","views":len(views),"files":len(views)*len(TYPES),"index":str(HERE/"geometry-control-bundle-index.json")},sort_keys=True))
    return 0


if __name__=="__main__":sys.exit(main())
