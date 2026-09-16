"""Paint approved pose endpoints before their source-matched cosmetics."""
from __future__ import annotations

lazy import json
lazy from pathlib import Path

lazy from PySide6.QtCore import Qt
lazy from PySide6.QtGui import QPainter, QPixmap

lazy from domain.outfit_pack import resolve_active_selection
lazy from domain.outfit_pack_makeup import read_makeup_intensity, read_makeup_slot_intensities
lazy from domain import outfit_pack_official
lazy from infrastructure.reviewed_garment_assets import (
    COMPLETE_EXPRESSION_DYNAMIC_SOURCE,
    ReviewedGarmentPose,
)
lazy from infrastructure.reviewed_pose_motion import ReviewedPoseMotion, load_reviewed_pose_motion


# Resolve the official identity now so a lazily imported module object exposes the string.
BUILTIN_MAKEUP_PACK_ID = outfit_pack_official.BUILTIN_MAKEUP_PACK_ID
COSMETIC_SLOTS = frozenset({"eyes", "cheeks", "lips"})
LIGHT_STRENGTH = 0.55
# The installed complete half-body expression set, relative to the project root
# the overlay was built for (``ActiveOutfitOverlay.asset_root``).  Its presence
# and pose list are the evidence that the complete-expression route answers for a
# pose, which is what releases that pose's retained reviewed motion root.
COMPLETE_EXPRESSIONS_ROOT = Path("assets") / "expressions" / "complete-expressions"


class ReviewedPoseOverlayMixin:
    """Optional native-motion extension of the reviewed garment adapter."""

    def _complete_expression_pose_ids(self) -> frozenset[str]:
        """Pose ids the installed complete half-body expression set binds.

        The installed manifest is the authority for which poses the
        complete-expression route answers.  An absent or unreadable root means no
        pose is declared, so every pose keeps the retained reviewed motion root
        exactly as before this declaration existed.
        """
        cached = getattr(self, "_complete_expression_poses", None)
        if cached is None:
            manifest_path = (
                Path(self._asset_root) / COMPLETE_EXPRESSIONS_ROOT / "manifest.json"
            )
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                cached = frozenset()
            else:
                poses = manifest.get("poses") if isinstance(manifest, dict) else None
                cached = frozenset(poses) if isinstance(poses, dict) else frozenset()
            self._complete_expression_poses = cached
        return cached

    def _dynamic_source(self, view_id: str, pose: ReviewedGarmentPose) -> str | None:
        """The declared authority for one reviewed pose's frame dynamics.

        A pose record may declare ``dynamic_source`` itself.  The two installed
        poses instead acquire the declaration from the installed
        complete-expression manifest, because that manifest is a pinned owner
        artifact that the installer writes byte-for-byte.  A pose that declares
        nothing keeps the original fail-closed reviewed-motion contract.
        """
        declared = getattr(pose, "dynamic_source", None)
        if declared is not None:
            return declared
        if view_id in self._complete_expression_pose_ids():
            return COMPLETE_EXPRESSION_DYNAMIC_SOURCE
        return None

    def _native_motion(self, view_id: str) -> ReviewedPoseMotion | None:
        if self.native_neutral(view_id) is None:
            return None
        pose = self._reviewed_assets.poses[view_id]
        if not pose.motion_required:
            return None
        if self._dynamic_source(view_id, pose) == COMPLETE_EXPRESSION_DYNAMIC_SOURCE:
            # The installed complete-expression set answers for this pose, and
            # ``LayeredParametricFaceRenderer`` consults it before this motion
            # root.  An expression it does not bind must therefore fall through
            # to ``native_neutral(silhouette)`` - a still frame of the same
            # approved native - instead of being refused by a retained,
            # source-bound motion root that no longer matches the new native.
            # Nothing is released: ``motion_required`` stays true and every
            # source binding stays in force for a pose that does not declare this.
            return None
        cache = getattr(self, "_reviewed_motion_assets", None)
        if cache is None:
            cache = self._reviewed_motion_assets = {}
        if view_id not in cache:
            cache[view_id] = load_reviewed_pose_motion(
                self._reviewed_assets.root / view_id / "motion",
                expected_native_body_sha256=pose.native_source_sha256,
                expected_source_sha256=pose.approved_source_sha256,
            )
        return cache[view_id]

    def has_native_motion(self, view_id: str) -> bool:
        """Whether the retained reviewed motion root answers for this pose.

        A pose whose declared dynamic source is the installed complete-expression
        set reports ``False``: its dynamics come from that set.  For every other
        pose a missing or corrupt required endpoint still raises instead of
        silently using an old face.
        """
        return self._native_motion(view_id) is not None

    def _native_cosmetic_strengths(
        self, *, slots: frozenset[str] = COSMETIC_SLOTS,
        variant: str | None = None,
    ) -> dict[str, float] | None:
        selected = resolve_active_selection(self._store, "makeup")
        if selected.effective_pack_id == "builtin":
            return dict.fromkeys(slots, 0.0)
        if selected.effective_pack_id != BUILTIN_MAKEUP_PACK_ID:
            return None
        # Keep installed archive/profile verification authoritative.
        self._selected_variant("makeup", selected)
        if variant is None and selected.effective_variant_id not in {"light", "classic"}:
            raise ValueError("Reviewed pose motion lacks the selected makeup variant.")
        if variant is not None and variant != selected.effective_variant_id:
            raise ValueError("Reviewed pose motion variant does not match makeup selection.")
        intensity = read_makeup_intensity(self._store)
        # v3 supplies distinct source-bound layers for each variant.  Their
        # material is already authored at the selected strength, so the old
        # light-family factor applies only when the v1/v2 caller did not pass a
        # material variant.
        if variant is None and selected.effective_variant_id == "light":
            intensity *= LIGHT_STRENGTH
        multipliers = read_makeup_slot_intensities(self._store, slots=slots)
        return {slot: intensity * multipliers[slot] for slot in slots}

    def _native_variant(self, assets: ReviewedPoseMotion) -> str | None:
        """Resolve the selected v3 material, or keep legacy assets unchanged."""
        if getattr(assets, "variants", None) is None:
            return None
        selected = resolve_active_selection(self._store, "makeup")
        if selected.effective_pack_id == "builtin":
            return None
        if selected.effective_pack_id != BUILTIN_MAKEUP_PACK_ID:
            return None
        self._selected_variant("makeup", selected)
        variant = selected.effective_variant_id
        if variant not in assets.variants:
            raise ValueError("Reviewed pose motion lacks the selected makeup variant.")
        return variant

    def _paint_native_cosmetics(
        self, frame: QPixmap, assets: ReviewedPoseMotion, state: str,
        *, slots: frozenset[str] | None = None,
        variant: str | None = None,
    ) -> QPixmap:
        selected_slots = frozenset(assets.cosmetic_slots) if slots is None else slots
        has_variants = getattr(assets, "variants", None) is not None
        selected_variant = variant
        if has_variants and selected_variant is None:
            selected_variant = self._native_variant(assets)
        if selected_variant is None:
            strengths = self._native_cosmetic_strengths(slots=selected_slots)
        else:
            strengths = self._native_cosmetic_strengths(
                slots=selected_slots, variant=selected_variant,
            )
        if strengths is None:
            return frame
        painter = QPainter(frame)
        try:
            painter.setCompositionMode(QPainter.CompositionMode_SourceAtop)
            for slot in assets.cosmetic_slots:
                if slot not in selected_slots:
                    continue
                painter.setOpacity(strengths[slot])
                if has_variants and selected_variant is not None:
                    layer = assets.cosmetic(state, slot, variant=selected_variant)
                else:
                    layer = assets.cosmetic(state, slot)
                painter.drawPixmap(0, 0, layer)
        finally:
            painter.end()
        return frame

    def render_native_state(self, view_id: str, *, speaking: bool = False) -> QPixmap | None:
        """Compose the source body, current mouth, cosmetics and selected clothing."""
        assets = self._native_motion(view_id)
        if assets is None:
            return None
        frames = getattr(self, "_reviewed_native_frames", None)
        if frames is None:
            frames = self._reviewed_native_frames = {}
        variant = self._native_variant(assets)
        key = (view_id, speaking, variant or "legacy")
        if key in frames:
            return QPixmap(frames[key])
        frame = self.native_neutral(view_id)
        speech_available = speaking and "speech" in assets.patches
        if speech_available:
            painter = QPainter(frame)
            painter.drawPixmap(0, 0, assets.patch("speech"))
            painter.end()
        state = "speech" if speech_available else "rest"
        frame = self._paint_native_cosmetics(
            frame, assets, state, variant=variant,
        )
        frame = self.apply_appearance(frame, view_id)
        strengths = (
            self._native_cosmetic_strengths()
            if variant is None
            else self._native_cosmetic_strengths(variant=variant)
        )
        if strengths is None:
            frame = self.apply_makeup(frame, view_id)
        frames[key] = QPixmap(frame)
        return frame

    def render_native_blink(
        self, base: QPixmap, view_id: str, *, eye_state: str,
    ) -> QPixmap | None:
        """Replace only the eyes; preserve the current mouth and garment physics."""
        assets = self._native_motion(view_id)
        if assets is None:
            return None
        if eye_state not in {"half", "closed"}:
            # This source has two approved blink endpoints. Intermediate timer
            # phases hold neutral rather than blending an unrelated eyelid.
            return QPixmap(base)
        if not self._native_eye_endpoint_available(assets, eye_state):
            # A source that retains no authored endpoint for this phase keeps
            # the current eye authority instead of substituting another state.
            return QPixmap(base)
        cache = getattr(self, "_reviewed_native_eyes", None)
        if cache is None:
            cache = self._reviewed_native_eyes = {}
        variant = self._native_variant(assets)
        key = (view_id, eye_state, variant or "legacy")
        if key not in cache:
            cache[key] = self._native_eyes_for_state(
                assets, eye_state, variant=variant,
            )
        eyes = QPixmap(cache[key])
        if eyes.size() != base.size():
            eyes = eyes.scaled(base.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        result = QPixmap(base)
        painter = QPainter(result)
        painter.drawPixmap(0, 0, eyes)
        painter.end()
        return result

    @staticmethod
    def _native_eye_endpoint_available(
        assets: ReviewedPoseMotion,
        eye_state: str,
    ) -> bool:
        """Return whether the source retained the authored eye endpoint."""

        if eye_state == "half":
            half_inputs = assets.half_inputs
            return half_inputs is not None and "patch" in half_inputs
        return eye_state in assets.patches

    def _native_eyes_for_state(
        self,
        assets: ReviewedPoseMotion,
        eye_state: str,
        *,
        variant: str | None = None,
    ) -> QPixmap:
        """Build a cached eye-state patch from the matching native endpoint."""

        if eye_state == "half":
            eyes = assets.half_input("patch")
        elif eye_state == "closed":
            eyes = assets.patch("closed")
        else:
            raise ValueError(f"Unsupported native eye state: {eye_state}")
        slots = frozenset({"foundation", "eyes"}).intersection(assets.cosmetic_slots)
        return self._paint_native_cosmetics(
            eyes, assets, eye_state, slots=slots, variant=variant,
        )

    def _closed_native_eyes(
        self,
        view_id: str,
        assets: ReviewedPoseMotion,
        *,
        variant: str | None = None,
    ) -> QPixmap:
        return self._native_eyes_for_state(assets, "closed", variant=variant)
