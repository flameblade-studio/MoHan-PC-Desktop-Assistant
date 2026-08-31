"""Losslessly adapt verified MHRVTX2 float64 vertices for the CPU renderer."""

from __future__ import annotations

import argparse
import struct
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = args.input.read_bytes()
    if len(data) < 16 or data[:8] != b"MHRVTX2\0":
        raise ValueError("input is not MHRVTX2")
    vertex_count, components = struct.unpack_from("<II", data, 8)
    if vertex_count != 18_439 or components != 3:
        raise ValueError(f"unexpected shape: {vertex_count}x{components}")
    payload = data[16:]
    expected = vertex_count * components * 8
    if len(payload) != expected:
        raise ValueError(f"payload bytes {len(payload)} != {expected}")
    args.output.write_bytes(b"MHRVRTX1" + struct.pack("<I", vertex_count) + payload)
    print(f"vertex_count={vertex_count} components={components} payload_bytes={len(payload)} lossless_payload_copy=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
