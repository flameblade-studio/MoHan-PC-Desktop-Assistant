"""Small in-memory images cover body-pack composition contracts."""
from __future__ import annotations

lazy import os
lazy import hashlib
lazy import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

lazy import pytest
lazy from PySide6.QtCore import QRect, Qt
lazy from PySide6.QtGui import QColor, QImage, QPainter, QPixmap, QRegion
lazy from PySide6.QtWidgets import QApplication

lazy from domain.character_layer_plan import (
    CharacterLayerAsset,
    CharacterLayerMask,
    CharacterLayerPlan,
    CharacterLayerPlanError,
    parse_character_layer_views,
)
lazy from infrastructure.body_pack_compositor import (
    MAX_ALPHA_REGION_CACHE_BYTES,
    _ALPHA_REGIONS,
    body_pack_alpha_region,
    compose_body_pack_frame,
)

HALF_ALPHA = 128
TINY_ALPHA_CACHE_BUDGET = 256
EXPECTED_ALPHA_CACHE_ENTRIES = 2


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _solid(width: int, color: QColor) -> QPixmap:
    image = QImage(width, 1, QImage.Format_RGBA8888)
    image.fill(color)
    return QPixmap.fromImage(image)


def _sparse(width: int, pixels: dict[int, QColor]) -> QPixmap:
    image = QImage(width, 1, QImage.Format_RGBA8888)
    image.fill(QColor(0, 0, 0, 0))
    for x, color in pixels.items():
        image.setPixelColor(x, 0, color)
    return QPixmap.fromImage(image)


def _premultiplied_pixel(image: QImage) -> tuple[int, int, int, int]:
    converted = image.convertToFormat(QImage.Format_RGBA8888_Premultiplied)
    pixels = bytes(converted.constBits())[:4]
    return pixels[0], pixels[1], pixels[2], pixels[3]


def _asset(kind: str, name: str) -> CharacterLayerAsset:
    return CharacterLayerAsset(kind, name, "a" * 64, (0, 0))


def test_layers_follow_declared_order_including_hair_back_after_garment(
    qt_app: QApplication,
) -> None:
    base = _solid(3, QColor("green"))
    garment = _solid(3, QColor("red"))
    rear_hair = _solid(3, QColor("blue"))
    assets = {
        "garment.png": garment,
        "hair-back.png": rear_hair,
    }
    plan = CharacterLayerPlan(
        ("base", "garment", "hair-back"),
        (_asset("garment", "garment.png"), _asset("hair-back", "hair-back.png")),
    )

    result = compose_body_pack_frame(base, plan, lambda record: assets[record.path])

    assert result.toImage().pixelColor(1, 0) == QColor("blue")
    assert qt_app is not None


def test_missing_order_uses_legacy_hair_back_underpaint(qt_app: QApplication) -> None:
    base = _sparse(3, {0: QColor("green")})
    rear_hair = _solid(3, QColor("red"))
    plan = parse_character_layer_views(
        {
            "yaw+000-pitch+00": {
                "layers": [
                    {
                        "kind": "hair-back",
                        "path": "hair-back.png",
                        "sha256": "e" * 64,
                        "anchor": [0, 0],
                    }
                ]
            }
        }
    )["yaw+000-pitch+00"]

    result = compose_body_pack_frame(base, plan, lambda _record: rear_hair).toImage()

    assert result.pixelColor(0, 0) == QColor("green")
    assert result.pixelColor(1, 0) == QColor("red")
    assert qt_app is not None


def test_base_hide_nonzero_alpha_hard_clears_independent_of_face_core(
    qt_app: QApplication,
) -> None:
    base = _solid(4, QColor("green"))
    mask = _sparse(
        4,
        {
            0: QColor(255, 255, 255, 1),
            1: QColor(255, 255, 255, 127),
            3: QColor(255, 255, 255, 1),
        },
    )
    correction = _sparse(4, {0: QColor("blue"), 2: QColor("red")})
    plan = CharacterLayerPlan(
        ("base", "body-fix"),
        (_asset("body-fix", "body-fix.png"),),
        CharacterLayerMask("base-hide.png", "b" * 64, (0, 0)),
    )
    assets = {"base-hide.png": mask, "body-fix.png": correction}

    result = compose_body_pack_frame(
        base,
        plan,
        lambda record: assets[record.path],
        face_core=_sparse(4, {0: QColor(255, 255, 255, 255)}),
    ).toImage()

    assert result.pixelColor(0, 0) == QColor("green")
    assert result.pixelColor(1, 0).alpha() == 0
    assert result.pixelColor(2, 0) == QColor("red")
    assert result.pixelColor(3, 0).alpha() == 0
    assert qt_app is not None


def test_alpha_region_includes_alpha_one_and_accepts_empty_masks(
    qt_app: QApplication,
) -> None:
    mask = _sparse(3, {1: QColor(255, 255, 255, 1), 2: QColor(255, 255, 255, 127)})
    region = body_pack_alpha_region(mask)

    assert region.contains(QRect(1, 0, 1, 1))
    assert region.contains(QRect(2, 0, 1, 1))
    assert not region.contains(QRect(0, 0, 1, 1))
    assert body_pack_alpha_region(_sparse(3, {})).isEmpty()
    assert qt_app is not None


def test_makeup_is_source_atop_in_face_core_and_preserves_base_alpha(
    qt_app: QApplication,
) -> None:
    base = _sparse(
        4,
        {
            0: QColor(0, 255, 0, 128),
            1: QColor("green"),
            2: QColor("green"),
        },
    )
    makeup = _sparse(
        4,
        {
            0: QColor(255, 0, 0, HALF_ALPHA),
            1: QColor(255, 0, 0, HALF_ALPHA),
            2: QColor(255, 0, 0, HALF_ALPHA),
            3: QColor(255, 0, 0, HALF_ALPHA),
        },
    )
    garment = _sparse(4, {0: QColor("magenta"), 1: QColor("yellow")})
    plan = CharacterLayerPlan(
        ("base", "makeup", "garment"),
        (_asset("makeup", "makeup.png"), _asset("garment", "garment.png")),
    )
    assets = {"makeup.png": makeup, "garment.png": garment}
    face_core = _sparse(
        4, {0: QColor(255, 255, 255, 255), 3: QColor(255, 255, 255, 255)}
    )

    result = compose_body_pack_frame(
        base, plan, lambda record: assets[record.path], face_core=face_core,
    ).toImage()

    protected_pixel = result.pixelColor(0, 0)
    assert protected_pixel.red() > 0 and protected_pixel.green() > 0
    assert protected_pixel != QColor("magenta")
    assert protected_pixel.alpha() == HALF_ALPHA
    assert result.pixelColor(1, 0) == QColor("yellow")
    assert result.pixelColor(2, 0) == QColor("green")
    assert result.pixelColor(3, 0).alpha() == 0
    assert qt_app is not None


def test_alpha_region_cache_reuses_digest(monkeypatch, qt_app: QApplication) -> None:
    first_mask = _sparse(3, {0: QColor(255, 255, 255, 255)})
    other_mask = _sparse(3, {2: QColor(255, 255, 255, 255)})
    digest = hashlib.sha256(b"body-pack-alpha-cache-reuse").hexdigest()

    first = body_pack_alpha_region(first_mask, digest)
    second = body_pack_alpha_region(other_mask, digest)

    assert second == first
    assert f"sha256:{digest}" in _ALPHA_REGIONS
    assert MAX_ALPHA_REGION_CACHE_BYTES > 0
    assert qt_app is not None


def test_alpha_region_cache_evicts_lru_entries_at_its_byte_budget(
    monkeypatch, qt_app: QApplication,
) -> None:
    import infrastructure.body_pack_compositor as compositor

    monkeypatch.setattr(compositor, "MAX_ALPHA_REGION_CACHE_BYTES", TINY_ALPHA_CACHE_BUDGET)
    monkeypatch.setattr(compositor, "_ALPHA_REGIONS", compositor.OrderedDict())
    monkeypatch.setattr(compositor, "_alpha_region_cache_bytes", 0)
    digests = [hashlib.sha256(f"alpha-cache-{index}".encode()).hexdigest() for index in range(3)]
    masks = [_sparse(2, {index % 2: QColor(255, 255, 255, 255)}) for index in range(3)]

    for mask, digest in zip(masks[:2], digests[:2], strict=True):
        body_pack_alpha_region(mask, digest)
    body_pack_alpha_region(masks[0], digests[0])
    body_pack_alpha_region(masks[2], digests[2])

    assert list(compositor._ALPHA_REGIONS) == [f"sha256:{digests[0]}", f"sha256:{digests[2]}"]
    assert compositor._alpha_region_cache_bytes == TINY_ALPHA_CACHE_BUDGET
    assert len(compositor._ALPHA_REGIONS) == EXPECTED_ALPHA_CACHE_ENTRIES
    assert qt_app is not None


def test_full_resolution_alpha_conversion_beats_previous_python_scan(
    qt_app: QApplication,
) -> None:
    image = QImage(1024, 1536, QImage.Format_RGBA8888)
    image.fill(QColor(255, 255, 255, 1))
    mask = QPixmap.fromImage(image)

    started = time.perf_counter()
    region = body_pack_alpha_region(mask, "e" * 64)
    optimized_seconds = time.perf_counter() - started

    started = time.perf_counter()
    scalar_image = mask.toImage().convertToFormat(QImage.Format_ARGB32)
    reference = QRegion()
    for y in range(scalar_image.height()):
        x = 0
        while x < scalar_image.width():
            while x < scalar_image.width() and scalar_image.pixel(x, y) >> 24 == 0:
                x += 1
            start = x
            while x < scalar_image.width() and scalar_image.pixel(x, y) >> 24 != 0:
                x += 1
            if start < x:
                reference = reference.united(QRegion(QRect(start, y, x - start, 1)))
    reference_seconds = time.perf_counter() - started

    assert region == reference
    assert optimized_seconds < reference_seconds
    assert qt_app is not None


def test_missing_plan_returns_base_copy_without_loading_assets(qt_app: QApplication) -> None:
    base = _solid(2, QColor("green"))

    result = compose_body_pack_frame(
        base,
        None,
        lambda _record: pytest.fail("A missing plan must not load character assets."),
    )

    assert result.toImage() == base.toImage()
    result.fill(QColor("red"))
    assert base.toImage().pixelColor(0, 0) == QColor("green")
    assert qt_app is not None


def test_parser_returns_immutable_view_plans_and_accepts_makeup_order() -> None:
    views = parse_character_layer_views(
        {
            "yaw+000-pitch+00": {
                "order": ["base", "body-fix", "makeup"],
                "layers": [
                    {
                        "kind": "makeup",
                        "path": "makeup.png",
                        "sha256": "c" * 64,
                        "anchor": [0, 0],
                    }
                ],
            }
        }
    )

    assert views["yaw+000-pitch+00"].layers[0].kind == "makeup"
    with pytest.raises(TypeError):
        views["yaw+000-pitch+00"] = views["yaw+000-pitch+00"]


def test_parser_rejects_makeup_after_garment() -> None:
    with pytest.raises(CharacterLayerPlanError, match="Makeup must follow the base"):
        parse_character_layer_views(
            {
                "yaw+000-pitch+00": {
                    "order": ["base", "garment", "makeup"],
                    "layers": [],
                }
            }
        )


def test_parser_rejects_nonzero_layer_anchor() -> None:
    with pytest.raises(CharacterLayerPlanError, match="anchor"):
        parse_character_layer_views(
            {
                "yaw+000-pitch+00": {
                    "order": ["base", "garment"],
                    "layers": [
                        {
                            "kind": "garment",
                            "path": "garment.png",
                            "sha256": "d" * 64,
                            "anchor": [1, 0],
                        }
                    ],
                }
            }
        )


@pytest.mark.parametrize("kind", ["body-fix", "garment", "hair-front", "ornament"])
def test_face_feather_weights_character_layers(qt_app: QApplication, kind: str) -> None:
    base = _solid(3, QColor(0, 0, 255))
    core = _sparse(3, {1: QColor(255, 255, 255, 128), 2: QColor("white")})
    plan = CharacterLayerPlan(("base", kind), (_asset(kind, "layer.png"),))
    result = compose_body_pack_frame(
        base, plan, lambda _record: _solid(3, QColor("red")), face_core=core,
    ).toImage()
    assert result.pixelColor(0, 0) == QColor("red")
    assert result.pixelColor(1, 0) == QColor(127, 0, 128)
    assert result.pixelColor(2, 0) == QColor(0, 0, 255)


@pytest.mark.parametrize(
    ("witness", "body_rgba", "kind", "layer_rgba", "hide_alpha", "face_alpha"),
    [
        pytest.param(
            "yaw+060-pitch+00", (133, 91, 80, 255), "hair-back",
            (186, 140, 124, 255), 0, 255, id="yaw-060-hair-back",
        ),
        pytest.param(
            "front-eureka", (230, 198, 187, 255), "body-fix",
            (233, 197, 187, 253), 255, 115, id="front-eureka",
        ),
        pytest.param(
            "front-mock-scold", (198, 155, 135, 254), "body-fix",
            (201, 159, 139, 253), 255, 133, id="front-mock-scold",
        ),
        pytest.param(
            "front-mock-hit", (220, 170, 157, 254), "body-fix",
            (216, 169, 156, 253), 255, 132, id="front-mock-hit",
        ),
    ],
)
def test_root_cause_witnesses_follow_premultiplied_face_formula(
    qt_app: QApplication,
    witness: str,
    body_rgba: tuple[int, int, int, int],
    kind: str,
    layer_rgba: tuple[int, int, int, int],
    hide_alpha: int,
    face_alpha: int,
) -> None:
    base = _solid(1, QColor(*body_rgba))
    layer = _solid(1, QColor(*layer_rgba))
    core = _sparse(1, {0: QColor(255, 255, 255, face_alpha)})
    assets = {"layer.png": layer}
    mask = None
    if hide_alpha:
        assets["hide.png"] = _sparse(1, {0: QColor(255, 255, 255, hide_alpha)})
        mask = CharacterLayerMask("hide.png", "f" * 64, (0, 0))
    plan = CharacterLayerPlan(("base", kind), (_asset(kind, "layer.png"),), mask)
    result = compose_body_pack_frame(
        base, plan, lambda record: assets[record.path], face_core=core,
    ).toImage()

    body_endpoint = base.toImage().convertToFormat(QImage.Format_RGBA8888_Premultiplied)
    cleared_body = body_endpoint.copy()
    if hide_alpha:
        binary_hide = QImage(1, 1, QImage.Format_RGBA8888)
        binary_hide.fill(QColor(255, 255, 255, 255))
        clear_painter = QPainter(cleared_body)
        clear_painter.setCompositionMode(QPainter.CompositionMode_DestinationOut)
        clear_painter.drawImage(0, 0, binary_hide)
        clear_painter.end()

    character_endpoint = QImage(1, 1, QImage.Format_RGBA8888_Premultiplied)
    character_endpoint.fill(Qt.transparent)
    endpoint_painter = QPainter(character_endpoint)
    endpoint_painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
    endpoint_painter.drawImage(0, 0, cleared_body)
    endpoint_painter.drawImage(0, 0, layer.toImage())
    endpoint_painter.end()

    protected = _premultiplied_pixel(body_endpoint)
    character = _premultiplied_pixel(character_endpoint)
    expected = tuple(
        (protected[channel] * face_alpha
         + character[channel] * (255 - face_alpha) + 127) // 255
        for channel in range(4)
    )
    actual = _premultiplied_pixel(result)
    assert max(abs(actual[channel] - expected[channel]) for channel in range(4)) <= 1, witness


def test_role_layers_keep_native_alpha_until_the_final_face_formula(
    qt_app: QApplication,
) -> None:
    core = _sparse(3, {1: QColor(255, 255, 255, 128), 2: QColor("white")})
    plan = CharacterLayerPlan(
        ("base", "body-fix", "garment"),
        (_asset("body-fix", "fix.png"), _asset("garment", "garment.png")),
    )
    assets = {
        "fix.png": _solid(3, QColor("red")),
        "garment.png": _solid(3, QColor("green")),
    }
    result = compose_body_pack_frame(
        _solid(3, QColor("blue")), plan, lambda record: assets[record.path],
        face_core=core,
    ).toImage()
    assert result.pixelColor(0, 0) == QColor("green")
    assert result.pixelColor(1, 0) == QColor(0, 64, 128)
    assert result.pixelColor(2, 0) == QColor("blue")


def test_face_feather_weights_base_hide_clearing(qt_app: QApplication) -> None:
    core = _sparse(3, {1: QColor(255, 255, 255, 128), 2: QColor("white")})
    plan = CharacterLayerPlan(
        ("base",), (), CharacterLayerMask("hide.png", "f" * 64, (0, 0)),
    )
    result = compose_body_pack_frame(
        _solid(3, QColor("blue")), plan,
        lambda _record: _solid(3, QColor(255, 255, 255, 1)), face_core=core,
    ).toImage()
    assert [result.pixelColor(x, 0).alpha() for x in range(3)] == [0, 128, 255]


def test_face_feather_weights_makeup_and_preserves_destination_alpha(
    qt_app: QApplication,
) -> None:
    core = _sparse(4, {1: QColor(255, 255, 255, 128), 2: QColor("white"),
                       3: QColor("white")})
    base = _sparse(4, {x: QColor(0, 0, 255, 128) for x in range(3)})
    plan = CharacterLayerPlan(("base", "makeup"), (_asset("makeup", "makeup.png"),))
    result = compose_body_pack_frame(
        base, plan, lambda _record: _solid(4, QColor("red")), face_core=core,
    ).toImage()
    assert result.pixelColor(0, 0) == QColor(0, 0, 255, 128)
    feather = result.pixelColor(1, 0)
    assert abs(feather.red() - 128) <= 1
    assert abs(feather.blue() - 127) <= 1
    assert feather.alpha() == HALF_ALPHA
    assert result.pixelColor(2, 0) == QColor(255, 0, 0, 128)
    assert result.pixelColor(3, 0).alpha() == 0


def test_makeup_source_atop_changes_bprime_and_is_excluded_from_x(
    qt_app: QApplication,
) -> None:
    core = _sparse(3, {0: QColor("white"), 1: QColor(255, 255, 255, 128)})
    plan = CharacterLayerPlan(("base", "makeup"), (_asset("makeup", "makeup.png"),))
    makeup = _sparse(3, {x: QColor(255, 0, 0, 128) for x in range(3)})
    result = compose_body_pack_frame(
        _solid(3, QColor("blue")), plan, lambda _record: makeup, face_core=core,
    ).toImage()
    assert result.pixelColor(0, 0) == QColor(128, 0, 127)
    assert result.pixelColor(1, 0) == QColor(64, 0, 191)
    assert result.pixelColor(2, 0) == QColor("blue")


def test_transparent_face_core_keeps_layers_and_suppresses_makeup(
    qt_app: QApplication,
) -> None:
    plan = CharacterLayerPlan(
        ("base", "body-fix", "makeup"),
        (_asset("body-fix", "layer.png"), _asset("makeup", "makeup.png")),
    )
    assets = {"layer.png": _solid(3, QColor("red")),
              "makeup.png": _solid(3, QColor("blue"))}
    result = compose_body_pack_frame(
        _solid(3, QColor("green")), plan, lambda record: assets[record.path],
        face_core=_sparse(3, {}),
    ).toImage()
    assert all(result.pixelColor(x, 0) == QColor("red") for x in range(3))


def test_rear_hair_uses_the_same_face_formula_as_every_role_layer(
    qt_app: QApplication,
) -> None:
    plan = CharacterLayerPlan(("base", "hair-back"), (_asset("hair-back", "hair.png"),))
    core = _sparse(3, {0: QColor("white"), 1: QColor(255, 255, 255, 128)})
    result = compose_body_pack_frame(
        _solid(3, QColor("green")), plan, lambda _record: _solid(3, QColor("red")),
        face_core=core,
    ).toImage()
    assert result.pixelColor(0, 0) == QColor("green")
    assert result.pixelColor(1, 0) == QColor(127, 64, 0)
    assert result.pixelColor(2, 0) == QColor("red")
