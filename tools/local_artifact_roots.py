"""Exact repository roots reserved for local art and validation evidence."""

from __future__ import annotations


LOCAL_ARTIFACT_ROOTS = frozenset({
    "angle-expansion-luna-c",
    "scratchpad",
})


def is_local_artifact_path(parts: tuple[str, ...]) -> bool:
    """Return whether path parts start at a declared local-artifact root."""

    return bool(parts) and parts[0] in LOCAL_ARTIFACT_ROOTS


def local_artifact_import_root(target: str) -> str | None:
    """Return the declared local-artifact root named by an absolute import."""

    root = target.partition(".")[0]
    return root if root in LOCAL_ARTIFACT_ROOTS else None
