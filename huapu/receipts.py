"""Versioned, deterministic receipt envelopes for Huapu operations."""

from __future__ import annotations

lazy import json
lazy from collections.abc import Mapping, Sequence
lazy from dataclasses import dataclass, field

lazy from huapu.hashing import FileDigest

RECEIPT_SCHEMA = "flameblade.huapu.receipt"
RECEIPT_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class Receipt:
    """A data-only operation receipt with explicit subject and file identities."""

    operation: str
    status: str
    subject: str
    files: tuple[FileDigest, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for label, value in (
            ("operation", self.operation),
            ("status", self.status),
            ("subject", self.subject),
        ):
            if not value or value != value.strip():
                raise ValueError(f"receipt {label} must be non-empty trimmed text")
        paths = tuple(item.path for item in self.files)
        if paths != tuple(sorted(paths)) or len(set(paths)) != len(paths):
            raise ValueError("receipt files must use unique paths in code-point order")

    def to_document(self) -> dict[str, object]:
        return {
            "schema": RECEIPT_SCHEMA,
            "schema_version": RECEIPT_SCHEMA_VERSION,
            "operation": self.operation,
            "status": self.status,
            "subject": self.subject,
            "files": [item.to_document() for item in self.files],
            "metadata": dict(self.metadata),
        }


def render_receipt(receipt: Receipt) -> str:
    """Render one UTF-8-compatible JSON receipt with deterministic LF output."""
    return json.dumps(
        receipt.to_document(),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        indent=2,
    ) + "\n"


def receipt_for_files(
    operation: str,
    status: str,
    subject: str,
    files: Sequence[FileDigest],
    *,
    metadata: Mapping[str, object] | None = None,
) -> Receipt:
    """Create a receipt after sorting measured files by portable path."""
    return Receipt(
        operation,
        status,
        subject,
        tuple(sorted(files, key=lambda item: item.path)),
        {} if metadata is None else dict(metadata),
    )
