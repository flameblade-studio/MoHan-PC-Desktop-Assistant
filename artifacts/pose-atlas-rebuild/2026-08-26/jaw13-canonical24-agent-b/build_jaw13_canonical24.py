from __future__ import annotations

import csv, hashlib, json
from collections import defaultdict
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent
BASE = Path(r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision")
SRC = BASE / r"artifacts\pose-atlas-rebuild\2026-08-25\ufbx-lod1-extractor-agent-a\candidate3-yaw-controls-24"
NPZ, CTRLS = SRC / "candidate3-vertex-projections.npz", SRC / "controls"
WEIGHTS = BASE / r"artifacts\pose-atlas-rebuild\2026-08-25\skin-weight-parts-agent-a\vertex-skin-weights.tsv"
VIEWS = ROOT / "views"
YAWS = tuple(range(-180, 180, 15))

def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""): h.update(chunk)
    return h.hexdigest().upper()

def vid(yaw: int) -> str: return f"yaw{yaw:+04d}-pitch+00"

def native(formal: int) -> int:
    value = -formal
    while value >= 180: value -= 360
    while value < -180: value += 360
    return value

def jaw_vertices() -> np.ndarray:
    total, jaw = defaultdict(float), defaultdict(float)
    with WEIGHTS.open(encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            i, w = int(row["vertex_index"]), float(row["weight"])
            total[i] += w
            if row["bone_name"] == "c_jaw": jaw[i] += w
    values = sorted(i for i, w in jaw.items() if total[i] and w / total[i] >= .55)
    if len(values) < 13: raise RuntimeError("fewer than 13 c_jaw vertices")
    return np.asarray(values, dtype=np.int64)

def candidates(ids: np.ndarray, xy: np.ndarray):
    columns = {}
    for vertex, point in zip(ids, xy, strict=True):
        x = round(float(point[0])); prior = columns.get(x)
        if prior is None or point[1] > prior[1][1]: columns[x] = (int(vertex), point.copy())
    ordered = [columns[x] for x in sorted(columns)]
    env_ids = np.asarray([r[0] for r in ordered], dtype=np.int64)
    env_xy = np.asarray([r[1] for r in ordered], dtype=np.float64)
    length = np.concatenate(([0.], np.cumsum(np.linalg.norm(np.diff(env_xy, axis=0), axis=1))))
    if len(env_ids) < 13 or length[-1] <= 0: raise RuntimeError("degenerate lower envelope")
    chosen = []
    for target in np.linspace(0, length[-1], 13):
        index = next(int(i) for i in np.argsort(abs(length-target), kind="stable") if int(i) not in chosen)
        chosen.append(index)
    chosen = np.asarray(sorted(chosen), dtype=np.int64)
    return env_ids[chosen], env_xy[chosen], length[chosen] / length[-1], len(env_ids)

def spline(points: np.ndarray) -> np.ndarray:
    padded, curve = np.vstack((points[0], points, points[-1])), []
    for i in range(1, len(padded)-2):
        p0, p1, p2, p3 = padded[i-1:i+3]
        for t in np.linspace(0, 1, 32, endpoint=False):
            t2, t3 = t*t, t*t*t
            curve.append(.5*(2*p1+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t2+(-p0+3*p1-3*p2+p3)*t3))
    curve.append(points[-1])
    return np.asarray(curve)

def overlay(base: Image.Image, ids: np.ndarray, xy: np.ndarray, curve=None) -> Image.Image:
    image, font = base.convert("RGB"), ImageFont.load_default()
    draw = ImageDraw.Draw(image)
    if curve is not None: draw.line([tuple(map(float,p)) for p in curve], fill=(0,255,255), width=4)
    draw.line([tuple(map(float,p)) for p in xy], fill=(255,210,0), width=2)
    for number, point in enumerate(xy, 1):
        x,y = map(float, point); draw.ellipse((x-6,y-6,x+6,y+6), fill=(255,40,40), outline="white", width=2)
        draw.text((x+8,y-8), str(number), fill="white", font=font, stroke_width=2, stroke_fill="black")
    draw.rectangle((10,10,625,36), fill="black")
    draw.text((16,17), "MESH_CANDIDATE 1-13 | real c_jaw vertices | NOT MediaPipe/FLAME", fill=(255,210,0), font=font)
    return image

def main() -> int:
    for path in (NPZ, WEIGHTS, CTRLS):
        if not path.exists(): raise FileNotFoundError(path)
    VIEWS.mkdir(parents=True, exist_ok=True)
    jaw_ids, records, tiles = jaw_vertices(), [], []
    with np.load(NPZ, allow_pickle=False) as data:
        for formal in YAWS:
            render = native(formal); rows = np.where(data["yaw_degrees"] == render)[0]
            if len(rows) != 1: raise RuntimeError(f"projection row count for {formal}: {len(rows)}")
            row, fview, nview = int(rows[0]), vid(formal), vid(render)
            paths = {kind: CTRLS / f"{nview}_{kind}.png" for kind in ("normal","depth","silhouette")}
            for path in paths.values():
                if not path.is_file() or Image.open(path).size != (1024,1536): raise RuntimeError(f"bad control: {path}")
            projected, depth = data["screen_xy"][row,jaw_ids], data["camera_depth"][row,jaw_ids]
            ids, xy, arc, env_count = candidates(jaw_ids, projected); curve = spline(xy)
            numbered, smooth = overlay(Image.open(paths["normal"]),ids,xy), overlay(Image.open(paths["normal"]),ids,xy,curve)
            numbered_path = VIEWS / f"{fview}_jaw13-mesh-candidates-overlay.png"
            smooth_path = VIEWS / f"{fview}_jaw13-smoothed-conditioning.png"
            numbered.save(numbered_path); smooth.save(smooth_path)
            depth_map = {int(v): float(d) for v,d in zip(jaw_ids,depth,strict=True)}
            points = [{"candidate_number":n,"vertex_id":int(v),"screen_xy":[float(p[0]),float(p[1])],"camera_depth":depth_map[int(v)],"normalized_envelope_arclength":float(a),"status":"MESH_CANDIDATE"} for n,(v,p,a) in enumerate(zip(ids,xy,arc,strict=True),1)]
            evidence = {"schema":"mohan.jaw13_mesh_candidates.canonical_view.v1","status":"PASS_MESH_CANDIDATE_STAGING_ONLY","formal_view_id":fview,"formal_yaw":formal,"renderer_native_yaw":render,"projection_row":row,"mirror":False,"sign_contract":"formal yaw uses renderer-native negative yaw; no pixel mirroring","candidate_count":13,"method":"actual c_jaw FBX skin-weight share >=0.55; per-view projected lower envelope; 13 unique real vertices nearest equal cumulative arc-length targets","truth_boundary":"MESH_CANDIDATE only; not MediaPipe/FLAME/formal anatomical landmarks","inputs":{"projection_npz":{"path":str(NPZ),"sha256":sha(NPZ)},"skin_weights":{"path":str(WEIGHTS),"sha256":sha(WEIGHTS)},**{k:{"path":str(p),"sha256":sha(p)} for k,p in paths.items()}},"c_jaw_vertex_count":int(len(jaw_ids)),"lower_envelope_real_vertex_count":env_count,"candidates":points,"smoothed_curve":{"method":"Catmull-Rom through 13 real mesh candidates","point_count":int(len(curve)),"formal_landmarks":False},"outputs":{"numbered_overlay":{"path":str(numbered_path),"sha256":sha(numbered_path)},"smoothed_conditioning":{"path":str(smooth_path),"sha256":sha(smooth_path)}},"flux_started":False,"formal_asset_promotion":False}
            json_path = VIEWS / f"{fview}_jaw13-mesh-candidates.json"
            json_path.write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            records.append({"formal_view_id":fview,"renderer_native_yaw":render,"projection_row":row,"mirror":False,"vertex_ids":[p["vertex_id"] for p in points],"json":{"path":str(json_path),"sha256":sha(json_path)},"overlay":{"path":str(numbered_path),"sha256":sha(numbered_path)},"smooth":{"path":str(smooth_path),"sha256":sha(smooth_path)}})
            lo=np.floor(xy.min(0)-85).astype(int); hi=np.ceil(xy.max(0)+85).astype(int)
            tiles.append((fview,smooth.crop((max(0,int(lo[0])),max(0,int(lo[1])),min(1024,int(hi[0])),min(1536,int(hi[1]))))))
    contact=Image.new("RGB",(1800,1040),(25,27,31)); draw=ImageDraw.Draw(contact); font=ImageFont.load_default()
    for i,(label,crop) in enumerate(tiles):
        thumb=ImageOps.contain(crop,(288,228),Image.Resampling.LANCZOS); x=(i%6)*300; y=(i//6)*260
        contact.paste(thumb,(x+(300-thumb.width)//2,y+28)); draw.text((x+8,y+8),label,fill="white",font=font)
    contact_path=ROOT/"jaw13-canonical24-contact.png"; contact.save(contact_path)
    count=len(list(VIEWS.iterdir()))
    if count != 72: raise RuntimeError(f"exact file count {count} != 72")
    manifest={"schema":"mohan.jaw13_mesh_candidates.canonical24.v1","status":"PASS_24_VIEW_MESH_CANDIDATE_STAGING_ONLY","canonical_view_count":len(records),"candidate_count_per_view":13,"total_mesh_candidate_points":len(records)*13,"files_per_view":3,"exact_view_file_count":count,"expected_view_file_count":72,"mirror_used":False,"projection_policy":"each formal view independently reads its renderer-native negative-yaw projection row","truth_boundary":"MESH_CANDIDATE only; no MediaPipe/FLAME landmark claim","records":records,"contact":{"path":str(contact_path),"sha256":sha(contact_path)},"flux_started":False,"formal_asset_promotion":False}
    manifest_path=ROOT/"jaw13-canonical24-manifest.json"; manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":manifest["status"],"canonical_views":len(records),"view_files":count,"total_candidates":312,"contact":str(contact_path),"contact_sha256":sha(contact_path),"manifest":str(manifest_path),"manifest_sha256":sha(manifest_path)},ensure_ascii=False))
    return 0

if __name__ == "__main__": raise SystemExit(main())
