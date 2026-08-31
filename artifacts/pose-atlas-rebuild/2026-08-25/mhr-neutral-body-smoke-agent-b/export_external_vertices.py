from __future__ import annotations
import argparse, struct
from pathlib import Path

def main()->int:
    p=argparse.ArgumentParser(); p.add_argument("--calculator-output",type=Path,required=True); p.add_argument("--case-index",type=int,default=0); p.add_argument("--output",type=Path,required=True); a=p.parse_args()
    data=a.calculator_output.read_bytes()
    if data[:8]!=b"MHRBDY1\0": raise RuntimeError("invalid calculator format")
    vertex_count,case_count=struct.unpack_from("<II",data,8)
    if not 0<=a.case_index<case_count: raise RuntimeError("case index out of range")
    block=64+vertex_count*3*8; offset=16+a.case_index*block+64; payload=data[offset:offset+vertex_count*3*8]
    if len(payload)!=vertex_count*3*8: raise RuntimeError("truncated calculator output")
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_bytes(b"MHRVRTX1"+struct.pack("<I",vertex_count)+payload)
    print(f"vertex_count={vertex_count} case_index={a.case_index} output_bytes={a.output.stat().st_size}"); return 0
if __name__=="__main__": raise SystemExit(main())
