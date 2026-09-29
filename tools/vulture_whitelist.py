"""Reasoned names retained for dynamic framework contracts.

Vulture reads this file as live-name declarations; it is not imported by the
application.
"""

# Pytest injects this fixture for its QApplication lifetime side effect.  Tests
# intentionally do not read the yielded object after injection.
qapp  # ruff: ignore[useless-expression, undefined-name]
