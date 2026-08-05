"""Benign-only calibration eligibility and deterministic subsampling service."""

from dataclasses import dataclass

import polars as pl

from datp_core.calibration.eligibility import (
    calibration_support,
    decide_eligibility,
    eligible_clients,
    load_benign_calibration_references,
    reject_calibration_evaluation_overlap,
    reject_score_coordinate_mismatch,
)
from datp_core.calibration.models import CalibrationReplicateManifest, EligibilityDecision
from datp_core.calibration.sampling import build_calibration_replicate
from datp_core.datasets.partitioning.contracts import ClientIdentity
from datp_core.domain.enums import ScoreFrameColumn
from datp_core.domain.values import CalibrationSize, ReplicateIndex, SubsampleReplicateCount
from datp_core.protocols.inference import FixedScoreInvariant, ScoreArtifactManifest, ScoreRecord
from datp_core.protocols.models import CalibrationEligibilityProtocol


@dataclass(frozen=True, slots=True)
class CalibrationRequest:
    score_manifest: ScoreArtifactManifest
    protocol: CalibrationEligibilityProtocol
    calibration_sizes: tuple[CalibrationSize, ...]
    replicate_count: SubsampleReplicateCount


@dataclass(frozen=True, slots=True)
class CalibrationResult:
    eligibility: tuple[EligibilityDecision, ...]
    eligible_clients: tuple[ClientIdentity, ...]
    replicate_manifests: tuple[CalibrationReplicateManifest, ...]


def calibrate(request: CalibrationRequest) -> CalibrationResult:
    reject_score_coordinate_mismatch(request.score_manifest.calibration_records)
    invariant = FixedScoreInvariant.from_manifest(request.score_manifest)
    evaluation_row_ids_by_client = {
        record.scored_client.client_id: _evaluation_stable_row_ids(record)
        for record in request.score_manifest.evaluation_records
    }
    decisions: list[EligibilityDecision] = []
    references_by_client = {}
    ordered_calibration_records = sorted(
        request.score_manifest.calibration_records,
        key=lambda record: record.scored_client,
    )
    for record in ordered_calibration_records:
        references = load_benign_calibration_references(record)
        reject_calibration_evaluation_overlap(
            frozenset(reference.stable_row_id for reference in references),
            evaluation_row_ids_by_client.get(record.scored_client.client_id, frozenset()),
        )
        references_by_client[record.scored_client] = references
        support = calibration_support(record, references, invariant.calibration_score_set_checksum)
        decisions.append(decide_eligibility(support, request.protocol))
    eligible = eligible_clients(tuple(decisions))
    replicate_manifests = tuple(
        build_calibration_replicate(
            client=client,
            coordinate=request.score_manifest.coordinate,
            training_seed=request.score_manifest.coordinate.training_seed,
            replicate_index=ReplicateIndex(replicate_index),
            references=references_by_client[client],
            sizes=request.calibration_sizes,
        )
        for client in eligible
        for replicate_index in range(request.replicate_count.value)
    )
    return CalibrationResult(
        eligibility=tuple(decisions),
        eligible_clients=eligible,
        replicate_manifests=replicate_manifests,
    )


def _evaluation_stable_row_ids(record: ScoreRecord) -> frozenset[str]:
    frame = pl.read_parquet(record.path)
    return frozenset(str(value) for value in frame.get_column(ScoreFrameColumn.STABLE_ROW_ID.value).to_list())
