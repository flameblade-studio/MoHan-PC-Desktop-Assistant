use crate::error::NativeError;

const MAX_RATE_CONVERSION_OUTPUT_SAMPLES: u128 = 4_194_304;

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct RateState {
    pub(crate) tail_frame: Vec<i16>,
    pub(crate) phase: u64,
}

pub(crate) fn decode_pcm16(data: &[u8], channels: usize) -> Result<Vec<i16>, NativeError> {
    if channels == 0 {
        return Err(NativeError::InvalidArgument(
            "channels must be at least one",
        ));
    }
    let frame_width = channels
        .checked_mul(2)
        .ok_or(NativeError::NumericOverflow("PCM16 frame width overflowed"))?;
    if !data.len().is_multiple_of(frame_width) {
        return Err(NativeError::InvalidArgument(
            "PCM16 data must contain complete frames",
        ));
    }
    Ok(data
        .chunks_exact(2)
        .map(|bytes| i16::from_le_bytes([bytes[0], bytes[1]]))
        .collect())
}

pub(crate) fn encode_pcm16(samples: &[i16]) -> Vec<u8> {
    let mut encoded = Vec::with_capacity(samples.len().saturating_mul(2));
    for sample in samples {
        encoded.extend_from_slice(&sample.to_le_bytes());
    }
    encoded
}

fn clip_pcm16(value: f64) -> Result<i16, NativeError> {
    if !value.is_finite() {
        return Err(NativeError::NumericOverflow(
            "PCM16 arithmetic produced a non-finite value",
        ));
    }
    let clipped = value.floor().clamp(-32_768.0, 32_767.0);
    #[allow(clippy::cast_possible_truncation)]
    let sample = clipped as i16;
    Ok(sample)
}

pub(crate) fn scale_pcm16(data: &[u8], factor: f64) -> Result<Vec<u8>, NativeError> {
    if !factor.is_finite() {
        return Err(NativeError::InvalidArgument("gain factor must be finite"));
    }
    let samples = decode_pcm16(data, 1)?;
    let adjusted = samples
        .into_iter()
        .map(|sample| clip_pcm16(f64::from(sample) * factor))
        .collect::<Result<Vec<_>, _>>()?;
    Ok(encode_pcm16(&adjusted))
}

pub(crate) fn stereo_to_mono_pcm16(
    data: &[u8],
    left_factor: f64,
    right_factor: f64,
) -> Result<Vec<u8>, NativeError> {
    if !left_factor.is_finite() || !right_factor.is_finite() {
        return Err(NativeError::InvalidArgument("mix factors must be finite"));
    }
    let samples = decode_pcm16(data, 2)?;
    let mixed = samples
        .chunks_exact(2)
        .map(|frame| {
            clip_pcm16(f64::from(frame[0]) * left_factor + f64::from(frame[1]) * right_factor)
        })
        .collect::<Result<Vec<_>, _>>()?;
    Ok(encode_pcm16(&mixed))
}

pub(crate) fn rate_convert_pcm16(
    data: &[u8],
    channels: usize,
    input_rate: u32,
    output_rate: u32,
    state: Option<RateState>,
) -> Result<(Vec<u8>, Option<RateState>), NativeError> {
    if input_rate == 0 || output_rate == 0 {
        return Err(NativeError::InvalidArgument(
            "sample rates must be positive",
        ));
    }
    let samples = decode_pcm16(data, channels)?;
    if let Some(previous) = &state
        && previous.tail_frame.len() != channels
    {
        return Err(NativeError::InvalidArgument(
            "resampling state channel count changed",
        ));
    }
    if input_rate == output_rate {
        return Ok((data.to_vec(), None));
    }
    if samples.is_empty() {
        return Ok((Vec::new(), state));
    }

    let mut frames = samples
        .chunks_exact(channels)
        .map(<[i16]>::to_vec)
        .collect::<Vec<_>>();
    let mut phase = 0_u128;
    if let Some(previous) = state {
        frames.insert(0, previous.tail_frame);
        phase = u128::from(previous.phase);
    }

    let last_index = frames.len() - 1;
    let last_index_u128 = u128::try_from(last_index)
        .map_err(|_| NativeError::NumericOverflow("resampling frame count overflowed"))?;
    let last_position = last_index_u128.checked_mul(u128::from(output_rate)).ok_or(
        NativeError::NumericOverflow("resampling position overflowed"),
    )?;
    let output_frames = if phase > last_position {
        0
    } else {
        (last_position - phase) / u128::from(input_rate) + 1
    };
    let channels_u128 = u128::try_from(channels)
        .map_err(|_| NativeError::NumericOverflow("resampling channel count overflowed"))?;
    let output_samples =
        output_frames
            .checked_mul(channels_u128)
            .ok_or(NativeError::NumericOverflow(
                "resampling output size overflowed",
            ))?;
    if output_samples > MAX_RATE_CONVERSION_OUTPUT_SAMPLES {
        return Err(NativeError::InvalidArgument(
            "resampling output size exceeds the supported limit",
        ));
    }
    let output_capacity = usize::try_from(output_samples)
        .map_err(|_| NativeError::NumericOverflow("resampling output size overflowed"))?;
    let mut converted = Vec::with_capacity(output_capacity);
    while phase <= last_position {
        let source_index = usize::try_from(phase / u128::from(output_rate))
            .map_err(|_| NativeError::NumericOverflow("resampling source index overflowed"))?;
        let fraction = phase % u128::from(output_rate);
        if source_index == last_index && fraction != 0 {
            break;
        }
        if fraction == 0 {
            converted.extend_from_slice(&frames[source_index]);
        } else {
            let current_frame = &frames[source_index];
            let next_frame = &frames[source_index + 1];
            let fraction = u32::try_from(fraction).map_err(|_| {
                NativeError::NumericOverflow("resampling fraction exceeds exact range")
            })?;
            let fraction_as_float = f64::from(fraction);
            let output_rate_as_float = f64::from(output_rate);
            for channel in 0..channels {
                let current = f64::from(current_frame[channel]);
                let difference = f64::from(next_frame[channel]) - f64::from(current_frame[channel]);
                converted.push(clip_pcm16(
                    current + difference * fraction_as_float / output_rate_as_float,
                )?);
            }
        }
        phase = phase
            .checked_add(u128::from(input_rate))
            .ok_or(NativeError::NumericOverflow("resampling phase overflowed"))?;
    }

    let remaining_phase = phase
        .checked_sub(last_position)
        .ok_or(NativeError::NumericOverflow("resampling state underflowed"))?;
    let next_phase = u64::try_from(remaining_phase)
        .map_err(|_| NativeError::NumericOverflow("resampling state overflowed"))?;
    let next_state = RateState {
        tail_frame: frames[last_index].clone(),
        phase: next_phase,
    };
    Ok((encode_pcm16(&converted), Some(next_state)))
}

#[cfg(test)]
mod tests {
    use super::{
        MAX_RATE_CONVERSION_OUTPUT_SAMPLES, RateState, rate_convert_pcm16, scale_pcm16,
        stereo_to_mono_pcm16,
    };
    use crate::error::NativeError;

    fn pcm(samples: &[i16]) -> Vec<u8> {
        samples
            .iter()
            .flat_map(|sample| sample.to_le_bytes())
            .collect()
    }

    fn samples(data: &[u8]) -> Vec<i16> {
        data.chunks_exact(2)
            .map(|bytes| i16::from_le_bytes([bytes[0], bytes[1]]))
            .collect()
    }

    #[test]
    fn scale_matches_python_floor_and_saturation() {
        let adjusted = scale_pcm16(&pcm(&[-32_768, -1_001, 0, 1_001, 32_767]), 0.5)
            .expect("valid PCM16 should scale");
        assert_eq!(samples(&adjusted), [-16_384, -501, 0, 500, 16_383]);
        let saturated =
            scale_pcm16(&pcm(&[-20_000, 20_000]), 2.0).expect("valid PCM16 should saturate");
        assert_eq!(samples(&saturated), [-32_768, 32_767]);
    }

    #[test]
    fn stereo_mix_preserves_frames() {
        let mixed = stereo_to_mono_pcm16(
            &pcm(&[1_000, -1_000, 1_001, -1_001, 32_767, 32_767]),
            0.5,
            0.5,
        )
        .expect("valid stereo PCM16 should mix");
        assert_eq!(samples(&mixed), [0, 0, 32_767]);
    }

    #[test]
    fn streamed_resampling_is_continuous() {
        let (first, state) = rate_convert_pcm16(&pcm(&[0, 1_000, 2_000, 3_000]), 1, 4, 8, None)
            .expect("first chunk should convert");
        let (second, state) = rate_convert_pcm16(&pcm(&[4_000, 5_000]), 1, 4, 8, state)
            .expect("second chunk should convert");
        let mut combined = first;
        combined.extend_from_slice(&second);
        assert_eq!(
            samples(&combined),
            [
                0, 500, 1_000, 1_500, 2_000, 2_500, 3_000, 3_500, 4_000, 4_500, 5_000
            ]
        );
        assert!(matches!(state, Some(RateState { .. })));
    }

    #[test]
    fn oversized_resampling_is_rejected_before_output_allocation() {
        let output_rate = u32::try_from(MAX_RATE_CONVERSION_OUTPUT_SAMPLES + 1)
            .expect("test limit should fit in u32");
        let error = rate_convert_pcm16(&pcm(&[0, 1]), 1, 1, output_rate, None)
            .expect_err("amplifying request must be bounded");
        assert_eq!(
            error,
            NativeError::InvalidArgument("resampling output size exceeds the supported limit")
        );
    }
}
