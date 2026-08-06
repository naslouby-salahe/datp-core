"""Threshold calibration and persisted evaluation evidence loading."""

from pathlib import Path

import polars as pl
from pydantic import ValidationError

from datp_core.domain.enums import ContractSubject, MetricId, PartitionRole, ScoreFrameColumn
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values.checksums import checksum_file
from datp_core.domain.values.counts import RowCount
from datp_core.domain.values.ratios import MetricValue, ScoreValue
from datp_core.evaluation.federated.contracts import FederatedEvaluationDocument
from datp_core.evaluation.models import MetricStatus, metric_by_id
from datp_core.pipeline.scoring.models import FederatedScoreArtifactManifest
from datp_core.protocols.calibration import MINIMUM_BENIGN_SUPPORT
from datp_core.protocols.inference import FixedScoreInvariant
from datp_core.thresholding.quantiles import ClientBenignCalibrationScores


def eligible_calibration_scores(
    score_manifest: FederatedScoreArtifactManifest,
    role: PartitionRole = PartitionRole.CALIBRATION,
) -> tuple[ClientBenignCalibrationScores, ...]:
    """Load benign calibration scores for clients that meet the locked support floor.

    Threshold construction must receive only the eligible cohort (``n_k >= 100``).
    Clients below the floor remain present in score artifacts and evaluation
    cohorts, but they must not contribute local quantiles to shared, local,
    family, cluster, or comparator constructions.
    """
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
    candidates = tuple(
        ClientBenignCalibrationScores(
            record.scored_client,
            score_manifest.coordinate,
            tuple(
                ScoreValue(float(value))
                for value in pl.read_parquet(record.path)[ScoreFrameColumn.RECONSTRUCTION_ERROR.value].to_list()
            ),
            checksum_file(record.path),
            score_set_checksum,
        )
        for record in sorted(score_manifest.records_for(role), key=lambda item: item.scored_client)
    )
    eligible = tuple(item for item in candidates if MINIMUM_BENIGN_SUPPORT.fits_within(RowCount(len(item.scores))))
    if not eligible:
        raise ScientificContractError(
            "no client meets the minimum benign calibration support for threshold construction",
            subject=ContractSubject.CALIBRATION,
        )
    return eligible


def load_evaluation_document(path: Path) -> FederatedEvaluationDocument:
    """Load a federated evaluation document only when its COMPLETE digest matches.

    Analysis and peer fixed-score discovery must not accept incomplete, partial,
    or hand-edited documents that lack a matching publication COMPLETE marker.
    """
    from datp_core.domain.provenance import canonical_checksum
    from datp_core.evaluation.federated.publication import FederatedEvaluationAssetName

    complete_path = path.with_name(FederatedEvaluationAssetName.COMPLETE)
    try:
        if not path.is_file():
            raise ScientificContractError(
                f"completed evaluation document is missing: {path}",
                subject=ContractSubject.ARTIFACT_PATH,
            )
        if not complete_path.is_file():
            raise ScientificContractError(
                f"evaluation COMPLETE marker is missing for document: {path}",
                subject=ContractSubject.ARTIFACT_PATH,
            )
        document = FederatedEvaluationDocument.model_validate_json(path.read_text(encoding="utf-8"))
        marker = complete_path.read_text(encoding="utf-8").strip()
        if marker != canonical_checksum(document).value:
            raise ScientificContractError(
                f"evaluation COMPLETE digest does not match document identity: {path}",
                subject=ContractSubject.ARTIFACT_PATH,
            )
        return document
    except ScientificContractError:
        raise
    except (OSError, UnicodeError, ValidationError, ValueError) as error:
        raise ScientificContractError(
            f"completed evaluation document is unreadable or invalid: {path}",
            subject=ContractSubject.ARTIFACT_PATH,
        ) from error


def population_metric(document: FederatedEvaluationDocument, metric: MetricId) -> MetricValue:
    result = metric_by_id(document.population.metrics, metric)
    if result.status is not MetricStatus.AVAILABLE or result.value is None:
        raise ScientificContractError(f"required metric is unavailable: {metric.value}")
    return result.value
