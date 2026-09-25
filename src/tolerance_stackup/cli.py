"""Command-line entry point."""

import argparse
from pathlib import Path

from .engineering import calculate_stackup
from .io import read_components
from .model import Specification
from .reporting import write_json, write_markdown, write_plot
from .statistics import simulate, summarize


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze a one-dimensional tolerance stack-up.")
    parser.add_argument("csv", type=Path, help="component CSV in millimeters")
    parser.add_argument("--lsl", type=float, required=True, help="lower specification limit (mm)")
    parser.add_argument("--usl", type=float, required=True, help="upper specification limit (mm)")
    parser.add_argument(
        "--samples", type=int, default=100_000, help="Monte Carlo samples (default: 100000)"
    )
    parser.add_argument("--seed", type=int, default=20260925, help="random seed")
    parser.add_argument("--output", type=Path, default=Path("."), help="output directory")
    parser.add_argument(
        "--case-description",
        default="User-defined one-dimensional tolerance chain.",
        help="short description included in the report",
    )
    parser.add_argument(
        "--result-name", default="Functional result", help="name for the chain output quantity"
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        components = read_components(args.csv)
        spec = Specification(args.lsl, args.usl)
        stack = calculate_stackup(components)
        samples = simulate(components, args.samples, args.seed)
        summary = summarize(samples, spec, args.seed)
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "plots").mkdir(exist_ok=True)
        (args.output / "reports").mkdir(exist_ok=True)
        write_json(
            args.output / "reports/results.json",
            components,
            spec,
            stack,
            summary,
            args.case_description,
            args.result_name,
        )
        write_markdown(
            args.output / "reports/report.md",
            components,
            spec,
            stack,
            summary,
            args.case_description,
            args.result_name,
        )
        write_plot(
            args.output / "plots/stackup_distribution.png",
            samples,
            spec,
            stack.nominal_mm,
            args.result_name,
        )
    except (OSError, ValueError) as exc:
        raise SystemExit(f"error: {exc}") from exc
    print(f"Nominal result: {stack.nominal_mm:.6f} mm")
    print(f"Worst-case: [{stack.worst_case_min_mm:.6f}, {stack.worst_case_max_mm:.6f}] mm")
    print(f"RSS tolerance: ±{stack.rss_tolerance_mm:.6f} mm")
    print(f"Monte Carlo: mean={summary.mean_mm:.6f} mm, s={summary.standard_deviation_mm:.6f} mm")
    print(f"In spec: {summary.in_spec_percent:.4f}% | out: {summary.out_of_spec_percent:.4f}%")
    cp_text = f"{summary.cp:.4f}" if summary.cp is not None else "undefined (s=0)"
    cpk_text = f"{summary.cpk:.4f}" if summary.cpk is not None else "undefined (s=0)"
    print(f"Cp={cp_text} | Cpk={cpk_text}")
    print(f"Wrote outputs under {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
