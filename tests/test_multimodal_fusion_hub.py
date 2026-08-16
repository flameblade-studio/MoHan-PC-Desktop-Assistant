from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from air_interaction import AirHandPoint, AirHandSample
lazy from gesture_intent import HandSide
lazy from multimodal_fusion_hub import (
    FaceExpression,
    FaceMeshFrame,
    FaceMeshPoint,
    GazeState,
    MultimodalFusionHub,
    VoiceActivityState,
)


def face(*, smile: bool = True) -> FaceMeshFrame:
    points = [FaceMeshPoint(0.5, 0.5) for _ in range(478)]
    points[1] = FaceMeshPoint(0.5, 0.70 if smile else 0.45)
    points[61] = FaceMeshPoint(0.45, 0.50)
    points[291] = FaceMeshPoint(0.55, 0.50)
    points[152] = FaceMeshPoint(0.5, 0.70)
    points[33] = FaceMeshPoint(0.40, 0.40)
    points[133] = FaceMeshPoint(0.50, 0.40)
    points[263] = FaceMeshPoint(0.50, 0.40)
    points[362] = FaceMeshPoint(0.60, 0.40)
    for index in range(468, 473):
        points[index] = FaceMeshPoint(0.45, 0.40)
    for index in range(473, 478):
        points[index] = FaceMeshPoint(0.55, 0.40)
    return FaceMeshFrame(tuple(points))


def hand(side: HandSide) -> AirHandSample:
    points = [AirHandPoint(0.5, 0.8) for _ in range(21)]
    points[0] = AirHandPoint(0.5, 0.70)
    for mcp, pip, tip, offset in (
        (5, 6, 8, -0.12),
        (9, 10, 12, -0.04),
        (13, 14, 16, 0.04),
        (17, 18, 20, 0.12),
    ):
        points[mcp] = AirHandPoint(0.5 + offset, 0.65)
        points[pip] = AirHandPoint(0.5 + offset, 0.52)
        points[tip] = AirHandPoint(0.5 + offset, 0.30)
    points[2] = AirHandPoint(0.43, 0.70)
    points[4] = AirHandPoint(0.30, 0.58)
    return AirHandSample(side, 0.95, tuple(points))


def assert_hub_fuses_face_voice_audio_and_prompt() -> None:
    hub = MultimodalFusionHub()
    result = hub.process(
        1.0,
        hands=(hand(HandSide.RIGHT),),
        face=face(),
        audio_samples=(0.10, -0.10, 0.10, -0.10),
        user_speech_text="墨寒，今天合作愉快。",
        language="zh-TW",
    )
    assert result.face is not None
    assert result.face.expression is FaceExpression.SMILE_LIKE
    assert result.face.gaze_state is GazeState.SCREEN_LIKE
    assert result.voice.state is VoiceActivityState.ACTIVE
    assert result.lip_sync.mouth_open_y > 0.0
    assert result.live2d_parameters["ParamMouthOpenY"] > 0.0
    assert result.llm_ready_prompt is not None
    assert "user-speech" in result.llm_ready_prompt
    assert "墨寒" in result.llm_ready_prompt


def assert_hub_degrades_without_optional_inputs() -> None:
    hub = MultimodalFusionHub()
    result = hub.process(2.0, user_speech_text="仍然可以正常使用。")
    assert result.face is None
    assert result.voice.state is VoiceActivityState.UNKNOWN
    assert result.air_interaction is None
    assert result.llm_ready_prompt is not None
    assert result.live2d_parameters["ParamMouthOpenY"] == 0.0


def assert_hub_rejects_out_of_order_frames() -> None:
    hub = MultimodalFusionHub()
    hub.process(3.0)
    try:
        hub.process(2.0)
    except ValueError as error:
        assert "time ordered" in str(error)
    else:
        raise AssertionError("multimodal frames must be monotonic")


def run() -> None:
    assert_hub_fuses_face_voice_audio_and_prompt()
    assert_hub_degrades_without_optional_inputs()
    assert_hub_rejects_out_of_order_frames()
    print("MULTIMODAL_FUSION_HUB_OK")


if __name__ == "__main__":
    run()
