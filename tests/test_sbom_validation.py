from __future__ import annotations

lazy import json
lazy import sys
lazy import tempfile
lazy from collections.abc import Callable
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy from tools.validate_release_sboms import (
    ComponentPolicy,
    SbomEntry,
    _finalize_dependency_graph,
    _license_values,
    _pinned_requirements,
    _privacy_content_gate,
    _privacy_gate,
    _profile_policies,
    _project_metadata,
    _release_version,
    _validate_components,
    load_policies,
)
lazy from version_info import FALLBACK_VERSION

CURRENT_TAG = f"v{FALLBACK_VERSION}"
CURRENT_PACKAGE_VERSION = _release_version(CURRENT_TAG)


def expect_value_error(operation: Callable[[], object]) -> str:
    try:
        operation()
    except ValueError as error:
        return str(error)
    raise AssertionError("operation unexpectedly succeeded")


def runtime_policy(
    name: str = "example-package",
    version: str = "1.2.3",
) -> ComponentPolicy:
    return ComponentPolicy(
        name=name,
        version=version,
        license_expression="MIT",
        scope="runtime",
        profiles=("windows",),
    )


def test_release_version_and_repository_policy_are_synchronized() -> None:
    assert _release_version("v9.8.7-rc.6") == "9.8.7rc6"
    assert _release_version("v9.8.7") == "9.8.7"
    for invalid in ("9.8.7-rc.6", "v9.8", "v9.8.7-rc.0"):
        message = expect_value_error(lambda value=invalid: _release_version(value))
        assert "vN.N.N or vN.N.N-rc.N" in message

    policies = load_policies(ROOT / "sbom" / "components.toml")
    windows = _profile_policies(policies, "windows")
    preview = _profile_policies(policies, "preview")
    assert _pinned_requirements(ROOT / "requirements-runtime.txt") == {
        policy.normalized_name: policy.version for policy in windows
    }
    assert _pinned_requirements(ROOT / "requirements-preview-runtime.txt") == {
        policy.normalized_name: policy.version for policy in preview
    }
    assert {policy.name for policy in policies if policy.scope == "build"} == {
        "PyInstaller"
    }

    _project_metadata(
        SbomEntry(
            profile="windows",
            path=ROOT / "unused.cdx.json",
            requirements=ROOT / "requirements-runtime.txt",
            pyproject=ROOT / "pyproject.toml",
            root_name="mohan-desktop-assistant",
        ),
        CURRENT_PACKAGE_VERSION,
        windows,
    )
    _project_metadata(
        SbomEntry(
            profile="preview",
            path=ROOT / "unused.cdx.json",
            requirements=ROOT / "requirements-preview-runtime.txt",
            pyproject=ROOT / "sbom" / "preview.pyproject.toml",
            root_name="mohan-desktop-assistant-preview",
        ),
        CURRENT_PACKAGE_VERSION,
        preview,
    )


def test_component_license_and_dependency_graph_are_complete() -> None:
    policy = runtime_policy()
    component: dict[str, object] = {
        "type": "library",
        "name": policy.name,
        "version": policy.version,
        "bom-ref": policy.purl,
        "purl": policy.purl,
    }
    references = _validate_components(
        {policy.normalized_name: component},
        (policy,),
    )
    assert references == {policy.normalized_name: policy.purl}
    assert _license_values(component) == ("MIT",)

    bom: dict[str, object] = {
        "dependencies": [
            {"ref": "application-root", "dependsOn": []},
            {"ref": policy.purl, "dependsOn": []},
        ]
    }
    _finalize_dependency_graph(bom, "application-root", {policy.purl})
    assert bom["dependencies"] == [
        {"ref": "application-root", "dependsOn": [policy.purl]},
        {"ref": policy.purl, "dependsOn": []},
    ]

    incomplete: dict[str, object] = {
        "dependencies": [{"ref": "application-root", "dependsOn": []}]
    }
    message = expect_value_error(
        lambda: _finalize_dependency_graph(
            incomplete,
            "application-root",
            {policy.purl},
        )
    )
    assert "node set is incomplete" in message


def test_privacy_gate_rejects_paths_and_secret_like_values() -> None:
    with tempfile.TemporaryDirectory(prefix="mohan-sbom-test-") as raw:
        path = Path(raw) / "inventory.json"
        path.write_text(
            json.dumps({"component": "safe", "version": "1.0"}),
            encoding="utf-8",
        )
        _privacy_gate(path)

        path.write_text('{"path":"C:/Users/private/file.txt"}', encoding="utf-8")
        assert "Windows absolute path" in expect_value_error(
            lambda: _privacy_gate(path)
        )

        secret_field = "api" + "_key"
        privacy_payload = json.dumps({secret_field: "a" * 8 + "1" * 6})
        assert "secret-like value" in expect_value_error(
            lambda: _privacy_content_gate(
                privacy_payload,
                "in-memory test fixture",
            )
        )


def main() -> None:
    test_release_version_and_repository_policy_are_synchronized()
    test_component_license_and_dependency_graph_are_complete()
    test_privacy_gate_rejects_paths_and_secret_like_values()
    print("CYCLONEDX_RELEASE_SBOM_GOVERNANCE_OK")


if __name__ == "__main__":
    main()
