from __future__ import annotations

lazy import sys
lazy import hashlib
lazy import io
lazy from dataclasses import replace
lazy from datetime import UTC, datetime
lazy from pathlib import Path
lazy from tempfile import TemporaryDirectory
lazy from urllib.error import HTTPError
lazy from urllib.request import Request

lazy import cv2
lazy import numpy as np
lazy import pytest
lazy from integrations import openai_outfit_generator as outfit_generator_module

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_HALF_VIEWS = 7
EXPECTED_FULL_VIEWS = 24
HTTP_AUTHENTICATION_FAILED = 401
HTTP_RATE_LIMITED = 429
EXPECTED_TRANSIENT_ATTEMPTS = 3
EXPECTED_RECOVERY_CALLS = 2
sys.path.insert(0, str(ROOT))

lazy from application.self_generating_wardrobe import (
    FashionTrendSignal,
    OutfitCreationRequest,
)
lazy from domain.character_framing import FRAMING_RECTS, FramingMode
lazy from domain.outfit_pack import REQUIRED_SILHOUETTES
lazy from integrations.openai_outfit_generator import (
    FULL_SIZE,
    HALF_REQUEST_SIZE,
    HALF_SIZE,
    GeneratedOutfitImageAuditor,
    OpenAIOutfitDraftGenerator,
    OpenAIImageEditTransport,
    OpenAIImageEditOptions,
    OutfitImageGenerationError,
)


def test_http_failure_without_headers_remains_diagnostic() -> None:
    error = HTTPError(
        "https://api.openai.com/v1/images/edits",
        HTTP_AUTHENTICATION_FAILED,
        "unauthorized",
        None,
        None,
    )

    failure = OpenAIImageEditTransport._http_failure(error)

    assert failure.code == "authentication-failed"
    assert failure.http_status == HTTP_AUTHENTICATION_FAILED
    assert failure.request_id == ""


def test_image_transport_does_not_retry_authentication_failure(monkeypatch) -> None:
    calls = []

    def unauthorized(*_args, **_kwargs):
        calls.append(True)
        raise HTTPError(
            "https://api.openai.com/v1/images/edits",
            HTTP_AUTHENTICATION_FAILED,
            "private provider detail",
            {},
            io.BytesIO(b'{"error":{"code":"invalid_api_key"}}'),
        )

    monkeypatch.setattr("urllib.request.urlopen", unauthorized)
    transport = OpenAIImageEditTransport(OpenAIImageEditOptions("secret-key"))

    with pytest.raises(OutfitImageGenerationError) as caught:
        transport._open_with_retry(Request("https://example.test"))

    assert len(calls) == 1
    assert caught.value.public_status == "failed:authentication-failed"
    assert "secret-key" not in str(caught.value)
    assert "private provider detail" not in str(caught.value)


@pytest.mark.parametrize("status", (HTTP_RATE_LIMITED, 500, 503))
def test_image_transport_retries_transient_http_failures_without_leaks(
    status: int,
    monkeypatch,
) -> None:
    calls = []

    def transient(*_args, **_kwargs):
        calls.append(True)
        raise HTTPError(
            "https://api.openai.com/v1/images/edits",
            status,
            "private provider detail",
            {},
            io.BytesIO(b"not-json"),
        )

    monkeypatch.setattr("urllib.request.urlopen", transient)
    monkeypatch.setattr(
        outfit_generator_module,
        "TRANSIENT_RETRY_DELAYS_SECONDS",
        (0.0, 0.0),
    )
    transport = OpenAIImageEditTransport(OpenAIImageEditOptions("secret-key"))

    with pytest.raises(OutfitImageGenerationError) as caught:
        transport._open_with_retry(Request("https://example.test"))

    assert len(calls) == EXPECTED_TRANSIENT_ATTEMPTS
    expected = (
        "rate-limited" if status == HTTP_RATE_LIMITED else "provider-unavailable"
    )
    assert caught.value.public_status == f"failed:{expected}"
    assert "secret-key" not in str(caught.value)
    assert "private provider detail" not in str(caught.value)


def test_image_transport_recovers_after_one_network_disconnect(monkeypatch) -> None:
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            return None

        def read(self, limit: int = -1) -> bytes:
            payload = b'{"ok":true}'
            return payload if limit < 0 else payload[:limit]

    calls = []

    def reconnect(*_args, **_kwargs):
        calls.append(True)
        if len(calls) == 1:
            raise OSError("private network route")
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", reconnect)
    monkeypatch.setattr(
        outfit_generator_module,
        "TRANSIENT_RETRY_DELAYS_SECONDS",
        (0.0, 0.0),
    )
    transport = OpenAIImageEditTransport(OpenAIImageEditOptions("secret-key"))

    payload = transport._open_with_retry(Request("https://example.test"))

    assert payload == b'{"ok":true}'
    assert len(calls) == EXPECTED_RECOVERY_CALLS


class FakeTransport:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[int, int]]] = []

    def edit(
        self,
        _reference_png: bytes,
        prompt: str,
        size: tuple[int, int],
    ) -> bytes:
        self.calls.append((prompt, size))
        width, height = size
        image = np.zeros((height, width, 4), dtype=np.uint8)
        image[height // 2:height // 2 + 40, width // 2 - 60:width // 2 + 60] = (
            120, 80, 40, 255
        )
        ok, encoded = cv2.imencode(".png", image)
        assert ok
        return bytes(encoded)


def _request(job_id: str) -> OutfitCreationRequest:
    return OutfitCreationRequest(
        job_id,
        "zh-TW",
        "indoor",
        25.0,
        "calm",
        "everyday",
        "original blue and silver modern hanfu",
        datetime(2026, 8, 22, tzinfo=UTC),
    )


def test_damaged_generation_checkpoint_regenerates_only_that_view(
    tmp_path: Path,
) -> None:
    transport = FakeTransport()
    generator = OpenAIOutfitDraftGenerator(transport, ROOT, tmp_path)
    checkpoint = tmp_path / "resume-test" / "garment-frontmcrossed.png"
    checkpoint.parent.mkdir(parents=True)
    checkpoint.write_bytes(b"torn checkpoint")

    normalized = generator._checkpointed_edit(
        _request("resume-test"),
        "front-crossed",
        "garment",
        (ROOT / "assets" / "expressions" / "idle_front.png").read_bytes(),
        "test prompt",
        HALF_REQUEST_SIZE,
        HALF_SIZE,
    )

    assert len(transport.calls) == 1
    assert checkpoint.read_bytes() == normalized
    decoded = cv2.imdecode(np.frombuffer(normalized, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    assert decoded.shape == (HALF_SIZE[1], HALF_SIZE[0], 4)


def test_generation_checkpoint_rejects_path_escape(tmp_path: Path) -> None:
    generator = OpenAIOutfitDraftGenerator(FakeTransport(), ROOT, tmp_path)
    try:
        generator._checkpointed_edit(
            _request("../escape"),
            "front-crossed",
            "garment",
            b"not-used",
            "test prompt",
            HALF_REQUEST_SIZE,
            HALF_SIZE,
        )
    except OutfitImageGenerationError as error:
        assert error.code == "invalid-checkpoint-id"
    else:
        raise AssertionError("Path-escaping generation job was accepted.")


def test_validated_trend_provenance_is_retained_without_copying_source(
    tmp_path: Path,
) -> None:
    transport = FakeTransport()
    generator = OpenAIOutfitDraftGenerator(transport, ROOT, tmp_path)
    trend = FashionTrendSignal(
        "https://example.com/current-fashion",
        "Soft layered tailoring",
        ("blue-silver palette", "flowing layered silhouette"),
        "Abstract inspiration only.",
    )

    draft = generator.create(_request("trend-record"), (trend,), ("front-crossed",))

    assert draft.generation_record["trend_sources"] == [
        {
            "source_url": trend.source_url,
            "title": trend.title,
            "license_note": trend.license_note,
            "abstract_traits": list(trend.abstract_traits),
        }
    ]
    prompt = transport.calls[0][0]
    assert trend.source_url not in prompt
    assert trend.title not in prompt
    assert all(trait in prompt for trait in trend.abstract_traits)


def test_generation_record_never_persists_the_private_design_prompt(
    tmp_path: Path,
) -> None:
    generator = OpenAIOutfitDraftGenerator(FakeTransport(), ROOT, tmp_path)
    private = "conversation camera identity location memory API-KEY-secret"
    request = replace(_request("private-record"), creative_direction=private)

    draft = generator.create(request, (), ("front-crossed",))
    record_text = str(dict(draft.generation_record))

    assert private not in record_text
    expected_design = generator._design_prompt(request, ())
    assert draft.generation_record["design_prompt_sha256"] == hashlib.sha256(
        expected_design.encode("utf-8")
    ).hexdigest()


def test_checkpoint_disk_failure_is_diagnostic_and_leaves_no_partial(
    tmp_path: Path,
    monkeypatch,
) -> None:
    generator = OpenAIOutfitDraftGenerator(FakeTransport(), ROOT, tmp_path)
    original_write = Path.write_bytes

    def fail_temporary(path: Path, data: bytes) -> int:
        if path.suffix == ".tmp":
            raise OSError("disk full at private path")
        return original_write(path, data)

    monkeypatch.setattr(Path, "write_bytes", fail_temporary)
    try:
        generator._checkpointed_edit(
            _request("disk-failure"),
            "front-crossed",
            "garment",
            (ROOT / "assets" / "expressions" / "idle_front.png").read_bytes(),
            "prompt",
            HALF_REQUEST_SIZE,
            HALF_SIZE,
        )
    except OutfitImageGenerationError as error:
        assert error.public_status == "failed:checkpoint-write-failed"
        assert "private path" not in error.public_status
    else:
        raise AssertionError("Checkpoint write failure was reported as success.")
    assert not tuple(tmp_path.rglob("*.tmp"))


def run() -> None:
    transport = FakeTransport()
    generator = OpenAIOutfitDraftGenerator(transport, ROOT)
    request = OutfitCreationRequest(
        "provider-test",
        "zh-TW",
        "indoor",
        25.0,
        "calm",
        "everyday",
        "original blue and silver modern hanfu",
        datetime(2026, 8, 22, tzinfo=UTC),
    )
    draft = generator.create(request, (), REQUIRED_SILHOUETTES)
    assert len(transport.calls) == len(REQUIRED_SILHOUETTES)
    assert set(draft.manifest["looks"][0]["variants"][0]["poses"]) == set(
        REQUIRED_SILHOUETTES
    )
    assert draft.generation_record["model"] == "gpt-image-2"
    assert any(size == FULL_SIZE for _prompt, size in transport.calls)
    assert all("OUTPUT ONLY" in prompt for prompt, _size in transport.calls)

    # One coherent outfit must cover all three runtime compositions. HALF has
    # seven authored portrait/gesture silhouettes; FULL_BODY and THREE_QUARTER
    # deliberately share the 24 registered PoseAtlas overlays, with the latter
    # represented by a non-empty crop of those same full-body canvases.
    half_views = tuple(
        view for view in REQUIRED_SILHOUETTES if not view.startswith("yaw")
    )
    full_views = tuple(
        view for view in REQUIRED_SILHOUETTES if view.startswith("yaw")
    )
    assert len(half_views) == EXPECTED_HALF_VIEWS
    assert len(full_views) == EXPECTED_FULL_VIEWS
    three_quarter = FRAMING_RECTS[FramingMode.THREE_QUARTER]
    assert 0.0 <= three_quarter.left < three_quarter.right <= 1.0
    assert 0.0 <= three_quarter.top < three_quarter.bottom <= 1.0
    assert set(full_views).issubset(
        draft.manifest["looks"][0]["variants"][0]["poses"]
    )

    # Exercise the production auditor against the exact quarantine layout.
    with TemporaryDirectory() as temporary:
        job = Path(temporary)
        for path, data in draft.assets.items():
            destination = job / "source" / Path(*path.split("/"))
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
        assert GeneratedOutfitImageAuditor().audit(job, draft.manifest) == ()

    rainy_transport = FakeTransport()
    rainy_generator = OpenAIOutfitDraftGenerator(rainy_transport, ROOT)
    rainy_request = OutfitCreationRequest(
        "rain-provider-test",
        "zh-TW",
        "rain",
        20.0,
        "calm",
        "everyday",
        "original blue and silver rain-ready hanfu",
        datetime(2026, 8, 22, tzinfo=UTC),
        requested_categories=frozenset({"garment", "handheld"}),
        accessory_direction="original ink-wash oil-paper umbrella",
    )
    rainy_draft = rainy_generator.create(rainy_request, (), REQUIRED_SILHOUETTES)
    assert len(rainy_transport.calls) == 2 * len(REQUIRED_SILHOUETTES)
    accessory = rainy_draft.manifest["accessories"][0]
    assert accessory["accessory_kind"] == "handheld"
    assert set(accessory["variants"][0]["poses"]) == set(REQUIRED_SILHOUETTES)
    assert rainy_draft.manifest["ensembles"][0]["selections"]["handheld"]
    print("OPENAI_OUTFIT_GENERATOR_OK")


if __name__ == "__main__":
    run()
