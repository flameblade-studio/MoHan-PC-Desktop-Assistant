# PoseAtlas v4 release assets

This directory contains the 24-view PoseAtlas v4 asset set included with MoHan v4.0.0.

The PNG files are normalized native RGBA assets. Body sidecars use alpha-silhouette registration.
Hand sidecars contain only observations produced by the project ONNX hand model after the
fixed augmentations recorded in `BUILD-METADATA.json`. Natural occlusion is represented by
explicit declarations and never by invented landmark coordinates.

Source authorization and public redistribution were confirmed by the rights holder on 2026-08-16.
`audit.json` records the completed reproducible hand and full-body working-asset check. The
v4.0.0 release policy packages these actual assets and their sidecars without requiring a
separate formal promotion audit bundle.
