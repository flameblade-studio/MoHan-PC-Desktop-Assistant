from __future__ import annotations

lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NATIVE_ROOT = ROOT / "native" / "mohan_accel"

NATIVE_OPERATION_COUNT = 5
I16_DECODE_COUNT = 2


def test_native_bindings_borrow_bytes_and_release_python() -> None:
    bindings = (NATIVE_ROOT / "src" / "lib.rs").read_text(encoding="utf-8")
    assert "use pyo3::pybacked::PyBackedBytes;" in bindings
    assert bindings.count("data: PyBackedBytes") >= NATIVE_OPERATION_COUNT
    assert bindings.count("py.detach(move ||") >= NATIVE_OPERATION_COUNT
    for operation in (
        "analyze_pcm16",
        "infer_vowel_pcm16",
        "scale_pcm16",
        "stereo_to_mono_pcm16",
        "rate_convert_pcm16",
    ):
        assert f"fn {operation}(" in bindings


def test_pcm16_is_decoded_explicitly_without_float_reinterpretation() -> None:
    rust_sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((NATIVE_ROOT / "src").glob("*.rs"))
    )
    assert rust_sources.count("i16::from_le_bytes") >= I16_DECODE_COUNT
    assert "&[f32]" not in rust_sources
    assert "from_raw_parts" not in rust_sources
    cargo_manifest = (NATIVE_ROOT / "Cargo.toml").read_text(encoding="utf-8")
    assert 'unsafe_code = "forbid"' in cargo_manifest


def test_goertzel_stays_dependency_free_until_measurement_justifies_fft() -> None:
    manifests = "\n".join(
        (NATIVE_ROOT / filename).read_text(encoding="utf-8")
        for filename in ("Cargo.toml", "Cargo.lock")
    )
    assert "rustfft" not in manifests.casefold()
    lip_sync = (NATIVE_ROOT / "src" / "lip_sync.rs").read_text(encoding="utf-8")
    assert "goertzel_power" in lip_sync


def test_benchmark_fixture_is_a_real_20_ms_50_hz_pcm16_frame() -> None:
    from tools import benchmark_native_acceleration as benchmark

    frame = benchmark._frame()
    stereo = benchmark._stereo_frame(frame)
    assert len(frame) == 480 * 2
    assert len(stereo) == 480 * 2 * 2
    assert all(
        stereo[index : index + 2] == stereo[index + 2 : index + 4]
        for index in range(0, len(stereo), 4)
    )
