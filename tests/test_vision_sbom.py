from __future__ import annotations

lazy import sys
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy from tools.validate_release_sboms import (
    _add_and_validate_assets,
    _asset_component,
    _profile_assets,
    load_asset_policies,
    load_policies,
    validate_asset_package_manifest,
)

COMMIT_HASH_LENGTH = 40
EXPECTED_VARIANT_COUNT = 2
EXPECTED_MODEL_REVISIONS = {
    "assets/vision-models/face_detection_yunet_2023mar.onnx": (
        "f12e12798e8314f7c074a6656816c048dcc95b7a"
    ),
    "assets/vision-models/face_recognition_sface_2021dec.onnx": (
        "ba91a3b91d00d76e86540d4013f944bd6b514e39"
    ),
    "assets/vision-models/object_detection_nanodet_2022nov.onnx": (
        "510899a2a0adb8c25957915fd030d66dbd553919"
    ),
    "assets/vision-models/palm_detection_mediapipe_2023feb.onnx": (
        "8de36535ea29e8f9d41e6e3fa5a0df14bab00ec5"
    ),
    "assets/vision-models/handpose_estimation_mediapipe_2023feb.onnx": (
        "56cef36ae45e5a6da7eba01a91631f6d7e955da1"
    ),
}

EXPECTED_BUNDLED_MODEL_REVISIONS = {
    "assets/vision-models/face_landmark_468.tflite": "face_landmark.tflite",
    "assets/vision-models/iris_landmark.tflite": "iris_landmark.tflite",
    "assets/vision-models/silero_vad_v4.0.onnx": "v4.0",
}

EXPECTED_FONT_ASSETS = {
    "assets/fonts/LXGW-WenKai-TC/LXGWWenKaiTC-Regular.ttf": {
        "version": "1.522",
        "size_bytes": 15_267_616,
        "sha256": "b1a0795862c1415bf3f393ea50b2a4ea6275012cf5bad3f94feeb1222f555731",
        "source_revision": "v1.522",
        "license": "SIL OFL 1.1",
    },
    "assets/fonts/Cinzel/Cinzel[wght].ttf": {
        "version": "2.000",
        "size_bytes": 125_468,
        "sha256": "f4d83d34d1f6c741193e4acf4b3dff9531e5a67b6aa65228d00a7db72a4e0f34",
        "source_revision": "45071f07c63e863a539442ef3562b71ab1f147a6",
        "license": "SIL OFL 1.1",
    },
}


def assert_runtime_dependencies_are_governed() -> None:
    policies = load_policies(ROOT / "sbom" / "components.toml")
    windows = {policy.normalized_name: policy for policy in policies if "windows" in policy.profiles}
    expected = {
        "cryptography": ("50.0.0", "Apache-2.0 OR BSD-3-Clause"),
        "numpy": ("2.5.2", "BSD-3-Clause"),
        "opencv-python": ("5.0.0.93", "Apache-2.0"),
    }
    for name, (version, license_expression) in expected.items():
        assert windows[name].version == version
        assert windows[name].license_expression == license_expression


def assert_models_are_machine_verifiable() -> None:
    assets = load_asset_policies(ROOT / "sbom" / "components.toml")
    windows = tuple(
        asset
        for asset in _profile_assets(assets, "windows")
        if asset.component_type == "machine-learning-model"
    )
    by_path = {asset.path.as_posix(): asset for asset in windows}
    expected_revisions = {
        **EXPECTED_MODEL_REVISIONS,
        **EXPECTED_BUNDLED_MODEL_REVISIONS,
    }
    assert set(by_path) == set(expected_revisions)
    assert all(asset.component_type == "machine-learning-model" for asset in windows)
    for path, expected_revision in expected_revisions.items():
        asset = by_path[path]
        assert asset.source_revision == expected_revision
        if path.endswith(".onnx") and path not in {
            "assets/vision-models/silero_vad_v4.0.onnx",
        }:
            assert len(expected_revision) == COMMIT_HASH_LENGTH
        assert expected_revision in asset.source
    assert {asset.license_expression for asset in windows} == {"MIT", "Apache-2.0"}
    bom: dict[str, object] = {"components": [], "dependencies": []}
    references = _add_and_validate_assets(bom, windows)
    assert len(references) == len(expected_revisions)
    components = bom["components"]
    assert isinstance(components, list)
    assert len(components) == len(expected_revisions)
    for asset, component in zip(windows, components, strict=True):
        assert component == _asset_component(asset)
        assert component["hashes"] == [{"alg": "SHA-256", "content": asset.sha256}]
        assert component["externalReferences"] == [
            {"type": "distribution", "url": asset.source}
        ]
    build_script = (ROOT / "build.ps1").read_text(encoding="utf-8")
    assert '--add-data "assets;assets"' in build_script
    assert '--add-data "THIRD_PARTY_NOTICES.md;."' in build_script


def test_bundled_fonts_are_governed_in_windows_and_preview_sboms() -> None:
    assets = load_asset_policies(ROOT / "sbom" / "components.toml")
    expected_paths = set(EXPECTED_FONT_ASSETS)
    for profile in ("windows", "preview"):
        selected = _profile_assets(assets, profile)
        by_path = {asset.path.as_posix(): asset for asset in selected}
        assert expected_paths <= set(by_path)
        font_assets = tuple(by_path[path] for path in sorted(expected_paths))
        for asset in font_assets:
            expected = EXPECTED_FONT_ASSETS[asset.path.as_posix()]
            local = ROOT / asset.path
            assert asset.component_type == "file"
            assert asset.version == expected["version"]
            assert asset.size_bytes == expected["size_bytes"]
            assert asset.sha256 == expected["sha256"]
            assert asset.source_revision == expected["source_revision"]
            assert asset.license_expression == expected["license"]
            assert local.stat().st_size == asset.size_bytes
            assert asset.source_revision in asset.source
        bom: dict[str, object] = {"components": [], "dependencies": []}
        references = _add_and_validate_assets(bom, font_assets)
        assert len(references) == len(expected_paths)
        components = bom["components"]
        assert isinstance(components, list)
        assert components == [_asset_component(asset) for asset in font_assets]


def assert_hash_drift_fails_closed() -> None:
    assets = load_asset_policies(ROOT / "sbom" / "components.toml")
    with TemporaryDirectory() as raw:
        package_root = Path(raw)
        asset = assets[0]
        path = package_root / asset.path
        path.parent.mkdir(parents=True)
        path.write_bytes(b"tampered-model")
        try:
            _add_and_validate_assets(
                {"components": [], "dependencies": []},
                (asset,),
                package_root=package_root,
            )
        except ValueError as exc:
            assert "hash drifted" in str(exc)
        else:
            raise AssertionError("tampered model must fail SBOM validation")


def assert_pack_manifest_contract_rejects_unknown_provenance() -> None:
    manifest = """\
schema = 1

[[asset]]
name = "Example outfit texture"
version = "1.0.0"
type = "file"
path = "assets/outfits/example.png"
sha256 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
source = "https://example.invalid/example.png"
source_revision = "unknown"
license = "CC-BY-4.0"
profiles = ["windows"]
"""
    # Future theme/outfit package manifests use the same asset schema. Missing
    # source or license fields must never be accepted as release inventory.
    for field in ("source", "license", "sha256", "path", "version"):
        damaged = manifest.replace(f'{field} = ', f'ignored_{field} = ', 1)
        with TemporaryDirectory() as raw:
            policy = Path(raw) / "components.toml"
            policy.write_text(damaged, encoding="utf-8")
            try:
                load_asset_policies(policy)
            except ValueError:
                pass
            else:
                raise AssertionError(f"asset manifest without {field} must fail")


def outfit_manifest(*, role: str = "garment") -> str:
    return f'''\
schema = 1

[package]
id = "example-summer-pack"
version = "1.0.0"
provenance = "original-derivative-design"
reference_policy = "design-reference-only"

[core_body_skin]
id = "mohan-core-body-skin-v1"
sha256 = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"

[[variant]]
id = "swimsuit-blue"

[[variant]]
id = "swimsuit-red"

[[reference]]
id = "real-garment-photo"
source = "https://example.invalid/reference.jpg"
license = "LicenseRef-Reference-Only"
policy = "design-reference-only"
redistributable = false
packaged = false

[[asset]]
name = "Original summer garment"
role = "{role}"
sha256 = "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
license = "LicenseRef-Flameblade-Original"
provenance = "original-derivative-design"
redistributable = true
variants = ["swimsuit-blue", "swimsuit-red"]
references = ["real-garment-photo"]

[[asset]]
name = "Shoulder visibility mask"
role = "occlusion"
sha256 = "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
license = "LicenseRef-Flameblade-Original"
provenance = "original-derivative-design"
redistributable = true
variants = ["swimsuit-blue", "swimsuit-red"]
references = []
'''


def assert_outfit_pack_identity_and_reference_boundaries() -> None:
    approved_core = {
        "mohan-core-body-skin-v1": "b" * 64,
    }
    with TemporaryDirectory() as raw:
        manifest = Path(raw) / "package.toml"
        manifest.write_text(outfit_manifest(), encoding="utf-8")
        report = validate_asset_package_manifest(
            manifest,
            official_core_body_skin=approved_core,
        )
        assert report["variant_count"] == EXPECTED_VARIANT_COUNT
        assert report["asset_count"] == EXPECTED_VARIANT_COUNT
        assert report["reference_count"] == 1
        assert report["core_body_skin"] == {
            "id": "mohan-core-body-skin-v1",
            "sha256": "b" * 64,
        }
        for role in ("identity", "face", "skin-tone", "body-shape", "core-body-skin"):
            manifest.write_text(outfit_manifest(role=role), encoding="utf-8")
            try:
                validate_asset_package_manifest(
                    manifest,
                    official_core_body_skin=approved_core,
                )
            except ValueError as exc:
                assert "forbidden" in str(exc)
            else:
                raise AssertionError(f"outfit pack must not provide {role}")
        for forbidden in (
            "redistributable = false",
            "packaged = true",
        ):
            damaged = outfit_manifest().replace(forbidden, forbidden.replace("false", "true") if "false" in forbidden else forbidden)
            if forbidden == "packaged = true":
                damaged = outfit_manifest().replace("packaged = false", "packaged = true")
            manifest.write_text(damaged, encoding="utf-8")
            try:
                validate_asset_package_manifest(
                    manifest,
                    official_core_body_skin=approved_core,
                )
            except ValueError:
                pass
            else:
                raise AssertionError("real garment reference must not be packaged or redistributed")
        manifest.write_text(outfit_manifest(), encoding="utf-8")
        try:
            validate_asset_package_manifest(
                manifest,
                official_core_body_skin={"mohan-core-body-skin-v1": "e" * 64},
            )
        except ValueError as exc:
            assert "approved core_body_skin" in str(exc)
        else:
            raise AssertionError("outfit pack must not replace official body skin")


def run() -> None:
    assert_runtime_dependencies_are_governed()
    assert_models_are_machine_verifiable()
    test_bundled_fonts_are_governed_in_windows_and_preview_sboms()
    assert_hash_drift_fails_closed()
    assert_pack_manifest_contract_rejects_unknown_provenance()
    assert_outfit_pack_identity_and_reference_boundaries()
    print("VISION_SBOM_OK")


if __name__ == "__main__":
    run()
