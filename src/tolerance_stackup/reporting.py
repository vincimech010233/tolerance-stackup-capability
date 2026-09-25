"""Structured output, Markdown report, and plot generation."""

import json
from pathlib import Path
from platform import python_version

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from numpy.typing import NDArray

from .model import Component, Specification, StackupResult
from .statistics import SimulationSummary


def write_json(
    path: Path,
    components: list[Component],
    spec: Specification,
    stack: StackupResult,
    summary: SimulationSummary,
    case_description: str,
    result_name: str,
) -> None:
    data = {
        "units": "mm",
        "case_description": case_description,
        "result_name": result_name,
        "components": [item.__dict__ for item in components],
        "specification": {"lsl_mm": spec.lsl_mm, "usl_mm": spec.usl_mm},
        "stackup": stack.__dict__,
        "monte_carlo": summary.__dict__,
        "distribution_assumption": "independent normal components; each bilateral tolerance is ±3σ",
        "software_versions": {
            "python": python_version(),
            "numpy": np.__version__,
            "matplotlib": matplotlib.__version__,
        },
    }
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def write_markdown(
    path: Path,
    components: list[Component],
    spec: Specification,
    stack: StackupResult,
    summary: SimulationSummary,
    case_description: str,
    result_name: str,
) -> None:
    table_rows = "\n".join(
        f"| {c.name} | {c.nominal_mm:.3f} | ±{c.tolerance_mm:.3f} | {c.direction:+d} |"
        for c in components
    )
    if stack.worst_case_min_mm < spec.lsl_mm or stack.worst_case_max_mm > spec.usl_mm:
        decision = (
            "Los límites worst-case exceden la especificación. La fracción fuera de especificación "
            "y Cp/Cpk describen únicamente la simulación indicada en este informe. Revisar diseño, "
            "tolerancias y datos representativos antes de decidir; no demuestra capacidad "
            "de fabricación."
        )
    else:
        decision = (
            "El intervalo worst-case está dentro de la especificación para esta cadena y sus "
            "tolerancias declaradas. La capacidad simulada sigue siendo condicional a los "
            "supuestos estadísticos y no demuestra capacidad de fabricación."
        )
    cp_text = f"{summary.cp:.4f}" if summary.cp is not None else "indefinido (s=0)"
    cpk_text = f"{summary.cpk:.4f}" if summary.cpk is not None else "indefinido (s=0)"
    text = f"""# Informe de acumulación de tolerancias

## Conjunto y modelo

{case_description} Todas las dimensiones están en milímetros. Se modela una cadena unidimensional
con contribuciones independientes; no se modelan deformación, temperatura ni incertidumbre de
medida.

| Componente | Nominal (mm) | Tolerancia bilateral (mm) | Dirección |
|---|---:|---:|---:|
{table_rows}

La especificación para {result_name} es [{spec.lsl_mm:.3f}, {spec.usl_mm:.3f}] mm (LSL–USL), según
la definición de entrada; no representa necesariamente un plano o norma de fabricante.

## Resultados

| Método / estadístico | Resultado |
|---|---:|
| Nominal | {stack.nominal_mm:.6f} mm |
| Worst-case | {stack.worst_case_min_mm:.6f} a {stack.worst_case_max_mm:.6f} mm |
| Tolerancia worst-case | ±{stack.worst_case_tolerance_mm:.6f} mm |
| RSS | ±{stack.rss_tolerance_mm:.6f} mm |
| Monte Carlo | {summary.count:,} muestras; seed {summary.seed} |
| Media simulada | {summary.mean_mm:.6f} mm |
| Desviación estándar muestral | {summary.standard_deviation_mm:.6f} mm |
| Mínimo / máximo simulados | {summary.minimum_mm:.6f} / {summary.maximum_mm:.6f} mm |
| Dentro de especificación | {summary.in_spec_percent:.4f}% ({summary.in_spec_count}) |
| Fuera de especificación | {summary.out_of_spec_percent:.4f}% ({summary.out_of_spec_count}) |
| Cp / Cpk | {cp_text} / {cpk_text} |

![Distribución Monte Carlo con límites de especificación](../plots/stackup_distribution.png)

## Hipótesis e interpretación

- Worst-case suma aritméticamente todas las magnitudes de tolerancia; cubre cualquier combinación
  de extremos si las cotas y el modelo geométrico son correctos.
- RSS es la raíz de la suma de cuadrados de las tolerancias. Es una estimación estadística para
  contribuciones independientes y centradas, no un límite garantizado worst-case.
- Monte Carlo usa normales independientes centradas en cada nominal y supone que cada tolerancia
  bilateral equivale a ±3σ. Las normales no se truncan: algunas muestras pueden exceder tolerancias.
  La seed permite repetir esta realización; otro número de muestras/seed puede cambiarla.
- Cp = (USL−LSL)/(6s), Cpk = min((USL−media)/(3s), (media−LSL)/(3s)), con desviación muestral s.
  Resumen la dispersión y el centrado del modelo normal simulado. Requieren un proceso estable,
  datos representativos y supuestos de distribución apropiados para interpretarse como capacidad.

## Conclusión técnica prudente

{decision}

Los resultados son sintéticos y educativos. No constituyen validación metrológica ni estudio de
capacidad de proceso real; no certifican producción ni sustituyen datos medidos, análisis de
estabilidad, correlación, sistema de medición o revisión de ingeniería.
"""
    path.write_text(text, encoding="utf-8")


def write_plot(
    path: Path,
    samples: NDArray[np.float64],
    specification: Specification,
    nominal_mm: float,
    result_name: str,
) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5), constrained_layout=True)
    ax.hist(samples, bins=70, color="#2878a5", edgecolor="white", linewidth=0.35)
    ax.axvline(specification.lsl_mm, color="#b33b3b", linestyle="--", label="LSL / USL")
    ax.axvline(specification.usl_mm, color="#b33b3b", linestyle="--")
    ax.axvline(nominal_mm, color="#222222", linestyle=":", label="Nominal")
    ax.set(
        title="Monte Carlo stack-up distribution",
        xlabel=f"{result_name} (mm)",
        ylabel="Count",
    )
    ax.legend(frameon=False)
    fig.savefig(path, format="png", dpi=140, metadata={"Software": ""})
    plt.close(fig)
