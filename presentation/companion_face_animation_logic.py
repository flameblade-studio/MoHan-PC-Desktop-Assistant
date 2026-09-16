"""Pure pose decisions shared by the companion face animation surface."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace

lazy from domain.face_rig import FaceMotionFrame, FacePose

__all__ = ("align_speech_motion", "needs_pose_transition")


def needs_pose_transition(
    current_expression: str,
    target_expression: str,
    physics_expression_poses: Mapping[str, str | FacePose],
    fade: bool,
) -> bool:
    """Return whether two authored expressions require a pose crossfade."""

    current_pose = physics_expression_poses.get(current_expression)
    target_pose = physics_expression_poses.get(target_expression)
    return (
        fade
        and current_pose is not None
        and target_pose is not None
        and current_pose != target_pose
    )


def align_speech_motion(
    motion: FaceMotionFrame,
    speech_expression: str,
    physics_expression_poses: Mapping[str, str | FacePose],
    fallback_pose: str | FacePose,
) -> FaceMotionFrame:
    """Pin a motion frame to the speech expression's authored pose canvas.

    Speech mouth layers are cut on their expression's pose canvas, while the
    live motion frame may still carry the previous audio-viseme pose.  Keeping
    both values aligned prevents a stale pose from showing beside the mouth.
    """

    pose_name = physics_expression_poses.get(speech_expression, fallback_pose)
    if motion.pose.value == pose_name and motion.expression == speech_expression:
        return motion
    return replace(
        motion,
        pose=FacePose(pose_name),
        expression=speech_expression,
    )
