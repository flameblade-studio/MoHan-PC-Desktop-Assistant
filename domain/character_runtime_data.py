"""Typed cached access to character-owned rig and expression data."""

from __future__ import annotations

lazy from domain import character_expression_data as _expression_data
lazy from domain import character_rig_data as _rig_data
lazy from domain.character_pack import character_data_models as _data_models
lazy from domain import character_default_paths as _default_paths

# Resolve the public facade once so consumers never receive nested lazy proxies.
DEFAULT_EXPRESSION_CATALOG_PATH = _default_paths.DEFAULT_EXPRESSION_CATALOG_PATH
DEFAULT_RIG_MANIFEST_PATH = _default_paths.DEFAULT_RIG_MANIFEST_PATH
EXPRESSION_SCHEMA = _data_models.EXPRESSION_SCHEMA
RIG_SCHEMA = _data_models.RIG_SCHEMA
SCHEMA_VERSION = _data_models.SCHEMA_VERSION
ArmSpec = _data_models.ArmSpec
BodyMeasurementsSpec = _data_models.BodyMeasurementsSpec
BodyProportionsSpec = _data_models.BodyProportionsSpec
BrowGuardSpec = _data_models.BrowGuardSpec
CanvasSpec = _data_models.CanvasSpec
CharacterRigManifest = _data_models.CharacterRigManifest
ExpressionRuleSpec = _data_models.ExpressionRuleSpec
ExpressionStateCatalog = _data_models.ExpressionStateCatalog
FaceCalibrationSpec = _data_models.FaceCalibrationSpec
FacePoseAssetSpec = _data_models.FacePoseAssetSpec
FullBodyCalibrationSpec = _data_models.FullBodyCalibrationSpec
PhysicsSpec = _data_models.PhysicsSpec
PoseSpec = _data_models.PoseSpec
SourceBoundExasperatedSpec = _data_models.SourceBoundExasperatedSpec
ViewportSpec = _data_models.ViewportSpec
ViewRingSpec = _data_models.ViewRingSpec
default_expression_catalog = _expression_data.default_expression_catalog
load_expression_catalog = _expression_data.load_expression_catalog
default_rig_manifest = _rig_data.default_rig_manifest
load_rig_manifest = _rig_data.load_rig_manifest

__all__ = (
    "DEFAULT_EXPRESSION_CATALOG_PATH",
    "DEFAULT_RIG_MANIFEST_PATH",
    "EXPRESSION_SCHEMA",
    "RIG_SCHEMA",
    "SCHEMA_VERSION",
    "ArmSpec",
    "BodyMeasurementsSpec",
    "BodyProportionsSpec",
    "BrowGuardSpec",
    "CanvasSpec",
    "CharacterRigManifest",
    "ExpressionRuleSpec",
    "ExpressionStateCatalog",
    "FaceCalibrationSpec",
    "FacePoseAssetSpec",
    "FullBodyCalibrationSpec",
    "PhysicsSpec",
    "PoseSpec",
    "SourceBoundExasperatedSpec",
    "ViewRingSpec",
    "ViewportSpec",
    "default_expression_catalog",
    "default_rig_manifest",
    "load_expression_catalog",
    "load_rig_manifest",
)
