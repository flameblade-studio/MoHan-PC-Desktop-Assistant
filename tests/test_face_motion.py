from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from domain.face_motion import FaceMotionController
lazy from domain.face_rig import FacePose, Viseme
lazy from domain.lip_sync import VisemeDynamics

SMILE_THRESHOLD = 0.5
BLUSH_THRESHOLD = 0.8


def run() -> None:
    dynamics = VisemeDynamics()
    controller = FaceMotionController()

    frames = [
        controller.advance(
            dynamics.advance(0.8, "A"),
            pose=pose,
            expression="happy",
        )
        for pose in ("front", "lean", "cheek")
    ]
    assert {frame.pose for frame in frames} == {
        FacePose.FRONT,
        FacePose.LEAN,
        FacePose.CHEEK,
    }
    assert all(frame.expression_shape.eye_smile > SMILE_THRESHOLD for frame in frames)
    assert all(frame.mouth.corner_smile == 0.0 for frame in frames)
    assert frames[-1].mouth.aperture > 0.0

    for _ in range(3):
        shy = controller.advance(
            dynamics.advance(0.62, "I"),
            pose="front",
            expression="shy_cute_front",
            blink=1.0,
        )
    assert shy.viseme in {Viseme.I, Viseme.E}
    assert shy.expression_shape.blink == 1.0
    assert shy.expression_shape.blush > BLUSH_THRESHOLD

    closed = controller.close(pose="cheek", expression="happy")
    assert closed.viseme is Viseme.CLOSED
    assert closed.mouth.aperture == 0.0
    assert closed.mouth.corner_smile > SMILE_THRESHOLD
    assert closed.expression_shape.eye_smile > SMILE_THRESHOLD
    print("FACE_MOTION_OK")


if __name__ == "__main__":
    run()
