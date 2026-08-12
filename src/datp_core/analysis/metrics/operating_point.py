import numpy as np

from datp_core.analysis.metrics.models import AvailableMetric, ClientMetricResult, MetricStatus, metric_by_id
from datp_core.core.contracts import StrictModel
from datp_core.core.errors import ErrorMessage, ScientificContractError
from datp_core.core.identifiers import MetricId
from datp_core.core.numeric import MetricValue, Quantile, Ratio
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.thresholds.quantiles import ClientBenignCalibrationScores


class HeldOutOperatingPointDiagnostic(StrictModel):
    client: ClientIdentity
    calibration_exceedance: Ratio
    signed_calibration_target_error: MetricValue
    held_out_false_positive_rate: Ratio
    signed_target_error: MetricValue
    absolute_target_error: MetricValue
    signed_calibration_generalization_gap: MetricValue
    absolute_calibration_generalization_gap: MetricValue


class HeldOutOperatingPointSummary(StrictModel):
    mean_absolute_target_error: MetricValue
    median_absolute_target_error: MetricValue
    worst_absolute_target_error: MetricValue
    mean_absolute_calibration_generalization_gap: MetricValue
    median_absolute_calibration_generalization_gap: MetricValue
    worst_absolute_calibration_generalization_gap: MetricValue


def evaluate_held_out_operating_points(
    clients: tuple[ClientMetricResult, ...],
    calibration_scores: tuple[ClientBenignCalibrationScores, ...],
    target_quantile: Quantile,
) -> tuple[tuple[HeldOutOperatingPointDiagnostic, ...], HeldOutOperatingPointSummary | None]:
    calibration_by_client = {item.client: item for item in calibration_scores}
    if len(calibration_by_client) != len(calibration_scores):
        raise ScientificContractError(ErrorMessage("operating-point diagnostics require unique calibration clients"))
    diagnostics: list[HeldOutOperatingPointDiagnostic] = []
    target = 1.0 - target_quantile.value
    for client in clients:
        fpr = metric_by_id(client.metrics, MetricId.FALSE_POSITIVE_RATE)
        calibration = calibration_by_client.get(client.client)
        if calibration is None or not isinstance(fpr, AvailableMetric):
            continue
        if fpr.status is not MetricStatus.AVAILABLE:
            raise ScientificContractError(ErrorMessage("available FPR metric has an invalid status"))
        calibration_exceedance = sum(score.exceeds(client.threshold) for score in calibration.scores) / len(
            calibration.scores
        )
        calibration_target_error = calibration_exceedance - target
        signed_target_error = fpr.value.value - target
        generalization_gap = fpr.value.value - calibration_exceedance
        diagnostics.append(
            HeldOutOperatingPointDiagnostic(
                client=client.client,
                calibration_exceedance=Ratio(calibration_exceedance),
                signed_calibration_target_error=MetricValue(calibration_target_error),
                held_out_false_positive_rate=Ratio(fpr.value.value),
                signed_target_error=MetricValue(signed_target_error),
                absolute_target_error=MetricValue(abs(signed_target_error)),
                signed_calibration_generalization_gap=MetricValue(generalization_gap),
                absolute_calibration_generalization_gap=MetricValue(abs(generalization_gap)),
            )
        )
    if not diagnostics:
        return (), None
    target_errors = np.asarray(
        tuple(item.absolute_target_error.value for item in diagnostics), dtype=np.float64
    )
    gaps = np.asarray(
        tuple(item.absolute_calibration_generalization_gap.value for item in diagnostics), dtype=np.float64
    )
    return tuple(diagnostics), HeldOutOperatingPointSummary(
        mean_absolute_target_error=MetricValue(float(np.mean(target_errors))),
        median_absolute_target_error=MetricValue(float(np.median(target_errors))),
        worst_absolute_target_error=MetricValue(float(np.max(target_errors))),
        mean_absolute_calibration_generalization_gap=MetricValue(float(np.mean(gaps))),
        median_absolute_calibration_generalization_gap=MetricValue(float(np.median(gaps))),
        worst_absolute_calibration_generalization_gap=MetricValue(float(np.max(gaps))),
    )
