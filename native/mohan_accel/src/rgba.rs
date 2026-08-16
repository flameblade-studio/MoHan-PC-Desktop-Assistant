use std::fmt;

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::pybacked::PyBackedBytes;
use pyo3::types::{PyBytes, PyModule};
use rayon::prelude::*;

const RGBA_CHANNELS: usize = 4;
const ALPHA_MAX: u32 = 255;
const CROSSFADE_MAX: u32 = 65_535;
const PARALLEL_PIXEL_THRESHOLD: usize = 262_144;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum RgbaError {
    EmptyCanvas,
    InvalidRgbaLength,
    FrameSizeMismatch,
    InvalidWeight,
    InvalidMask,
    CoordinateOverflow,
    VisiblePixelOutsideCanvas,
    VisiblePixelOutsideApprovedRegion,
}

impl fmt::Display for RgbaError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        let message = match self {
            Self::EmptyCanvas => "RGBA canvas dimensions must be positive",
            Self::InvalidRgbaLength => "RGBA data length must be divisible by four",
            Self::FrameSizeMismatch => "RGBA data size does not match its dimensions",
            Self::InvalidWeight => "Crossfade weight must be between 0 and 65535",
            Self::InvalidMask => "RGBA masks must be binary and match the target canvas",
            Self::CoordinateOverflow => "RGBA coordinates exceed the supported range",
            Self::VisiblePixelOutsideCanvas => "Visible source pixel leaves the target canvas",
            Self::VisiblePixelOutsideApprovedRegion => {
                "Visible source pixel leaves its approved target region"
            }
        };
        formatter.write_str(message)
    }
}

impl From<RgbaError> for PyErr {
    fn from(error: RgbaError) -> Self {
        PyValueError::new_err(error.to_string())
    }
}

pub(crate) fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add(
        "__rgba_parallel_pixel_threshold__",
        PARALLEL_PIXEL_THRESHOLD,
    )?;
    module.add_function(wrap_pyfunction!(alpha_over_rgba, module)?)?;
    module.add_function(wrap_pyfunction!(crossfade_rgba, module)?)?;
    module.add_function(wrap_pyfunction!(composite_region_rgba, module)?)?;
    Ok(())
}

#[pyfunction]
fn alpha_over_rgba<'py>(
    py: Python<'py>,
    target: Bound<'py, PyBytes>,
    source: Bound<'py, PyBytes>,
) -> PyResult<Bound<'py, PyBytes>> {
    let target = PyBackedBytes::from(target);
    let source = PyBackedBytes::from(source);
    let output = py.detach(move || alpha_over(&target, &source))?;
    Ok(PyBytes::new(py, &output))
}

#[pyfunction]
fn crossfade_rgba<'py>(
    py: Python<'py>,
    first: Bound<'py, PyBytes>,
    second: Bound<'py, PyBytes>,
    second_weight: u32,
) -> PyResult<Bound<'py, PyBytes>> {
    let first = PyBackedBytes::from(first);
    let second = PyBackedBytes::from(second);
    let output = py.detach(move || crossfade(&first, &second, second_weight))?;
    Ok(PyBytes::new(py, &output))
}

#[pyfunction]
#[pyo3(signature = (
    target,
    target_width,
    target_height,
    source,
    source_width,
    source_height,
    anchor_x,
    anchor_y,
    approved_region,
    immutable_identity,
    occlusion_masks=None
))]
#[allow(clippy::too_many_arguments)]
fn composite_region_rgba<'py>(
    py: Python<'py>,
    target: Bound<'py, PyBytes>,
    target_width: usize,
    target_height: usize,
    source: Bound<'py, PyBytes>,
    source_width: usize,
    source_height: usize,
    anchor_x: isize,
    anchor_y: isize,
    approved_region: Bound<'py, PyBytes>,
    immutable_identity: Bound<'py, PyBytes>,
    occlusion_masks: Option<Vec<Bound<'py, PyBytes>>>,
) -> PyResult<Bound<'py, PyBytes>> {
    let request = RegionComposite {
        target: PyBackedBytes::from(target),
        target_width,
        target_height,
        source: PyBackedBytes::from(source),
        source_width,
        source_height,
        anchor_x,
        anchor_y,
        approved_region: PyBackedBytes::from(approved_region),
        immutable_identity: PyBackedBytes::from(immutable_identity),
        occlusion_masks: occlusion_masks
            .unwrap_or_default()
            .into_iter()
            .map(PyBackedBytes::from)
            .collect(),
    };
    let output = py.detach(move || composite_region(&request))?;
    Ok(PyBytes::new(py, &output))
}

fn alpha_over(target: &[u8], source: &[u8]) -> Result<Vec<u8>, RgbaError> {
    validate_equal_rgba(target, source)?;
    let mut output = target.to_vec();
    if should_parallelize(source.len() / RGBA_CHANNELS) {
        output
            .par_chunks_exact_mut(RGBA_CHANNELS)
            .zip(source.par_chunks_exact(RGBA_CHANNELS))
            .for_each(|(target_pixel, source_pixel)| {
                blend_pixel(target_pixel, 0, source_pixel, 0);
            });
    } else {
        for index in (0..source.len()).step_by(RGBA_CHANNELS) {
            blend_pixel(&mut output, index, source, index);
        }
    }
    Ok(output)
}

fn crossfade(first: &[u8], second: &[u8], second_weight: u32) -> Result<Vec<u8>, RgbaError> {
    validate_equal_rgba(first, second)?;
    if second_weight > CROSSFADE_MAX {
        return Err(RgbaError::InvalidWeight);
    }
    let first_weight = CROSSFADE_MAX - second_weight;
    let mix = |left: &u8, right: &u8| {
        let mixed =
            u32::from(*left) * first_weight + u32::from(*right) * second_weight + CROSSFADE_MAX / 2;
        bounded_byte(mixed / CROSSFADE_MAX)
    };
    if should_parallelize(first.len() / RGBA_CHANNELS) {
        Ok(first
            .par_iter()
            .zip(second.par_iter())
            .map(|(left, right)| mix(left, right))
            .collect())
    } else {
        Ok(first
            .iter()
            .zip(second)
            .map(|(left, right)| mix(left, right))
            .collect())
    }
}

struct RegionComposite<Buffer, Mask> {
    target: Buffer,
    target_width: usize,
    target_height: usize,
    source: Buffer,
    source_width: usize,
    source_height: usize,
    anchor_x: isize,
    anchor_y: isize,
    approved_region: Buffer,
    immutable_identity: Buffer,
    occlusion_masks: Vec<Mask>,
}

fn composite_region<Buffer, Mask>(
    request: &RegionComposite<Buffer, Mask>,
) -> Result<Vec<u8>, RgbaError>
where
    Buffer: AsRef<[u8]> + Sync,
    Mask: AsRef<[u8]> + Sync,
{
    let target_pixels = checked_pixels(request.target_width, request.target_height)?;
    let source_pixels = checked_pixels(request.source_width, request.source_height)?;
    let target = request.target.as_ref();
    let source = request.source.as_ref();
    let approved_region = request.approved_region.as_ref();
    let immutable_identity = request.immutable_identity.as_ref();
    validate_sized_rgba(target, target_pixels)?;
    validate_sized_rgba(source, source_pixels)?;
    validate_mask(approved_region, target_pixels)?;
    validate_mask(immutable_identity, target_pixels)?;
    for mask in &request.occlusion_masks {
        validate_mask(mask.as_ref(), target_pixels)?;
    }
    let target_width =
        isize::try_from(request.target_width).map_err(|_| RgbaError::CoordinateOverflow)?;
    let target_height =
        isize::try_from(request.target_height).map_err(|_| RgbaError::CoordinateOverflow)?;

    validate_visible_region(
        request,
        source,
        approved_region,
        immutable_identity,
        target_width,
        target_height,
    )?;
    let mut output = target.to_vec();
    if should_parallelize(source_pixels) {
        composite_region_parallel(request, &mut output, source);
    } else {
        composite_region_serial(request, &mut output, source);
    }
    Ok(output)
}

fn validate_visible_region<Buffer, Mask>(
    request: &RegionComposite<Buffer, Mask>,
    source: &[u8],
    approved_region: &[u8],
    immutable_identity: &[u8],
    target_width: isize,
    target_height: isize,
) -> Result<(), RgbaError>
where
    Buffer: AsRef<[u8]>,
    Mask: AsRef<[u8]>,
{
    for source_y in 0..request.source_height {
        for source_x in 0..request.source_width {
            let source_pixel = source_y * request.source_width + source_x;
            let source_index = source_pixel * RGBA_CHANNELS;
            if source[source_index + 3] == 0 {
                continue;
            }
            let target_x = offset_coordinate(request.anchor_x, source_x)?;
            let target_y = offset_coordinate(request.anchor_y, source_y)?;
            if target_x < 0 || target_y < 0 || target_x >= target_width || target_y >= target_height
            {
                return Err(RgbaError::VisiblePixelOutsideCanvas);
            }
            let target_x = usize::try_from(target_x).map_err(|_| RgbaError::CoordinateOverflow)?;
            let target_y = usize::try_from(target_y).map_err(|_| RgbaError::CoordinateOverflow)?;
            let target_pixel = target_y * request.target_width + target_x;
            if request
                .occlusion_masks
                .iter()
                .any(|mask| mask.as_ref()[target_pixel] != 0)
            {
                continue;
            }
            if immutable_identity[target_pixel] != 0 || approved_region[target_pixel] == 0 {
                return Err(RgbaError::VisiblePixelOutsideApprovedRegion);
            }
        }
    }
    Ok(())
}

fn composite_region_serial<Buffer, Mask>(
    request: &RegionComposite<Buffer, Mask>,
    output: &mut [u8],
    source: &[u8],
) where
    Buffer: AsRef<[u8]>,
    Mask: AsRef<[u8]>,
{
    for source_y in 0..request.source_height {
        for source_x in 0..request.source_width {
            blend_region_pixel(request, output, source, source_x, source_y);
        }
    }
}

fn composite_region_parallel<Buffer, Mask>(
    request: &RegionComposite<Buffer, Mask>,
    output: &mut [u8],
    source: &[u8],
) where
    Buffer: AsRef<[u8]> + Sync,
    Mask: AsRef<[u8]> + Sync,
{
    let row_bytes = request.target_width * RGBA_CHANNELS;
    output
        .par_chunks_exact_mut(row_bytes)
        .enumerate()
        .for_each(|(target_y, target_row)| {
            let source_y = isize::try_from(target_y)
                .ok()
                .and_then(|value| value.checked_sub(request.anchor_y))
                .and_then(|value| usize::try_from(value).ok());
            let Some(source_y) = source_y.filter(|value| *value < request.source_height) else {
                return;
            };
            for source_x in 0..request.source_width {
                let source_index = (source_y * request.source_width + source_x) * RGBA_CHANNELS;
                if source[source_index + 3] == 0 {
                    continue;
                }
                let target_x = offset_coordinate(request.anchor_x, source_x)
                    .ok()
                    .and_then(|value| usize::try_from(value).ok());
                let Some(target_x) = target_x.filter(|value| *value < request.target_width) else {
                    continue;
                };
                let target_pixel = target_y * request.target_width + target_x;
                if request
                    .occlusion_masks
                    .iter()
                    .any(|mask| mask.as_ref()[target_pixel] != 0)
                {
                    continue;
                }
                blend_pixel(target_row, target_x * RGBA_CHANNELS, source, source_index);
            }
        });
}

fn blend_region_pixel<Buffer, Mask>(
    request: &RegionComposite<Buffer, Mask>,
    output: &mut [u8],
    source: &[u8],
    source_x: usize,
    source_y: usize,
) where
    Buffer: AsRef<[u8]>,
    Mask: AsRef<[u8]>,
{
    let source_index = (source_y * request.source_width + source_x) * RGBA_CHANNELS;
    if source[source_index + 3] == 0 {
        return;
    }
    let Some(target_x) = offset_coordinate(request.anchor_x, source_x)
        .ok()
        .and_then(|value| usize::try_from(value).ok())
    else {
        return;
    };
    let Some(target_y) = offset_coordinate(request.anchor_y, source_y)
        .ok()
        .and_then(|value| usize::try_from(value).ok())
    else {
        return;
    };
    let target_pixel = target_y * request.target_width + target_x;
    if request
        .occlusion_masks
        .iter()
        .any(|mask| mask.as_ref()[target_pixel] != 0)
    {
        return;
    }
    blend_pixel(output, target_pixel * RGBA_CHANNELS, source, source_index);
}

fn validate_equal_rgba(first: &[u8], second: &[u8]) -> Result<(), RgbaError> {
    if first.len() != second.len() {
        return Err(RgbaError::FrameSizeMismatch);
    }
    if !first.len().is_multiple_of(RGBA_CHANNELS) {
        return Err(RgbaError::InvalidRgbaLength);
    }
    Ok(())
}

fn should_parallelize(pixels: usize) -> bool {
    pixels >= PARALLEL_PIXEL_THRESHOLD && rayon::current_num_threads() > 1
}

fn checked_pixels(width: usize, height: usize) -> Result<usize, RgbaError> {
    if width == 0 || height == 0 {
        return Err(RgbaError::EmptyCanvas);
    }
    width
        .checked_mul(height)
        .ok_or(RgbaError::FrameSizeMismatch)
}

fn validate_sized_rgba(data: &[u8], pixels: usize) -> Result<(), RgbaError> {
    let expected = pixels
        .checked_mul(RGBA_CHANNELS)
        .ok_or(RgbaError::FrameSizeMismatch)?;
    if data.len() != expected {
        return Err(RgbaError::FrameSizeMismatch);
    }
    Ok(())
}

fn validate_mask(mask: &[u8], pixels: usize) -> Result<(), RgbaError> {
    if mask.len() != pixels || mask.iter().any(|value| *value > 1) {
        return Err(RgbaError::InvalidMask);
    }
    Ok(())
}

fn offset_coordinate(anchor: isize, offset: usize) -> Result<isize, RgbaError> {
    let offset = isize::try_from(offset).map_err(|_| RgbaError::CoordinateOverflow)?;
    anchor
        .checked_add(offset)
        .ok_or(RgbaError::CoordinateOverflow)
}

fn blend_pixel(target: &mut [u8], target_index: usize, source: &[u8], source_index: usize) {
    let source_alpha = u32::from(source[source_index + 3]);
    if source_alpha == 0 {
        return;
    }
    let inverse = ALPHA_MAX - source_alpha;
    for channel in 0..3 {
        let blended = u32::from(source[source_index + channel]) * source_alpha
            + u32::from(target[target_index + channel]) * inverse;
        target[target_index + channel] = bounded_byte(blended / ALPHA_MAX);
    }
    let target_alpha = u32::from(target[target_index + 3]);
    target[target_index + 3] =
        bounded_byte((source_alpha + (target_alpha * inverse) / ALPHA_MAX).min(ALPHA_MAX));
}

fn bounded_byte(value: u32) -> u8 {
    match u8::try_from(value) {
        Ok(value) => value,
        Err(_) => unreachable!("RGBA integer arithmetic guarantees an eight-bit result"),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn opaque(red: u8, green: u8, blue: u8) -> Vec<u8> {
        vec![red, green, blue, 255]
    }

    #[test]
    fn transparent_pixel_is_an_exact_no_op() {
        let target = vec![17, 31, 47, 63];
        assert_eq!(alpha_over(&target, &[200, 150, 100, 0]).unwrap(), target);
    }

    #[test]
    fn alpha_over_matches_the_python_integer_contract() {
        let target = vec![20, 40, 60, 80];
        let source = vec![200, 100, 50, 128];
        assert_eq!(
            alpha_over(&target, &source).unwrap(),
            vec![110, 70, 54, 167]
        );
    }

    #[test]
    fn alpha_over_rejects_misaligned_or_different_frames() {
        assert_eq!(
            alpha_over(&[0, 0, 0], &[0, 0, 0]).unwrap_err(),
            RgbaError::InvalidRgbaLength
        );
        assert_eq!(
            alpha_over(&[0, 0, 0, 0], &[0; 8]).unwrap_err(),
            RgbaError::FrameSizeMismatch
        );
    }

    #[test]
    fn crossfade_preserves_endpoints_and_rounds_like_python() {
        let first = vec![0, 1, 127, 255];
        let second = vec![255, 127, 1, 0];
        assert_eq!(crossfade(&first, &second, 0).unwrap(), first);
        assert_eq!(crossfade(&first, &second, 65_535).unwrap(), second);
        assert_eq!(
            crossfade(&[0, 1, 2, 3], &[255, 254, 253, 252], 32_768).unwrap(),
            vec![128, 128, 128, 128]
        );
        assert_eq!(
            crossfade(&[0; 4], &[0; 4], 65_536).unwrap_err(),
            RgbaError::InvalidWeight
        );
    }

    #[test]
    fn regional_composite_honors_anchor_region_identity_and_occlusion() {
        let target = vec![10; 3 * 2 * RGBA_CHANNELS];
        let source = [opaque(200, 100, 50), opaque(7, 8, 9)].concat();
        let mut approved = vec![0; 6];
        approved[1] = 1;
        approved[2] = 1;
        let identity = vec![0; 6];
        let mut occlusion = vec![0; 6];
        occlusion[2] = 1;
        let output = composite_region(&RegionComposite {
            target: target.clone(),
            target_width: 3,
            target_height: 2,
            source,
            source_width: 2,
            source_height: 1,
            anchor_x: 1,
            anchor_y: 0,
            approved_region: approved,
            immutable_identity: identity,
            occlusion_masks: vec![occlusion],
        })
        .unwrap();
        assert_eq!(&output[4..8], &[200, 100, 50, 255]);
        assert_eq!(&output[8..12], &target[8..12]);
    }

    #[test]
    fn transparent_off_canvas_pixel_is_ignored_but_visible_pixel_is_rejected() {
        let request = |source: Vec<u8>| RegionComposite {
            target: vec![0; RGBA_CHANNELS],
            target_width: 1,
            target_height: 1,
            source,
            source_width: 1,
            source_height: 1,
            anchor_x: -1,
            anchor_y: 0,
            approved_region: vec![1],
            immutable_identity: vec![0],
            occlusion_masks: Vec::<Vec<u8>>::new(),
        };
        assert_eq!(
            composite_region(&request(vec![1, 2, 3, 0])).unwrap(),
            vec![0; 4]
        );
        assert_eq!(
            composite_region(&request(vec![1, 2, 3, 1])).unwrap_err(),
            RgbaError::VisiblePixelOutsideCanvas
        );
    }

    #[test]
    fn regional_composite_rejects_invalid_masks_and_protected_pixels() {
        let base = || RegionComposite {
            target: vec![0; RGBA_CHANNELS],
            target_width: 1,
            target_height: 1,
            source: opaque(1, 2, 3),
            source_width: 1,
            source_height: 1,
            anchor_x: 0,
            anchor_y: 0,
            approved_region: vec![1],
            immutable_identity: vec![0],
            occlusion_masks: Vec::<Vec<u8>>::new(),
        };
        let mut invalid_mask = base();
        invalid_mask.approved_region = vec![2];
        assert_eq!(
            composite_region(&invalid_mask).unwrap_err(),
            RgbaError::InvalidMask
        );
        let mut protected = base();
        protected.immutable_identity = vec![1];
        assert_eq!(
            composite_region(&protected).unwrap_err(),
            RgbaError::VisiblePixelOutsideApprovedRegion
        );
    }
}
