from __future__ import annotations

import argparse
from pathlib import Path

import torch


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--topology-obj", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    model = torch.jit.load(str(args.model), map_location="cpu")
    identity = torch.zeros((1, 45), dtype=torch.float32)
    pose = torch.zeros((1, 204), dtype=torch.float32)
    expression = torch.zeros((1, 72), dtype=torch.float32)
    with torch.no_grad():
        vertices, skeleton = model(identity, pose, expression, False)

    if vertices.shape != (1, 18439, 3):
        raise RuntimeError(f"unexpected vertices shape: {tuple(vertices.shape)}")
    if skeleton.shape != (1, 127, 8):
        raise RuntimeError(f"unexpected skeleton shape: {tuple(skeleton.shape)}")
    if not bool(torch.isfinite(vertices).all()):
        raise RuntimeError("vertices contain non-finite values")

    faces = [
        line
        for line in args.topology_obj.read_text(encoding="utf-8").splitlines()
        if line.startswith("f ")
    ]
    if len(faces) != 36874:
        raise RuntimeError(f"unexpected face count: {len(faces)}")

    verts = vertices[0].cpu().tolist()
    with args.output.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write("# MHR v1.0.1 zero-neutral vertices with LOD1 topology\n")
        stream.write("o mhr_zero_neutral_lod1\n")
        for x, y, z in verts:
            stream.write(f"v {x:.9g} {y:.9g} {z:.9g}\n")
        for face in faces:
            stream.write(face)
            stream.write("\n")

    extent = vertices.amax(dim=1) - vertices.amin(dim=1)
    print(f"vertices={vertices.shape[1]}")
    print(f"triangles={len(faces)}")
    print(f"extent={extent[0].tolist()}")
    print(f"output={args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
