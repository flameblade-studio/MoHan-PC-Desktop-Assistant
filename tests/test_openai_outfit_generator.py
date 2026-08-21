from __future__ import annotations

lazy import sys
lazy from datetime import UTC, datetime
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

lazy import cv2
lazy import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lazy from application.self_generating_wardrobe import OutfitCreationRequest
lazy from domain.character_framing import FRAMING_RECTS, FramingMode
lazy from domain.outfit_pack import REQUIRED_SILHOUETTES
lazy from integrations.openai_outfit_generator import (
    FULL_SIZE,
    GeneratedOutfitImageAuditor,
    OpenAIOutfitDraftGenerator,
)


class FakeTransport:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[int, int]]] = []

    def edit(
        self,
        _reference_png: bytes,
        prompt: str,
        size: tuple[int, int],
    ) -> bytes:
        self.calls.append((prompt, size))
        width, height = size
        image = np.zeros((height, width, 4), dtype=np.uint8)
        image[height // 2:height // 2 + 40, width // 2 - 60:width // 2 + 60] = (
            120, 80, 40, 255
        )
        ok, encoded = cv2.imencode(".png", image)
        assert ok
        return bytes(encoded)


def run() -> None:
    transport = FakeTransport()
    generator = OpenAIOutfitDraftGenerator(transport, ROOT)
    request = OutfitCreationRequest(
        "provider-test",
        "zh-TW",
        "indoor",
        25.0,
        "calm",
        "everyday",
        "original blue and silver modern hanfu",
        datetime(2026, 8, 22, tzinfo=UTC),
    )
    draft = generator.create(request, (), REQUIRED_SILHOUETTES)
    assert len(transport.calls) == len(REQUIRED_SILHOUETTES)
    assert set(draft.manifest["looks"][0]["variants"][0]["poses"]) == set(
        REQUIRED_SILHOUETTES
    )
    assert draft.generation_record["model"] == "gpt-image-2"
    assert any(size == FULL_SIZE for _prompt, size in transport.calls)
    assert all("OUTPUT ONLY" in prompt for prompt, _size in transport.calls)

    # One coherent outfit must cover all three runtime compositions. HALF has
    # seven authored portrait/gesture silhouettes; FULL_BODY and THREE_QUARTER
    # deliberately share the 24 registered PoseAtlas overlays, with the latter
    # represented by a non-empty crop of those same full-body canvases.
    half_views = tuple(
        view for view in REQUIRED_SILHOUETTES if not view.startswith("yaw")
    )
    full_views = tuple(
        view for view in REQUIRED_SILHOUETTES if view.startswith("yaw")
    )
    assert len(half_views) == 7
    assert len(full_views) == 24
    three_quarter = FRAMING_RECTS[FramingMode.THREE_QUARTER]
    assert 0.0 <= three_quarter.left < three_quarter.right <= 1.0
    assert 0.0 <= three_quarter.top < three_quarter.bottom <= 1.0
    assert set(full_views).issubset(
        draft.manifest["looks"][0]["variants"][0]["poses"]
    )

    # Exercise the production auditor against the exact quarantine layout.
    with TemporaryDirectory() as temporary:
        job = Path(temporary)
        for path, data in draft.assets.items():
            destination = job / "source" / Path(*path.split("/"))
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
        assert GeneratedOutfitImageAuditor().audit(job, draft.manifest) == ()

    rainy_transport = FakeTransport()
    rainy_generator = OpenAIOutfitDraftGenerator(rainy_transport, ROOT)
    rainy_request = OutfitCreationRequest(
        "rain-provider-test",
        "zh-TW",
        "rain",
        20.0,
        "calm",
        "everyday",
        "original blue and silver rain-ready hanfu",
        datetime(2026, 8, 22, tzinfo=UTC),
        requested_categories=frozenset({"garment", "handheld"}),
        accessory_direction="original ink-wash oil-paper umbrella",
    )
    rainy_draft = rainy_generator.create(rainy_request, (), REQUIRED_SILHOUETTES)
    assert len(rainy_transport.calls) == 2 * len(REQUIRED_SILHOUETTES)
    accessory = rainy_draft.manifest["accessories"][0]
    assert accessory["accessory_kind"] == "handheld"
    assert set(accessory["variants"][0]["poses"]) == set(REQUIRED_SILHOUETTES)
    assert rainy_draft.manifest["ensembles"][0]["selections"]["handheld"]
    print("OPENAI_OUTFIT_GENERATOR_OK")


if __name__ == "__main__":
    run()
