"""Monte Carlo model and summary statistics."""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from .model import Component, Specification


@dataclass(frozen=True)
class SimulationSummary:
    count: int
    seed: int
    mean_mm: float
    standard_deviation_mm: float
    minimum_mm: float
    maximum_mm: float
    in_spec_count: int
    out_of_spec_count: int
    in_spec_percent: float
    out_of_spec_percent: float
    cp: float | None
    cpk: float | None


def simulate(components: list[Component], count: int, seed: int) -> NDArray[np.float64]:
    """Sample independent normal dimensions with bilateral tolerance treated as ±3σ."""
    if count < 2:
        raise ValueError("sample count must be at least 2")
    if not components:
        raise ValueError("at least one component is required")
    rng = np.random.default_rng(seed)
    result = np.zeros(count, dtype=np.float64)
    for item in components:
        samples = rng.normal(item.nominal_mm, item.tolerance_mm / 3.0, count)
        result += item.direction * samples
    return result


def summarize(
    samples: NDArray[np.float64], specification: Specification, seed: int
) -> SimulationSummary:
    """Calculate sample statistics, yield, and conventional sample Cp/Cpk."""
    if samples.ndim != 1 or samples.size < 2:
        raise ValueError("at least two one-dimensional samples are required")
    if not np.all(np.isfinite(samples)):
        raise ValueError("samples must all be finite")
    mean = float(np.mean(samples))
    std = float(np.std(samples, ddof=1))
    in_spec = (samples >= specification.lsl_mm) & (samples <= specification.usl_mm)
    in_count = int(np.count_nonzero(in_spec))
    out_count = int(samples.size - in_count)
    if std == 0:
        cp = None
        cpk = None
    else:
        cp = (specification.usl_mm - specification.lsl_mm) / (6.0 * std)
        cpk = min(
            (specification.usl_mm - mean) / (3.0 * std),
            (mean - specification.lsl_mm) / (3.0 * std),
        )
    return SimulationSummary(
        count=int(samples.size),
        seed=seed,
        mean_mm=mean,
        standard_deviation_mm=std,
        minimum_mm=float(np.min(samples)),
        maximum_mm=float(np.max(samples)),
        in_spec_count=in_count,
        out_of_spec_count=out_count,
        in_spec_percent=100.0 * in_count / samples.size,
        out_of_spec_percent=100.0 * out_count / samples.size,
        cp=cp,
        cpk=cpk,
    )
