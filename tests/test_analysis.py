import math

import numpy as np
import pytest

from tolerance_stackup.cli import main
from tolerance_stackup.engineering import calculate_stackup
from tolerance_stackup.io import read_components
from tolerance_stackup.model import Component, Specification
from tolerance_stackup.reporting import write_json
from tolerance_stackup.statistics import simulate, summarize


def test_single_component_known_nominal_and_bounds() -> None:
    result = calculate_stackup([Component("shaft", 20.0, 0.02, 1)])
    assert result.nominal_mm == 20.0
    assert result.worst_case_tolerance_mm == 0.02
    assert result.worst_case_min_mm == pytest.approx(19.98)
    assert result.worst_case_max_mm == pytest.approx(20.02)
    assert result.rss_tolerance_mm == 0.02


def test_signed_chain_and_manual_rss() -> None:
    items = [
        Component("housing", 35.0, 0.08, 1),
        Component("bearing", 10.0, 0.02, -1),
        Component("spacer", 24.9, 0.03, -1),
    ]
    result = calculate_stackup(items)
    assert result.nominal_mm == pytest.approx(0.1)
    assert result.worst_case_tolerance_mm == pytest.approx(0.13)
    assert result.worst_case_min_mm == pytest.approx(-0.03)
    assert result.worst_case_max_mm == pytest.approx(0.23)
    assert result.rss_tolerance_mm == pytest.approx(math.sqrt(0.08**2 + 0.02**2 + 0.03**2))


def test_empty_chain_rejected() -> None:
    with pytest.raises(ValueError, match="at least one"):
        calculate_stackup([])


def test_csv_valid(tmp_path) -> None:
    path = tmp_path / "parts.csv"
    path.write_text(
        "component,nominal_mm,tolerance_mm,direction\nshaft,20,0.02,1\nbearing,5,0.01,-1\n",
        encoding="utf-8",
    )
    assert read_components(path) == [
        Component("shaft", 20.0, 0.02, 1),
        Component("bearing", 5.0, 0.01, -1),
    ]


@pytest.mark.parametrize(
    "content",
    [
        "component,nominal_mm\nshaft,20\n",
        "component,nominal_mm,tolerance_mm,direction\nshaft,20,0.02,0\n",
        "component,nominal_mm,tolerance_mm,direction\nshaft,not-a-number,0.02,1\n",
        "component,nominal_mm,tolerance_mm,direction\nshaft,20,0.02,1,extra\n",
        "component,nominal_mm,tolerance_mm,direction\n",
    ],
)
def test_invalid_csv_rejected(tmp_path, content: str) -> None:
    path = tmp_path / "invalid.csv"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError):
        read_components(path)


def test_negative_tolerance_rejected() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        Component("shaft", 10.0, -0.01, 1)


@pytest.mark.parametrize(
    "nominal,tolerance", [(float("nan"), 0.1), (1.0, float("inf")), (float("-inf"), 0.1)]
)
def test_non_finite_dimensions_rejected(nominal: float, tolerance: float) -> None:
    with pytest.raises(ValueError, match="finite"):
        Component("invalid", nominal, tolerance, 1)


def test_negative_nominal_and_non_finite_specification_rejected() -> None:
    with pytest.raises(ValueError, match="nominal dimension"):
        Component("invalid", -1.0, 0.1, 1)
    with pytest.raises(ValueError, match="finite"):
        Specification(float("nan"), 1.0)


@pytest.mark.parametrize("lsl,usl", [(1.0, 1.0), (2.0, 1.0)])
def test_incoherent_specification_rejected(lsl: float, usl: float) -> None:
    with pytest.raises(ValueError, match="LSL must be less"):
        Specification(lsl, usl)


def test_known_cp_cpk() -> None:
    summary = summarize(np.array([1.0, 2.0, 3.0]), Specification(0.0, 4.0), seed=7)
    assert summary.mean_mm == 2.0
    assert summary.standard_deviation_mm == 1.0
    assert summary.cp == pytest.approx(2.0 / 3.0)
    assert summary.cpk == pytest.approx(2.0 / 3.0)
    assert summary.in_spec_percent == 100.0
    assert summary.out_of_spec_percent == 0.0


def test_cpk_detects_off_center_mean() -> None:
    summary = summarize(np.array([1.0, 1.0, 2.0]), Specification(0.0, 4.0), seed=7)
    assert summary.cpk < summary.cp


def test_monte_carlo_is_reproducible_and_uses_signed_nominal() -> None:
    items = [Component("span", 8.0, 0.3, 1), Component("part", 3.0, 0.4, -1)]
    first = simulate(items, 1000, seed=42)
    second = simulate(items, 1000, seed=42)
    assert np.array_equal(first, second)
    assert float(np.mean(first)) == pytest.approx(5.0, abs=0.06)
    assert float(np.std(first, ddof=1)) == pytest.approx(math.sqrt(0.3**2 + 0.4**2) / 3, abs=0.006)


def test_simulation_and_summary_edge_cases() -> None:
    with pytest.raises(ValueError, match="at least 2"):
        simulate([Component("x", 1.0, 0.1, 1)], 1, seed=1)
    with pytest.raises(ValueError, match="one-dimensional"):
        summarize(np.ones((2, 2)), Specification(0.0, 2.0), seed=1)
    with pytest.raises(ValueError, match="finite"):
        summarize(np.array([1.0, float("nan")]), Specification(0.0, 2.0), seed=1)
    summary = summarize(np.array([-1.0, -1.0]), Specification(0.0, 2.0), seed=1)
    assert summary.out_of_spec_count == 2
    assert summary.out_of_spec_percent == 100.0
    assert summary.cp is None
    assert summary.cpk is None


def test_zero_spread_results_are_json_compatible(tmp_path) -> None:
    components = [Component("exact", 1.0, 0.0, 1)]
    spec = Specification(0.0, 2.0)
    stack = calculate_stackup(components)
    summary = summarize(simulate(components, 10, seed=3), spec, seed=3)
    output = tmp_path / "results.json"
    write_json(output, components, spec, stack, summary, "Exact dimensional chain.", "Result")
    assert '"cp": null' in output.read_text(encoding="utf-8")
    assert '"cpk": null' in output.read_text(encoding="utf-8")


def test_cli_uses_user_supplied_case_labels(tmp_path, monkeypatch) -> None:
    csv_path = tmp_path / "parts.csv"
    csv_path.write_text(
        "component,nominal_mm,tolerance_mm,direction\npart,1,0.01,1\n", encoding="utf-8"
    )
    output = tmp_path / "output"
    monkeypatch.setattr(
        "sys.argv",
        [
            "tolerance-stackup",
            str(csv_path),
            "--lsl",
            "0.9",
            "--usl",
            "1.1",
            "--samples",
            "100",
            "--case-description",
            "Test assembly description.",
            "--result-name",
            "Test clearance",
            "--output",
            str(output),
        ],
    )
    assert main() == 0
    report = (output / "reports/report.md").read_text(encoding="utf-8")
    assert "Test assembly description." in report
    assert "Test clearance" in report
    results = (output / "reports/results.json").read_text(encoding="utf-8")
    assert '"case_description": "Test assembly description."' in results
    assert '"result_name": "Test clearance"' in results
    assert (output / "plots/stackup_distribution.png").is_file()
