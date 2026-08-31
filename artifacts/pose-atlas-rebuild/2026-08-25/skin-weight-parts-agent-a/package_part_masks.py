from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
CONTROL = PROJECT / "artifacts/pose-atlas-rebuild/2026-08-25/ufbx-lod1-extractor-agent-a/candidate3-yaw-controls-24/controls"
OUT = HERE / "masks"
YAW = tuple(range(-180, 180, 15))
COLORS = {0:(0,0,0),1:(235,80,80),2:(80,160,235),3:(255,170,60),4:(255,215,80),5:(180,235,80),6:(225,110,190),7:(180,90,225),8:(120,90,225),9:(80,210,160),10:(60,180,120),11:(40,140,90),12:(80,210,220),13:(60,170,200),14:(50,120,180),255:(255,0,255)}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    OUT.mkdir(exist_ok=True)
    records=[]; thumbs=[]
    for yaw in YAW:
        view=f"yaw{yaw:+04d}-pitch+00"
        source=HERE/"masks-pgm"/f"{view}_part-id.pgm"
        image=Image.open(source); image.load()
        if image.mode != "L" or image.size != (1024,1536): raise ValueError(view)
        image_data = image.get_flattened_data()
        ids=Counter(image_data)
        unexpected=set(ids)-set(COLORS)
        if unexpected: raise ValueError(f"unexpected IDs {unexpected}")
        target=OUT/f"{view}_part-id.png"; image.save(target,optimize=False)
        silhouette=Image.open(CONTROL/f"{view}_silhouette.png").convert("L")
        expected={i for i,v in enumerate(silhouette.get_flattened_data()) if v>0}
        actual={i for i,v in enumerate(image_data) if v>0}
        union=len(expected|actual); iou=len(expected&actual)/union if union else 1.0
        records.append({"view_id":view,"path":str(target.relative_to(HERE)).replace("\\","/"),"sha256":digest(target),"mode":"L","size":[1024,1536],"part_pixel_counts":{str(k):v for k,v in sorted(ids.items())},"occupancy_iou_vs_candidate3_silhouette":iou})
        rgb=Image.new("RGB",image.size)
        rgb.putdata([COLORS[value] for value in image_data])
        thumb=rgb.resize((256,384),Image.Resampling.NEAREST)
        canvas=Image.new("RGB",(256,408),(245,245,245));canvas.paste(thumb,(0,24));ImageDraw.Draw(canvas).text((5,5),view,fill=(0,0,0));thumbs.append(canvas)
    sheet=Image.new("RGB",(6*256,4*408),(255,255,255))
    for index,thumb in enumerate(thumbs):sheet.paste(thumb,((index%6)*256,(index//6)*408))
    sheet_path=HERE/"part-id-contact-sheet.png";sheet.save(sheet_path)
    report={"schema":"mohan.mhr.skin-weight-part-mask-qa.v1","status":"PASS","truth_boundary":"Skin-weight-derived control masks, not clothing or final art.","views":records,"summary":{"file_count":len(records),"all_1024x1536_L":all(r["mode"]=="L" and r["size"]==[1024,1536] for r in records),"min_occupancy_iou":min(r["occupancy_iou_vs_candidate3_silhouette"] for r in records),"contact_sheet_sha256":digest(sheet_path)}}
    (HERE/"part-id-mask-qa.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"PASS","files":len(records),"min_iou":report["summary"]["min_occupancy_iou"],"contact_sheet_sha256":report["summary"]["contact_sheet_sha256"]},sort_keys=True))
    return 0


if __name__=="__main__":sys.exit(main())
