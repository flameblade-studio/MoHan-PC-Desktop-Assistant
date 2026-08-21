from __future__ import annotations

lazy import sys
lazy from math import isclose
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from visual_social_cues import (
    FacialCueMeasurements,
    GazeHeadDirection,
    ObservableFacialCue,
    observe_social_cues,
)

EXPECTED_CONFIDENCE = 0.91
EXPECTED_AMBIGUOUS_CONFIDENCE = 0.49


def assert_only_observable_candidates_are_exposed() -> None:
    observation = observe_social_cues(
        FacialCueMeasurements(
            smile_like=0.91,
            eyes_closed_like=0.72,
            brow_tension_like=0.31,
            fatigue_candidate=0.69,
            screen_alignment=0.88,
        )
    )
    assert observation.facial_cues == (
        ObservableFacialCue.SMILE_LIKE,
        ObservableFacialCue.EYES_CLOSED_LIKE,
        ObservableFacialCue.FATIGUE_CANDIDATE,
    )
    assert observation.gaze_head_direction is GazeHeadDirection.SCREEN_LIKE
    assert observation.confidence == EXPECTED_CONFIDENCE
    assert isclose(observation.uncertainty, 0.09)


def assert_ambiguous_and_missing_evidence_remain_unknown() -> None:
    ambiguous = observe_social_cues(
        FacialCueMeasurements(smile_like=0.6, screen_alignment=0.5)
    )
    assert ambiguous.facial_cues == (ObservableFacialCue.UNKNOWN,)
    assert ambiguous.gaze_head_direction is GazeHeadDirection.UNKNOWN
    assert ambiguous.confidence == EXPECTED_AMBIGUOUS_CONFIDENCE
    absent = observe_social_cues(FacialCueMeasurements())
    assert absent.facial_cues == (ObservableFacialCue.UNKNOWN,)
    assert absent.confidence == 0.0
    assert absent.uncertainty == 1.0


def assert_direction_is_descriptive_not_mental_state() -> None:
    away = observe_social_cues(FacialCueMeasurements(screen_alignment=0.1))
    assert away.gaze_head_direction is GazeHeadDirection.AWAY
    exported = {cue.value for cue in ObservableFacialCue}
    assert exported == {
        "smile-like",
        "eyes-closed-like",
        "brow-tension-like",
        "fatigue-candidate",
        "unknown",
    }


def assert_invalid_measurements_are_rejected() -> None:
    for invalid in (-0.1, 1.1, float("nan")):
        try:
            FacialCueMeasurements(smile_like=invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid visual evidence must not be accepted.")


def run() -> None:
    assert_only_observable_candidates_are_exposed()
    assert_ambiguous_and_missing_evidence_remain_unknown()
    assert_direction_is_descriptive_not_mental_state()
    assert_invalid_measurements_are_rejected()
    print("VISUAL_SOCIAL_CUES_OK")


if __name__ == "__main__":
    run()
