"""Stage: benign-only calibration eligibility and deterministic subsampling.

A pure computation stage: it consumes an immutable score manifest and produces
typed eligibility decisions and subsampling replicate manifests. It writes nothing
to disk — the downstream threshold-construction stage is the one that publishes
durable, atomically-reusable artifacts.
"""

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
from datp_core.domain.enums import ScoreFrameColumn, StageOperationId
from datp_core.domain.values import CalibrationSize, ReplicateIndex, SubsampleReplicateCount
from datp_core.populations.models import ClientIdentity
from datp_core.protocols.models import CalibrationEligibilityProtocol
from datp_core.scoring.models import FixedScoreInvariant, ScoreArtifactManifest, ScoreRecord


@dataclass(frozen=True, slots=True)
class CalibrateRequest:
    score_manifest: ScoreArtifactManifest
    protocol: CalibrationEligibilityProtocol
    calibration_sizes: tuple[CalibrationSize, ...]
    replicate_count: SubsampleReplicateCount


@dataclass(frozen=True, slots=True)
class CalibrateStageResult:
    stage: StageOperationId
    eligibility: tuple[EligibilityDecision, ...]
    eligible_clients: tuple[ClientIdentity, ...]
    replicate_manifests: tuple[CalibrationReplicateManifest, ...]


def _evaluation_stable_row_ids(record: ScoreRecord) -> frozenset[str]:
    frame = pl.read_parquet(record.path)
    return frozenset(str(value) for value in frame.get_column(ScoreFrameColumn.STABLE_ROW_ID.value).to_list())


def calibrate_stage(request: CalibrateRequest) -> CalibrateStageResult:
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
    return CalibrateStageResult(
        stage=StageOperationId.CALIBRATE,
        eligibility=tuple(decisions),
        eligible_clients=eligible,
        replicate_manifests=replicate_manifests,
    )
