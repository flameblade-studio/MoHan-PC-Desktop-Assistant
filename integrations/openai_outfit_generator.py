"""OpenAI GPT Image 2 provider for quarantine-first outfit generation.

The provider produces full-canvas, registered transparent garment overlays.
It never installs output itself; :mod:`application.self_generating_wardrobe`
owns quarantine, audit, packaging, and installation.
"""

from __future__ import annotations

lazy import base64
lazy import hashlib
lazy import json
lazy import secrets
lazy from urllib import error as urllib_error
lazy from urllib import request as urllib_request
lazy from dataclasses import dataclass
lazy from pathlib import Path
lazy from typing import Protocol

lazy import cv2
lazy import numpy as np

lazy from application.self_generating_wardrobe import (
    FashionTrendSignal,
    GeneratedOutfitDraft,
    OutfitCreationRequest,
)
lazy from domain.outfit_pack import (
    BASE_SILHOUETTES,
    GESTURE_SILHOUETTES,
    POSE_ATLAS_SILHOUETTES,
)

OPENAI_IMAGE_EDITS_URL = "https://api.openai.com/v1/images/edits"
OPENAI_IMAGE_MODEL = "gpt-image-2"
HALF_SIZE = (1254, 1254)
HALF_REQUEST_SIZE = (1264, 1264)
FULL_SIZE = (1024, 1536)
MAX_RESPONSE_BYTES = 128 * 1024 * 1024
LANGUAGES = ("zh-TW", "zh-CN", "en", "ja-JP")
BODY_REGIONS = (
    "neck", "shoulder-left", "shoulder-right", "arm-left", "arm-right",
    "torso", "leg-left", "leg-right",
)


class OutfitImageGenerationError(RuntimeError):
    """A sanitized, user-displayable image-provider failure."""


class OutfitImageEditTransport(Protocol):
    def edit(
        self,
        reference_png: bytes,
        prompt: str,
        size: tuple[int, int],
    ) -> bytes: ...


@dataclass(frozen=True, slots=True)
class OpenAIImageEditOptions:
    api_key: str
    timeout_seconds: float = 180.0
    quality: str = "medium"
    endpoint: str = OPENAI_IMAGE_EDITS_URL


class OpenAIImageEditTransport:
    """Small stdlib HTTP adapter; API keys and image payloads are never logged."""

    def __init__(self, options: OpenAIImageEditOptions) -> None:
        key = options.api_key.strip()
        if not key:
            raise OutfitImageGenerationError("OpenAI API key is unavailable.")
        if options.quality not in {"low", "medium", "high"}:
            raise ValueError("Unsupported GPT Image quality.")
        self._options = options
        self._api_key = key

    def edit(
        self,
        reference_png: bytes,
        prompt: str,
        size: tuple[int, int],
    ) -> bytes:
        if not reference_png.startswith(b"\x89PNG\r\n\x1a\n"):
            raise OutfitImageGenerationError("Outfit reference is not a PNG image.")
        boundary = f"mohan-{secrets.token_hex(16)}"
        body = self._multipart(
            boundary,
            {
                "model": OPENAI_IMAGE_MODEL,
                "prompt": prompt,
                "size": f"{size[0]}x{size[1]}",
                "quality": self._options.quality,
                "background": "transparent",
            },
            "image[]",
            "mohan-reference.png",
            reference_png,
        )
        request = urllib_request.Request(
            self._options.endpoint,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Accept": "application/json",
            },
        )
        try:
            with urllib_request.urlopen(
                request,
                timeout=self._options.timeout_seconds,
            ) as response:
                payload = response.read(MAX_RESPONSE_BYTES + 1)
        except urllib_error.HTTPError as error:
            status = int(getattr(error, "code", 0) or 0)
            raise OutfitImageGenerationError(
                f"GPT Image request failed with HTTP {status}."
            ) from None
        except (OSError, TimeoutError, urllib_error.URLError):
            raise OutfitImageGenerationError(
                "GPT Image request could not reach the provider."
            ) from None
        if len(payload) > MAX_RESPONSE_BYTES:
            raise OutfitImageGenerationError("GPT Image response was too large.")
        try:
            value = json.loads(payload.decode("utf-8"))
            encoded = value["data"][0]["b64_json"]
            image = base64.b64decode(encoded, validate=True)
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError):
            raise OutfitImageGenerationError(
                "GPT Image returned an invalid image response."
            ) from None
        return image

    @staticmethod
    def _multipart(
        boundary: str,
        fields: dict[str, str],
        file_field: str,
        filename: str,
        data: bytes,
    ) -> bytes:
        marker = boundary.encode("ascii")
        chunks: list[bytes] = []
        for name, value in fields.items():
            chunks.extend(
                (
                    b"--" + marker + b"\r\n",
                    f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("ascii"),
                    value.encode("utf-8"),
                    b"\r\n",
                )
            )
        chunks.extend(
            (
                b"--" + marker + b"\r\n",
                (
                    f'Content-Disposition: form-data; name="{file_field}"; '
                    f'filename="{filename}"\r\n'
                ).encode("ascii"),
                b"Content-Type: image/png\r\n\r\n",
                data,
                b"\r\n--" + marker + b"--\r\n",
            )
        )
        return b"".join(chunks)


def _localized(value: str) -> dict[str, str]:
    return dict.fromkeys(LANGUAGES, value)


def _safe_view(view_id: str) -> str:
    return view_id.replace("+", "p").replace("-", "m")


def _reference_path(root: Path, view_id: str) -> Path:
    half = {
        "cheek-rest": root / "assets" / "expressions" / "idle.png",
        "left-neutral": root / "assets" / "expressions" / "idle_lean.png",
        "front-crossed": root / "assets" / "expressions" / "idle_front.png",
        "front-mock-scold": root / "assets" / "expressions" / "mock_scold.png",
        "front-mock-hit": root / "assets" / "expressions" / "mock_hit_front.png",
        "front-eureka": root / "assets" / "expressions" / "eureka_front.png",
        "front-exasperated": root / "assets" / "expressions" / "exasperated_front.png",
    }
    if view_id in half:
        return half[view_id]
    return root / "assets" / "pose-atlas" / "v4" / f"{view_id}.png"


def _decode_registered_png(
    data: bytes,
    target: tuple[int, int],
) -> tuple[bytes, np.ndarray]:
    matrix = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    if matrix is None or matrix.ndim != 3 or matrix.shape[2] != 4:
        raise OutfitImageGenerationError(
            "Generated outfit must be an RGBA image with transparency."
        )
    target_width, target_height = target
    height, width = matrix.shape[:2]
    if width < target_width or height < target_height:
        raise OutfitImageGenerationError("Generated outfit canvas is too small.")
    if (width, height) != target:
        left = (width - target_width) // 2
        top = (height - target_height) // 2
        matrix = matrix[top:top + target_height, left:left + target_width]
    alpha = matrix[:, :, 3]
    opaque_pixels = int(np.count_nonzero(alpha))
    if opaque_pixels < max(64, target_width * target_height // 5000):
        raise OutfitImageGenerationError("Generated outfit layer is empty.")
    if opaque_pixels > target_width * target_height * 0.72:
        raise OutfitImageGenerationError(
            "Generated outfit replaced too much of the character canvas."
        )
    ok, encoded = cv2.imencode(".png", matrix)
    if not ok:
        raise OutfitImageGenerationError("Generated outfit could not be encoded.")
    return bytes(encoded), matrix


def _transparent_png(size: tuple[int, int]) -> bytes:
    width, height = size
    image = np.zeros((height, width, 4), dtype=np.uint8)
    ok, encoded = cv2.imencode(".png", image)
    if not ok:
        raise OutfitImageGenerationError("Transparent compatibility layer failed.")
    return bytes(encoded)


def _asset(path: str, slot: str, z_order: int) -> dict[str, object]:
    return {"slot": slot, "path": path, "anchor": [0, 0], "z_order": z_order}


class OpenAIOutfitDraftGenerator:
    """Generate one coherent garment overlay for every required silhouette."""

    def __init__(
        self,
        transport: OutfitImageEditTransport,
        project_root: Path,
    ) -> None:
        self._transport = transport
        self._root = Path(project_root)

    def create(
        self,
        request: OutfitCreationRequest,
        trends: tuple[FashionTrendSignal, ...],
        required_views: tuple[str, ...],
    ) -> GeneratedOutfitDraft:
        unsupported = request.requested_categories - {"garment", "handheld"}
        if unsupported:
            raise OutfitImageGenerationError(
                "This provider supports garments and contextual handheld items only."
            )
        design = self._design_prompt(request, trends)
        assets: dict[str, bytes] = {}
        garment_poses: dict[str, list[dict[str, object]]] = {}
        handheld_poses: dict[str, list[dict[str, object]]] = {}
        hair_poses: dict[str, list[dict[str, object]]] = {}
        reference_hashes: dict[str, str] = {}
        for view_id in required_views:
            reference_path = _reference_path(self._root, view_id)
            if not reference_path.is_file():
                raise OutfitImageGenerationError(
                    f"Authoritative outfit reference is missing: {view_id}."
                )
            reference = reference_path.read_bytes()
            target = FULL_SIZE if view_id in POSE_ATLAS_SILHOUETTES else HALF_SIZE
            requested = target if target == FULL_SIZE else HALF_REQUEST_SIZE
            generated = self._transport.edit(
                reference,
                self._view_prompt(design, view_id, target),
                requested,
            )
            normalized, _matrix = _decode_registered_png(generated, target)
            safe = _safe_view(view_id)
            garment_path = f"assets/garment-{safe}.png"
            assets[garment_path] = normalized
            garment_poses[view_id] = [_asset(garment_path, "outerwear", 10)]

            if "handheld" in request.requested_categories:
                handheld = self._transport.edit(
                    reference,
                    self._handheld_prompt(request, view_id, target),
                    requested,
                )
                normalized_handheld, _handheld_matrix = _decode_registered_png(
                    handheld,
                    target,
                )
                handheld_path = f"assets/handheld-{safe}.png"
                assets[handheld_path] = normalized_handheld
                handheld_poses[view_id] = [
                    _asset(handheld_path, "handheld", 50)
                ]

            # The base portrait already contains the canonical hairstyle. A
            # selected, transparent compatibility hairstyle preserves it while
            # satisfying the complete-ensemble contract without regenerating
            # or altering identity-bearing hair.
            blank = _transparent_png(target)
            back_path = f"assets/hair-back-{safe}.png"
            front_path = f"assets/hair-front-{safe}.png"
            assets[back_path] = blank
            assets[front_path] = blank
            hair_poses[view_id] = [
                _asset(back_path, "back", -10),
                _asset(front_path, "front", 20),
            ]
            reference_hashes[view_id] = hashlib.sha256(reference).hexdigest()
        manifest = self._manifest(
            request,
            garment_poses,
            hair_poses,
            handheld_poses,
        )
        record = {
            "provider": "openai-image-api",
            "model": OPENAI_IMAGE_MODEL,
            "quality": "provider-configured",
            "transparent_background_requested": True,
            "design_prompt": design,
            "reference_sha256": reference_hashes,
            "view_count": len(required_views),
            "generated_categories": sorted(request.requested_categories),
        }
        return GeneratedOutfitDraft(
            manifest,
            frozendict(assets),
            frozendict(record),
        )

    @staticmethod
    def _design_prompt(
        request: OutfitCreationRequest,
        trends: tuple[FashionTrendSignal, ...],
    ) -> str:
        trend_traits = ", ".join(
            trait for trend in trends for trait in trend.abstract_traits
        ) or "none"
        return (
            f"Original outfit direction: {request.creative_direction}. "
            f"Context: {request.weather}, {request.temperature_c:.1f} C, "
            f"mood {request.mood}, occasion {request.occasion}. "
            f"Abstract trend traits: {trend_traits}. Keep one identical clothing "
            "design, materials, colors, fasteners and embroidery across every view."
        )

    @staticmethod
    def _view_prompt(
        design: str,
        view_id: str,
        target: tuple[int, int],
    ) -> str:
        return (
            "Create a production-ready transparent PNG clothing overlay for the "
            "exact MoHan reference image supplied. OUTPUT ONLY the new garment pixels; "
            "every other pixel must be fully transparent. Preserve the exact canvas, "
            "character pose, body proportions and pixel registration. Never draw or "
            "alter face, skin, hands, hair, hair ornament, eyes, mouth, background or "
            "body geometry. The overlay must cover the existing garment cleanly, obey "
            "natural sleeve and body occlusion, and contain no detached fragments. "
            f"Target registered canvas after normalization: {target[0]}x{target[1]}; "
            f"view identifier: {view_id}. {design}"
        )

    @staticmethod
    def _handheld_prompt(
        request: OutfitCreationRequest,
        view_id: str,
        target: tuple[int, int],
    ) -> str:
        return (
            "Create a production-ready transparent PNG handheld accessory overlay "
            "for the exact MoHan reference image supplied. OUTPUT ONLY the accessory "
            "pixels; every other pixel must be fully transparent. Keep the canvas and "
            "pixel registration exact. Place the handle at her right-hand grip and "
            "respect the visible hand occlusion. Never draw or alter face, skin, body, "
            "hands, clothing, hair, ornament or background; do not cover her face. "
            "Keep one identical accessory design across all views. "
            f"Target registered canvas after normalization: {target[0]}x{target[1]}; "
            f"view identifier: {view_id}. {request.accessory_direction}"
        )

    @staticmethod
    def _manifest(
        request: OutfitCreationRequest,
        garment_poses: dict[str, list[dict[str, object]]],
        hair_poses: dict[str, list[dict[str, object]]],
        handheld_poses: dict[str, list[dict[str, object]]],
    ) -> dict[str, object]:
        visibility = {
            view: dict.fromkeys(BODY_REGIONS, "covered")
            for view in garment_poses
        }
        rules = dict.fromkeys(garment_poses, "behind-hands")
        collar = dict.fromkeys(garment_poses, "behind-collar")
        handheld_selected = bool(handheld_poses)
        handheld_rules = dict.fromkeys(handheld_poses, "behind-hands")
        accessories = []
        if handheld_selected:
            accessories.append({
                "id": "contextual-handheld",
                "accessory_kind": "handheld",
                "display_names": _localized("情境手持配飾"),
                "variants": [{
                    "id": "generated",
                    "display_names": _localized("自主生成"),
                    "poses": handheld_poses,
                    "placement": dict.fromkeys(handheld_poses, "hand-right"),
                    "hand_occlusion": handheld_rules,
                }],
            })
        return {
            "format": "mohan-outfit-pack",
            "version": 2,
            "id": "generated-placeholder",
            "pack_version": "1.0.0",
            "app_range": ">=4.0.0,<5.0.0",
            "display_names": _localized("墨寒自主設計服裝"),
            "compatible_body_profile": {"id": "mohan-body-v1", "version": 1},
            "source": {
                "kind": "original",
                "author": "MoHan autonomous wardrobe with OpenAI GPT Image 2",
                "license": "Project License",
                "reference_included": False,
            },
            "authoring": {"template": "mohan-official-poses", "version": 2},
            "looks": [{
                "id": "contextual-outfit",
                "display_names": _localized("情境衣裝"),
                "variants": [{
                    "id": "generated",
                    "display_names": _localized("自主生成"),
                    "fabric_behavior": "draped",
                    "body_visibility": visibility,
                    "poses": garment_poses,
                }],
            }],
            "hairstyles": [{
                "id": "canonical-hair",
                "display_names": _localized("墨寒原髮型"),
                "variants": [{
                    "id": "preserved",
                    "display_names": _localized("保持原貌"),
                    "poses": hair_poses,
                    "face_occlusion_masks": dict.fromkeys(garment_poses, "none"),
                    "hand_occlusion": rules,
                    "garment_occlusion": collar,
                }],
            }],
            "headwear": [],
            "accessories": accessories,
            "ensembles": [{
                "id": "autonomous-look",
                "display_names": _localized("墨寒自主搭配"),
                "autonomous_profile": {
                    "thermal_bands": ["hot", "warm", "mild", "cool", "cold"],
                    "weather": [request.weather] if request.weather in {
                        "clear", "cloudy", "rain", "storm", "snow", "windy", "indoor"
                    } else ["indoor"],
                    "moods": [request.mood] if request.mood in {
                        "calm", "cheerful", "affectionate", "reserved", "upset", "focused"
                    } else ["calm"],
                    "occasions": [request.occasion] if request.occasion in {
                        "everyday", "work", "formal", "holiday", "birthday",
                        "christmas", "valentines"
                    } else ["everyday"],
                    "priority": 20,
                },
                "selections": {
                    "garment": {"item_id": "contextual-outfit", "variant_id": "generated"},
                    "hairstyle": {"item_id": "canonical-hair", "variant_id": "preserved"},
                    "headwear": None,
                    "weapon": None,
                    "handheld": (
                        {"item_id": "contextual-handheld", "variant_id": "generated"}
                        if handheld_selected else None
                    ),
                    "jewelry": None,
                    "foreground-effect": None,
                },
            }],
        }


def _protected_face_path(root: Path, view_id: str) -> Path:
    if view_id in POSE_ATLAS_SILHOUETTES:
        return root / "assets" / "pose-atlas" / "v4-layered" / f"{view_id}_base.png"
    pose = {
        "cheek-rest": "cheek",
        "left-neutral": "lean",
    }.get(view_id, "front")
    return root / "assets" / "expressions" / "layered" / f"{pose}_base.png"


class GeneratedOutfitImageAuditor:
    """Fail closed on malformed, opaque, empty, or overbroad generated layers."""

    def __init__(self, project_root: Path | None = None) -> None:
        self._root = Path(project_root) if project_root is not None else None

    def audit(
        self,
        job_directory: Path,
        manifest: dict[str, object],
    ) -> tuple[str, ...]:
        issues: list[str] = []
        source = Path(job_directory) / "source"
        looks = manifest.get("looks")
        if not isinstance(looks, list) or not looks:
            return ("generated-garment-manifest-missing",)
        try:
            garment_poses = looks[0]["variants"][0]["poses"]
        except (KeyError, IndexError, TypeError):
            return ("generated-garment-poses-missing",)
        if not isinstance(garment_poses, dict):
            return ("generated-garment-poses-invalid",)
        pose_groups: list[tuple[str, dict[str, object]]] = [
            ("garment", garment_poses)
        ]
        accessories = manifest.get("accessories", [])
        if isinstance(accessories, list):
            for item in accessories:
                if not isinstance(item, dict) or item.get("accessory_kind") != "handheld":
                    continue
                try:
                    handheld_poses = item["variants"][0]["poses"]
                except (KeyError, IndexError, TypeError):
                    issues.append("handheld:poses-missing")
                    continue
                if not isinstance(handheld_poses, dict):
                    issues.append("handheld:poses-invalid")
                    continue
                pose_groups.append(("handheld", handheld_poses))
        for category, poses in pose_groups:
            issues.extend(self._audit_poses(source, category, poses))
        return tuple(issues)

    def _audit_poses(
        self,
        source: Path,
        category: str,
        poses: dict[str, object],
    ) -> tuple[str, ...]:
        issues: list[str] = []
        for view_id, entries in poses.items():
            issue_id = f"{category}:{view_id}"
            if not isinstance(entries, list) or not entries:
                issues.append(f"{issue_id}:missing-layer")
                continue
            path = entries[0].get("path") if isinstance(entries[0], dict) else None
            if not isinstance(path, str):
                issues.append(f"{issue_id}:invalid-path")
                continue
            image = cv2.imread(str(source / Path(*path.split("/"))), cv2.IMREAD_UNCHANGED)
            expected = FULL_SIZE if view_id in POSE_ATLAS_SILHOUETTES else HALF_SIZE
            if image is None or image.ndim != 3 or image.shape[2] != 4:
                issues.append(f"{issue_id}:not-rgba")
                continue
            if (image.shape[1], image.shape[0]) != expected:
                issues.append(f"{issue_id}:wrong-size")
                continue
            nonzero = int(np.count_nonzero(image[:, :, 3]))
            pixels = expected[0] * expected[1]
            if nonzero < max(64, pixels // 5000):
                issues.append(f"{issue_id}:empty")
            elif nonzero > pixels * 0.72:
                issues.append(f"{issue_id}:overbroad-alpha")
            if self._root is not None:
                protected_path = _protected_face_path(self._root, view_id)
                protected = cv2.imread(str(protected_path), cv2.IMREAD_UNCHANGED)
                if (
                    protected is None
                    or protected.ndim != 3
                    or protected.shape[2] != 4
                    or protected.shape[:2] != image.shape[:2]
                ):
                    issues.append(f"{issue_id}:protected-mask-unavailable")
                    continue
                face_alpha = protected[:, :, 3] > 8
                face_pixels = int(np.count_nonzero(face_alpha))
                overlap = int(np.count_nonzero((image[:, :, 3] > 8) & face_alpha))
                if face_pixels and overlap / face_pixels > 0.005:
                    issues.append(f"{issue_id}:face-overlap")
        return tuple(issues)
