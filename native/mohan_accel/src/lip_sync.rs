use std::f64::consts::PI;

use crate::error::NativeError;

const VOWEL_FORMANTS: [(&str, (f64, f64)); 5] = [
    ("A", (800.0, 1_200.0)),
    ("I", (300.0, 2_400.0)),
    ("U", (350.0, 850.0)),
    ("E", (500.0, 2_000.0)),
    ("O", (500.0, 950.0)),
];

// Squared PCM16 values use at most 30 bits. Limiting analysis to 2^23
// samples keeps their sum at or below 2^53, where f64 represents every
// integer exactly. A 50 Hz / 24 kHz MoHan frame contains only 480 samples.
const MAX_EXACT_PCM16_SAMPLES: usize = 8_388_608;

// This order is the deterministic CPython 3.15 iteration order of the
// reference implementation's numeric candidate set. Ties therefore preserve
// the same first-candidate behavior instead of changing a viseme at a boundary.
const CANDIDATE_FREQUENCIES: [f64; 15] = [
    800.0, 1_600.0, 450.0, 2_400.0, 300.0, 1_200.0, 2_000.0, 850.0, 500.0, 950.0, 3_000.0, 600.0,
    250.0, 700.0, 350.0,
];

fn decode_truncated_pcm16(data: &[u8]) -> Vec<i16> {
    data.chunks_exact(2)
        .map(|bytes| i16::from_le_bytes([bytes[0], bytes[1]]))
        .collect()
}

fn exact_f64_from_usize(value: usize) -> Result<f64, NativeError> {
    let exact = u32::try_from(value).map_err(|_| {
        NativeError::NumericOverflow("PCM16 buffer exceeds the supported analysis size")
    })?;
    Ok(f64::from(exact))
}

fn exact_f64_from_u64(value: u64) -> f64 {
    const TWO_POW_32: f64 = 4_294_967_296.0;
    let high = u32::try_from(value >> 32).expect("upper half of u64 fits u32");
    let low = u32::try_from(value & u64::from(u32::MAX)).expect("lower half fits u32");
    f64::from(high) * TWO_POW_32 + f64::from(low)
}

fn exact_f64_from_sample_rate(value: i64) -> Result<f64, NativeError> {
    let exact = u64::try_from(value)
        .map_err(|_| NativeError::InvalidArgument("sample rate must be positive"))?;
    Ok(exact_f64_from_u64(exact))
}

pub(crate) fn analyze_pcm16(data: &[u8]) -> Result<(f64, f64), NativeError> {
    if data.len() < 4 {
        return Ok((0.0, 0.0));
    }
    let samples = decode_truncated_pcm16(data);
    if samples.is_empty() {
        return Ok((0.0, 0.0));
    }
    if samples.len() > MAX_EXACT_PCM16_SAMPLES {
        return Err(NativeError::NumericOverflow(
            "PCM16 buffer exceeds the exact analysis range",
        ));
    }
    let sum_squares = samples.iter().try_fold(0_u64, |total, sample| {
        let value = i64::from(*sample);
        let square = u64::try_from(value * value).expect("squared i16 is non-negative");
        total
            .checked_add(square)
            .ok_or(NativeError::NumericOverflow(
                "PCM16 RMS accumulation overflowed",
            ))
    })?;
    let sample_count = exact_f64_from_usize(samples.len())?;
    let rms = (exact_f64_from_u64(sum_squares) / sample_count).sqrt();
    let loudness = ((rms - 90.0) / 6_200.0).clamp(0.0, 1.0);
    let crossings = samples
        .windows(2)
        .filter(|pair| (pair[0] < 0 && pair[1] >= 0) || (pair[0] >= 0 && pair[1] < 0))
        .count();
    let crossing_rate = exact_f64_from_usize(crossings)?
        / exact_f64_from_usize(samples.len().saturating_sub(1).max(1))?;
    let articulation = (crossing_rate / 0.24).clamp(0.0, 1.0);
    Ok((loudness, articulation))
}

fn goertzel_power(samples: &[f64], sample_rate: f64, frequency: f64) -> f64 {
    let coefficient = 2.0 * (2.0 * PI * frequency / sample_rate).cos();
    let mut previous = 0.0;
    let mut previous_two = 0.0;
    for sample in samples {
        let current = sample + coefficient * previous - previous_two;
        previous_two = previous;
        previous = current;
    }
    (previous_two * previous_two + previous * previous - coefficient * previous * previous_two)
        .max(0.0)
}

pub(crate) fn infer_vowel_pcm16(
    data: &[u8],
    sample_rate: i64,
) -> Result<(f64, &'static str), NativeError> {
    let (level, articulation) = analyze_pcm16(data)?;
    if level < 0.025 {
        return Ok((level, "CLOSED"));
    }
    if articulation >= 0.48 {
        return Ok((level, "CONSONANT"));
    }
    let raw = decode_truncated_pcm16(data);
    if raw.len() < 32 || sample_rate <= 0 {
        return Ok((level, "E"));
    }

    let sample_rate = exact_f64_from_sample_rate(sample_rate)?;
    let sample_count = exact_f64_from_usize(raw.len())?;
    // Every running integer sum remains exact in f64 under the bound enforced
    // by analyze_pcm16, avoiding a lossy integer cast and matching Python.
    let sample_sum = raw.iter().map(|sample| f64::from(*sample)).sum::<f64>();
    let mean = sample_sum / sample_count;
    let scale = raw
        .iter()
        .map(|sample| (f64::from(*sample) - mean).abs())
        .fold(1.0_f64, f64::max);
    let last_index = exact_f64_from_usize(raw.len() - 1)?;
    let windowed = raw
        .iter()
        .enumerate()
        .map(|(index, sample)| {
            Ok(((f64::from(*sample) - mean) / scale)
                * (0.54 - 0.46 * (2.0 * PI * exact_f64_from_usize(index)? / last_index).cos()))
        })
        .collect::<Result<Vec<_>, NativeError>>()?;

    let powers = CANDIDATE_FREQUENCIES
        .iter()
        .copied()
        .filter(|frequency| *frequency < sample_rate / 2.0)
        .map(|frequency| (frequency, goertzel_power(&windowed, sample_rate, frequency)))
        .collect::<Vec<_>>();
    let strongest = |minimum: f64, maximum: f64| {
        let mut selected: Option<(f64, f64)> = None;
        for &(frequency, power) in &powers {
            if !(minimum..=maximum).contains(&frequency) {
                continue;
            }
            if selected.is_none_or(|(_, selected_power)| power > selected_power) {
                selected = Some((frequency, power));
            }
        }
        selected.map(|(frequency, _)| frequency)
    };
    let first_formant = strongest(250.0, 850.0);
    let second_formant = strongest(800.0, 3_000.0);
    let (Some(first_formant), Some(second_formant)) = (first_formant, second_formant) else {
        return Ok((level, "E"));
    };

    let mut selected = VOWEL_FORMANTS[0];
    let mut selected_distance = f64::INFINITY;
    for candidate in VOWEL_FORMANTS {
        let (first, second) = candidate.1;
        let distance = (first_formant.max(1.0) / first).ln().abs()
            + 0.8 * (second_formant.max(1.0) / second).ln().abs();
        if distance < selected_distance {
            selected = candidate;
            selected_distance = distance;
        }
    }
    Ok((level, selected.0))
}

#[cfg(test)]
mod tests {
    use std::f64::consts::PI;

    use super::{VOWEL_FORMANTS, analyze_pcm16, infer_vowel_pcm16};

    fn encode(samples: impl Iterator<Item = i16>) -> Vec<u8> {
        samples.flat_map(i16::to_le_bytes).collect()
    }

    #[test]
    fn silence_and_crossings_match_the_reference_contract() {
        assert_eq!(analyze_pcm16(&vec![0_u8; 480]), Ok((0.0, 0.0)));
        let alternating = encode((0..240).map(|index| if index % 2 == 0 { -9_000 } else { 9_000 }));
        let (level, articulation) = analyze_pcm16(&alternating).expect("analysis should succeed");
        assert!(level > 0.9);
        assert!((articulation - 1.0).abs() < f64::EPSILON);
    }

    #[test]
    fn synthetic_formants_keep_all_five_visemes() {
        for (vowel, (first, second)) in VOWEL_FORMANTS {
            let samples = encode((0..960).map(|index| {
                let time = f64::from(index) / 24_000.0;
                let sample = 7_000.0 * (2.0 * PI * first * time).sin()
                    + 5_000.0 * (2.0 * PI * second * time).sin();
                #[allow(clippy::cast_possible_truncation)]
                let sample = sample as i16;
                sample
            }));
            assert_eq!(
                infer_vowel_pcm16(&samples, 24_000)
                    .expect("vowel inference should succeed")
                    .1,
                vowel,
            );
        }
    }
}
