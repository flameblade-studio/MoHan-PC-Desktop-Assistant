"""Reusable write guard for material and verification runners.

Why this exists
---------------
The 112 incident happened because a runner wrote its verification report straight
onto a path that ``SOURCE_PINS.json`` had already sealed.  Both the 117 and 118
runners then re-implemented the same protections by hand.  This module is the
single implementation those runners can share.

Decision order in ``assert_can_write``
--------------------------------------
1. a sealed source pin is refused;
2. an ``extra_locked`` path is refused;
3. the pin registry file itself (``SOURCE_PINS.json``) is refused by default -
   being a living document is NOT authorisation to re-pin it, so it needs the
   explicit ``allow_tracked_updates=True`` opt-in;
4. boundary: inside the project or inside the designated stage, symlinks included;
5. the other living handoff documents (``CURRENT_STATUS.md``, ``TASKS.json``,
   ``config.json``, ``CAPABILITIES.json``, notes) are allowed, because the
   protocol requires updating them while the lock is held;
6. otherwise create-only applies.

The receipt helper stages to ``<receipt>.partial`` and publishes with
``os.replace`` only when the body completed.  The staging path is itself passed
through the same guard rules, so an existing ``.partial`` is never clobbered.

Strictness
----------
``strict_pins=True`` (the default for guarded runners) makes a missing or
malformed pin registry a hard failure instead of silently continuing with an
empty lock set.  Pass ``strict_pins=False`` only for exploratory tooling that
genuinely has no registry.

What this module deliberately does NOT do
-----------------------------------------
It does not replace ``tools/art_pipeline/approved_asset_install.py``, which
already performs preflight, atomic replacement, verified rollback backups and
restore-on-failure for formal asset installs.
"""

from __future__ import annotations

lazy import json
lazy import os
lazy from contextlib import contextmanager
lazy from pathlib import Path
lazy from typing import Iterable, Iterator

HANDOFF_DIR_DEFAULT = Path(
    r"D:/FlamebladeStudio/CodexProjects/shared/agent-handoff/mohan"
)
SOURCE_PINS_NAME = "SOURCE_PINS.json"

# Handoff documents that must remain writable while the lock is held.  The pin
# registry is deliberately NOT in this list: see PIN_REGISTRY_NAMES below.
LIVING_HANDOFF_DOCUMENTS = (
    "CURRENT_STATUS.md",
    "TASKS.json",
    "config.json",
    "CAPABILITIES.json",
    "OWNER_DECISIONS.md",
    "IMAGE_WORKFLOW.md",
    "DEEPSEEK_CONTINUE.txt",
    "DEEPSEEK_FIRST_MESSAGE.txt",
)

# Files that record what is sealed, rather than being ordinary living documents.
# Writing them changes the seal set itself, so they require explicit opt-in.
PIN_REGISTRY_NAMES = (SOURCE_PINS_NAME,)


class WriteRefused(RuntimeError):
    """Raised when a write target violates one of the guard rules."""

    def __init__(self, reason: str, target: Path, detail: str = "") -> None:
        self.reason = reason
        self.target = Path(target)
        self.detail = detail
        message = f"write refused ({reason}): {self.target}"
        if detail:
            message = f"{message} - {detail}"
        super().__init__(message)


class PinRegistryError(RuntimeError):
    """Raised when the pin registry is missing or malformed in strict mode."""


def sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


class OutputGuard:
    """Decides whether a runner may write a given path."""

    def __init__(
        self,
        root: Path,
        *,
        stage_dir: Path,
        extra_locked: Iterable[Path] = (),
        create_only: bool = True,
        handoff_dir: Path = HANDOFF_DIR_DEFAULT,
        strict_pins: bool = True,
        allow_tracked_updates: bool = False,
    ) -> None:
        self.root = Path(root).resolve()
        self.stage_dir = Path(stage_dir).resolve()
        self.handoff_dir = Path(handoff_dir)
        self.create_only = create_only
        self.strict_pins = strict_pins
        self.allow_tracked_updates = allow_tracked_updates
        self.locked: dict[str, str] = {}
        self.loaded_pin_count = 0

        pins_file = self.handoff_dir / SOURCE_PINS_NAME
        if not pins_file.is_file():
            if strict_pins:
                raise PinRegistryError(
                    f"pin registry missing: {pins_file} (strict_pins=True refuses to continue with an empty lock set)"
                )
        else:
            try:
                data = json.loads(pins_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError as error:
                if strict_pins:
                    raise PinRegistryError(f"pin registry is not valid JSON: {pins_file}: {error}") from error
                data = None
            if data is None:
                pass
            elif not isinstance(data, dict) or not isinstance(data.get("entries"), list):
                if strict_pins:
                    raise PinRegistryError(
                        f"pin registry has no 'entries' list: {pins_file}"
                    )
            else:
                for item in data["entries"]:
                    if isinstance(item, dict) and item.get("path"):
                        self.locked[str(Path(item["path"]).resolve()).lower()] = "source_pin"
                    elif strict_pins:
                        raise PinRegistryError(
                            f"pin registry entry without a path: {pins_file}"
                        )
                self.loaded_pin_count = len(self.locked)

        for path in extra_locked:
            self.locked[str(Path(path).resolve()).lower()] = "extra_locked"

    # -- classification -------------------------------------------------
    def is_locked(self, path: Path) -> str | None:
        return self.locked.get(str(Path(path).resolve()).lower())

    def is_living_document(self, path: Path) -> bool:
        resolved = Path(path).resolve()
        if resolved.parent != self.handoff_dir.resolve():
            return False
        return resolved.name in LIVING_HANDOFF_DOCUMENTS

    def is_pin_registry(self, path: Path) -> bool:
        resolved = Path(path).resolve()
        if resolved.parent != self.handoff_dir.resolve():
            return False
        return resolved.name in PIN_REGISTRY_NAMES

    def is_inside_stage(self, path: Path) -> bool:
        try:
            return Path(path).resolve().is_relative_to(self.stage_dir)
        except OSError:
            return False

    # -- rules ----------------------------------------------------------
    def assert_can_write(self, path: Path) -> Path:
        target = Path(path)
        resolved = target.resolve()
        lock = self.is_locked(target)

        # 1. sealed source pins win over everything
        if lock == "source_pin":
            raise WriteRefused(
                "source_pin", target,
                "target is sealed; write a new file (e.g. a -deepseek-01 variant) instead",
            )

        # 2. explicit extra locks win over the living-document allowance
        if lock == "extra_locked":
            raise WriteRefused(
                "extra_locked", target,
                "target is explicitly locked; write a new file instead",
            )

        # 3. the pin registry is not an ordinary living document
        if self.is_pin_registry(target) and not self.allow_tracked_updates:
            raise WriteRefused(
                "pin_registry_locked", target,
                "re-pinning needs an explicit authorisation: construct the guard with allow_tracked_updates=True",
            )

        # 4. boundary: inside the project or inside the designated stage
        inside_root = resolved.is_relative_to(self.root)
        inside_stage = resolved.is_relative_to(self.stage_dir)
        inside_handoff = resolved.parent == self.handoff_dir.resolve()
        if not (inside_root or inside_stage or inside_handoff):
            raise WriteRefused("outside_allowed_boundary", target, str(resolved))
        if target.is_symlink():
            link_target = target.resolve()
            if not (link_target.is_relative_to(self.root)
                    or link_target.is_relative_to(self.stage_dir)
                    or link_target.parent == self.handoff_dir.resolve()):
                raise WriteRefused("symlink_escape", target, str(link_target))

        # 5. ordinary living handoff documents stay writable
        if self.is_living_document(target):
            return target

        # 6. create-only
        if self.create_only and target.exists():
            raise WriteRefused("already_exists", target, "caller requested create-only output")

        return target

    # -- receipt timing -------------------------------------------------
    @contextmanager
    def plan_receipt(self, receipt_path: Path, payload_builder) -> Iterator[dict]:
        """Yield a dict the caller fills in; the receipt is published only if the
        block completes without raising.

        The staging path goes through the same guard rules as any other output,
        and an existing ``.partial`` is never overwritten, so a previous
        interrupted run is not silently clobbered.
        """
        target = self.assert_can_write(receipt_path)
        temporary = self._staging_path(target)
        if temporary.exists():
            raise WriteRefused(
                "partial_already_exists", temporary,
                "a previous run left a staging file; inspect it instead of overwriting",
            )
        state: dict = {}
        yield state
        payload = payload_builder(state)
        temporary.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        if not temporary.is_file():
            raise RuntimeError(f"receipt staging failed: {temporary}")
        os.replace(temporary, target)

    def _staging_path(self, target: Path) -> Path:
        temporary = target.with_name(target.name + ".partial")
        # the staging file is an output in its own right: apply the same rules,
        # minus create-only (existence is checked explicitly by the caller)
        self._assert_staging_allowed(temporary)
        return temporary

    def _assert_staging_allowed(self, temporary: Path) -> None:
        resolved = temporary.resolve()
        lock = self.is_locked(temporary)
        if lock is not None:
            raise WriteRefused(lock, temporary, "staging path is sealed")
        if self.is_pin_registry(temporary):
            raise WriteRefused("pin_registry_locked", temporary, "staging path targets the pin registry")
        inside_root = resolved.is_relative_to(self.root)
        inside_stage = resolved.is_relative_to(self.stage_dir)
        if not (inside_root or inside_stage or resolved.parent == self.handoff_dir.resolve()):
            raise WriteRefused("outside_allowed_boundary", temporary, str(resolved))

    def verify_complete(self, required: Iterable[Path]) -> list[str]:
        """Return the list of required artefacts that are missing."""
        return [str(p) for p in required if not Path(p).is_file()]


def load_guard(
    root: Path,
    *,
    stage_dir: Path,
    extra_locked: Iterable[Path] = (),
    create_only: bool = True,
    handoff_dir: Path = HANDOFF_DIR_DEFAULT,
    strict_pins: bool = True,
    allow_tracked_updates: bool = False,
) -> OutputGuard:
    return OutputGuard(
        root,
        stage_dir=stage_dir,
        extra_locked=extra_locked,
        create_only=create_only,
        handoff_dir=handoff_dir,
        strict_pins=strict_pins,
        allow_tracked_updates=allow_tracked_updates,
    )
