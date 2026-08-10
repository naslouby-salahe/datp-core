"""Benign-only calibration eligibility and deterministic subsampling service."""

from dataclasses import dataclass

import polars as pl

from datp_core.core.contracts import ClientCollection, ClientOwned
from datp_core.core.identifiers import ScoreFrameColumn, StableRowId
from datp_core.core.numeric import CalibrationSize, ReplicateIndex, SubsampleReplicateCount
from datp_core.data.populations.contracts import ClientIdentity, EligibleCohort
from datp_core.detector.scoring.models import FederatedScoreArtifactManifest, FederatedScoreRecord
from datp_core.thresholds.calibration.eligibility import (
    CalibrationSampleReference,
    EligibilityDecision,
    calibration_support,
    decide_eligibility,
    eligible_clients,
    load_benign_calibration_references,
    reject_calibration_evaluation_overlap,
    reject_score_coordinate_mismatch,
)
from datp_core.thresholds.calibration.sampling import CalibrationReplicateManifest, build_calibration_replicate
from datp_core.thresholds.protocols import CalibrationEligibilityProtocol


@dataclass(frozen=True, slots=True, kw_only=True)
class CalibrationRequest:
    score_manifest: FederatedScoreArtifactManifest
    protocol: CalibrationEligibilityProtocol
    calibration_sizes: tuple[CalibrationSize, ...]
    replicate_count: SubsampleReplicateCount


@dataclass(frozen=True, slots=True, kw_only=True)
class CalibrationResult:
    eligibility: tuple[EligibilityDecision, ...]
    eligible_clients: EligibleCohort
    replicate_manifests: tuple[CalibrationReplicateManifest, ...]


def calibrate(request: CalibrationRequest) -> CalibrationResult:
    score_manifest = request.score_manifest
    reject_score_coordinate_mismatch(score_manifest.calibration_records)

    evaluation_row_ids_by_client = ClientCollection(
        items=tuple(
            ClientOwned(client=record.scored_client, value=_evaluation_stable_row_ids(record))
            for record in score_manifest.evaluation_records
        )
    )

    decisions: list[EligibilityDecision] = []
    references_items: list[ClientOwned[ClientIdentity, tuple[CalibrationSampleReference, ...]]] = []

    ordered_calibration_records = sorted(
        score_manifest.calibration_records,
        key=lambda record: record.scored_client,
    )

    for record in ordered_calibration_records:
        client = record.scored_client
        references = load_benign_calibration_references(record)

        calib_row_ids = frozenset(reference.stable_row_id for reference in references)
        reject_calibration_evaluation_overlap(
            calib_row_ids,
            evaluation_row_ids_by_client.require(client),
        )

        references_items.append(ClientOwned(client=client, value=references))

        support = calibration_support(record, references)
        decisions.append(decide_eligibility(support, request.protocol))

    references_collection: ClientCollection[ClientIdentity, tuple[CalibrationSampleReference, ...]] = ClientCollection(
        items=tuple(references_items)
    )
    decisions_tuple = tuple(decisions)
    eligible = eligible_clients(decisions_tuple)

    coordinate = score_manifest.coordinate
    training_seed = coordinate.training_seed
    calib_sizes = request.calibration_sizes

    replicate_manifests = tuple(
        build_calibration_replicate(
            client=client,
            coordinate=coordinate,
            training_seed=training_seed,
            replicate_index=ReplicateIndex(replicate_index),
            references=references_collection.require(client),
            sizes=calib_sizes,
        )
        for client in eligible
        for replicate_index in range(request.replicate_count.value)
    )

    return CalibrationResult(
        eligibility=decisions_tuple,
        eligible_clients=eligible,
        replicate_manifests=replicate_manifests,
    )


def _evaluation_stable_row_ids(record: FederatedScoreRecord) -> frozenset[StableRowId]:
    frame = pl.read_parquet(record.path, columns=[ScoreFrameColumn.STABLE_ROW_ID.value])
    values = frame.get_column(ScoreFrameColumn.STABLE_ROW_ID.value).cast(pl.String).to_list()
    return frozenset(StableRowId(value) for value in values)
