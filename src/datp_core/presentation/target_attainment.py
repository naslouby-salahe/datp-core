from pathlib import Path

from datp_core.analysis.mechanisms.equity_pareto import EquityTargetAttainmentRow, EquityUtilityParetoView
from datp_core.core.identifiers import FileContentText
from datp_core.runtime.filesystem import write_text_atomically


def render_target_attainment_table(view: EquityUtilityParetoView) -> str:
    """Render the held-out diagnostics that accompany every policy in one Pareto view."""

    lines = [
        "# Calibration generalization and target-attainment diagnostics",
        "",
        "| Policy | Mean absolute target error | Mean worst-client target error | "
        "Mean absolute calibration-generalization gap | Seed count |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    lines.extend(_row(row) for row in view.target_attainment)
    return "\n".join(lines) + "\n"


def export_target_attainment_table(view: EquityUtilityParetoView, destination: Path) -> Path:
    return write_text_atomically(destination, FileContentText(render_target_attainment_table(view)))


def _row(row: EquityTargetAttainmentRow) -> str:
    policy = row.threshold_method.value
    if row.shrinkage_weight is not None:
        policy = f"{policy}(lambda={row.shrinkage_weight.value:g})"
    return (
        f"| `{policy}` | {row.mean_absolute_target_error.value:.12g} | "
        f"{row.worst_absolute_target_error.value:.12g} | "
        f"{row.mean_absolute_calibration_generalization_gap.value:.12g} | "
        f"{len(row.seed_mean_absolute_target_errors)} |"
    )
