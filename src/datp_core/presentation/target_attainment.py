from pathlib import Path

from datp_core.analysis.mechanisms.equity_pareto import EquityTargetAttainmentRow, EquityUtilityParetoView
from datp_core.analysis.metrics.federated import FederatedEvaluationDocument
from datp_core.analysis.metrics.operating_point import HeldOutOperatingPointDiagnostic
from datp_core.core.errors import ErrorMessage, ScientificContractError
from datp_core.core.identifiers import FederatedThresholdMethod, FileContentText
from datp_core.core.numeric import Seed
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


def render_confirmatory_operating_point_table(
    documents: tuple[FederatedEvaluationDocument, ...],
    expected_seeds: tuple[Seed, ...],
) -> str:
    """Render the per-client, per-seed held-out falsification record for the confirmatory pair."""

    _require_complete_confirmatory_pair(documents, expected_seeds)
    lines = [
        "# Confirmatory calibration-to-held-out operating-point record",
        "",
        "This is a design-level falsification record, not a hypothesis test. Calibration and evaluation "
        "row identities are validated as disjoint before threshold construction; no p-value is attached.",
        "",
        "| Seed | Policy | Client | Calibration exceedance | Calibration target error | "
        "Signed test FPR target error | Absolute test FPR target error | "
        "Calibration generalization gap |",
        "| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for document in sorted(documents, key=_document_sort_key):
        lines.extend(
            _operating_point_row(document, diagnostic)
            for diagnostic in sorted(document.diagnostics.held_out_operating_points, key=lambda item: item.client)
        )
    return "\n".join(lines) + "\n"


def export_confirmatory_operating_point_table(
    documents: tuple[FederatedEvaluationDocument, ...],
    expected_seeds: tuple[Seed, ...],
    destination: Path,
) -> Path:
    return write_text_atomically(
        destination,
        FileContentText(render_confirmatory_operating_point_table(documents, expected_seeds)),
    )


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


def _require_complete_confirmatory_pair(
    documents: tuple[FederatedEvaluationDocument, ...],
    expected_seeds: tuple[Seed, ...],
) -> None:
    required_methods = frozenset(
        {
            FederatedThresholdMethod.SHARED_THRESHOLD,
            FederatedThresholdMethod.LOCAL_THRESHOLD,
        }
    )
    observed: dict[Seed, set[FederatedThresholdMethod]] = {}
    for document in documents:
        if document.threshold_method not in required_methods:
            raise ScientificContractError(
                ErrorMessage("confirmatory operating-point record accepts only shared and local threshold evidence")
            )
        methods = observed.setdefault(document.score_coordinate.training_seed, set())
        if document.threshold_method in methods:
            raise ScientificContractError(
                ErrorMessage("confirmatory operating-point record repeats a seed/policy cell")
            )
        methods.add(document.threshold_method)
    expected = frozenset(expected_seeds)
    incomplete = tuple(seed for seed, methods in observed.items() if methods != required_methods)
    if len(expected) != len(expected_seeds) or not expected or incomplete or frozenset(observed) != expected:
        raise ScientificContractError(
            ErrorMessage("confirmatory operating-point record requires each declared shared/local seed pair")
        )


def _document_sort_key(document: FederatedEvaluationDocument) -> tuple[int, str]:
    return (document.score_coordinate.training_seed.value, document.threshold_method.value)


def _operating_point_row(
    document: FederatedEvaluationDocument,
    diagnostic: HeldOutOperatingPointDiagnostic,
) -> str:
    return (
        f"| {document.score_coordinate.training_seed.value} | `{document.threshold_method.value}` | "
        f"`{diagnostic.client.client_id.value}` | {diagnostic.calibration_exceedance.value:.12g} | "
        f"{diagnostic.signed_calibration_target_error.value:.12g} | "
        f"{diagnostic.signed_target_error.value:.12g} | {diagnostic.absolute_target_error.value:.12g} | "
        f"{diagnostic.signed_calibration_generalization_gap.value:.12g} |"
    )
