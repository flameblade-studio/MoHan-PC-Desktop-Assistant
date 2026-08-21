from __future__ import annotations

lazy import logging
lazy from collections.abc import Callable
lazy from types import ModuleType

lazy import pytest

lazy from application.native_acceleration import NativeAcceleration
lazy from domain import lip_sync, pcm_audio

NATIVE_OPERATION_COUNT = 5


def _pcm(*samples: int) -> bytes:
    return b"".join(sample.to_bytes(2, "little", signed=True) for sample in samples)


def _native_rate_conversion(
    data: bytes,
    channels: int,
    input_rate: int,
    output_rate: int,
    state: tuple[tuple[int, ...], int] | None,
) -> tuple[bytes, tuple[tuple[int, ...], int] | None]:
    python_state = (
        None if state is None else pcm_audio.Pcm16RateState(state[0], state[1])
    )
    converted, next_state = pcm_audio.rate_convert_pcm16(
        data,
        channels,
        input_rate,
        output_rate,
        python_state,
    )
    native_state = (
        None
        if next_state is None
        else (next_state.tail_frame, next_state.phase)
    )
    return converted, native_state


def _reference_native_module() -> ModuleType:
    module = ModuleType("_mohan_accel")
    module.__version__ = "test"
    module.analyze_pcm16 = lip_sync.analyze_pcm16
    module.infer_vowel_pcm16 = lip_sync.infer_vowel_pcm16
    module.scale_pcm16 = pcm_audio.scale_pcm16
    module.stereo_to_mono_pcm16 = pcm_audio.stereo_to_mono_pcm16
    module.rate_convert_pcm16 = _native_rate_conversion
    return module


def _assert_same_contract_error(
    reference: Callable[[], object],
    accelerated: Callable[[], object],
) -> None:
    with pytest.raises(Exception) as reference_error:
        reference()
    with pytest.raises(type(reference_error.value)) as accelerated_error:
        accelerated()
    assert str(accelerated_error.value) == str(reference_error.value)


def test_missing_native_module_falls_back_and_reports_once() -> None:
    attempts: list[str] = []

    def missing(name: str) -> ModuleType:
        attempts.append(name)
        raise ModuleNotFoundError(name)

    accelerator = NativeAcceleration(module_loader=missing)
    mono = _pcm(-3_000, 0, 3_000, 0)
    stereo = _pcm(-3_000, 3_000, 1_000, -1_000)
    assert accelerator.analyze_pcm16(mono) == lip_sync.analyze_pcm16(mono)
    assert accelerator.infer_vowel_pcm16(mono) == lip_sync.infer_vowel_pcm16(mono)
    assert accelerator.scale_pcm16(mono, 0.5) == pcm_audio.scale_pcm16(
        mono,
        0.5,
    )
    assert accelerator.stereo_to_mono_pcm16(stereo) == (
        pcm_audio.stereo_to_mono_pcm16(stereo)
    )
    assert accelerator.rate_convert_pcm16(mono, 1, 24_000, 48_000) == (
        pcm_audio.rate_convert_pcm16(mono, 1, 24_000, 48_000)
    )
    status = accelerator.status()
    assert attempts == ["_mohan_accel"]
    assert not status.available
    assert status.load_error is not None
    assert "ModuleNotFoundError" in status.load_error


def test_each_native_operation_is_used_when_available() -> None:
    module = _reference_native_module()
    accelerator = NativeAcceleration(module_loader=lambda _name: module)

    mono = _pcm(-3_000, 0, 3_000, 0)
    stereo = _pcm(-3_000, 3_000, 1_000, -1_000)
    assert accelerator.analyze_pcm16(mono) == lip_sync.analyze_pcm16(mono)
    assert accelerator.infer_vowel_pcm16(mono) == lip_sync.infer_vowel_pcm16(mono)
    assert accelerator.scale_pcm16(mono, 0.5) == pcm_audio.scale_pcm16(mono, 0.5)
    assert accelerator.stereo_to_mono_pcm16(stereo) == (
        pcm_audio.stereo_to_mono_pcm16(stereo)
    )
    converted, state = accelerator.rate_convert_pcm16(mono, 1, 24_000, 48_000)
    assert (converted, state) == pcm_audio.rate_convert_pcm16(
        mono,
        1,
        24_000,
        48_000,
    )
    assert accelerator.status().available
    assert accelerator.status().verified_operations == (
        "analyze_pcm16",
        "infer_vowel_pcm16",
        "rate_convert_pcm16",
        "scale_pcm16",
        "stereo_to_mono_pcm16",
    )
    assert accelerator.status().operation_failures == ()


def test_verified_operations_prevalidate_every_request_against_python_contract(
    monkeypatch,
) -> None:
    module = _reference_native_module()
    accelerator = NativeAcceleration(module_loader=lambda _name: module)
    mono = _pcm(-3_000, 0, 3_000, 0)
    stereo = _pcm(-3_000, 3_000, 1_000, -1_000)
    accelerator.analyze_pcm16(mono)
    accelerator.infer_vowel_pcm16(mono)
    accelerator.scale_pcm16(mono, 0.5)
    accelerator.stereo_to_mono_pcm16(stereo)
    accelerator.rate_convert_pcm16(mono, 1, 24_000, 48_000)

    calls = dict.fromkeys(
        (
            "analyze_pcm16",
            "infer_vowel_pcm16",
            "scale_pcm16",
            "stereo_to_mono_pcm16",
            "rate_convert_pcm16",
        ),
        0,
    )

    def accept_analysis(*_arguments: object) -> tuple[float, float]:
        calls["analyze_pcm16"] += 1
        return 0.0, 0.0

    def accept_vowel(*_arguments: object) -> tuple[float, str]:
        calls["infer_vowel_pcm16"] += 1
        return 0.0, "CLOSED"

    def accept_scale(*_arguments: object) -> bytes:
        calls["scale_pcm16"] += 1
        return b""

    def accept_stereo(*_arguments: object) -> bytes:
        calls["stereo_to_mono_pcm16"] += 1
        return b""

    def accept_rate(*_arguments: object) -> tuple[bytes, None]:
        calls["rate_convert_pcm16"] += 1
        return b"", None

    module.analyze_pcm16 = accept_analysis
    module.infer_vowel_pcm16 = accept_vowel
    module.scale_pcm16 = accept_scale
    module.stereo_to_mono_pcm16 = accept_stereo
    module.rate_convert_pcm16 = accept_rate

    _assert_same_contract_error(
        lambda: lip_sync.analyze_pcm16("not-pcm"),
        lambda: accelerator.analyze_pcm16("not-pcm"),
    )
    with monkeypatch.context() as size_limit:
        size_limit.setattr(lip_sync, "MAX_EXACT_PCM16_ANALYSIS_SAMPLES", 1)
        oversized = _pcm(0, 1)
        _assert_same_contract_error(
            lambda: lip_sync.analyze_pcm16(oversized),
            lambda: accelerator.analyze_pcm16(oversized),
        )
    _assert_same_contract_error(
        lambda: lip_sync.infer_vowel_pcm16(mono, 0),
        lambda: accelerator.infer_vowel_pcm16(mono, 0),
    )
    _assert_same_contract_error(
        lambda: lip_sync.infer_vowel_pcm16(mono, 1 << 63),
        lambda: accelerator.infer_vowel_pcm16(mono, 1 << 63),
    )
    _assert_same_contract_error(
        lambda: pcm_audio.scale_pcm16(b"\x00", 0.5),
        lambda: accelerator.scale_pcm16(b"\x00", 0.5),
    )
    _assert_same_contract_error(
        lambda: pcm_audio.scale_pcm16(mono, float("nan")),
        lambda: accelerator.scale_pcm16(mono, float("nan")),
    )
    _assert_same_contract_error(
        lambda: pcm_audio.stereo_to_mono_pcm16(b"\x00\x00"),
        lambda: accelerator.stereo_to_mono_pcm16(b"\x00\x00"),
    )
    _assert_same_contract_error(
        lambda: pcm_audio.stereo_to_mono_pcm16(stereo, float("inf"), 0.5),
        lambda: accelerator.stereo_to_mono_pcm16(stereo, float("inf"), 0.5),
    )
    mismatched_state = pcm_audio.Pcm16RateState((0, 1), 0)
    _assert_same_contract_error(
        lambda: pcm_audio.rate_convert_pcm16(
            mono,
            1,
            24_000,
            48_000,
            mismatched_state,
        ),
        lambda: accelerator.rate_convert_pcm16(
            mono,
            1,
            24_000,
            48_000,
            mismatched_state,
        ),
    )
    _assert_same_contract_error(
        lambda: pcm_audio.rate_convert_pcm16(_pcm(0, 1), 1, 1, 4_194_305),
        lambda: accelerator.rate_convert_pcm16(
            _pcm(0, 1),
            1,
            1,
            4_194_305,
        ),
    )

    assert calls == dict.fromkeys(calls, 0)
    status = accelerator.status()
    assert len(status.verified_operations) == NATIVE_OPERATION_COUNT
    assert status.disabled_operations == ()
    assert status.operation_failures == ()


def test_verified_native_operation_does_not_recompute_python_fallback(
    monkeypatch,
) -> None:
    original_scale = pcm_audio.scale_pcm16
    module = ModuleType("_mohan_accel")
    module.scale_pcm16 = original_scale
    accelerator = NativeAcceleration(module_loader=lambda _name: module)
    data = _pcm(-1_001, 1_001)
    expected = original_scale(data, 0.5)

    assert accelerator.scale_pcm16(data, 0.5) == expected

    def forbidden_fallback(*_arguments: object) -> bytes:
        raise AssertionError("verified operation recomputed the Python fallback")

    monkeypatch.setattr(pcm_audio, "scale_pcm16", forbidden_fallback)
    assert accelerator.scale_pcm16(data, 0.5) == expected


def test_single_native_failure_is_observable_and_falls_back(
    caplog,
) -> None:
    module = ModuleType("_mohan_accel")

    def fail(payload: bytes, _factor: float) -> bytes:
        raise RuntimeError(f"native fault leaked={payload.hex()}")

    module.scale_pcm16 = fail
    accelerator = NativeAcceleration(module_loader=lambda _name: module)
    data = _pcm(-1_001, 1_001)
    with caplog.at_level(logging.WARNING):
        actual = accelerator.scale_pcm16(data, 0.5)
    assert actual == pcm_audio.scale_pcm16(data, 0.5)
    assert accelerator.status().operation_failures == (("scale_pcm16", 1),)
    assert "RuntimeError" in caplog.text
    assert data.hex() not in caplog.text


def test_every_native_operation_fault_falls_back(caplog) -> None:
    module = ModuleType("_mohan_accel")

    def fail(*_arguments: object) -> object:
        raise RuntimeError("isolated native fault")

    for operation in (
        "analyze_pcm16",
        "infer_vowel_pcm16",
        "scale_pcm16",
        "stereo_to_mono_pcm16",
        "rate_convert_pcm16",
    ):
        setattr(module, operation, fail)

    accelerator = NativeAcceleration(module_loader=lambda _name: module)
    mono = _pcm(-3_000, 0, 3_000, 0)
    stereo = _pcm(-3_000, 3_000, 1_000, -1_000)
    with caplog.at_level(logging.WARNING):
        assert accelerator.analyze_pcm16(mono) == lip_sync.analyze_pcm16(mono)
        assert accelerator.infer_vowel_pcm16(mono) == lip_sync.infer_vowel_pcm16(mono)
        assert accelerator.scale_pcm16(mono, 0.5) == pcm_audio.scale_pcm16(
            mono,
            0.5,
        )
        assert accelerator.stereo_to_mono_pcm16(stereo) == (
            pcm_audio.stereo_to_mono_pcm16(stereo)
        )
        assert accelerator.rate_convert_pcm16(mono, 1, 24_000, 48_000) == (
            pcm_audio.rate_convert_pcm16(mono, 1, 24_000, 48_000)
        )

    assert accelerator.status().operation_failures == (
        ("analyze_pcm16", 1),
        ("infer_vowel_pcm16", 1),
        ("rate_convert_pcm16", 1),
        ("scale_pcm16", 1),
        ("stereo_to_mono_pcm16", 1),
    )
    assert caplog.text.count("RuntimeError") == NATIVE_OPERATION_COUNT
    assert mono.hex() not in caplog.text


def test_rate_conversion_rejects_oversized_output_before_dispatch(
    monkeypatch,
) -> None:
    calls: list[str] = []

    def must_not_run(*_arguments: object) -> object:
        calls.append("called")
        raise AssertionError("oversized conversion reached an implementation")

    module = ModuleType("_mohan_accel")
    module.rate_convert_pcm16 = must_not_run
    monkeypatch.setattr(pcm_audio, "rate_convert_pcm16", must_not_run)
    accelerator = NativeAcceleration(module_loader=lambda _name: module)

    with pytest.raises(pcm_audio.PcmAudioError, match="output size"):
        accelerator.rate_convert_pcm16(_pcm(0, 1), 1, 1, 4_194_305)

    assert calls == []


def test_invalid_input_still_raises_the_python_contract_error() -> None:
    module = ModuleType("_mohan_accel")
    module.stereo_to_mono_pcm16 = lambda *_arguments: (_ for _ in ()).throw(
        ValueError("native validation")
    )
    accelerator = NativeAcceleration(module_loader=lambda _name: module)
    try:
        accelerator.stereo_to_mono_pcm16(b"\x00\x00")
    except pcm_audio.PcmAudioError:
        pass
    else:
        raise AssertionError("the Python reference validation was bypassed")
    assert accelerator.status().disabled_operations == ()
    assert accelerator.status().operation_failures == ()


def test_invalid_native_result_is_observable_and_falls_back(caplog) -> None:
    module = ModuleType("_mohan_accel")
    module.rate_convert_pcm16 = lambda *_arguments: (b"invalid", ["bad-state"])
    accelerator = NativeAcceleration(module_loader=lambda _name: module)
    data = _pcm(0, 1_000, 2_000)
    with caplog.at_level(logging.WARNING):
        actual = accelerator.rate_convert_pcm16(data, 1, 24_000, 48_000)
    assert actual == pcm_audio.rate_convert_pcm16(data, 1, 24_000, 48_000)
    assert accelerator.status().operation_failures == (("rate_convert_pcm16", 1),)
    assert "TypeError" in caplog.text


def test_valid_but_incorrect_native_result_is_disabled_after_one_call() -> None:
    module = ModuleType("_mohan_accel")
    calls = 0

    def wrong_scale(_data: bytes, _factor: float) -> bytes:
        nonlocal calls
        calls += 1
        return b"\x00\x00\x00\x00"

    module.scale_pcm16 = wrong_scale
    accelerator = NativeAcceleration(module_loader=lambda _name: module)
    data = _pcm(-1_001, 1_001)
    expected = pcm_audio.scale_pcm16(data, 0.5)

    assert accelerator.scale_pcm16(data, 0.5) == expected
    assert accelerator.scale_pcm16(data, 0.5) == expected
    assert calls == 1
    status = accelerator.status()
    assert status.disabled_operations == ("scale_pcm16",)
    assert status.verified_operations == ()
    assert status.operation_failures == (("scale_pcm16", 1),)
