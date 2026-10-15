"""Build front-crossed rigs through the V5 source-bound makeup workflow.

Reuses existing approved pigment and mouth frames. Candidate generation is the
same bounded registration, soft lip-surface and native aperture process as V5.
Original inputs are backed up with hashes before applying any candidate.
"""
from __future__ import annotations

lazy import argparse
lazy import copy
lazy import hashlib
lazy import io
lazy import json
lazy import sys
lazy import subprocess
lazy import zipfile
lazy from pathlib import Path

lazy import cv2
lazy import numpy as np
lazy from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SIZE = (1254, 1254)
ROI = (450, 345, 780, 625)
FRAMES = ROOT / "assets/expressions/complete-expressions/frames"
KNOTS = (0.0, .15, .30, .45, .55, .70, .85, 1.0)
COLOR_SUPPORT_EPSILON = .001
SOURCE_LIPS = (568, 644, [558, 551, 546, 550, 546, 550, 554, 558],
               [559, 560, 560, 561, 560, 560, 559, 559], None,
               [559, 568, 577, 580, 579, 575, 566, 559])
ORAL_DARK_THRESHOLD = 125
PACK = "assets/official-packs/mohan.makeup.builtin.mohan-outfit"
MAIN_EYE_SOURCE_COMMIT = "b8bd116634a3659de6d15a51f2668de5b20b84c4"
MAIN_EYE_SOURCE_PACK_SHA256 = "f8871cf98d76d37f8bfb6be033590138386f3fff434d33ae98172caf2a66a4ea"
STATES = ("rest", "half", "closed")
FAMILIES = ("neutral", "small", "a", "o")


def rgba(path: Path) -> np.ndarray:
    with Image.open(path) as source:
        return np.asarray(source.convert("RGBA")).copy()


def encoded(pixels: np.ndarray) -> bytes:
    buffer = io.BytesIO()
    Image.fromarray(pixels).save(buffer, format="PNG")
    return buffer.getvalue()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8", newline="\n")


def curves(spec: tuple, x: np.ndarray) -> tuple[np.ndarray, ...]:
    left, right, upper, inner_top, inner_bottom, lower = spec
    position = np.clip((x - left) / (right - left), 0, 1)
    return tuple(np.interp(position, KNOTS, values) for values in (upper, inner_top, inner_bottom or inner_top, lower))


def registration(target: np.ndarray, source: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    left, top, right, bottom = ROI
    target_gray = cv2.cvtColor(target[top:bottom, left:right, :3], cv2.COLOR_RGB2GRAY)
    source_gray = cv2.cvtColor(source[top:bottom, left:right, :3], cv2.COLOR_RGB2GRAY)
    flow = cv2.calcOpticalFlowFarneback(target_gray, source_gray, None, .5, 5, 31, 6, 7, 1.5, 0)
    yy, xx = np.mgrid[:bottom - top, :right - left].astype(np.float32)
    return xx + flow[:, :, 0], yy + flow[:, :, 1]


def warp(layer: np.ndarray, mapping: tuple[np.ndarray, np.ndarray]) -> np.ndarray:
    left, top, right, bottom = ROI
    result = layer.copy()
    # Premultiplied resampling keeps transparent boundaries free of dark fringes.
    source = layer[top:bottom, left:right].astype(np.float32)
    source[:, :, :3] *= source[:, :, 3:4] / 255
    mapped = cv2.remap(source, *mapping, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    mapped[:, :, :3] = np.divide(mapped[:, :, :3] * 255, mapped[:, :, 3:4], out=np.zeros_like(mapped[:, :, :3]), where=mapped[:, :, 3:4] > 0)
    result[top:bottom, left:right] = np.clip(np.rint(mapped), 0, 255).astype(np.uint8)
    return result


def _lip_source_coordinates(spec, xx, yy):
    left, right = spec[:2]
    top, inner_top, inner_bottom, bottom = curves(spec, xx)
    mapped_x = SOURCE_LIPS[0] + (xx - left) / (right - left) * (SOURCE_LIPS[1] - SOURCE_LIPS[0])
    src_top, src_inner_top, src_inner_bottom, src_bottom = curves(SOURCE_LIPS, mapped_x)
    upper_fraction = (yy - top) / np.maximum(inner_top - top, 1)
    lower_fraction = (yy - inner_bottom) / np.maximum(bottom - inner_bottom, 1)
    mapped_y = np.where(yy < (inner_top + inner_bottom) / 2, src_top + upper_fraction * (src_inner_top - src_top), src_inner_bottom + lower_fraction * (src_bottom - src_inner_bottom))
    return mapped_x, mapped_y


def _mapped_lip_color(source, mapped_x, mapped_y):
    reference = rgba(FRAMES / "front-crossed-neutral-rest.rgba.png")
    alpha = source[:, :, 3].astype(np.float32) / 255
    delta = source[:, :, :3].astype(np.float32) - reference[:, :, :3].astype(np.float32)
    # #211 selective transfer: retain native texture, transfer only original
    # cosmetic color differences through soft feature-local geometry.
    weighted = cv2.GaussianBlur(delta * alpha[:, :, None], (0, 0), 3)
    support = cv2.GaussianBlur(alpha, (0, 0), 3)
    delta = np.divide(weighted, support[:, :, None], out=np.zeros_like(weighted), where=support[:, :, None] > COLOR_SUPPORT_EPSILON)
    return cv2.remap(delta, mapped_x, mapped_y.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)


def aligned_lips(source: np.ndarray, spec: tuple, native: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    # Each lip is warped independently between measured outer and inner curves.
    # This preserves the original style's RGB/alpha while respecting native mouths.
    left, right = spec[:2]
    yy, xx = np.mgrid[524:604, 545:686].astype(np.float32)
    top, inner_top, inner_bottom, bottom = curves(spec, xx)
    mapped_x, mapped_y = _lip_source_coordinates(spec, xx, yy)
    mapped_delta = _mapped_lip_color(source, mapped_x, mapped_y)
    target = cv2.remap(source, mapped_x, mapped_y.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    target[:, :, :3] = np.clip(np.rint(native[524:604, 545:686, :3].astype(float) + mapped_delta), 0, 255).astype(np.uint8)
    band = ((yy >= top) & (yy <= inner_top)) | ((yy >= inner_bottom) & (yy <= bottom))
    band &= (xx > left) & (xx < right)
    # #211: feather the lip surface, then protect the source-bound oral opening.
    soft = np.asarray(Image.fromarray(band.astype(np.uint8) * 255).filter(ImageFilter.GaussianBlur(3))).astype(float) / 255
    opening = (yy >= inner_top - 1.5) & (yy <= inner_bottom + 1.5) & (xx >= left) & (xx <= right)
    guard = np.asarray(Image.fromarray(opening.astype(np.uint8) * 255).filter(ImageFilter.GaussianBlur(1))).astype(float) / 255
    target[:, :, 3] = np.rint(target[:, :, 3] * soft * (1 - guard)).astype(np.uint8)
    # The original lip seam stays exclusively in the unmodified bare frame.
    target[opening] = 0
    target[(xx < left - 3) | (xx > right + 3)] = 0
    result = np.zeros_like(source)
    result[524:604, 545:686] = target
    oral = np.zeros(SIZE[::-1], dtype=np.uint8)
    oral[524:604, 545:686] = opening.astype(np.uint8) * 255
    return result, oral


def bounded(layer: np.ndarray, rectangles: list[list[int]]) -> np.ndarray:
    allowed = np.zeros(SIZE[::-1], dtype=bool)
    for x, y, width, height in rectangles:
        allowed[y:y + height, x:x + width] = True
    layer[~allowed] = 0
    return layer


def mask_rgba(alpha: np.ndarray) -> np.ndarray:
    result = np.zeros((*alpha.shape, 4), dtype=np.uint8)
    result[..., 3] = alpha
    return result


class RigBuilder:
    """Keep captured inputs and candidate stages within one bounded workspace."""

    def __init__(self, root: Path, evidence: Path, apply: bool) -> None:
        self.root = root
        self.evidence = evidence
        self.apply = apply
        self.changes = {}
        self.pins = {}
        evidence.mkdir(parents=True, exist_ok=True)

    def original(self, relative: str) -> bytes:
        backup = self.evidence / "backups" / relative
        if not backup.exists():
            backup.parent.mkdir(parents=True, exist_ok=True)
            backup.write_bytes((self.root / relative).read_bytes())
        data = backup.read_bytes()
        self.pins[relative] = digest(data)
        return data

    def put(self, relative: str, pixels: np.ndarray) -> dict:
        data = encoded(pixels)
        self.changes[relative] = data
        return {"path": relative, "sha256": digest(data), "width": 1254,
                "height": 1254, "anchor": [0, 0]}

    def prepare(self) -> None:
        self.complete_path = "assets/expressions/complete-expressions/manifest.json"
        self.complete = json.loads(self.original(self.complete_path))
        self.safe = json.loads(self.original("assets/makeup-safe-regions.json"))
        self.staging = self.evidence / "authoring"
        self.staging.mkdir(exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(self.original(PACK))) as archive:
            self.pack = json.loads(archive.read("manifest.json"))
            for name in archive.namelist():
                destination = self.staging / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(archive.read(name))

    def repair_mouth(self) -> None:
        # V5 bounded soft mouth composition, sourced from the already-clean A frame.
        # The whole mouth is transferred to keep the lip/teeth junction continuous.
        donor_path = "assets/expressions/complete-expressions/frames/front-attentive_front-a-rest.rgba.png"
        donor = np.asarray(Image.open(io.BytesIO(self.original(donor_path))).convert("RGBA"))
        mouth_mask = Image.new("L", SIZE)
        ImageDraw.Draw(mouth_mask).ellipse((557, 539, 664, 589), fill=255)
        weight = np.asarray(mouth_mask.filter(ImageFilter.GaussianBlur(3))).copy()
        weight[:524] = 0
        weight[596:] = 0
        weight[:, :555] = 0
        weight[:, 680:] = 0
        self.put("assets/front-makeup-rigs/front-crossed-mouth-repair-mask.png", mask_rgba(weight))
        for state in STATES:
            relative = f"assets/expressions/complete-expressions/frames/front-crossed-a-{state}.rgba.png"
            base = np.asarray(Image.open(io.BytesIO(self.original(relative))).convert("RGBA")).copy()
            t = weight[..., None].astype(np.float32) / 255
            base[..., :3] = np.rint(base[..., :3] * (1 - t) + donor[..., :3] * t).astype(np.uint8)
            descriptor = self.put(relative, base)
            record = self.complete["poses"]["front-crossed"]["frames"]["a"][state]
            record["sha256"] = descriptor["sha256"]
            record["repair"] = {"tool": "tools/art_pipeline/front_crossed_rig.py",
                                "donor": donor_path, "donor_sha256": self.pins[donor_path],
                                "mask": "assets/front-makeup-rigs/front-crossed-mouth-repair-mask.png"}

        self.frames = {}
        for family in FAMILIES:
            relative = f"assets/expressions/complete-expressions/frames/front-crossed-{family}-rest.rgba.png"
            self.frames[family] = np.asarray(Image.open(io.BytesIO(self.changes.get(relative) or self.original(relative))).convert("RGBA")).copy()

    def eye_masks(self) -> None:
        self.region = copy.deepcopy(self.safe["silhouettes"]["front-attentive_front"])
        self.region["rig"] = "assets/front-makeup-rigs/front-crossed-neutral"
        for field in ("foundation_masks", "eye_aperture_masks"):
            self.region[field] = {}
        # V5 authored upper/lower native-lid polygons, half narrowing, closed empty.
        xs = ((523, 530, 540, 550, 560, 570, 575), (622, 628, 638, 650, 662, 674, 679))
        uppers = ((435, 431, 428, 427, 430, 437, 442), (441, 436, 430, 428, 428, 432, 437))
        for state in STATES:
            mask = Image.new("L", SIZE)
            if state != "closed":
                for x, upper in zip(xs, uppers, strict=True):
                    lower = tuple(max(a, b) for a, b in zip(upper, (upper[0], 441, 443, 444, 444, 443, upper[-1]), strict=True))
                    top = upper if state == "rest" else tuple(round(a + .7 * (b - a)) for a, b in zip(upper, lower, strict=True))
                    ImageDraw.Draw(mask).polygon(list(zip(x, top, strict=True)) + list(reversed(list(zip(x, lower, strict=True)))), fill=255)
            aperture = np.asarray(mask)
            face = Image.new("L", SIZE)
            ImageDraw.Draw(face).ellipse((492, 358, 717, 641), fill=255)
            face_pixels = np.asarray(face).copy()
            face_pixels[aperture > 0] = 0
            folder = "assets/makeup-safe-regions/front-crossed"
            self.region["eye_aperture_masks"][state] = self.put(f"{folder}/eye-aperture-{state}.png", mask_rgba(aperture))
            self.region["foundation_masks"][state] = self.put(f"{folder}/foundation-{state}.png", mask_rgba(face_pixels))
            for family in FAMILIES:
                self.put(f"assets/front-makeup-rigs/front-crossed-{family}-eye-aperture-{state}.png", mask_rgba(aperture))

    def mouth_rigs(self) -> None:
        neutral_guard = aligned_lips(rgba(self.staging / next(a for a in self.pack["makeup"][0]["variants"][0]["poses"]["front-crossed"] if a["slot"] == "lips")["path"]), SOURCE_LIPS, self.frames["neutral"])[1]
        self.oral_records = {}
        for family, target in self.frames.items():
            # V5 source-specific dark oral mask, never a donor expression's cutout.
            oral = np.zeros(SIZE[::-1], dtype=np.uint8)
            oral[535:600, 550:678] = (np.max(target[535:600, 550:678, :3], axis=2) < ORAL_DARK_THRESHOLD) * 255
            descriptor = self.put(f"assets/front-makeup-rigs/front-crossed-{family}_oral_cavity.png", mask_rgba(neutral_guard if family == "neutral" else oral))
            if family != "neutral":
                self.oral_records[family] = {"path": "../../front-makeup-rigs/" + Path(descriptor["path"]).name,
                                        "sha256": descriptor["sha256"]}
            # The V5 exclusion rig assigns ownership to the opening only. Lip
            # colour is owned by the independent makeup mouth-state declarations.
            for role in ("lip_upper", "lip_lower", "teeth_tongue"):
                self.put(f"assets/front-makeup-rigs/front-crossed-{family}_{role}.png",
                    mask_rgba(np.zeros_like(oral)))
        # Runtime complete-frame loader confines oral mask paths beneath its root.
        for family in ("small", "a", "o"):
            source = self.changes[f"assets/front-makeup-rigs/front-crossed-{family}_oral_cavity.png"]
            relative = f"assets/expressions/complete-expressions/masks/front-crossed-rig-oral-{family}.png"
            self.changes[relative] = source
            self.oral_records[family] = {"path": "masks/" + Path(relative).name, "sha256": digest(source)}
        self.complete["poses"]["front-crossed"]["oral_masks"] = self.oral_records

    def makeup(self) -> None:
        for variant in self.pack["makeup"][0]["variants"]:
            style = variant["id"]
            source_lips = next(a for a in variant["poses"]["front-crossed"] if a["slot"] == "lips")
            source_pixels = rgba(self.staging / source_lips["path"])
            neutral_lips, _ = aligned_lips(source_pixels, SOURCE_LIPS, self.frames["neutral"])
            for family in FAMILIES:
                target = self.frames[family]
                layer = neutral_lips if family == "neutral" else warp(neutral_lips, registration(target, self.frames["neutral"]))
                oral = np.asarray(Image.open(io.BytesIO(self.changes[f"assets/front-makeup-rigs/front-crossed-{family}_oral_cavity.png"])))[:, :, 3]
                contours, _ = cv2.findContours(oral, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                guard = np.zeros_like(oral)
                cv2.drawContours(guard, contours, -1, 255, thickness=cv2.FILLED)
                softened = np.asarray(Image.fromarray(guard).filter(ImageFilter.GaussianBlur(1))).astype(float) / 255
                layer[..., 3] = np.rint(layer[..., 3] * (1 - softened)).astype(np.uint8)
                layer[guard > 0] = 0
                layer = bounded(layer, self.region["slots"]["lips"])
                relative = f"assets/front-rig-{style}-{family}-lips.png"
                (self.staging / relative).write_bytes(encoded(layer))
                declaration = {**source_lips, "path": relative, "sha256": digest((self.staging / relative).read_bytes())}
                if family == "neutral":
                    variant["poses"]["front-crossed"] = [a if a["slot"] != "lips" else declaration for a in variant["poses"]["front-crossed"]]
                else:
                    variant["mouth_states"][family]["front-crossed"] = [declaration]
            self.eye_pigment()

    def approved_glamorous_eyes(self) -> dict[str, bytes]:
        """Read the approved eye layers from the pinned main pack without resampling."""
        data = subprocess.check_output(
            ["git", "show", f"{MAIN_EYE_SOURCE_COMMIT}:{PACK}"], cwd=self.root,
        )
        if digest(data) != MAIN_EYE_SOURCE_PACK_SHA256:
            raise ValueError("Pinned main makeup pack SHA-256 mismatch")
        self.pins[f"{MAIN_EYE_SOURCE_COMMIT}:{PACK}"] = digest(data)
        layers = {}
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            manifest = json.loads(archive.read("manifest.json"))
            variant = next(v for v in manifest["makeup"][0]["variants"] if v["id"] == "glamorous")
            for state in STATES:
                table = variant["poses"] if state == "rest" else variant["eye_states"][state]
                record = next(a for a in table["front-crossed"] if a["slot"] == "eyes")
                layer = archive.read(record["path"])
                if digest(layer) != record["sha256"]:
                    raise ValueError(f"Pinned main eye layer SHA-256 mismatch: {state}")
                self.pins[f"{MAIN_EYE_SOURCE_COMMIT}:{record['path']}"] = digest(layer)
                layers[state] = layer
        return layers

    def eye_pigment(self) -> None:
        from tools.art_pipeline.front_crossed_pigment import painted_eyes
        self.original("assets/front-makeup-rigs/front-crossed-brush-plan.json")
        glamorous_eyes = self.approved_glamorous_eyes()
        for variant in self.pack["makeup"][0]["variants"]:
            style = variant["id"]
            for state in STATES:
                table = variant["poses"] if state == "rest" else variant["eye_states"][state]
                target_record = next(a for a in table["front-crossed"] if a["slot"] == "eyes")
                if style == "glamorous":
                    data = glamorous_eyes[state]
                else:
                    target = rgba(FRAMES / f"front-crossed-neutral-{state}.rgba.png")
                    layer = painted_eyes(target, state, self.root / "assets/front-makeup-rigs/front-crossed-brush-plan.json")
                    if style == "light":
                        layer[..., 3] = np.rint(layer[..., 3].astype(float) * .55).astype(np.uint8)
                    layer = bounded(layer, self.region["slots"]["eyes"])
                    data = encoded(layer)
                relative = f"assets/front-rig-{style}-{state}-eyes.png"
                (self.staging / relative).write_bytes(data)
                table["front-crossed"] = [a if a["slot"] != "eyes" else {**target_record, "path": relative, "sha256": digest((self.staging / relative).read_bytes())} for a in table["front-crossed"]]

    def preserve_mouth(self) -> None:
        """Retain the incoming mouth after its second visual rejection."""
        original_pack = json.loads(zipfile.ZipFile(io.BytesIO(self.original(PACK))).read("manifest.json"))
        for variant, baseline in zip(self.pack["makeup"][0]["variants"], original_pack["makeup"][0]["variants"], strict=True):
            lips = next(a for a in baseline["poses"]["front-crossed"] if a["slot"] == "lips")
            variant["poses"]["front-crossed"] = [a if a["slot"] != "lips" else lips for a in variant["poses"]["front-crossed"]]
            for family in ("small", "a", "o"):
                variant["mouth_states"][family]["front-crossed"] = baseline["mouth_states"][family]["front-crossed"]
        self.complete = json.loads(self.original(self.complete_path))
        for relative in list(self.changes):
            if "front-crossed" in relative and not ("eye-aperture" in relative or "foundation-" in relative):
                del self.changes[relative]
        for state in STATES:
            relative = f"assets/expressions/complete-expressions/frames/front-crossed-a-{state}.rgba.png"
            self.changes[relative] = self.original(relative)
        for family in ("small", "a", "o"):
            relative = f"assets/expressions/complete-expressions/masks/front-crossed-oral-{family}.png"
            self.changes[relative] = self.original(relative)
        # A rest mouth keeps the incoming legacy exclusion exactly. The new
        # explicit eye apertures remain independent of this rejected stage.
        painted = np.maximum(rgba(self.root / "assets/expressions/layered/front_oral_cavity.png")[..., 3], rgba(self.root / "assets/expressions/layered/front_teeth_tongue.png")[..., 3])
        covering = np.maximum(rgba(self.root / "assets/expressions/layered/front_lip_upper.png")[..., 3], rgba(self.root / "assets/expressions/layered/front_lip_lower.png")[..., 3])
        oral = np.where((painted > 0) & (covering == 0), 255, 0).astype(np.uint8)
        self.put("assets/front-makeup-rigs/front-crossed-neutral_oral_cavity.png", mask_rgba(oral))
        for role in ("lip_upper", "lip_lower", "teeth_tongue"):
            self.put(f"assets/front-makeup-rigs/front-crossed-neutral_{role}.png", mask_rgba(np.zeros_like(oral)))

    def seal(self) -> None:
        from application.outfit_pack_builder import build_outfit_pack
        from domain.outfit_pack_makeup import load_makeup_safe_regions
        self.safe["silhouettes"]["front-crossed"] = self.region
        self.changes["assets/makeup-safe-regions.json"] = (json.dumps(self.safe, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        self.changes[self.complete_path] = (json.dumps(self.complete, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        # Remove replaced single-owner members before sealing the unique manifest.
        from tools.art_pipeline.source_bound_pack_scope import path_counts
        used = path_counts(self.pack)
        for file in (self.staging / "assets").glob("*.png"):
            if file.relative_to(self.staging).as_posix() not in used:
                file.unlink()
        write_json(self.staging / "manifest.json", self.pack)
        self.preview = self.evidence / "candidate"
        for relative, data in self.changes.items():
            destination = self.preview / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
        for entry in self.safe["silhouettes"].values():
            for field in ("foundation_masks", "eye_aperture_masks"):
                for descriptor in entry.get(field, {}).values():
                    relative = descriptor["path"]
                    destination = self.preview / relative
                    if not destination.exists():
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        destination.write_bytes((self.root / relative).read_bytes())
        regions = load_makeup_safe_regions(self.preview / "assets/makeup-safe-regions.json")
        output = self.evidence / "candidate.mohan-outfit"
        if output.exists():
            output.unlink()
        build_outfit_pack(self.staging / "manifest.json", self.staging, output, makeup_regions=regions)
        self.changes[PACK] = output.read_bytes()

    def install(self) -> None:
        previous = self.evidence / "receipt.json"
        accepted = {}
        if previous.exists():
            accepted = {r["path"]: r["after_sha256"] for r in json.loads(previous.read_text(encoding="utf-8"))["files"]}
        for relative, data in self.changes.items():
            path = self.root / relative
            if path.exists():
                before = self.original(relative)
                if digest(path.read_bytes()) not in {digest(before), digest(data), accepted.get(relative)}:
                    raise ValueError(f"Installed asset has unrelated edits: {relative}")
        receipt = []
        for relative, data in self.changes.items():
            path = self.root / relative
            before = self.original(relative) if path.exists() else None
            receipt.append({"path": relative, "before_sha256": digest(before) if before else None, "after_sha256": digest(data)})
            if self.apply:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
        if self.apply and not self.eyes_only:
            for family in ("small", "a", "o"):
                obsolete = self.root / f"assets/expressions/complete-expressions/masks/front-crossed-oral-{family}.png"
                if obsolete.exists():
                    self.original(obsolete.relative_to(self.root).as_posix())
                    obsolete.unlink()
        if self.apply and self.eyes_only:
            for relative in accepted:
                if relative.startswith("assets/") and relative not in self.changes and "front-crossed" in relative:
                    path = self.root / relative
                    if path.exists() and digest(path.read_bytes()) == accepted[relative]:
                        self.original(relative)
                        path.unlink()
        write_json(self.evidence / "receipt.json", {"method": "V5 bounded soft composition, native apertures, premultiplied pigment registration, soft lip surfaces", "inputs": self.pins, "files": receipt, "applied": self.apply, "eyes_only": self.eyes_only, "mouth_stage": "preserved_after_second_visual_failure" if self.eyes_only else "rejected_candidate"})
        print("FRONT_CROSSED_RIG", len(receipt), "applied", self.apply)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--eyes-only", action="store_true", help="Preserve the rejected mouth stage and apply only eye data")
    parser.add_argument("--evidence", type=Path, default=ROOT / ".quality-tmp/front-fix/round2/rig")
    args = parser.parse_args()
    from application.character_runtime_bootstrap import activate_product_character_runtime
    activate_product_character_runtime(ROOT)
    builder = RigBuilder(ROOT, args.evidence.resolve(), args.apply)
    builder.prepare()
    builder.repair_mouth()
    builder.eye_masks()
    builder.mouth_rigs()
    builder.makeup()
    builder.eyes_only = args.eyes_only
    if args.apply and not args.eyes_only:
        raise ValueError("The mouth stage failed its second visual review; use --eyes-only for delivery")
    if args.eyes_only:
        builder.preserve_mouth()
    builder.seal()
    builder.install()


if __name__ == "__main__":
    main()
