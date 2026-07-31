from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
TEMP = ROOT / "tmp" / "expression-repair"
EXPRESSIONS = (
    "mock_scold",
    "mock_hit_front",
    "exasperated_front",
    "eureka_front",
)
FRAMES = ("closed", "mid", "open", "round")


def frame_path(expression: str, frame: str) -> Path:
    if frame == "closed":
        return ROOT / "assets" / "expressions" / f"{expression}.png"
    if expression == "mock_scold":
        return TEMP / f"{expression}_{frame}_composite.png"
    return TEMP / f"{expression}_{frame}.png"


def main() -> None:
    cell_width = 300
    portrait_height = 300
    detail_height = 180
    header_height = 38
    sheet = Image.new(
        "RGB",
        (
            cell_width * len(FRAMES),
            (portrait_height + detail_height + header_height)
            * len(EXPRESSIONS),
        ),
        (12, 29, 42),
    )
    painter = ImageDraw.Draw(sheet)
    for row, expression in enumerate(EXPRESSIONS):
        row_top = row * (portrait_height + detail_height + header_height)
        for column, frame in enumerate(FRAMES):
            source = Image.open(frame_path(expression, frame)).convert("RGBA")
            portrait = source.resize((300, 300), Image.Resampling.LANCZOS)
            x = column * cell_width
            sheet.paste(portrait, (x, row_top), portrait)
            detail = source.crop((470, 430, 750, 690))
            detail.thumbnail((280, detail_height), Image.Resampling.LANCZOS)
            detail_x = x + (cell_width - detail.width) // 2
            detail_y = row_top + portrait_height
            sheet.paste(detail.convert("RGB"), (detail_x, detail_y))
            painter.text(
                (x + 8, row_top + portrait_height + detail_height + 8),
                f"{expression} / {frame}",
                fill=(235, 245, 250),
            )
    output = TEMP / "gesture-speech-assets-audit.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)
    print(output)


if __name__ == "__main__":
    main()
