from __future__ import annotations
import hashlib,json,shutil
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw

ROOT=Path(r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision")
A=ROOT/"artifacts/pose-atlas-rebuild/2026-08-25"
OUT=Path(__file__).resolve().parent
SOURCE=A/"candidate3-formal-controls-bundle-agent-a/formal-controls"
SOURCE_MANIFEST=A/"candidate3-formal-controls-bundle-agent-a/formal-controls-manifest.json"
B00=ROOT/"artifacts/pose-atlas-rebuild/2026-08-24/mother-views/yaw+000-pitch+00.approved-rgba.png"
HEIGHT_EVIDENCE=A/"ufbx-lod1-extractor-agent-a/body-morph-candidate3/verify-stdout.json"
EXPECTED={"silhouette":"E32D072BF5DD41E4CBC7EC0B8BF96B98EF52873AC142060935BEB3DF23E448E1","depth":"0EC54A9B35C0C049BC883EBD0DFFFA8F0FF8AA4F6C0A9CCB6F7C5158BF0904FD","normal":"885011EA5317D0478B4EBAD39D4E829647EBD2A626E7E89FB925022CCAB2BCDF"}
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def panel(im:Image.Image,label:str)->Image.Image:
 out=Image.new("RGB",(380,570),"white");v=im.convert("RGB");v.thumbnail((360,510),Image.Resampling.LANCZOS);out.paste(v,((380-v.width)//2,50+(510-v.height)//2));ImageDraw.Draw(out).text((8,10),label,fill="black");return out
def main()->int:
 source={k:SOURCE/f"yaw+045-pitch+00_{k}.png" for k in EXPECTED}
 actual={k:sha(p) for k,p in source.items() if p.is_file()}
 if actual!=EXPECTED:return 4
 controls=OUT/"controls";controls.mkdir(exist_ok=True)
 copied={}
 for k,p in source.items():
  dst=controls/f"yaw+045-pitch+00_{k}.png";shutil.copy2(p,dst)
  if sha(dst)!=EXPECTED[k]:return 4
  copied[k]=dst
 sil=np.asarray(Image.open(copied["silhouette"]).convert("L"),dtype=np.uint8)
 depth=np.asarray(Image.open(copied["depth"]).convert("L"),dtype=np.uint8)
 normal=np.asarray(Image.open(copied["normal"]).convert("RGB"),dtype=np.uint8)
 fg=sil>=128;ys,xs=np.nonzero(fg);bbox=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
 technical={"size_1024x1536":all(Image.open(p).size==(1024,1536) for p in copied.values()),"modes":{"silhouette":Image.open(copied["silhouette"]).mode,"depth":Image.open(copied["depth"]).mode,"normal":Image.open(copied["normal"]).mode},"silhouette_binary_values":sorted(int(v) for v in np.unique(sil)),"silhouette_corners":[int(sil[0,0]),int(sil[0,-1]),int(sil[-1,0]),int(sil[-1,-1])],"depth_background_nonzero":int(np.count_nonzero(depth[~fg])),"normal_background_nonzero_channels":int(np.count_nonzero(normal[~fg])),"foreground_bbox_exclusive":bbox,"projected_height_px":bbox[3]-bbox[1],"height_authority_cm":168.0,"pixel_per_cm_projection":(bbox[3]-bbox[1])/168.0}
 b00=Image.open(B00).convert("RGBA");b00rgb=Image.alpha_composite(Image.new("RGBA",b00.size,"white"),b00).convert("RGB")
 panels=[panel(Image.open(copied[k]),f"SEPARATE {k}; never final RGB") for k in ("silhouette","depth","normal")]+[panel(b00rgb,"B00 garment reference only: blue outer / white inner / low shoes")]
 contact=Image.new("RGB",(1520,570),(220,220,220))
 for i,p in enumerate(panels):contact.paste(p,(i*380,0))
 contact_path=OUT/"separated-controls-contact.png";contact.save(contact_path)
 contract={"schema":"mohan.yaw045.separated_geometry_controls/v1","status":"PASS_CPU_GEOMETRY_BUNDLE_ONLY","formal_view_id":"yaw+045-pitch+00","formal_yaw_degrees":45,"source_control_file_id":"yaw-045-pitch+00","source_renderer_yaw_degrees":-45,"camera":"orthographic","canvas":[1024,1536],"mirror":False,"controls_are_separate_inputs":True,"controls_must_never_be_composited_into_final_rgb":True,"geometry_authority":"candidate3 MHR/ufbx geometry candidate only","height_contract":{"cm":168.0,"evidence_path":str(HEIGHT_EVIDENCE),"evidence_sha256":sha(HEIGHT_EVIDENCE),"note":"candidate3 inherited exact uniform height scaling; projected pixels are camera registration, not centimeters"},"shoulder_contract":{"source":"candidate3 mesh projection","reestimated_in_bundle":False,"note":"MHR A-pose shoulders are geometry guidance; garment shoulder/sleeve silhouette still requires art QA"},"garment_and_art_contract":{"blue_outer_robe":True,"white_inner_robe":True,"detachable_outfit":True,"wide_sleeves_and_skirt":"required_generation_and_manual_gate_not_guaranteed_by_nude_geometry","low_white_shoes":"required_generation_and_manual_gate_not_guaranteed_by_geometry","identity":"requires Pure Face Mask v3 PASS and human comparison"},"execution_gate":{"pure_face_mask_v3":"MUST_PASS_BEFORE_GPU","model_load_count":1,"attempt_rounds":1,"identity_drift":"HOLD","current_status":"WAITING_PURE_FACE_MASK_V3","gpu_used":False},"technical":technical,"sources":{"manifest":{"path":str(SOURCE_MANIFEST),"sha256":sha(SOURCE_MANIFEST)},**{k:{"path":str(source[k]),"sha256":actual[k]} for k in source}},"outputs":{"controls":{k:{"path":str(copied[k]),"sha256":sha(copied[k])} for k in copied},"contact":{"path":str(contact_path),"sha256":sha(contact_path)}},"formal_art_pass":False,"exit_code":0}
 (OUT/"control-bundle-manifest.json").write_text(json.dumps(contract,ensure_ascii=False,indent=2),encoding="utf-8");print(json.dumps(contract,ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
