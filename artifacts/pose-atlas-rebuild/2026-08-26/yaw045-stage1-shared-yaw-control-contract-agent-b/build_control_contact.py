from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


HERE = Path(__file__).resolve().parent
REQ = json.loads((HERE / "control-requirements.json").read_text(encoding="utf-8"))


def font(size: int):
    path = Path(r"C:\Windows\Fonts\arial.ttf")
    return ImageFont.truetype(str(path), size) if path.is_file() else ImageFont.load_default()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    canvas = Image.new("RGB", (1536, 1840), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((24, 18), "yaw+045 stage-1 shared-yaw control bundle | renderer -45 | mirror=false", fill="black", font=font(30))
    names = ("silhouette", "depth", "normal")
    for index, name in enumerate(names):
        item = REQ["control_inputs"][name]
        image = Image.open(item["path"]).convert("RGB")
        image.thumbnail((500, 1500), Image.Resampling.NEAREST)
        x = 12 + index * 508
        canvas.paste(image, (x, 90))
        draw.text((x + 10, 100), name, fill="white", font=font(24), stroke_width=3, stroke_fill="black")
        for band, (y0, y1) in REQ["measurement_gates"]["bands_y"].items():
            scale = image.height / 1536
            yy = 90 + round(y0 * scale)
            draw.line((x, yy, x + image.width, yy), fill=(255, 80, 0), width=2)
            draw.text((x + 6, yy + 3), band, fill=(255, 220, 0), font=font(16), stroke_width=2, stroke_fill="black")
        ax = x + round(512 * image.width / 1024)
        ay = 90 + round(1292 * image.height / 1536)
        draw.line((ax - 16, ay, ax + 16, ay), fill="lime", width=4)
        draw.line((ax, ay - 16, ax, ay + 16), fill="lime", width=4)
    draw.text((24, 1620), "Required: head/shoulders/chest/pelvis/feet = 45 +/- 7 deg; spread <= 8 deg", fill="black", font=font(26))
    draw.text((24, 1662), "Anchor [512,1292] (not bbox center); x +/-20 px, y +/-2 px; canvas margin >=16 px", fill="black", font=font(24))
    draw.text((24, 1704), "Ornament: fixed physical side -> expected canvas-right; mirror forbidden; occlusion cannot be PENDING", fill="black", font=font(24))
    draw.text((24, 1746), "Controls never enter final RGB. Machine PASS is not formal art PASS.", fill="red", font=font(26))
    out = HERE / "control-requirements-contact.png"
    canvas.save(out)
    result = {"path": str(out), "sha256": sha256(out), "size": list(canvas.size), "mode": canvas.mode}
    (HERE / "control-contact-report.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
