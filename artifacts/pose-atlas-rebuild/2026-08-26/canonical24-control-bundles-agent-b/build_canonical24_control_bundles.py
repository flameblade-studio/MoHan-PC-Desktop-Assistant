from __future__ import annotations

import hashlib, json, shutil
from pathlib import Path
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parent
BASE=Path(r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision")
SRC=BASE/r"artifacts\pose-atlas-rebuild\2026-08-25\ufbx-lod1-extractor-agent-a\candidate3-yaw-controls-24"
CONTROLS=SRC/"controls"
PARTS=BASE/r"artifacts\pose-atlas-rebuild\2026-08-25\skin-weight-parts-agent-a\masks"
JAW=BASE/r"artifacts\pose-atlas-rebuild\2026-08-26\jaw13-canonical24-agent-b\views"
REMAINING=BASE/r"artifacts\pose-atlas-rebuild\2026-08-26\remaining-geometry-controls-agent-b\controls"
OUTFIT_TEMPLATES=BASE/r"artifacts\pose-atlas-rebuild\2026-08-26\canonical24-ownership-templates-agent-c\masks"
ORNAMENT_CONTROLS=BASE/r"artifacts\pose-atlas-rebuild\2026-08-26\canonical24-ornament-visibility-controls-agent-b\controls"
BUNDLES=ROOT/"bundles"
YAWS=tuple(range(-180,180,15))
OWNERSHIP_KINDS=("ownership_anatomy","ownership_outfit","ownership_hair","ownership_ornament","ornament_mask")

def sha(p:Path)->str:
    h=hashlib.sha256();
    with p.open("rb") as f:
        for c in iter(lambda:f.read(1<<20),b""): h.update(c)
    return h.hexdigest().upper()

def vid(y:int)->str:return f"yaw{y:+04d}-pitch+00"
def native(y:int)->int:
    v=-y
    while v>=180:v-=360
    while v< -180:v+=360
    return v

def formal_geometry_source(view_id:str, kind:str)->Path|None:
    if kind=="ownership_outfit":
        template=OUTFIT_TEMPLATES/f"{view_id}_default_outfit_mask.png"
        if template.is_file():return template
    if kind in ("ownership_ornament","ornament_mask"):
        fixed_side=ORNAMENT_CONTROLS/f"{view_id}_ornament-fixed-side-mask.png"
        if fixed_side.is_file():return fixed_side
    suffix=kind.replace("_","-") if kind != "ornament_mask" else "ornament_mask"
    remaining=REMAINING/f"{view_id}_{suffix}.png"
    if remaining.is_file():return remaining
    yaw_token=view_id.removeprefix("yaw").split("-pitch",1)[0]
    dirname="yaw"+(yaw_token if yaw_token.startswith("-") else yaw_token.removeprefix("+"))
    individual=BASE/r"artifacts\pose-atlas-rebuild\2026-08-26"/f"{dirname}-geometry-controls-agent-d"/"controls"/f"{view_id}_{suffix}.png"
    if individual.is_file():return individual
    if kind=="ornament_mask":
        explicit_empty=individual.with_name(f"{view_id}_ownership-ornament.png")
        if explicit_empty.is_file():return explicit_empty
    return None

def shade(normal:Image.Image,silhouette:Image.Image):
    encoded=np.asarray(normal.convert("RGB"),dtype=np.float32)/255
    normals=encoded*2-1; light=np.asarray([-.35,-.45,.82],dtype=np.float32); light/=np.linalg.norm(light)
    value=.22+.78*np.clip(np.sum(normals*light,axis=2),0,1); mask=np.asarray(silhouette.convert("L"))>0
    base=np.full((*mask.shape,3),22,dtype=np.uint8); shaded=base.copy()
    base[mask]=[174,184,200]; lit=np.clip(value[...,None]*np.asarray([185,195,210]),0,255).astype(np.uint8); shaded[mask]=lit[mask]
    return Image.fromarray(base,"RGB"),Image.fromarray(shaded,"RGB")

def copy_exact(src:Path,dst:Path)->dict:
    shutil.copy2(src,dst)
    if sha(src)!=sha(dst):raise RuntimeError(f"copy hash mismatch: {src}")
    image=Image.open(dst)
    if image.size!=(1024,1536):raise RuntimeError(f"bad size: {dst}")
    return {"path":str(dst),"sha256":sha(dst),"source_path":str(src),"source_sha256":sha(src),"mode":image.mode,"size":[1024,1536],"physical_file":True,"derived":False}

def main()->int:
    for p in (CONTROLS,PARTS,JAW,REMAINING,OUTFIT_TEMPLATES,ORNAMENT_CONTROLS):
        if not p.is_dir():raise FileNotFoundError(p)
    BUNDLES.mkdir(parents=True,exist_ok=True); records=[]
    for formal in YAWS:
        render=native(formal); fview,nview=vid(formal),vid(render); folder=BUNDLES/fview; folder.mkdir(parents=True,exist_ok=True)
        stale_ornament_mask=folder/f"{fview}_ornament-mask.png"
        if stale_ornament_mask.is_file():stale_ornament_mask.unlink()
        source={"depth":CONTROLS/f"{nview}_depth.png","normal":CONTROLS/f"{nview}_normal.png","silhouette":CONTROLS/f"{nview}_silhouette.png","part_id":PARTS/f"{nview}_part-id.png","jaw13_overlay":JAW/f"{fview}_jaw13-mesh-candidates-overlay.png","jaw13_conditioning":JAW/f"{fview}_jaw13-smoothed-conditioning.png","jaw13_candidates":JAW/f"{fview}_jaw13-mesh-candidates.json"}
        source.update({kind:path for kind in OWNERSHIP_KINDS if (path:=formal_geometry_source(fview,kind)) is not None})
        for p in source.values():
            if not p.is_file():raise FileNotFoundError(p)
        files={}
        for kind in ("depth","normal","silhouette","part_id","jaw13_overlay","jaw13_conditioning"):
            suffix="part-id" if kind=="part_id" else kind.replace("_","-")
            files[kind]=copy_exact(source[kind],folder/f"{fview}_{suffix}.png")
        for kind in OWNERSHIP_KINDS:
            suffix=kind.replace("_","-") if kind!="ornament_mask" else "ornament_mask"
            path=folder/f"{fview}_{suffix}.png"
            if kind in source:
                files[kind]=copy_exact(source[kind],path)
                if kind=="ownership_outfit" and Image.open(path).convert("L").getbbox() is None:
                    raise RuntimeError(f"default outfit ownership must be non-empty: {path}")
                continue
            if kind=="ownership_anatomy":
                image=Image.open(source["silhouette"]).convert("L")
                derivation="same-yaw neutral anatomy silhouette"
            else:
                image=Image.new("L",(1024,1536),0)
                derivation="explicit empty mask because neutral geometry contains no independent outfit, hair, or ornament mesh"
            image.save(path)
            files[kind]={"path":str(path),"sha256":sha(path),"mode":"L","size":[1024,1536],"physical_file":True,"derived":True,"derivation":derivation}
        jaw_json=folder/f"{fview}_jaw13-candidates.json"; shutil.copy2(source["jaw13_candidates"],jaw_json)
        if sha(jaw_json)!=sha(source["jaw13_candidates"]):raise RuntimeError("jaw JSON copy mismatch")
        files["jaw13_candidates"]={"path":str(jaw_json),"sha256":sha(jaw_json),"source_path":str(source["jaw13_candidates"]),"source_sha256":sha(source["jaw13_candidates"]),"physical_file":True,"derived":False}
        base,shaded=shade(Image.open(source["normal"]),Image.open(source["silhouette"])); base_path=folder/f"{fview}_base-render.png"; shaded_path=folder/f"{fview}_shaded-render.png"; base.save(base_path);shaded.save(shaded_path)
        for kind,path in (("base_render",base_path),("shaded_render",shaded_path)):
            files[kind]={"path":str(path),"sha256":sha(path),"mode":"RGB","size":[1024,1536],"physical_file":True,"derived":True,"derivation":"deterministic geometry shading from same renderer-native normal+silhouette; not generated art"}
        anchor_path=folder/f"{fview}_registration-anchor.json"
        anchor={"schema":"mohan.full_canvas_registration_anchor.v1","view_id":fview,"canvas":[1024,1536],"body_center":[512,1292],"offset":[0,0],"full_canvas_registered":True,"mirror":False}
        anchor_path.write_text(json.dumps(anchor,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        files["registration_anchor"]={"path":str(anchor_path),"sha256":sha(anchor_path),"physical_file":True,"derived":False}
        index={"schema":"mohan.canonical_control_bundle.v2","status":"PASS_STAGING_ONLY","formal_view_id":fview,"formal_yaw":formal,"renderer_native_yaw":render,"mirror":False,"sign_contract":"formal yaw uses renderer-native negative yaw; no pixel mirroring","files":files,"required_controls":["depth","normal","silhouette","part_id","base_render","shaded_render","jaw13_overlay","jaw13_conditioning","jaw13_candidates",*OWNERSHIP_KINDS,"registration_anchor"],"flux_started":False,"formal_asset_promotion":False}
        index_path=folder/"control-bundle.json";index_path.write_text(json.dumps(index,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        records.append({"view_id":fview,"renderer_native_yaw":render,"mirror":False,"bundle_index":{"path":str(index_path),"sha256":sha(index_path)},"physical_file_count":len(list(folder.iterdir()))})
    required_per_bundle=16
    for record in records:
        if record["physical_file_count"]!=required_per_bundle:raise RuntimeError(f"bundle file count: {record}")
    manifest={"schema":"mohan.canonical_control_bundles.24.v2","status":"PASS_24_CANONICAL_CONTROL_BUNDLES_STAGING_ONLY","bundle_count":len(records),"required_files_per_bundle":required_per_bundle,"exact_bundle_file_count":sum(r["physical_file_count"] for r in records),"mirror_used":False,"records":records,"flux_started":False,"formal_asset_promotion":False}
    manifest_path=ROOT/"canonical24-control-bundles-manifest.json";manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":manifest["status"],"bundles":len(records),"files_per_bundle":required_per_bundle,"bundle_files":manifest["exact_bundle_file_count"],"manifest":str(manifest_path),"manifest_sha256":sha(manifest_path)},ensure_ascii=False));return 0

if __name__=="__main__":raise SystemExit(main())
