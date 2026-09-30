"""Only the face-safe official profile ornament may replace legacy suppression."""

lazy import pytest

lazy from domain.outfit_pack_official import (
    OFFICIAL_NATIVE_HAIR_ALIAS,
    OFFICIAL_NATIVE_HEADWEAR_ALIAS,
    native_overlay_is_redundant,
)

SAFE_SHA = "db3295c8e3138c4f4653a1470099834a48147fa82c6dc24b603dca2842fe3558"
OLD_SHA = "6be20baf4214cf1eabdf5c33700294901fdc9652843abdd8ede028d09ecdd545"
MIRROR_SHA = "99adbdc74158e7e83311449fa2604b903b96e6e7784142bf74b05ec3e4fe8916"
NEW_ROUND13_16D_SHA = "43491aa8bdbc9da72af123193a0cea4431cd9e1b82a2ddbf088c1e762e6c44a4"


@pytest.mark.parametrize("digest", [None, OLD_SHA, "0" * 64])
def test_unverified_plus090_headwear_remains_suppressed(digest: str | None) -> None:
    assert native_overlay_is_redundant(
        "headwear", OFFICIAL_NATIVE_HEADWEAR_ALIAS, "yaw+090-pitch+00", asset_sha256=digest,
    )


@pytest.mark.parametrize("digest", [SAFE_SHA, MIRROR_SHA, NEW_ROUND13_16D_SHA])
def test_verified_headwear_enters_existing_runtime_asset_checks(digest: str) -> None:
    assert not native_overlay_is_redundant(
        "headwear", OFFICIAL_NATIVE_HEADWEAR_ALIAS, "yaw+090-pitch+00", asset_sha256=digest,
    )


def test_hair_alias_and_other_views_keep_their_behavior() -> None:
    assert native_overlay_is_redundant(
        "hairstyle", OFFICIAL_NATIVE_HAIR_ALIAS, "yaw+090-pitch+00", asset_sha256=SAFE_SHA,
    )
    assert not native_overlay_is_redundant(
        "headwear", OFFICIAL_NATIVE_HEADWEAR_ALIAS, "yaw-090-pitch+00", asset_sha256=OLD_SHA,
    )
