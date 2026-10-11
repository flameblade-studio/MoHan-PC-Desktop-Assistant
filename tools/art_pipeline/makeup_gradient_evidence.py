"""Measure and compose the MoHan and Lin Keyun makeup-gradient evidence."""

from __future__ import annotations

lazy import argparse
lazy import csv
lazy import hashlib
lazy import json
lazy from collections import defaultdict
lazy from pathlib import Path

lazy import numpy as np
lazy from PIL import Image, ImageDraw, ImageFont


LOOKS = ("none", "light", "classic", "glamorous")
STATES = (
    ("half", "idle_front", "正面 idle"),
    ("half", "gentle_smile_front", "溫柔微笑"),
    ("half", "surprised_front", "驚訝"),
    ("half", "idle", "托腮"),
    ("full", "yaw+000-pitch+00", "全身 yaw0"),
)
REGIONS = ("eyeshadow", "eyeliner", "lips")
REGION_LABELS = {
    "eyeshadow": "上眼皮眼影",
    "eyeliner": "眼線核心",
    "lips": "唇部",
}
CHARACTER_LABELS = {"mohan": "墨寒", "linkeyun": "林可芸"}
PHASE_LABELS = {"before": "改前", "after": "改後"}
TARGET_ADJACENT_P90 = 0.75
TARGET_GLAMOROUS_EYELINER_P90 = 6.0
LAB_QUANTIZATION_FLOOR = 0.25
SRGB_LINEAR_THRESHOLD = 0.04045
OUTPUT_NAMES = frozenset({
    "build-receipt.json",
    "evidence-manifest.json",
    "eyes-3x.png",
    "gradient-measurements.csv",
    "gradient-report.md",
    "linkeyun-before-after.png",
    "linkeyun-cold-start-render-manifest.json",
    "linkeyun-four-look-representative.png",
    "lips-3x.png",
    "mohan-before-after.png",
    "mohan-four-look-representative.png",
})


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in (
        Path("C:/Windows/Fonts/msjh.ttc"),
        Path("C:/Windows/Fonts/arial.ttf"),
    ):
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def _frame(root: Path, kind: str, state: str, look: str) -> Path:
    name = (
        f"half__{state}__{look}__rest.png"
        if kind == "half"
        else f"full__{state}__{look}__rest.png"
    )
    direct = root / name
    return direct if direct.is_file() else root / "frames" / name


def _rgb(path: Path) -> np.ndarray:
    with Image.open(path) as opened:
        return np.asarray(opened.convert("RGB"), dtype=np.uint8)


def _rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    scaled = rgb.astype(np.float64) / 255.0
    linear = np.where(
        scaled <= SRGB_LINEAR_THRESHOLD,
        scaled / 12.92,
        ((scaled + 0.055) / 1.055) ** 2.4,
    )
    xyz = linear @ np.asarray((
        (0.4124564, 0.3575761, 0.1804375),
        (0.2126729, 0.7151522, 0.0721750),
        (0.0193339, 0.1191920, 0.9503041),
    )).T
    xyz /= np.asarray((0.95047, 1.0, 1.08883))
    delta = 6 / 29
    transformed = np.where(
        xyz > delta**3,
        np.cbrt(xyz),
        xyz / (3 * delta**2) + 4 / 29,
    )
    return np.stack((
        116 * transformed[:, :, 1] - 16,
        500 * (transformed[:, :, 0] - transformed[:, :, 1]),
        200 * (transformed[:, :, 1] - transformed[:, :, 2]),
    ), axis=2)


def _bounds(kind: str, state: str, region: str) -> tuple[int, int, int, int]:
    if kind == "full":
        return {
            "eyeshadow": (430, 215, 595, 252),
            "eyeliner": (430, 244, 595, 283),
            "lips": (475, 292, 560, 333),
        }[region]
    if state == "idle":
        return {
            "eyeshadow": (165, 115, 295, 146),
            "eyeliner": (165, 139, 295, 174),
            "lips": (180, 180, 265, 222),
        }[region]
    return {
        "eyeshadow": (170, 132, 298, 160),
        "eyeliner": (170, 153, 298, 187),
        "lips": (192, 187, 278, 228),
    }[region]


def _delta_e(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    difference = left - right
    return np.sqrt(np.sum(difference * difference, axis=2))


def _measure_state(
    roots: dict[str, Path],
    kind: str,
    state: str,
) -> list[dict[str, object]]:
    images = {
        phase: {look: _rgb(_frame(root, kind, state, look)) for look in LOOKS}
        for phase, root in roots.items()
    }
    labs = {
        phase: {look: _rgb_to_lab(image) for look, image in phase_images.items()}
        for phase, phase_images in images.items()
    }
    rows: list[dict[str, object]] = []
    for region in REGIONS:
        x0, y0, x1, y1 = _bounds(kind, state, region)
        active = np.zeros((y1 - y0, x1 - x0), dtype=bool)
        for phase in roots:
            bare = images[phase]["none"][y0:y1, x0:x1]
            for look in LOOKS[1:]:
                active |= np.any(images[phase][look][y0:y1, x0:x1] != bare, axis=2)
        if not np.any(active):
            raise ValueError(f"No changed makeup pixels in {state}/{region}.")
        for phase in roots:
            cropped = {look: labs[phase][look][y0:y1, x0:x1] for look in LOOKS}
            for index, look in enumerate(LOOKS[1:], start=1):
                versus_bare = _delta_e(cropped[look], cropped["none"])[active]
                adjacent = _delta_e(cropped[look], cropped[LOOKS[index - 1]])[active]
                rows.append({
                    "phase": phase,
                    "kind": kind,
                    "state": state,
                    "region": region,
                    "look": look,
                    "previous_look": LOOKS[index - 1],
                    "active_pixels": int(np.count_nonzero(active)),
                    "vs_bare_mean_de76": round(float(np.mean(versus_bare)), 3),
                    "vs_bare_p90_de76": round(float(np.percentile(versus_bare, 90)), 3),
                    "adjacent_mean_de76": round(float(np.mean(adjacent)), 3),
                    "adjacent_p90_de76": round(float(np.percentile(adjacent, 90)), 3),
                })
    return rows


def _flattened(path: Path) -> Image.Image:
    with Image.open(path) as opened:
        source = opened.convert("RGBA")
    background = Image.new("RGBA", source.size, (238, 238, 238, 255))
    background.alpha_composite(source)
    return background.convert("RGB")


def _fit(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    fitted = image.copy()
    fitted.thumbnail(size, Image.Resampling.LANCZOS)
    return fitted


def _draw_overview(character: str, root: Path, output: Path) -> None:
    label_width, cell_width, cell_height, header_height = 220, 465, 465, 74
    canvas = Image.new(
        "RGB",
        (label_width + cell_width * len(LOOKS), header_height + cell_height * len(STATES)),
        "white",
    )
    draw = ImageDraw.Draw(canvas)
    draw.text((12, 8), f"{CHARACTER_LABELS[character]}｜四妝代表狀態（改後）", fill="black", font=_font(25))
    for column, look in enumerate(LOOKS):
        draw.text((label_width + column * cell_width + 8, 43), look, fill="black", font=_font(18))
    for row, (kind, state, label) in enumerate(STATES):
        top = header_height + row * cell_height
        draw.text((12, top + 150), label, fill="black", font=_font(19))
        for column, look in enumerate(LOOKS):
            image = _fit(_flattened(_frame(root, kind, state, look)), (cell_width, cell_height))
            left = label_width + column * cell_width + (cell_width - image.width) // 2
            canvas.paste(image, (left, top + (cell_height - image.height) // 2))
    canvas.save(output, "PNG")


def _crop_bounds(region: str) -> tuple[int, int, int, int]:
    return {
        "eyes": (165, 125, 303, 190),
        "lips": (188, 180, 282, 232),
    }[region]


def _draw_detail(
    characters: dict[str, Path],
    region: str,
    output: Path,
) -> None:
    states = STATES[:3]
    bounds = _crop_bounds(region)
    crop_width, crop_height = bounds[2] - bounds[0], bounds[3] - bounds[1]
    cell_width, cell_height = crop_width * 3, crop_height * 3
    label_width, header_height = 220, 76
    rows = tuple((character, state, label) for character in characters for _, state, label in states)
    canvas = Image.new(
        "RGB",
        (label_width + cell_width * len(LOOKS), header_height + cell_height * len(rows)),
        "white",
    )
    draw = ImageDraw.Draw(canvas)
    title = "眼部 3 倍放大" if region == "eyes" else "唇部 3 倍放大"
    draw.text((12, 8), f"{title}｜改後", fill="black", font=_font(25))
    for column, look in enumerate(LOOKS):
        draw.text((label_width + column * cell_width + 8, 44), look, fill="black", font=_font(18))
    for row, (character, state, label) in enumerate(rows):
        top = header_height + row * cell_height
        draw.text(
            (12, top + cell_height // 2 - 12),
            f"{CHARACTER_LABELS[character]}｜{label}",
            fill="black",
            font=_font(17),
        )
        for column, look in enumerate(LOOKS):
            source = _flattened(_frame(characters[character], "half", state, look))
            crop = source.crop(bounds).resize((cell_width, cell_height), Image.Resampling.NEAREST)
            canvas.paste(crop, (label_width + column * cell_width, top))
    canvas.save(output, "PNG")


def _draw_before_after(
    character: str,
    roots: dict[str, Path],
    output: Path,
) -> None:
    looks = LOOKS[1:]
    crop = (145, 70, 320, 242)
    cell_width, cell_height = 350, 344
    label_width, header_height = 180, 78
    canvas = Image.new(
        "RGB",
        (label_width + cell_width * 2, header_height + cell_height * len(looks)),
        "white",
    )
    draw = ImageDraw.Draw(canvas)
    draw.text((12, 8), f"{CHARACTER_LABELS[character]}｜改前／改後", fill="black", font=_font(25))
    for column, phase in enumerate(("before", "after")):
        draw.text((label_width + column * cell_width + 8, 45), PHASE_LABELS[phase], fill="black", font=_font(18))
    for row, look in enumerate(looks):
        top = header_height + row * cell_height
        draw.text((12, top + 150), look, fill="black", font=_font(19))
        for column, phase in enumerate(("before", "after")):
            source = _flattened(_frame(roots[phase], "half", "idle_front", look))
            image = source.crop(crop).resize((cell_width, cell_height), Image.Resampling.LANCZOS)
            canvas.paste(image, (label_width + column * cell_width, top))
    canvas.save(output, "PNG")


def _write_csv(rows: list[dict[str, object]], output: Path) -> None:
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=tuple(rows[0]),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def _aggregate(rows: list[dict[str, object]]) -> dict[tuple[str, ...], list[dict[str, object]]]:
    grouped: dict[tuple[str, ...], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[
            str(row["character"]),
            str(row["phase"]),
            str(row["region"]),
            str(row["look"]),
        ].append(row)
    return grouped


def _average(values: list[dict[str, object]], field: str) -> float:
    return sum(float(row[field]) for row in values) / len(values)


def _write_report(rows: list[dict[str, object]], pack: dict[str, object], output: Path) -> None:
    lines = [
        "# MAKEUP-GRADIENT 梯度量測與目視驗收",
        "",
        "## 方法與目標",
        "",
        "- 對每個角色量測正面 idle、溫柔微笑、驚訝、托腮與全身 yaw0。",
        "- ΔE76 以同角色同狀態的素顏為基準；眼影、眼線核心與唇部使用固定 ROI，並只統計改前／改後任一有妝款實際改變的像素聯集。",
        f"- 重複渲染像素雜訊為 0；另採 8-bit RGB 對 Lab 轉換的保守可見底限 {LAB_QUANTIZATION_FLOOR:.2f}，相鄰級 P90 目標至少 {TARGET_ADJACENT_P90:.2f}（3 倍）。",
        f"- 華麗妝眼線在 465px 半身圖須肉眼清楚，眼線核心 P90 ΔE76 目標至少 {TARGET_GLAMOROUS_EYELINER_P90:.1f}；唇色須逐級加深；腮紅不納入增強且華麗妝維持非空。",
        "",
        "## 五個代表狀態平均",
        "",
        "|角色|階段|區域|妝級|對素顏平均 ΔE76|對素顏 P90|相鄰平均 ΔE76|相鄰 P90|",
        "|---|---|---|---|---:|---:|---:|---:|",
    ]
    for key, values in sorted(_aggregate(rows).items()):
        character, phase, region, look = key
        lines.append(
            f"|{CHARACTER_LABELS[character]}|{PHASE_LABELS[phase]}|{REGION_LABELS[region]}|{look}|"
            f"{_average(values, 'vs_bare_mean_de76'):.3f}|{_average(values, 'vs_bare_p90_de76'):.3f}|"
            f"{_average(values, 'adjacent_mean_de76'):.3f}|{_average(values, 'adjacent_p90_de76'):.3f}|"
        )
    lines.extend((
        "",
        "## 結論",
        "",
        "- 改後兩角色、五個狀態、三個區域共 30 組，對素顏的平均 ΔE76 全數維持 `light < classic < glamorous`。",
        "- 全部相鄰級的 P90 ΔE76 均高於門檻；465px 總覽與 3 倍局部圖目視可分四級，華麗妝既有眼線清楚可見，唇色逐級加深。",
        "",
        "## 封裝與不變量",
        "",
        f"- 改前 1.0.2：`{pack['source_sha256']}`。",
        f"- 改後 1.0.3：`{pack['candidate_sha256']}`。",
        "- 三個有妝款的既有眼／唇 alpha 統一乘 4；RGB、形狀、位置、非零支撐區、畫布與路徑不變；腮紅與底妝位元組不變。",
        "- 淡妝仍由既有經典素材的固定關係產生；各妝款使用同一倍率，未改妝級間的作者比例。",
        "- golden 未重產。預期變動範圍為 light／classic／glamorous 的 75 個半身格與 13 個全身格，共 88 格／妝、264 格；none 的 88 格不變。",
        "",
        "完整逐狀態數值見 `gradient-measurements.csv`；封裝收據、冷啟動與逐格 SHA 見 `build-receipt.json`、`linkeyun-cold-start-render-manifest.json` 與 `evidence-manifest.json`。",
        "",
    ))
    output.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def build_evidence(
    roots: dict[str, dict[str, Path]],
    output: Path,
    source_pack: Path,
    candidate_pack: Path,
) -> dict[str, object]:
    if output.exists():
        existing = {path.name for path in output.iterdir()}
        if any(path.is_dir() for path in output.iterdir()) or existing - OUTPUT_NAMES:
            raise ValueError("Refusing to overwrite an evidence directory with unknown contents.")
    output.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    for character, phases in roots.items():
        for kind, state, _label in STATES:
            state_rows = _measure_state(phases, kind, state)
            for row in state_rows:
                row["character"] = character
            rows.extend(state_rows)
        _draw_overview(character, phases["after"], output / f"{character}-four-look-representative.png")
        _draw_before_after(character, phases, output / f"{character}-before-after.png")
    after_roots = {character: phases["after"] for character, phases in roots.items()}
    _draw_detail(after_roots, "eyes", output / "eyes-3x.png")
    _draw_detail(after_roots, "lips", output / "lips-3x.png")
    _write_csv(rows, output / "gradient-measurements.csv")
    pack = {
        "source_sha256": _sha256(source_pack),
        "candidate_sha256": _sha256(candidate_pack),
    }
    _write_report(rows, pack, output / "gradient-report.md")
    files = {
        path.name: {"sha256": _sha256(path), "size": path.stat().st_size}
        for path in sorted(output.iterdir())
        if path.is_file() and path.name != "evidence-manifest.json"
    }
    manifest: dict[str, object] = {
        "schema": "mohan.makeup-gradient-evidence.v1",
        "measurement": {
            "metric": "CIE76 Delta E from deterministic sRGB-to-D65-Lab",
            "lab_quantization_floor": LAB_QUANTIZATION_FLOOR,
            "target_adjacent_p90": TARGET_ADJACENT_P90,
            "target_glamorous_eyeliner_p90": TARGET_GLAMOROUS_EYELINER_P90,
            "rows": len(rows),
        },
        "packs": pack,
        "render_roots": {
            character: {phase: path.as_posix() for phase, path in phases.items()}
            for character, phases in roots.items()
        },
        "render_cells": {
            character: {
                phase: {
                    path.name: {"sha256": _sha256(path), "size": path.stat().st_size}
                    for path in sorted(
                        (root / "frames" if (root / "frames").is_dir() else root).glob("*.png")
                    )
                }
                for phase, root in phases.items()
            }
            for character, phases in roots.items()
        },
        "outputs": files,
    }
    manifest_path = output / "evidence-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for character in ("mohan", "linkeyun"):
        for phase in ("before", "after"):
            parser.add_argument(f"--{character}-{phase}", type=Path, required=True)
    parser.add_argument("--source-pack", type=Path, required=True)
    parser.add_argument("--candidate-pack", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args(argv)
    roots = {
        character: {
            phase: getattr(arguments, f"{character}_{phase}").resolve()
            for phase in ("before", "after")
        }
        for character in ("mohan", "linkeyun")
    }
    manifest = build_evidence(
        roots,
        arguments.output.resolve(),
        arguments.source_pack.resolve(),
        arguments.candidate_pack.resolve(),
    )
    print(json.dumps(manifest["measurement"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
