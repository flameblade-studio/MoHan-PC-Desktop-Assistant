from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


PROJECT = Path(r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision")
REPRO = PROJECT / r"artifacts\pose-atlas-rebuild\2026-08-25\mhr-neutral-body-smoke-agent-b\candidate2-yaw075-independent-repro-agent-b"


SOURCES = [
    {
        "id": "formal_yaw075_geometry_base_mask",
        "role": "formal +075 geometry occupancy; renderer-native -075; no mirror",
        "path": REPRO / r"formal-yaw+075-sign-corrected-evidence\yaw+075-pitch+00_geometry-base-mask.png",
    },
    {
        "id": "formal_yaw075_depth",
        "role": "formal +075 depth control; renderer-native -075; no mirror",
        "path": REPRO / r"formal-yaw+075-sign-corrected-evidence\yaw+075-pitch+00_depth.png",
    },
    {
        "id": "formal_yaw075_view_normal",
        "role": "formal +075 view-normal control; renderer-native -075; no mirror",
        "path": REPRO / r"formal-yaw+075-sign-corrected-evidence\yaw+075-pitch+00_normal.png",
    },
    {
        "id": "b00_full_body_outfit_authority",
        "role": "full-body framing and blue-outer/white-inner outfit authority; clothing remains separable",
        "path": PROJECT / r"artifacts\pose-atlas-rebuild\2026-08-24\mother-views\yaw+000-pitch+00.approved-rgba.png",
    },
    {
        "id": "idle_front_identity_authority",
        "role": "face identity authority",
        "path": PROJECT / r"assets\expressions\idle_front.png",
    },
    {
        "id": "idle_lean_identity_authority",
        "role": "face identity authority",
        "path": PROJECT / r"assets\expressions\idle_lean.png",
    },
    {
        "id": "idle_identity_authority",
        "role": "face identity authority",
        "path": PROJECT / r"assets\expressions\idle.png",
    },
    {
        "id": "exec82b_ornament_physical_side_authority",
        "role": "user-confirmed ornament physical-side authority; do not mirror",
        "path": Path(r"C:\Users\hitos\.codex\generated_images\01a009be-0db2-7811-a647-3b7ac37528a9\exec-82b460bc-acca-4611-8a56-71194beded59.png"),
    },
    {
        "id": "yaw060_v8_angle_mother",
        "role": "adjacent +060 whole-body angle mother only; not identity authority",
        "path": PROJECT / r"artifacts\pose-atlas-rebuild\2026-08-25\yaw060-candidate-v8-endpoint-bracketed-main\yaw+060-pitch+00.candidate-v8.endpoint-bracketed.imagegen-raw.png",
    },
    {
        "id": "yaw090_v1_angle_mother",
        "role": "adjacent +090 whole-body angle mother only; not identity authority",
        "path": PROJECT / r"artifacts\pose-atlas-rebuild\2026-08-25\yaw090-candidate-v1-angle-overdrive-main\yaw+090-pitch+00.candidate-v1.angle-overdrive.imagegen-raw.png",
    },
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in (Path(r"C:\Windows\Fonts\msjh.ttc"), Path(r"C:\Windows\Fonts\arial.ttf")):
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def contain_on_background(path: Path, size: tuple[int, int], background: str) -> Image.Image:
    with Image.open(path) as source:
        rgba = source.convert("RGBA")
        composite = Image.new("RGBA", rgba.size, background)
        composite.alpha_composite(rgba)
        rgb = composite.convert("RGB")
    return ImageOps.contain(rgb, size, Image.Resampling.LANCZOS)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    missing = [str(item["path"]) for item in SOURCES if not item["path"].is_file()]
    if missing:
        (args.output_dir / "missing-inputs.json").write_text(
            json.dumps({"status": "FAIL", "missing": missing}, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return 4

    tile_width, tile_height = 560, 760
    columns, rows = 5, 2
    header_height = 300
    board = Image.new("RGB", (columns * tile_width, header_height + rows * tile_height), "#151922")
    draw = ImageDraw.Draw(board)
    title_font = load_font(44)
    rule_font = load_font(28)
    label_font = load_font(23)
    small_font = load_font(18)

    draw.text((30, 22), "墨寒 PoseAtlas +075 局部受控生成板（證據板，非正式素材）", font=title_font, fill="#ffffff")
    rules = [
        "正式 +075：臉／胸／軀幹共同朝畫布左；禁止鏡像；頭身必須同 yaw。",
        "身份只依三張 idle；髮飾物理側依 exec-82b；服裝藍外白內、低白鞋。",
        "core body／皮膚／頭髮與預設衣裝必須可拆；B00 衣服不得焊入 core。",
        "+060／+090 只作角度夾定；062 像素未載入、未混入本板。",
    ]
    for index, line in enumerate(rules):
        draw.text((38, 94 + index * 47), line, font=rule_font, fill="#d7e6ff")

    records = []
    for index, item in enumerate(SOURCES):
        column, row = index % columns, index // columns
        x0, y0 = column * tile_width, header_height + row * tile_height
        panel = (x0 + 12, y0 + 12, x0 + tile_width - 12, y0 + tile_height - 12)
        draw.rounded_rectangle(panel, radius=18, fill="#252b38", outline="#63718d", width=3)
        preview = contain_on_background(item["path"], (tile_width - 52, 590), "#8b8b8b")
        px = x0 + (tile_width - preview.width) // 2
        py = y0 + 72 + (590 - preview.height) // 2
        board.paste(preview, (px, py))
        draw.text((x0 + 24, y0 + 24), item["id"], font=label_font, fill="#ffffff")
        draw.text((x0 + 24, y0 + 676), item["role"], font=small_font, fill="#c8d3e6")

        with Image.open(item["path"]) as source:
            records.append(
                {
                    "id": item["id"],
                    "role": item["role"],
                    "path": str(item["path"].resolve()),
                    "sha256": sha256(item["path"]),
                    "size": list(source.size),
                    "mode": source.mode,
                    "board_operation": "display-only contain resize over neutral gray; source file unchanged",
                }
            )

    board_path = args.output_dir / "yaw+075-local-controlled-generation-board.png"
    board.save(board_path, optimize=False)
    manifest = {
        "schema": "mohan.pose_atlas.local_control_board.v1",
        "status": "PASS_CONTROL_BOARD_ONLY_NOT_FORMAL_ASSET",
        "formal_view_id": "yaw+075-pitch+00",
        "formal_direction": "face/chest/body toward canvas-left",
        "prohibitions": ["no mirroring", "no whole-person random generation", "no clothing welded into core", "no 062 pixels"],
        "required_art_contract": ["head and body share yaw", "blue outerwear", "white innerwear", "low white shoes", "separable outfit"],
        "board": {"path": str(board_path.resolve()), "sha256": sha256(board_path), "size": list(board.size), "mode": board.mode},
        "sources": records,
        "explicitly_excluded": ["062.png pixels"],
    }
    manifest_path = args.output_dir / "source-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "source_count": len(records), "board_sha256": manifest["board"]["sha256"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
