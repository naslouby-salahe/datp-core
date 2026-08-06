"""Threshold calibration and persisted evaluation evidence loading."""

from pathlib import Path

import polars as pl
from pydantic import ValidationError

from datp_core.domain.enums import MetricId, PartitionRole, ScoreFrameColumn
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values.checksums import checksum_file
from datp_core.domain.values.ratios import MetricValue
from datp_core.evaluation.federated.contracts import FederatedEvaluationDocument
from datp_core.evaluation.models import MetricStatus, metric_by_id
from datp_core.pipeline.scoring.models import FederatedScoreArtifactManifest
from datp_core.protocols.inference import FixedScoreInvariant
from datp_core.thresholding.quantiles import ClientBenignCalibrationScores


def eligible_calibration_scores(
    score_manifest: FederatedScoreArtifactManifest,
    role: PartitionRole = PartitionRole.CALIBRATION,
) -> tuple[ClientBenignCalibrationScores, ...]:
    invariant = FixedScoreInvariant.from_manifest(score_manifest)
    if role is PartitionRole.CALIBRATION:
        score_set_checksum = invariant.calibration_score_set_checksum
    elif role is PartitionRole.FUTURE_RECALIBRATION:
        score_set_checksum = invariant.future_recalibration_score_set_checksum
    else:
        raise ScientificContractError(
            "threshold calibration scores require a calibration partition role",
            subject=role,
        )
    if score_set_checksum is None:
        raise ScientificContractError("the requested calibration score set is unavailable", subject=role)
    return tuple(
        ClientBenignCalibrationScores(
            record.scored_client,
            score_manifest.coordinate,
            tuple(
                float(value)
                for value in pl.read_parquet(record.path)[ScoreFrameColumn.RECONSTRUCTION_ERROR.value].to_list()
            ),
            checksum_file(record.path),
            score_set_checksum,
        )
        for record in sorted(score_manifest.records_for(role), key=lambda item: item.scored_client)
    )


def load_evaluation_document(path: Path) -> FederatedEvaluationDocument:
    try:
        return FederatedEvaluationDocument.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValidationError, ValueError) as error:
        raise ScientificContractError(f"completed evaluation document is unreadable or invalid: {path}") from error


def population_metric(document: FederatedEvaluationDocument, metric: MetricId) -> MetricValue:
    result = metric_by_id(document.population.metrics, metric)
    if result.status is not MetricStatus.AVAILABLE or result.value is None:
        raise ScientificContractError(f"required metric is unavailable: {metric.value}")
    return result.value
