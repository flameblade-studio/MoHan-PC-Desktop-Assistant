"""v10：以幾何條件化量產 24 視角素體。擁有者 2026-08-31 核可 shaded s0.95。

配方（全部經探針實測）：
  初始圖  bundle 的 *_shaded-render.png 合成到淺灰底板（用同 bundle 的
          silhouette 遮罩，不需去背模型）
  strength 0.95   —— 0.70/0.80/0.88 殘留人偶體型，0.90 仍有色偏
  LoRA     0.85   —— 1.0 壓不住髮型，0.70 正面臉型變窄
  不用 normal map —— 0.90 與 0.95 兩檔皆造成系統性腳掌翹起

負向詞務必含 multiple people：淺灰底板讀作「可填滿的攝影棚空間」，
黑底讀作「虛空」。探針階段漏掉這一條，結果一張圖裡出現三個人。

yaw 符號：稽核記載 source_renderer_yaw = -formal_yaw，故輸出檔名取 bundle 的
負值，與既有 17 張 body2-yaw*.png 命名一致。

自我閘門：第一張產完即以連通分量數檢查人數，不通過就停止並回報，
不會讓 24 張帶著同一個缺陷跑完。
"""
import os
import sys
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image

# 本檔原於 session 暫存目錄開發，匯入路徑與資料根目錄都寫死。入庫時改為：
#   匯入路徑取自本檔所在目錄；資料根目錄可用 MOHAN_VISION_ROOT 覆寫，
#   預設保留原機器路徑，讓既有紀錄可重現。
sys.path.insert(0, str(Path(__file__).resolve().parent))
from thresholds import (
    BACK_YAW,
    FACE_AREA_MIN,
    FRONT_FACE_REQUIRED,
    GRAY_FIGURE_DISTANCE,
    REAR_FACE_FORBIDDEN,
    SILHOUETTE_ON,
)
from lora_loader import load_aitoolkit_chroma_lora
from chroma_mass_produce_v9 import BODY, HAIR, LORA, TAIL, GGUF, YUNET

ROOT = Path(os.environ.get(
    "MOHAN_VISION_ROOT",
    r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision",
))
BUNDLES = (
    ROOT / "artifacts/pose-atlas-rebuild/2026-08-26"
    / "canonical24-control-bundles-agent-b/bundles"
)
OUT = ROOT / "work/second-gen-body/chroma-views-v10-geo"
OUT.mkdir(parents=True, exist_ok=True)
WIDTH, HEIGHT = 832, 1248
PLATE = (196, 198, 200)
STRENGTH = 0.95
LORA_WEIGHT = 0.85

NEG = (
    "multiple people, two women, three women, duplicate person, twins, triptych, "
    "split screen, repeated figure, "
    "black background, dark background, vignette, spotlight, "
    "long hair falling over shoulders, hair down, loose long hair, bangs, fringe, "
    "hair covering the neck, hair on the shoulders, "
    "open mouth, parted lips, visible teeth, smiling, lipstick, red lips, "
    "male, masculine, mannequin, dummy, statue, gray skin, clay, "
    "tiptoe, raised heel, pointed toes, floating, "
    "earrings, necklace, jewelry, "
    "chubby, plump, thick thighs, wide hips, skinny, emaciated, tanned skin, "
    "low quality, worst quality, deformed, bad anatomy, extra limbs, "
    "deformed hands, deformed feet, blurry, cg, 3d render, watermark, text"
)


def formal_yaw(bundle_name: str) -> int:
    raw = int(bundle_name.split("yaw")[1].split("-pitch")[0])
    value = -raw
    # 稽核的正規形式是 -180，但既有 v9 的 17 張用 +180；統一成 +180 免得兩套對不上
    return BACK_YAW if abs(value) == BACK_YAW else value


def make_init(folder: Path) -> Image.Image:
    """合成到淺灰底板，並裁到人物身上。

    第一次嘗試不裁切，結果模型在左右的大片留白補上第二個人，自我閘門攔下。
    網格人物在 1024x1536 裡只佔窄窄一條；淺灰底把留白讀成可填充的攝影棚空間，
    黑底則讀作虛空，所以先前的黑底版本沒有這個問題。負向詞治不了構圖，
    只能消除那片空白——依 silhouette 的外接矩形裁切，再補到目標長寬比。
    """
    stem = folder.name
    shaded = Image.open(folder / f"{stem}_shaded-render.png").convert("RGB")
    mask = Image.open(folder / f"{stem}_silhouette.png").convert("L")
    plate = Image.new("RGB", shaded.size, PLATE)
    merged = Image.composite(shaded, plate, mask)

    box = mask.point(
        lambda v: 255 if v > SILHOUETTE_ON else 0).getbbox()
    if box:
        left, top, right, bottom = box
        pad_x = int((right - left) * 0.16)
        pad_y = int((bottom - top) * 0.05)
        left, top = max(0, left - pad_x), max(0, top - pad_y)
        right = min(merged.width, right + pad_x)
        bottom = min(merged.height, bottom + pad_y)
        # 補到 2:3，避免縮放時人物被拉扁
        target_ratio = WIDTH / HEIGHT
        width, height = right - left, bottom - top
        if width / height < target_ratio:
            need = int(height * target_ratio) - width
            left = max(0, left - need // 2)
            right = min(merged.width, right + need - need // 2)
        merged = merged.crop((left, top, right, bottom))
        if merged.width / merged.height < target_ratio:
            canvas = Image.new(
                "RGB", (int(merged.height * target_ratio), merged.height), PLATE
            )
            canvas.paste(merged, ((canvas.width - merged.width) // 2, 0))
            merged = canvas
    return merged.resize((WIDTH, HEIGHT), Image.LANCZOS)


def person_count(path: Path) -> int:
    """以剪影連通分量估計畫面人數；淺灰底與人物對比足夠，閾值切得乾淨。"""
    bgr = cv2.imread(str(path))
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    corners = np.concatenate([gray[:30, :30].ravel(), gray[:30, -30:].ravel()])
    background = float(np.median(corners))
    mask = (np.abs(gray.astype(np.int16) - background)
            > GRAY_FIGURE_DISTANCE).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    number, _labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    area = gray.shape[0] * gray.shape[1]
    return sum(1 for i in range(1, number) if stats[i, cv2.CC_STAT_AREA] > area * 0.01)


def verify_view(path: Path, yaw: int) -> str:
    bgr = cv2.imread(str(path))
    height, width = bgr.shape[:2]
    detector = cv2.FaceDetectorYN.create(str(YUNET), "", (320, 320), 0.6, 0.3, 5000)
    detector.setInputSize((width, height))
    _, found = detector.detect(bgr)
    has_face = found is not None and len(found) > 0
    area = 0.0
    if has_face:
        box = max(found, key=lambda f: f[2] * f[3])
        area = float(box[2] * box[3]) / (width * height)
    people = person_count(path)
    parts = [f"people={people}"]
    if people != 1:
        parts.append("FAIL multiple figures")
    if abs(yaw) >= REAR_FACE_FORBIDDEN and has_face:
        parts.append(f"FAIL back-view shows a face ({area:.4f})")
    elif abs(yaw) <= FRONT_FACE_REQUIRED and area < FACE_AREA_MIN:
        parts.append(f"FAIL frontal face too small ({area:.4f})")
    else:
        parts.append(f"ok face-area={area:.4f}")
    return "  ".join(parts)


def main() -> None:
    from diffusers import (
        ChromaImg2ImgPipeline, ChromaTransformer2DModel, GGUFQuantizationConfig,
    )

    folders = sorted(
        (f for f in BUNDLES.iterdir() if f.is_dir()),
        key=lambda f: abs(formal_yaw(f.name)),
    )
    print(f"bundles found: {len(folders)}", flush=True)

    transformer = ChromaTransformer2DModel.from_single_file(
        str(GGUF),
        quantization_config=GGUFQuantizationConfig(compute_dtype=torch.bfloat16),
        torch_dtype=torch.bfloat16,
    )
    pipe = ChromaImg2ImgPipeline.from_pretrained(
        "lodestones/Chroma1-HD", transformer=transformer, torch_dtype=torch.bfloat16
    )
    load_aitoolkit_chroma_lora(pipe, LORA, weight=LORA_WEIGHT)
    pipe.enable_model_cpu_offload()
    pipe.set_progress_bar_config(disable=True)
    print(f"v10 geo ready @ LoRA {LORA_WEIGHT} strength {STRENGTH}", flush=True)

    gate_done = False
    report = []
    for folder in folders:
        yaw = formal_yaw(folder.name)
        target = OUT / f"body2-yaw{yaw:+04d}.png"
        if target.exists():
            print(f"skip {target.name}", flush=True)
            gate_done = True
            continue
        image = pipe(
            prompt=(
                "mhn_identity, a full-body studio photograph of a beautiful young "
                f"East Asian woman, {HAIR}, elegant classical Chinese facial "
                f"features, {BODY}. {TAIL}"
            ),
            negative_prompt=NEG,
            image=make_init(folder),
            strength=STRENGTH,
            num_inference_steps=34,
            guidance_scale=5.0,
            generator=torch.Generator(device="cpu").manual_seed(7),
        ).images[0]
        image.save(target)
        verdict = verify_view(target, yaw)
        report.append((yaw, verdict))
        print(f"done {target.name} :: {verdict}", flush=True)

        if not gate_done:
            gate_done = True
            if "FAIL multiple figures" in verdict:
                print("GATE_FAILED 第一張出現多人，停止量產以免 24 張帶同一缺陷",
                      flush=True)
                return
            print("GATE_PASSED 第一張單人，繼續量產", flush=True)

    print("── 視角驗證彙總 ──", flush=True)
    for yaw, verdict in report:
        print(f"yaw{yaw:+05d}  {verdict}", flush=True)
    failures = [y for y, v in report if "FAIL" in v]
    print(f"FAILED VIEWS: {failures}" if failures else "ALL VIEWS PASSED", flush=True)
    print("V10_GEO_DONE", flush=True)


if __name__ == "__main__":
    main()
