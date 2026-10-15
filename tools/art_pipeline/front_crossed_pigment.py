"""Reuse V5 authored brush fields registered to front-crossed native lids."""
from __future__ import annotations

lazy import copy
lazy import json
lazy from pathlib import Path

lazy import numpy as np

BOX = (490, 375, 725, 470)
DARK_LASH_THRESHOLD = 125
SRGB_LINEAR_THRESHOLD = .04045
SRGB_ENCODE_THRESHOLD = .0031308
EYE_MIDPOINT_X = 600
YY, XX = np.indices((BOX[3] - BOX[1], BOX[2] - BOX[0]), dtype=float)
XX += BOX[0]
YY += BOX[1]
GAINS = {"rest": (12.630281448364258, 17.16641616821289),
         "half": (13.018136978149414, 13.181150436401367),
         "closed": (17.86478042602539, 14.49852180480957)}


def lab(rgb: np.ndarray) -> np.ndarray:
    """Same D65 sRGB -> CIELAB conversion as the previous concentration evidence."""
    pixels = rgb.astype(np.float64) / 255
    linear = np.where(pixels <= SRGB_LINEAR_THRESHOLD, pixels / 12.92, ((pixels + 0.055) / 1.055) ** 2.4)
    xyz = linear @ np.array(((0.4124564, 0.3575761, 0.1804375),
                             (0.2126729, 0.7151522, 0.0721750),
                             (0.0193339, 0.1191920, 0.9503041))).T
    xyz /= np.array((0.95047, 1.0, 1.08883))
    transformed = np.where(xyz > (6 / 29) ** 3, np.cbrt(xyz), xyz / (3 * (6 / 29) ** 2) + 4 / 29)
    return np.stack((116 * transformed[..., 1] - 16,
                     500 * (transformed[..., 0] - transformed[..., 1]),
                     200 * (transformed[..., 1] - transformed[..., 2])), axis=-1)


def lab_to_rgb(values: np.ndarray) -> np.ndarray:
    fy = (values[..., 0] + 16) / 116
    f = np.stack((fy + values[..., 1] / 500, fy, fy - values[..., 2] / 200), axis=-1)
    xyz = np.where(f > 6 / 29, f ** 3, 3 * (6 / 29) ** 2 * (f - 4 / 29))
    xyz *= np.array((.95047, 1., 1.08883))
    linear = xyz @ np.linalg.inv(np.array(((.4124564, .3575761, .1804375),
                                          (.2126729, .7151522, .0721750),
                                          (.0193339, .1191920, .9503041)))).T
    return np.where(linear <= SRGB_ENCODE_THRESHOLD, linear * 12.92,
                    1.055 * np.maximum(linear, 0) ** (1 / 2.4) - .055) * 255


def registered_marks(template: dict, traces: list, state: str) -> list:
    """Place each existing dab relative to the newly observed native lid.

    No image pixels or old eye-hole masks are warped. Each dab's centre and
    tangent are recomputed, and the complete resulting coordinates are saved.
    """
    marks = []
    for original in template['marks']:
        x, y, major, minor, angle, amount, colour = original
        side = 0 if x < EYE_MIDPOINT_X else 1
        previous = np.asarray(template['protected_lash_traces'][side])
        target = np.asarray(traces[side])
        old_top = np.interp(x, previous[:, 0], previous[:, 1])
        new_top = np.interp(x, target[:, 0], target[:, 1])
        old_slope = np.interp(x + 2, previous[:, 0], previous[:, 1]) - np.interp(x - 2, previous[:, 0], previous[:, 1])
        new_slope = np.interp(x + 2, target[:, 0], target[:, 1]) - np.interp(x - 2, target[:, 0], target[:, 1])
        angle += np.degrees(np.arctan2(new_slope, 4) - np.arctan2(old_slope, 4))
        # A closed lid presents a wider surface between the lashes and the fold.
        depth_scale = 1.15 if state == 'closed' else 1.
        new_y = new_top - (old_top - y) * depth_scale
        minor *= depth_scale
        marks.append([float(x), float(new_y), float(major), float(minor),
                      float(angle), float(amount), colour])
    return marks


def brush_field(plan: dict, palette: dict, base: np.ndarray) -> tuple:
    safe = np.ones(XX.shape)
    for trace in plan['protected_lash_traces']:
        coords = np.asarray(trace)
        active = (coords[0, 0] <= XX) & (coords[-1, 0] >= XX)
        top = np.interp(XX, coords[:, 0], coords[:, 1])
        safe[active] = np.minimum(safe[active], np.clip((top[active] - YY[active]) / .8, 0, 1))
    safe[base[..., 0] < DARK_LASH_THRESHOLD] = 0
    deposits = np.zeros(XX.shape)
    colour_mass = np.zeros((*XX.shape, 3))
    for x, y, major, minor, angle, amount, colour in plan['marks']:
        theta = np.radians(angle)
        dx, dy = XX - x, YY - y
        u = dx * np.cos(theta) + dy * np.sin(theta)
        v = -dx * np.sin(theta) + dy * np.cos(theta)
        radius = (u / major) ** 2 + (v / minor) ** 2
        dab = np.maximum(0, np.exp(-.5 * radius) - np.exp(-4.5)) / (1 - np.exp(-4.5))
        weight = dab * amount
        deposits += weight
        colour_mass += weight[..., None] * np.asarray(palette[colour])
    pigment = np.divide(colour_mass, deposits[..., None], out=np.zeros_like(colour_mass), where=deposits[..., None] > 0)
    pigment = shaded_pigment(pigment, base, plan["target_hue_angle_deg"])
    deposits *= safe
    return deposits, pigment, safe


def shaded_pigment(pigment: np.ndarray, base: np.ndarray, target_hue: float) -> np.ndarray:
    # Preserve the pigment hue while reducing its lightness over native creases.
    # Clamping individual RGB channels would rotate the warm rose hue.
    pigment_lab = lab(pigment)
    chroma = np.linalg.norm(pigment_lab[..., 1:], axis=-1)
    angle = np.radians(target_hue)
    pigment_lab[..., 1] = chroma * np.cos(angle)
    pigment_lab[..., 2] = chroma * np.sin(angle)
    lower = np.zeros(XX.shape)
    upper = pigment_lab[..., 0].copy()
    for _ in range(15):
        mid = (lower + upper) / 2
        candidate_lab = pigment_lab.copy()
        candidate_lab[..., 0] = mid
        candidate_rgb = lab_to_rgb(candidate_lab)
        valid = np.all(candidate_rgb <= base, axis=-1)
        lower = np.where(valid, mid, lower)
        upper = np.where(valid, upper, mid)
    pigment_lab[..., 0] = lower
    return np.rint(lab_to_rgb(pigment_lab)).clip(0, 255).astype(np.uint8)


def make_local_layer(deposits: np.ndarray, pigment: np.ndarray, gain: np.ndarray) -> np.ndarray:
    layer = np.zeros((*XX.shape, 4), dtype=np.uint8)
    layer[..., :3] = pigment
    layer[..., 3] = np.rint((1 - np.exp(-deposits * gain)) * 255).clip(0, 255).astype(np.uint8)
    layer[layer[..., 3] == 0] = 0
    return layer


def painted_eyes(native: np.ndarray, state: str, plan_path: Path) -> np.ndarray:
    config = json.loads(plan_path.read_text(encoding="utf-8"))
    template = config["frames"][state]
    plan = copy.deepcopy(template)
    if state == "rest":
        for side, trace in enumerate(plan["protected_lash_traces"]):
            for point in trace:
                point[1] += (6 if side == 0 else 7)
    plan["marks"] = registered_marks(template, plan["protected_lash_traces"], state)
    base = native[BOX[1]:BOX[3], BOX[0]:BOX[2], :3]
    deposits, pigment, _ = brush_field(plan, config["palette"], base)
    gains = np.where(XX < EYE_MIDPOINT_X, GAINS[state][0], GAINS[state][1])
    result = np.zeros_like(native)
    result[BOX[1]:BOX[3], BOX[0]:BOX[2]] = make_local_layer(deposits, pigment, gains)
    return result
