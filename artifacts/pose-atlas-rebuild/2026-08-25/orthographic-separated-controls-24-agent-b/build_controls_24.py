from __future__ import annotations
import hashlib,json,shutil
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw

ROOT=Path(r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision")
A=ROOT/"artifacts/pose-atlas-rebuild/2026-08-25"
SOURCE_ROOT=A/"candidate3-formal-controls-bundle-agent-a"
SOURCE_MANIFEST=SOURCE_ROOT/"formal-controls-manifest.json"
OUT=Path(__file__).resolve().parent
KINDS=("silhouette","depth","normal")
VIEWS=[-180,-165,-150,-135,-120,-105,-90,-75,-60,-45,-30,-15,0,15,30,45,60,75,90,105,120,135,150,165]
def view_id(y:int)->str:return f"yaw{y:+04d}-pitch+00"
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def mini(im:Image.Image,size=(96,400))->Image.Image:
 v=im.convert("RGB");v.thumbnail(size,Image.Resampling.LANCZOS);out=Image.new("RGB",size,"black");out.paste(v,((size[0]-v.width)//2,(size[1]-v.height)//2));return out
def main()->int:
 src=json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"));by_id={v["formal_view_id"]:v for v in src["views"]}
 controls=OUT/"controls";controls.mkdir(exist_ok=True)
 records=[];technical_failures=[];panels=[]
 for ordinal,yaw in enumerate(VIEWS):
  vid=view_id(yaw);source_record=by_id.get(vid)
  if source_record is None:technical_failures.append(f"missing_source_manifest_{vid}");continue
  expected_renderer=-yaw if yaw!=-180 else -180
  if source_record["source_renderer_yaw_degrees"]!=expected_renderer:technical_failures.append(f"yaw_mapping_{vid}")
  outputs={};images={}
  for kind in KINDS:
   source=Path(source_record["outputs"][kind]["absolute_path"]);target=controls/f"{vid}_{kind}.png";shutil.copy2(source,target)
   image=Image.open(target);array=np.asarray(image)
   expected_mode="RGB" if kind=="normal" else "L"
   if image.size!=(1024,1536) or image.mode!=expected_mode:technical_failures.append(f"image_contract_{vid}_{kind}")
   if sha(target).lower()!=source_record["outputs"][kind]["output_sha256"].lower():technical_failures.append(f"sha_{vid}_{kind}")
   sil=np.asarray(Image.open(controls/f"{vid}_silhouette.png").convert("L"))>=128 if (controls/f"{vid}_silhouette.png").is_file() else None
   if kind=="silhouette":
    vals=sorted(int(v) for v in np.unique(array));bg_ok=vals==[0,255] and all(int(array[yy,xx])==0 for yy,xx in ((0,0),(0,1023),(1535,0),(1535,1023)))
   else:bg_ok=None
   outputs[kind]={"path":str(target),"sha256":sha(target),"width":image.width,"height":image.height,"mode":image.mode,"background_zero":bg_ok}
   images[kind]=image.copy()
  sil=np.asarray(images["silhouette"].convert("L"))>=128
  depth=np.asarray(images["depth"].convert("L"));normal=np.asarray(images["normal"].convert("RGB"))
  outputs["depth"]["background_zero"]=bool(np.count_nonzero(depth[~sil])==0);outputs["depth"]["background_nonzero_count"]=int(np.count_nonzero(depth[~sil]))
  outputs["normal"]["background_zero"]=bool(np.count_nonzero(normal[~sil])==0);outputs["normal"]["background_nonzero_channel_count"]=int(np.count_nonzero(normal[~sil]))
  if not all(outputs[k]["background_zero"] for k in KINDS):technical_failures.append(f"background_{vid}")
  records.append({"ordinal":ordinal,"view_id":vid,"formal_yaw_degrees":yaw,"source_renderer_yaw_degrees":expected_renderer,"pitch_degrees":0,"camera":"orthographic","mirror":False,"controls_are_separate":True,"formal_art_pass":False,"outputs":outputs})
  cell=Image.new("RGB",(320,460),(230,230,230));draw=ImageDraw.Draw(cell);draw.text((8,8),f"{vid} | renderer {expected_renderer:+d}",fill="black")
  for i,k in enumerate(KINDS):cell.paste(mini(images[k]),(8+i*102,45));draw.text((8+i*102,430),k,fill="black")
  panels.append(cell)
 contact=Image.new("RGB",(6*320,4*460),(200,200,200))
 for i,p in enumerate(panels):contact.paste(p,((i%6)*320,(i//6)*460))
 contact_path=OUT/"orthographic-separated-controls-24-contact.png";contact.save(contact_path)
 manifest={"schema":"mohan.orthographic_separated_controls_24/v1","status":"PASS_CPU_CONTROLS_ONLY" if not technical_failures else "FAIL_CPU_CONTROLS","view_count":len(records),"controls_per_view":3,"exact_png_count":len(list(controls.glob("*.png"))),"canvas":{"width":1024,"height":1536},"yaw_step_degrees":15,"pitch_degrees":0,"camera":"orthographic","mapping_rule":"source_renderer_yaw=-formal_yaw; -180 canonical","mirror":False,"controls_must_remain_separate_from_final_rgb":True,"final_rgb_files_created":0,"gpu_used":False,"formal_main_view_pass_count":0,"source_manifest":{"path":str(SOURCE_MANIFEST),"sha256":sha(SOURCE_MANIFEST)},"views":records,"technical_failures":technical_failures,"contact":{"path":str(contact_path),"sha256":sha(contact_path)},"exit_code":0 if not technical_failures and len(records)==24 and len(list(controls.glob('*.png')))==72 else 4}
 (OUT/"controls-24-manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8");print(json.dumps({k:manifest[k] for k in ("status","view_count","exact_png_count","technical_failures","exit_code")},ensure_ascii=False,indent=2));return manifest["exit_code"]
if __name__=="__main__":raise SystemExit(main())
