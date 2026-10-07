"""Typed cached access to character-owned rig and expression data."""

from __future__ import annotations

lazy from domain import character_data_types as _data_types
lazy from domain import character_expression_data as _expression_data
lazy from domain import character_rig_data as _rig_data

# Resolve the public facade once so consumers never receive nested lazy proxies.
DEFAULT_EXPRESSION_CATALOG_PATH = _data_types.DEFAULT_EXPRESSION_CATALOG_PATH
DEFAULT_RIG_MANIFEST_PATH = _data_types.DEFAULT_RIG_MANIFEST_PATH
EXPRESSION_SCHEMA = _data_types.EXPRESSION_SCHEMA
RIG_SCHEMA = _data_types.RIG_SCHEMA
SCHEMA_VERSION = _data_types.SCHEMA_VERSION
ArmSpec = _data_types.ArmSpec
BodyMeasurementsSpec = _data_types.BodyMeasurementsSpec
BodyProportionsSpec = _data_types.BodyProportionsSpec
BrowGuardSpec = _data_types.BrowGuardSpec
CanvasSpec = _data_types.CanvasSpec
CharacterRigManifest = _data_types.CharacterRigManifest
ExpressionRuleSpec = _data_types.ExpressionRuleSpec
ExpressionStateCatalog = _data_types.ExpressionStateCatalog
FaceCalibrationSpec = _data_types.FaceCalibrationSpec
FacePoseAssetSpec = _data_types.FacePoseAssetSpec
FullBodyCalibrationSpec = _data_types.FullBodyCalibrationSpec
PhysicsSpec = _data_types.PhysicsSpec
PoseSpec = _data_types.PoseSpec
SourceBoundExasperatedSpec = _data_types.SourceBoundExasperatedSpec
ViewportSpec = _data_types.ViewportSpec
ViewRingSpec = _data_types.ViewRingSpec
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
