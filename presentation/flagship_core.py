"""Canonical presentation API for flagship action contracts.

Every public name is imported directly from its physical owner.  Python 3.15
keeps these imports lazy without exposing a dotted-module proxy to callers.
"""

from __future__ import annotations

lazy from application.flagship_action_runtime import (
    ActionExecutor,
    CancellationRegistry,
    parse_plan_json,
)
lazy from domain.flagship_action_models import (
    CAPABILITY_RISK,
    NEVER_AUTOMATE,
    RISK_NAMES,
    UNTRUSTED_INSTRUCTION_PATTERNS,
    ActionPlan,
    ActionRequest,
    ActionResult,
    PolicyDecision,
    RiskLevel,
    contains_untrusted_instruction,
    sanitize_external_content,
)
lazy from domain.flagship_action_policy import PolicyEngine
lazy from domain.safe_error import sanitize_error
lazy from infrastructure.flagship_windows_toolbox import WindowsToolbox

__all__ = (
    "CAPABILITY_RISK",
    "NEVER_AUTOMATE",
    "RISK_NAMES",
    "UNTRUSTED_INSTRUCTION_PATTERNS",
    "ActionExecutor",
    "ActionPlan",
    "ActionRequest",
    "ActionResult",
    "CancellationRegistry",
    "PolicyDecision",
    "PolicyEngine",
    "RiskLevel",
    "WindowsToolbox",
    "contains_untrusted_instruction",
    "parse_plan_json",
    "sanitize_error",
    "sanitize_external_content",
)

# CPython 3.15rc1 otherwise leaves aggregate re-exports as proxy objects in
# ``vars(module)``.  Materializing this compatibility API does not affect the
# startup path, whose consumers import each physical owner directly.
_MATERIALIZED_EXPORTS = (
    CAPABILITY_RISK,
    NEVER_AUTOMATE,
    RISK_NAMES,
    UNTRUSTED_INSTRUCTION_PATTERNS,
    ActionExecutor,
    ActionPlan,
    ActionRequest,
    ActionResult,
    CancellationRegistry,
    PolicyDecision,
    PolicyEngine,
    RiskLevel,
    WindowsToolbox,
    contains_untrusted_instruction,
    parse_plan_json,
    sanitize_error,
    sanitize_external_content,
)
