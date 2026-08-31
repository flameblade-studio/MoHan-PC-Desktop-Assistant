"""把整晚的證據並成一張圖：初始圖種類 × 強度 → 幾何與風格各自守住了沒有。

每格底下標的兩個數字都是可證偽的量測，不是觀感：
  IoU  輸出剪影與 bundle silhouette 的重疊；純文生圖基準 0.396 是下界，
       低於它就代表幾何沒進去
  彩度 前景平均飽和度；灰模自身 0.120 是下界，貼著它就代表沒上色
"""
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def cjk_font(size: int) -> ImageFont.FreeTypeFont:
    """PIL 預設點陣字型沒有中日韓字，中文標籤會全部變成方框。"""
    for name in ("msjh.ttc", "msyh.ttc", "simhei.ttf"):
        try:
            return ImageFont.truetype(rf"C:\Windows\Fonts\{name}", size)
        except OSError:
            continue
    return ImageFont.load_default()

sys.path.insert(0, str(Path(__file__).parent))
from recompute_iou import chroma, foreground, iou, true_control  # noqa: E402

ROOT = Path(os.environ.get(
    "MOHAN_VISION_ROOT",
    r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision",
))
GREY = ROOT / "work/second-gen-body/strength-iou-probe"
TINT = ROOT / "work/second-gen-body/tinted-strength-probe"
OUT = ROOT / "work/second-gen-body/geometry-conditioning-summary.png"

PANELS = [
    (GREY / "_init.png", "初始圖：灰模"),
    (GREY / "s085.png", "灰模 s0.85"),
    (GREY / "s095.png", "灰模 s0.95"),
    (GREY / "baseline-t2i.png", "純文生圖基準"),
    (TINT / "_init-tinted-hair.png", "初始圖：染色+髮"),
    (TINT / "tinted-hair-s085.png", "染色+髮 s0.85"),
    (TINT / "tinted-hair-s080.png", "染色+髮 s0.80"),
    (TINT / "tinted-s085.png", "染色 s0.85"),
]
TILE_H = 560
LABEL = 46


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    control = true_control()
    tiles = []
    for path, label in PANELS:
        if not path.exists():
            print(f"缺 {path.name}，略過")
            continue
        image = Image.open(path).convert("RGB")
        mask, _bg, _frac = foreground(path)
        note = f"IoU {iou(mask, control):.3f}   彩度 {chroma(path, mask):.3f}"
        tile = image.resize((image.width * TILE_H // image.height, TILE_H),
                            Image.LANCZOS)
        tiles.append((tile, label, note))

    if not tiles:
        print("沒有可用面板")
        return
    gap = 8
    width = sum(t.width for t, _, _ in tiles) + gap * (len(tiles) - 1)
    sheet = Image.new("RGB", (width, TILE_H + LABEL), (252, 252, 252))
    draw = ImageDraw.Draw(sheet)
    title_font, note_font = cjk_font(19), cjk_font(15)
    x = 0
    for tile, label, note in tiles:
        sheet.paste(tile, (x, LABEL))
        draw.text((x + 6, 4), label, fill=(15, 15, 15), font=title_font)
        draw.text((x + 6, 26), note, fill=(90, 90, 90), font=note_font)
        x += tile.width + gap
    sheet.save(OUT)
    print(f"{OUT}  {sheet.size}")


if __name__ == "__main__":
    main()
