from __future__ import annotations

import hashlib, json, math
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

PROJECT=Path(r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision")
ROOT=Path(__file__).resolve().parent
BUNDLES=PROJECT/r"artifacts\pose-atlas-rebuild\2026-08-26\canonical24-control-bundles-agent-b\bundles"
SOURCE_RGBA=PROJECT/r"assets\pose-atlas\v4-layered\yaw+000-pitch+00_ornament.png"
CONTROLS,OVERLAYS,ASSETS=ROOT/"controls",ROOT/"overlays",ROOT/"assets"
YAWS=tuple(range(-180,180,15)); CANVAS=(1024,1536)

def vid(y:int)->str:return f"yaw{y:+04d}-pitch+00"
def sha(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda:f.read(1<<20),b""):h.update(c)
    return h.hexdigest().upper()

def head_bbox(path:Path)->tuple[int,int,int,int]:
    a=np.asarray(Image.open(path).convert("L")); ys,xs=np.nonzero(a==1)
    if len(xs)==0:raise RuntimeError(f"head part ID 1 absent: {path}")
    return int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1

def pure_ornament_source(source:Image.Image,src_head:tuple[int,int,int,int])->Image.Image:
    """Remove the face pixels incorrectly baked into the legacy ornament layer."""
    rgba=np.asarray(source.convert("RGBA"),dtype=np.uint8).copy(); sx0,sy0,sx1,_=src_head
    yy,xx=np.indices(rgba.shape[:2]); rgb=rgba[:,:,:3].astype(np.int16)
    skin=(rgb[:,:,0]>80)&(rgb[:,:,0]>rgb[:,:,1]*1.06)&(rgb[:,:,1]>rgb[:,:,2]*1.03)
    # Crown and horizontal pin sit above the canonical forehead.  The approved
    # fixed-side tassel extends down only outside the image-right head edge.
    physical_region=(yy<sy0+16)|((xx>=sx1)&(yy<sy0+46))
    keep=(rgba[:,:,3]>0)&physical_region&(~skin)
    rgba[~keep]=0
    return Image.fromarray(rgba,"RGBA")

def project(source:Image.Image,src_head:tuple[int,int,int,int],dst_head:tuple[int,int,int,int],yaw:int):
    """Rotate one approved physical-side ornament surface; never mirror pixels."""
    rgba=np.asarray(source.convert("RGBA"),dtype=np.uint8); a=rgba[:,:,3]; ys,xs=np.nonzero(a>0)
    sx0,sy0,sx1,sy1=src_head; tx0,ty0,tx1,ty1=dst_head
    scx=(sx0+sx1-1)/2; tcx=(tx0+tx1-1)/2
    srx=max((sx1-sx0)*.72,1); trx=max((tx1-tx0)*.72,1)
    sh=max(sy1-sy0,1); th=max(ty1-ty0,1)
    # Formal yaw maps to renderer-native negative yaw.
    theta=math.radians(-yaw); ct,st=math.cos(theta),math.sin(theta)
    xl=np.clip((xs.astype(np.float32)-scx)/srx,-1.35,1.35)
    zl=np.sqrt(np.clip(1-np.minimum(np.abs(xl),1)**2,0,1))
    # The approved asset's image-right pin/tassel is the same physical side at every yaw.
    protrude=np.clip((xl-.15)/.85,0,1); zl*=.78-.18*protrude
    xr=xl*ct+zl*st; zr=-xl*st+zl*ct
    visible=(zr>=-.04)|(np.abs(xr)>=.82)|((protrude>=.35)&(zr>=-.38))
    xo=np.rint(tcx+xr*trx).astype(np.int32)
    yo=np.rint(ty0+(ys.astype(np.float32)-sy0)*(th/sh)).astype(np.int32)
    inside=visible&(xo>=0)&(xo<CANVAS[0])&(yo>=0)&(yo<CANVAS[1])
    out=np.zeros((CANVAS[1],CANVAS[0],4),dtype=np.uint8)
    indices=np.flatnonzero(inside)[np.argsort(zr[inside])]
    for i in indices:
        pixel=rgba[ys[i],xs[i]].copy(); gain=float(np.clip((zr[i]+.45)/.75,.30,1))
        pixel[3]=np.uint8(round(int(pixel[3])*gain)); x,y=int(xo[i]),int(yo[i])
        if pixel[3]>=out[y,x,3]:out[y,x]=pixel
    kernel=np.ones((3,3),np.uint8); mask=out[:,:,3]
    closed=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,kernel,iterations=1)
    fill=(closed>0)&(mask==0)
    if np.any(fill):
        rgb=cv2.dilate(out[:,:,:3],kernel,iterations=1); out[fill,:3]=rgb[fill]; out[fill,3]=closed[fill]
    mask=out[:,:,3]
    if yaw in (0,45,90) and np.count_nonzero(mask)==0:raise RuntimeError(f"Smoke3 fully occluded: {yaw:+d}")
    meta={"formal_yaw":yaw,"mirror_used":False,"projection":"fixed-side crown surface rotation with head occlusion","source_view":"yaw+000-pitch+00","source_head_bbox":list(src_head),"target_head_bbox":list(dst_head),"visible_pixels":int(np.count_nonzero(mask)),"alpha_sum":int(mask.astype(np.uint64).sum())}
    return Image.fromarray(out,"RGBA"),Image.fromarray(mask,"L"),meta

def overlay(base:Path,rgba:Image.Image,mask:Image.Image,yaw:int)->Image.Image:
    image=Image.alpha_composite(Image.open(base).convert("RGBA"),rgba)
    edge=cv2.morphologyEx(np.asarray(mask),cv2.MORPH_GRADIENT,np.ones((3,3),np.uint8))
    arr=np.asarray(image).copy(); arr[edge>0,:3]=(255,80,40); image=Image.fromarray(arr,"RGBA")
    d=ImageDraw.Draw(image); d.rectangle((12,12,370,52),fill=(0,0,0,190)); d.text((22,21),f"{vid(yaw)} | fixed side | mirror=false",fill="white",font=ImageFont.load_default())
    return image

def make_sheet(paths:list[Path],out:Path)->None:
    size=(256,384); sheet=Image.new("RGB",(1536,4*(384+28)),(28,31,36)); d=ImageDraw.Draw(sheet); font=ImageFont.load_default()
    for i,p in enumerate(paths):
        im=Image.open(p).convert("RGB"); im.thumbnail(size,Image.Resampling.LANCZOS)
        x=(i%6)*256+(256-im.width)//2; y=(i//6)*412; sheet.paste(im,(x,y)); d.text((x+5,y+390),p.stem.replace("_ornament-overlay",""),fill="white",font=font)
    sheet.save(out,quality=94,subsampling=0)

def main()->int:
    if not SOURCE_RGBA.is_file():raise FileNotFoundError(SOURCE_RGBA)
    legacy_source=Image.open(SOURCE_RGBA).convert("RGBA"); source_bundle=BUNDLES/vid(0)
    src_head=head_bbox(source_bundle/f"{vid(0)}_part-id.png")
    CONTROLS.mkdir(parents=True,exist_ok=True); OVERLAYS.mkdir(parents=True,exist_ok=True); ASSETS.mkdir(parents=True,exist_ok=True)
    source=pure_ornament_source(legacy_source,src_head)
    pure_source_path=ROOT/"yaw+000-pitch+00_ornament-pure-fixed-side.png"; source.save(pure_source_path)
    records=[]; overlays=[]
    for yaw in YAWS:
        view=vid(yaw); bundle=BUNDLES/view; target=head_bbox(bundle/f"{view}_part-id.png")
        rgba,mask,meta=project(source,src_head,target,yaw)
        rp=CONTROLS/f"{view}_ornament-fixed-side-rgba.png"; ap=ASSETS/f"{view}_ornament.png"; mp=CONTROLS/f"{view}_ornament-fixed-side-mask.png"; jp=CONTROLS/f"{view}_ornament-fixed-side.json"; op=OVERLAYS/f"{view}_ornament-overlay.png"
        rgba.save(rp); rgba.save(ap); mask.save(mp); meta.update({"rgba_path":str(rp),"rgba_sha256":sha(rp),"asset_path":str(ap),"asset_sha256":sha(ap),"mask_path":str(mp),"mask_sha256":sha(mp)})
        jp.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); overlay(bundle/f"{view}_shaded-render.png",rgba,mask,yaw).save(op)
        records.append(meta); overlays.append(op)
    sheet=ROOT/"canonical24-ornament-fixed-side-contact-sheet.jpg"; make_sheet(overlays,sheet)
    manifest=ROOT/"canonical24-ornament-visibility-manifest.json"
    data={"schema":"mohan.canonical24.ornament_fixed_side_visibility.v1","status":"STAGING_CONTROL_READY","view_count":len(records),"mirror_used":False,"legacy_source_rgba":str(SOURCE_RGBA),"legacy_source_sha256":sha(SOURCE_RGBA),"pure_source_rgba":str(pure_source_path),"pure_source_sha256":sha(pure_source_path),"records":records,"contact_sheet":str(sheet),"contact_sheet_sha256":sha(sheet)}
    manifest.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    smoke={vid(y):records[YAWS.index(y)]["visible_pixels"] for y in (0,45,90)}
    print(json.dumps({"status":data["status"],"views":len(records),"mirror_used":False,"smoke3_visible_pixels":smoke,"manifest":str(manifest),"contact_sheet":str(sheet)},ensure_ascii=False));return 0

if __name__=="__main__":raise SystemExit(main())
