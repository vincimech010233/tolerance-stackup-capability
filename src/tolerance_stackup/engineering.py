"""Deterministic tolerance-chain calculations."""

from collections.abc import Sequence
from math import sqrt

from .model import Component, StackupResult


def calculate_stackup(components: Sequence[Component]) -> StackupResult:
    """Return nominal, arithmetic worst-case bounds, and RSS tolerance in mm."""
    if not components:
        raise ValueError("at least one component is required")
    nominal = sum(item.direction * item.nominal_mm for item in components)
    worst_case = sum(item.tolerance_mm for item in components)
    rss = sqrt(sum(item.tolerance_mm**2 for item in components))
    return StackupResult(
        nominal_mm=nominal,
        worst_case_tolerance_mm=worst_case,
        worst_case_min_mm=nominal - worst_case,
        worst_case_max_mm=nominal + worst_case,
        rss_tolerance_mm=rss,
    )
