from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from cloud_scene_interpreter import CloudSceneInterpretation, SceneFactKind
lazy from cloud_vision_runtime import (
    CloudVisionResult,
    CloudVisionStatus,
)
lazy from cloud_vision_ui_bridge import (
    CloudLocalSceneIntegrator,
    CloudVisionUIResult,
    _safe_ui_result,
)
lazy from integrations.openai_vision_provider import (
    ClaimStatus,
    VisualClaim,
    VisualUnderstanding,
)
lazy from vision_domain import (
    IdentityObservation,
    IdentityState,
    SceneUnderstanding,
)


def cloud_result(operation_id: int = 7) -> CloudVisionResult:
    understanding = VisualUnderstanding(
        "A person may be reading beside a laptop.",
        (
            VisualClaim(
                "A person is visible.",
                ClaimStatus.OBSERVED,
                0.97,
                "Visible pixels show a person.",
            ),
            VisualClaim(
                "The person may be reading a book.",
                ClaimStatus.INFERRED,
                0.91,
                "A book-like object is visible.",
            ),
            VisualClaim(
                "The person is named Alice.",
                ClaimStatus.OBSERVED,
                0.99,
                "A possible name is visible.",
            ),
            VisualClaim(
                "A cup might be present.",
                ClaimStatus.UNCERTAIN,
                0.99,
                "The shape is unclear.",
            ),
        ),
        (),
    )
    return CloudVisionResult(
        operation_id,
        CloudVisionStatus.SUCCESS,
        1,
        understanding,
    )


def assert_ui_result_is_typed_and_suppresses_unsafe_claims() -> None:
    safe = _safe_ui_result(cloud_result())
    assert isinstance(safe.interpretation, CloudSceneInterpretation)
    assert safe.interpretation.operation_id == 7
    assert all(
        fact.kind is not SceneFactKind.PERSON
        for fact in safe.interpretation.facts
    )
    assert "Alice" not in repr(safe)
    assert "cup" not in repr(safe)
    assert not hasattr(safe, "speak")
    assert not hasattr(safe, "execute")


def assert_merge_preserves_local_identity_time_and_rejects_stale_results() -> None:
    owner = IdentityObservation(
        IdentityState.RECOGNIZED,
        "owner",
        "Owner",
        0.98,
    )
    local = SceneUnderstanding(owner, (), ("at_computer",), ())
    integrator = CloudLocalSceneIntegrator()
    integrator.observe_local(local, observed_at=1234.5)
    safe = _safe_ui_result(cloud_result())
    merged = integrator.merge_cloud(safe)
    assert merged is not None
    assert merged.scene.identity is owner
    assert merged.observed_at == 1234.5
    assert merged.scene.activities == ("at_computer", "possible_reading")
    assert integrator.merge_cloud(safe) is None
    assert integrator.merge_cloud(
        CloudVisionUIResult(CloudVisionStatus.STALE)
    ) is None
    assert integrator.merge_cloud(
        CloudVisionUIResult(CloudVisionStatus.CANCELLED)
    ) is None
    assert integrator.merge_cloud(
        CloudVisionUIResult(CloudVisionStatus.NETWORK_UNAVAILABLE)
    ) is None


def assert_missing_local_scene_and_non_monotonic_time_fail_closed() -> None:
    integrator = CloudLocalSceneIntegrator()
    assert integrator.merge_cloud(_safe_ui_result(cloud_result())) is None
    local = SceneUnderstanding(IdentityObservation(IdentityState.NO_FACE), (), (), ())
    integrator.observe_local(local, observed_at=20.0)
    try:
        integrator.observe_local(local, observed_at=19.0)
    except ValueError as error:
        assert "monotonic" in str(error)
    else:
        raise AssertionError("non-monotonic local evidence must be rejected")
    integrator.reset()
    assert integrator.merge_cloud(_safe_ui_result(cloud_result(8))) is None


def run() -> None:
    assert_ui_result_is_typed_and_suppresses_unsafe_claims()
    assert_merge_preserves_local_identity_time_and_rejects_stale_results()
    assert_missing_local_scene_and_non_monotonic_time_fail_closed()
    print("CLOUD_LOCAL_SCENE_INTEGRATION_OK")


if __name__ == "__main__":
    run()
