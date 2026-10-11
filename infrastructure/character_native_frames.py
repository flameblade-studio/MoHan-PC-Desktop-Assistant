"""Freeze character-owned whole full-body frames before the first render."""
from __future__ import annotations

lazy import io
lazy from pathlib import Path
lazy from PIL import Image
lazy from domain.face_rig import EyeState
lazy from infrastructure.layered_full_body_assets import VIEW_IDS

FULLBODY_CANVAS = (1024, 1536)


def load_native_fullbody_frames(
    root: Path, blink_views: frozenset[str],
) -> frozendict[str, frozendict[EyeState, bytes]]:
    """Require all views and each visible blink, with exact missing-frame errors.

    Back and side views without a visible eye use their own rest frame for every
    eye state. Every decoded source remains below the declared character root.
    """
    root = Path(root).resolve()
    result = {}
    for view_id in VIEW_IDS:
        states = (EyeState.REST, EyeState.HALF, EyeState.CLOSED) if view_id in blink_views else (EyeState.REST,)
        frames = {}
        for state in states:
            suffix = "" if state is EyeState.REST else f"_blink_{state.value}"
            path = root / f"{view_id}{suffix}.png"
            if not path.resolve().is_relative_to(root):
                raise ValueError(f"Native full-body frame escapes its root: {path}")
            try:
                data = path.read_bytes()
            except OSError as error:
                raise FileNotFoundError(f"Missing native full-body frame {view_id}/{state.value}: {path}") from error
            with Image.open(io.BytesIO(data)) as image:
                if image.format != "PNG" or image.mode != "RGBA" or image.size != FULLBODY_CANVAS:
                    raise ValueError(f"Native full-body frame requires 1024x1536 RGBA PNG: {path}")
                image.load()
            frames[state] = data
        result[view_id] = frozendict(frames)
    return frozendict(result)
