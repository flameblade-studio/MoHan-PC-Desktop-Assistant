"""二代素體 v9：全 24 視角純 t2i，改用側臉補完後的 identity LoRA v2。

與 v8 的三處差異：
1. LoRA 換成 v2（以擁有者認證的六張側臉權威圖加權重訓，補正 v8 側面「像別人」）。
2. 背面段（|yaw| >= 120）的視角語言改為正向描述「後腦勺與髮髻朝向鏡頭」。
   v8 用負向禁令封鎖回眸，24 張中 7 張視角驗證 FAIL——負向詞擋不住模型
   把「不要看鏡頭」讀成「看鏡頭」的注意力洩漏；正向描述才真正改變構圖。
3. 背面段額外描述後頸與肩胛的可見輪廓，讓模型有正面素材可畫，
   而非只被告知「不要畫臉」。措辭刻意避開「清楚可見」這類鏡頭指示語
   （P2 教訓：該措辭會被當成鏡位命令，把正面翻成背面）。
"""
import os
import sys
from pathlib import Path

import cv2
import torch

# 本檔原於 session 暫存目錄開發，匯入路徑與資料根目錄都寫死。入庫時改為：
#   匯入路徑取自本檔所在目錄；資料根目錄可用 MOHAN_VISION_ROOT 覆寫，
#   預設保留原機器路徑，讓既有紀錄可重現。
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lora_loader import load_aitoolkit_chroma_lora

ROOT = Path(os.environ.get(
    "MOHAN_VISION_ROOT",
    r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision",
))
OUT = ROOT / "work/second-gen-body/chroma-views-v9"
OUT.mkdir(parents=True, exist_ok=True)
# LoRA 權重不在資料根目錄下（在共用的 third-party 快取），另給環境變數。
LORA = Path(os.environ.get(
    "MOHAN_IDENTITY_LORA",
    r"D:\FlamebladeStudio\CodexProjects\.third-party-cache\ai-toolkit\output"
    r"\mohan-identity-chroma-v2\mohan-identity-chroma-v2.safetensors",
))
GGUF = ROOT / "tools/third_party/models/Chroma1-HD/Chroma1-HD-Q4_K_M.gguf"
YUNET = ROOT / "assets/vision-models/face_detection_yunet_2023mar.onnx"

# 2026-08-30 探針定案：LoRA v2 把「長髮＋高髻」學成身份的一部分（權威圖 caption
# 誤寫了 "with long black hair"）。權重 1.0 時任何措辭都壓不住，實測必須退到
# 0.85 才治得住，且識別度無可辨損失。措辭同時改為正向描述「耳與後頸是裸露皮膚」。
HAIR = (
    "her hair is scraped back into one very tight high bun at the crown with a "
    "single plain silver hairpin; the hair is short above the bun line so her "
    "ears and the whole nape of her neck are uncovered skin, and nothing hangs "
    "past her jaw"
)
LORA_WEIGHT = 0.85
BODY = (
    "slender graceful figure, slim waist, long slender legs, wearing a plain "
    "light-gray fitted two-piece bikini, bare arms, bare legs, bare feet"
)
TAIL = (
    "She stands upright in a neutral A-pose, arms relaxed at her sides, exactly two "
    "arms and exactly two legs, well-formed hands with five fingers each, well-formed "
    "bare feet with five toes each, even fair skin tone, the whole body from the top "
    "of her head to her toes is inside the frame, photorealistic, sharp focus, plain "
    "neutral light-gray studio background, soft even studio lighting. Her lips are "
    "gently closed together in a relaxed neutral expression, wearing no lipstick, "
    "her lips their own soft natural pink."
)
# 素體是換衣換表情的基底，嘴必須中性閉合、不上妝——否則每張都帶固定表情，
# 日後表情系統會與底圖打架。2026-08-30 擁有者比對唇形時連帶揪出此規格。


def prompt_for(view: str) -> str:
    return (
        "mhn_identity, a full-body studio photograph of a beautiful young East Asian "
        f"woman, {HAIR}, elegant classical Chinese facial features, {BODY}. {view} "
        f"{TAIL}"
    )


NEG_BASE = (
    "long hair falling over shoulders, hair down, loose long hair, side locks, "
    "ponytail, braid, bangs, fringe, hair below ears, hair covering the neck, "
    "hair on the shoulders, hair on the back, "
    "earrings, ear studs, necklace, jewelry, crystal hair ornament, flower hairpin, "
    "multiple hairpins, tiara, "
    "open mouth, parted lips, visible teeth, smiling, lipstick, red lips, "
    "glossy lips, heavy makeup, "
    "low quality, worst quality, ugly, lowres, anime, manga, watercolor, sketch, "
    "deformed, extra limbs, extra arms, extra legs, extra fingers, missing fingers, "
    "fused fingers, deformed hands, malformed hands, extra toes, missing toes, "
    "deformed feet, twisted knees, bad anatomy, mutated, disfigured, extra head, "
    "multiple people, blurry, cg, 3d render, watermark, text, cropped head, "
    "cropped feet, close-up, portrait crop, "
    "red blotchy skin, pink stains, mottled skin, reddish skin, pink color cast, "
    "purple background, color cast, chubby, plump, fat, overweight, thick thighs, "
    "wide hips, heavy build, skinny, emaciated, bony, tanned skin, dark skin, "
    "long neck, elongated neck, swan neck, bulging forehead, protruding forehead, "
    "stretched face, distorted face"
)
# 背面段仍保留少量負向詞當第二道保險，但主要靠正向措辭治本
NEG_BACK = "looking over shoulder, looking back, turning head, " + NEG_BASE

# 背面段共用的正向構圖語：給模型「該畫什麼」而非「不要畫什麼」
BACK_FACING = (
    "The back of her head faces the camera, so the camera frames her hair bun, the "
    "silver hairpin, the nape of her neck and her shoulder blades; her head stays "
    "aligned with her shoulders and her gaze continues straight ahead, away from the "
    "camera."
)

VIEWS: dict[int, str] = {
    0: "She faces the camera directly in a straight front view, her body squarely toward the camera.",
    15: "Her body is rotated 15 degrees to her right from a straight front view.",
    -15: "Her body is rotated 15 degrees to her left from a straight front view.",
    30: "Her body is rotated 30 degrees to her right from a straight front view.",
    -30: "Her body is rotated 30 degrees to her left from a straight front view.",
    45: "Her body is rotated 45 degrees to her right, a three-quarter view.",
    -45: "Her body is rotated 45 degrees to her left, a three-quarter view.",
    60: "Her body is rotated 60 degrees to her right, between three-quarter and profile.",
    -60: "Her body is rotated 60 degrees to her left, between three-quarter and profile.",
    75: "Her body is rotated 75 degrees to her right, very close to a side profile.",
    -75: "Her body is rotated 75 degrees to her left, very close to a side profile.",
    90: "Her body is rotated 90 degrees to her right, a pure side profile.",
    -90: "Her body is rotated 90 degrees to her left, a pure side profile.",
    105: "Her body is rotated 105 degrees to her right, just past a side profile.",
    -105: "Her body is rotated 105 degrees to her left, just past a side profile.",
    120: f"Her body is rotated 120 degrees to her right, a rear three-quarter stance. {BACK_FACING}",
    -120: f"Her body is rotated 120 degrees to her left, a rear three-quarter stance. {BACK_FACING}",
    135: f"Her body is rotated 135 degrees to her right, a strong rear three-quarter stance. {BACK_FACING}",
    -135: f"Her body is rotated 135 degrees to her left, a strong rear three-quarter stance. {BACK_FACING}",
    150: f"Her body is rotated 150 degrees to her right, nearly facing away. {BACK_FACING}",
    -150: f"Her body is rotated 150 degrees to her left, nearly facing away. {BACK_FACING}",
    165: f"Her body is rotated 165 degrees to her right, almost fully facing away. {BACK_FACING}",
    -165: f"Her body is rotated 165 degrees to her left, almost fully facing away. {BACK_FACING}",
    180: f"Her body is rotated a full 180 degrees, facing directly away from the camera. {BACK_FACING}",
}

NO_FACE_FROM = 135
FULL_FACE_TO = 30


def verify_view(path: Path, yaw: int) -> str:
    bgr = cv2.imread(str(path))
    if bgr is None:
        return "unreadable"
    height, width = bgr.shape[:2]
    detector = cv2.FaceDetectorYN.create(str(YUNET), "", (320, 320), 0.6, 0.3, 5000)
    detector.setInputSize((width, height))
    _, found = detector.detect(bgr)
    has_face = found is not None and len(found) > 0
    area = 0.0
    if has_face:
        box = max(found, key=lambda f: f[2] * f[3])
        area = float(box[2] * box[3]) / (width * height)
    if abs(yaw) >= NO_FACE_FROM and has_face:
        return f"FAIL back-view shows a face (area={area:.4f})"
    if abs(yaw) <= FULL_FACE_TO and area < 0.004:
        return f"FAIL frontal face too small (area={area:.4f})"
    return f"ok (face-area={area:.4f})"


def main() -> None:
    from diffusers import (
        ChromaPipeline, ChromaTransformer2DModel, GGUFQuantizationConfig,
    )

    if not Path(LORA).exists():
        raise SystemExit(f"LoRA 尚未產出：{LORA}")

    transformer = ChromaTransformer2DModel.from_single_file(
        str(GGUF),
        quantization_config=GGUFQuantizationConfig(compute_dtype=torch.bfloat16),
        torch_dtype=torch.bfloat16,
    )
    pipe = ChromaPipeline.from_pretrained(
        "lodestones/Chroma1-HD", transformer=transformer, torch_dtype=torch.bfloat16
    )
    load_aitoolkit_chroma_lora(pipe, LORA, weight=LORA_WEIGHT)
    pipe.enable_model_cpu_offload()
    pipe.set_progress_bar_config(disable=True)
    print(f"t2i ready (LoRA v2 @ {LORA_WEIGHT})", flush=True)

    report = []
    for yaw in sorted(VIEWS, key=abs):
        out = OUT / f"body2-yaw{yaw:+04d}.png"
        if out.exists():
            print("skip", out.name, flush=True)
            continue
        negative = NEG_BACK if abs(yaw) >= 120 else NEG_BASE
        image = pipe(
            prompt=prompt_for(VIEWS[yaw]),
            negative_prompt=negative,
            width=832,
            height=1248,
            num_inference_steps=32,
            guidance_scale=5.0,
            generator=torch.Generator(device="cpu").manual_seed(7),
        ).images[0]
        image.save(out)
        verdict = verify_view(out, yaw)
        report.append((yaw, verdict))
        print(f"done {out.name} :: {verdict}", flush=True)

    print("── 視角驗證彙總 ──", flush=True)
    for yaw, verdict in report:
        print(f"yaw{yaw:+05d}  {verdict}", flush=True)
    failures = [y for y, v in report if v.startswith("FAIL")]
    print(f"FAILED VIEWS: {failures}" if failures else "ALL VIEWS PASSED", flush=True)
    print("MASS_PRODUCE_V9_DONE", flush=True)


if __name__ == "__main__":
    main()
