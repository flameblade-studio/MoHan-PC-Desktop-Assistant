use std::fmt::{Display, Formatter};

use pyo3::PyErr;
use pyo3::exceptions::{PyOverflowError, PyValueError};

#[derive(Debug, Clone, Copy, Eq, PartialEq)]
pub(crate) enum NativeError {
    InvalidArgument(&'static str),
    NumericOverflow(&'static str),
}

impl Display for NativeError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::InvalidArgument(message) | Self::NumericOverflow(message) => {
                formatter.write_str(message)
            }
        }
    }
}

impl From<NativeError> for PyErr {
    fn from(error: NativeError) -> Self {
        match error {
            NativeError::InvalidArgument(message) => PyValueError::new_err(message),
            NativeError::NumericOverflow(message) => PyOverflowError::new_err(message),
        }
    }
}
