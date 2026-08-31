"""把 −yaw 系列水平鏡像成 +yaw，補齊右向視角。

診斷（2026-08-30）：提示詞的 "rotated N degrees to her right / to her left"
是**以角色為基準**的方位，擴散模型必須先建立角色身體座標系再反推鏡頭所見，
這種間接推理它做不好——實測四組 ±yaw 對照全部面向同一邊，左右指令完全失效。

鏡像優於重新生成：重生的每張臉與身體都會有細微差異，鏡像則保證左右
完全一致。素體是換衣換髮的基底，髮簪等不對稱細節左右互換可忽略。

原有的 +yaw 檔案（與 −yaw 同向、且彼此細節不一致）改名保留為
_nonmirrored-yaw*.png，不刪除。
"""
import os
import argparse
from pathlib import Path

from PIL import Image

SRC = Path(os.environ.get("MOHAN_VISION_ROOT",
    r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision")) / "work/second-gen-body/chroma-views-v9"


def mirror(yaws: list[int]) -> None:
    made = missing = 0
    for yaw in yaws:
        source = SRC / f"body2-yaw{-yaw:+04d}.png"
        target = SRC / f"body2-yaw{yaw:+04d}.png"
        if not source.exists():
            print(f"  來源缺漏 yaw{-yaw:+d}，跳過")
            missing += 1
            continue
        if target.exists():
            keep = SRC / f"_nonmirrored-yaw{yaw:+04d}.png"
            if not keep.exists():
                target.replace(keep)
            else:
                target.unlink()
        Image.open(source).convert("RGB").transpose(
            Image.FLIP_LEFT_RIGHT
        ).save(target)
        made += 1
        print(f"  yaw{yaw:+d}  <-  鏡像自 yaw{-yaw:+d}")
    print(f"MIRROR_DONE made={made} missing={missing}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--yaws", default="15,30,45,60,75,90,105,120",
        help="要鏡像產生的正 yaw，以逗號分隔",
    )
    arguments = parser.parse_args()
    yaws = [int(v) for v in arguments.yaws.split(",") if v.strip()]
    print(f"鏡像 {len(yaws)} 個視角：{yaws}")
    mirror(yaws)


if __name__ == "__main__":
    main()
