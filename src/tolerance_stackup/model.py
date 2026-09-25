"""Input models and validation for a one-dimensional tolerance chain."""

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class Component:
    name: str
    nominal_mm: float
    tolerance_mm: float
    direction: int

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("component name must not be empty")
        if not isfinite(self.nominal_mm) or not isfinite(self.tolerance_mm):
            raise ValueError(f"dimensions for {self.name!r} must be finite")
        if self.nominal_mm < 0:
            raise ValueError(f"nominal dimension for {self.name!r} must be non-negative")
        if self.tolerance_mm < 0:
            raise ValueError(f"tolerance for {self.name!r} must be non-negative")
        if self.direction not in (-1, 1):
            raise ValueError(f"direction for {self.name!r} must be -1 or 1")


@dataclass(frozen=True)
class Specification:
    lsl_mm: float
    usl_mm: float

    def __post_init__(self) -> None:
        if not isfinite(self.lsl_mm) or not isfinite(self.usl_mm):
            raise ValueError("specification limits must be finite")
        if self.lsl_mm >= self.usl_mm:
            raise ValueError("LSL must be less than USL")


@dataclass(frozen=True)
class StackupResult:
    nominal_mm: float
    worst_case_tolerance_mm: float
    worst_case_min_mm: float
    worst_case_max_mm: float
    rss_tolerance_mm: float
