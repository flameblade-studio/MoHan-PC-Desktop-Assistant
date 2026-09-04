from __future__ import annotations

lazy import numpy as np

lazy from tools.audit_official_pack_quality import brown_hair_metrics, component_metrics


EXPECTED_BROWN_PIXELS = 2
EXPECTED_COMPONENTS = 3
EXPECTED_MAIN_AREA = 400


def test_brown_hair_metrics_attributes_solid_pollution_and_holes() -> None:
    shape = (1254, 1254, 4)
    portrait = np.zeros(shape, dtype=np.uint8)
    front = np.zeros(shape, dtype=np.uint8)
    back = np.zeros(shape, dtype=np.uint8)
    base = np.zeros(shape, dtype=np.uint8)
    # BGR (40, 80, 100): mean 73.3 and R-B 60, so both pixels are suspect.
    portrait[150, 360:362] = (40, 80, 100, 255)
    front[150, 360, 3] = 255

    measured = brown_hair_metrics(portrait, front, back, base)

    assert measured["brown_pixels"] == EXPECTED_BROWN_PIXELS
    assert measured["brown_outfit_alpha_255"] == 1
    assert measured["brown_both_outfit_and_base_hair_alpha_0"] == 1


def test_component_metrics_measures_edge_distance_from_main() -> None:
    image = np.zeros((240, 240, 4), dtype=np.uint8)
    image[10:30, 10:30, 3] = 255
    image[31:36, 31:36, 3] = 255
    image[180:185, 180:185, 3] = 255

    measured = component_metrics(image)

    assert measured["component_count"] == EXPECTED_COMPONENTS
    assert measured["main_component_area"] == EXPECTED_MAIN_AREA
    assert measured["detached_over_100px"] == 1
    assert measured["unlinked_over_100px"] == 1


def test_component_metrics_treats_short_chain_gaps_as_linked() -> None:
    image = np.zeros((240, 240, 4), dtype=np.uint8)
    image[10:30, 10:30, 3] = 255
    image[40:45, 40:45, 3] = 255
    image[70:75, 70:75, 3] = 255

    measured = component_metrics(image)

    assert measured["component_count"] == EXPECTED_COMPONENTS
    assert measured["unlinked_over_100px"] == 0
