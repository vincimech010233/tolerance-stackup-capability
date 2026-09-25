"""CSV input parsing."""

import csv
from pathlib import Path

from .model import Component

REQUIRED_COLUMNS = {"component", "nominal_mm", "tolerance_mm", "direction"}


def read_components(path: Path) -> list[Component]:
    """Read component rows from CSV, rejecting missing or malformed data."""
    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None or not REQUIRED_COLUMNS.issubset(reader.fieldnames):
                raise ValueError(f"CSV must contain columns: {', '.join(sorted(REQUIRED_COLUMNS))}")
            components: list[Component] = []
            for line_number, row in enumerate(reader, start=2):
                try:
                    if None in row or any(row[key] is None for key in REQUIRED_COLUMNS):
                        raise ValueError("row has missing or extra fields")
                    components.append(
                        Component(
                            name=row["component"].strip(),
                            nominal_mm=float(row["nominal_mm"]),
                            tolerance_mm=float(row["tolerance_mm"]),
                            direction=int(row["direction"]),
                        )
                    )
                except (ValueError, TypeError) as exc:
                    raise ValueError(f"invalid CSV row {line_number}: {exc}") from exc
    except OSError as exc:
        raise ValueError(f"cannot read input CSV {path}: {exc}") from exc
    if not components:
        raise ValueError("CSV must contain at least one component")
    return components
