"""把灰模染成膚色再當初始圖。

單段 img2img 的兩難是這樣來的：低強度守得住幾何但輸出還是灰黏土，
高強度上得了色但幾何完全沒進去。兩難的根源是**初始圖的顏色先驗是錯的**——
模型看到一尊灰色雕像，就得花掉大部分的去噪預算去把它變成人，
而那筆預算一花下去，幾何也一起被改掉了。

解法是讓初始圖一開始就指向目標：灰模的明暗保留當光照，顏色換成膚色。
bundle 的 ownership 遮罩證實這具網格是全裸光頭（hair 與 ornament 皆 0%、
anatomy 與 silhouette 同為 9.6%），所以整具套同一組膚色即可，不必分區。

染色方式刻意保守——只在亮度通道上做線性重映射，不加任何紋理或細節，
免得把「我猜的膚色」變成模型會照抄的權威資訊。真正的膚色仍由 LoRA 決定。
"""
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(os.environ.get(
    "MOHAN_VISION_ROOT",
    r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision",
))
BUNDLES = (
    ROOT / "artifacts/pose-atlas-rebuild/2026-08-26"
    / "canonical24-control-bundles-agent-b/bundles"
)
PLATE = (196, 198, 200)
# 中性東亞膚色，刻意偏淡；只當顏色先驗，不當目標色
SKIN_DARK = np.array([150.0, 116.0, 100.0])
SKIN_LIGHT = np.array([248.0, 225.0, 210.0])
WIDTH, HEIGHT = 832, 1248


HAIR_DARK = np.array([38.0, 32.0, 34.0])


def _hair_hint(canvas: np.ndarray, inside: np.ndarray) -> np.ndarray:
    """在頭頂補一塊低頻暗色髮團。

    輸出一直是光頭，原因跟膚色一樣是低頻：網格沒有頭髮，低頻訊號就一路
    堅持「頭上沒有東西」，這不是把 strength 調高能解的（0.65 到 0.75 都光頭）。
    這裡只補「頭上有一團深色」這個低頻事實，形狀刻意做成粗糙的橢圓，
    不試圖畫出髮髻造型——真正的髮型由 LoRA 與提示詞決定。
    """
    rows = np.where(inside.any(axis=1))[0]
    if not rows.size:
        return canvas
    top, bottom = int(rows[0]), int(rows[-1])
    body_height = bottom - top
    # 頭部約佔站姿全高的前 13%。先前誤用「上 1/6 列的最大寬度」，
    # 那個範圍已含肩膀，於是半徑取到肩寬，整張臉被髮團蓋掉。
    head_rows = [r for r in rows if r <= top + body_height * 0.13]
    spans = [np.where(inside[r])[0] for r in head_rows]
    spans = [s for s in spans if s.size]
    if not spans:
        return canvas
    head_width = max(s[-1] - s[0] for s in spans)
    centre = int(np.mean([(s[0] + s[-1]) / 2 for s in spans]))
    head_height = body_height * 0.13

    height, width = inside.shape
    yy, xx = np.mgrid[0:height, 0:width]
    # 只補頭頂以上的髮髻塊面，加上頭皮前三成，一律不碰臉
    scalp_limit = top + head_height * 0.30
    bun = ((xx - centre) / (head_width * 0.52)) ** 2 + \
          ((yy - (top - head_height * 0.10)) / (head_height * 0.42)) ** 2 <= 1.0
    canvas[bun & (yy < scalp_limit)] = HAIR_DARK
    canvas[inside & (yy < scalp_limit)] = HAIR_DARK
    return canvas


def tinted_init(
    folder: Path,
    size: tuple[int, int] = (WIDTH, HEIGHT),
    *,
    hair_hint: bool = False,
    preserve_contrast: bool = False,
) -> Image.Image:
    """preserve_contrast：只換色度，保留灰模原本的明暗動態範圍。

    預設的做法把亮度重映射到 SKIN_DARK~SKIN_LIGHT 這條窄帶，實測把動態範圍
    從 148 壓到 106（少 28%）。明暗正是承載正反 3D 資訊的訊號——為了給對
    顏色先驗，反而削弱了判別正反的線索，而 yaw+000 連續兩次翻成背面。
    這個選項改成乘上膚色色度、亮度照舊，兩者兼得。
    """
    stem = folder.name
    return tinted_from_paths(
        folder / f"{stem}_shaded-render.png",
        folder / f"{stem}_silhouette.png",
        size, hair_hint=hair_hint, preserve_contrast=preserve_contrast,
    )


def tinted_from_paths(
    shaded_path: Path,
    silhouette_path: Path,
    size: tuple[int, int] = (WIDTH, HEIGHT),
    *,
    hair_hint: bool = False,
    preserve_contrast: bool = False,
) -> Image.Image:
    """直接指定兩張控制圖。candidate4 的控制圖是平鋪檔案而非 bundle 目錄。"""
    shaded = Image.open(shaded_path).convert("L")
    mask = Image.open(silhouette_path).convert("L")

    luma = np.asarray(shaded).astype(np.float32)
    inside = np.asarray(mask) > 24
    if inside.any():
        low = np.percentile(luma[inside], 3)
        high = np.percentile(luma[inside], 97)
        span = max(high - low, 1.0)
        t = np.clip((luma - low) / span, 0.0, 1.0)[..., None]
    else:
        t = np.zeros((*luma.shape, 1), dtype=np.float32)

    if preserve_contrast:
        # 膚色只提供色度，亮度直接沿用灰模；略為提亮以避免整體偏暗
        hue = (SKIN_DARK + SKIN_LIGHT) / 2.0
        skin = (luma[..., None] * 1.12).clip(0, 255) * (hue / hue.mean())
    else:
        skin = SKIN_DARK + (SKIN_LIGHT - SKIN_DARK) * t
    canvas = np.empty((*luma.shape, 3), dtype=np.float32)
    canvas[:] = np.array(PLATE, dtype=np.float32)
    canvas[inside] = skin[inside]
    if hair_hint:
        canvas = _hair_hint(canvas, inside)
        inside = inside | (np.abs(canvas - np.array(PLATE, dtype=np.float32))
                           .sum(axis=2) > 40)
    merged = Image.fromarray(canvas.clip(0, 255).astype(np.uint8), "RGB")

    box = Image.fromarray((inside * 255).astype(np.uint8)).getbbox()
    if box:
        left, top, right, bottom = box
        pad_x = int((right - left) * 0.16)
        pad_y = int((bottom - top) * 0.05)
        left, top = max(0, left - pad_x), max(0, top - pad_y)
        right = min(merged.width, right + pad_x)
        bottom = min(merged.height, bottom + pad_y)
        ratio = size[0] / size[1]
        if (right - left) / (bottom - top) < ratio:
            need = int((bottom - top) * ratio) - (right - left)
            left = max(0, left - need // 2)
            right = min(merged.width, right + need - need // 2)
        merged = merged.crop((left, top, right, bottom))
        if merged.width / merged.height < ratio:
            board = Image.new("RGB", (int(merged.height * ratio), merged.height), PLATE)
            board.paste(merged, ((board.width - merged.width) // 2, 0))
            merged = board
    return merged.resize(size, Image.LANCZOS)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    out = ROOT / "work/second-gen-body/tinted-init"
    out.mkdir(parents=True, exist_ok=True)
    for name in ("yaw+000-pitch+00", "yaw+090-pitch+00", "yaw-180-pitch+00"):
        image = tinted_init(BUNDLES / name)
        target = out / f"tinted-{name}.png"
        image.save(target)
        array = np.asarray(image).astype(np.float32)
        high, low = array.max(axis=2), array.min(axis=2)
        sat = np.where(high > 0, (high - low) / np.maximum(high, 1.0), 0.0)
        body = np.abs(array - np.array(PLATE)).sum(axis=2) > 40
        print(f"{target.name}  前景 {body.mean()*100:.1f}%  "
              f"前景彩度 {sat[body].mean():.3f}")


if __name__ == "__main__":
    main()
