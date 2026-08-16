mod error;
mod lip_sync;
mod pcm;
mod rgba;

use pyo3::prelude::*;
use pyo3::pybacked::PyBackedBytes;
use pyo3::types::{PyBytes, PyModule, PyTuple};

use crate::pcm::RateState;

#[pyfunction]
fn analyze_pcm16(py: Python<'_>, data: PyBackedBytes) -> PyResult<(f64, f64)> {
    Ok(py.detach(move || lip_sync::analyze_pcm16(&data))?)
}

#[pyfunction]
#[pyo3(signature = (data, sample_rate=24_000))]
fn infer_vowel_pcm16(
    py: Python<'_>,
    data: PyBackedBytes,
    sample_rate: i64,
) -> PyResult<(f64, &'static str)> {
    Ok(py.detach(move || lip_sync::infer_vowel_pcm16(&data, sample_rate))?)
}

#[pyfunction]
fn scale_pcm16(py: Python<'_>, data: PyBackedBytes, factor: f64) -> PyResult<Bound<'_, PyBytes>> {
    let adjusted = py.detach(move || pcm::scale_pcm16(&data, factor))?;
    Ok(PyBytes::new(py, &adjusted))
}

#[pyfunction]
#[pyo3(signature = (data, left_factor=0.5, right_factor=0.5))]
fn stereo_to_mono_pcm16(
    py: Python<'_>,
    data: PyBackedBytes,
    left_factor: f64,
    right_factor: f64,
) -> PyResult<Bound<'_, PyBytes>> {
    let mixed = py.detach(move || pcm::stereo_to_mono_pcm16(&data, left_factor, right_factor))?;
    Ok(PyBytes::new(py, &mixed))
}

type RateStateInput = Option<(Vec<i16>, u64)>;
type RateStateOutput<'py> = Option<(Bound<'py, PyTuple>, u64)>;
type RateConversionPayload<'py> = (Bound<'py, PyBytes>, RateStateOutput<'py>);

#[pyfunction]
#[pyo3(signature = (data, channels, input_rate, output_rate, state=None))]
fn rate_convert_pcm16(
    py: Python<'_>,
    data: PyBackedBytes,
    channels: usize,
    input_rate: u32,
    output_rate: u32,
    state: RateStateInput,
) -> PyResult<RateConversionPayload<'_>> {
    let native_state = state.map(|(tail_frame, phase)| RateState { tail_frame, phase });
    let (converted, next_state) = py.detach(move || {
        pcm::rate_convert_pcm16(&data, channels, input_rate, output_rate, native_state)
    })?;
    let payload = match next_state {
        Some(state) => Some((PyTuple::new(py, state.tail_frame)?, state.phase)),
        None => None,
    };
    Ok((PyBytes::new(py, &converted), payload))
}

#[pymodule]
fn _mohan_accel(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add("__version__", env!("CARGO_PKG_VERSION"))?;
    module.add_function(wrap_pyfunction!(analyze_pcm16, module)?)?;
    module.add_function(wrap_pyfunction!(infer_vowel_pcm16, module)?)?;
    module.add_function(wrap_pyfunction!(scale_pcm16, module)?)?;
    module.add_function(wrap_pyfunction!(stereo_to_mono_pcm16, module)?)?;
    module.add_function(wrap_pyfunction!(rate_convert_pcm16, module)?)?;
    rgba::register(module)?;
    Ok(())
}
