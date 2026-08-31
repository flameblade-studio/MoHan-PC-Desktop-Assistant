from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.source.read_bytes()
    if source[:8] != b"MHRVTX2\0" or len(source) < 16:
        raise ValueError("Expected MHRVTX2 binary")
    count, components = struct.unpack("<II", source[8:16])
    payload = source[16:]
    if count != 18_439 or components != 3 or len(payload) != count * components * 8:
        raise ValueError(f"Invalid vertex contract: {count} {components} {len(payload)}")
    adapted = b"MHRVRTX1" + struct.pack("<I", count) + payload
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(adapted)
    if adapted[12:] != payload:
        raise AssertionError("Payload copy was not exact")
    print(json.dumps({
        "status": "PASS_LOSSLESS_HEADER_ADAPTER",
        "source": str(args.source.resolve()),
        "source_sha256": sha256(source),
        "output": str(args.output.resolve()),
        "output_sha256": sha256(adapted),
        "vertex_count": count,
        "payload_bytes": len(payload),
        "payload_exact": True,
    }, indent=2))


if __name__ == "__main__":
    main()
