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
from datp_core.datasets.partitioning.contracts import EligibleCohort
from datp_core.domain.contracts import ClientCollection, ClientOwned
from datp_core.domain.enums import ScoreFrameColumn
from datp_core.domain.values.counts import CalibrationSize, ReplicateIndex, SubsampleReplicateCount
from datp_core.domain.values.identifiers import StableRowId
from datp_core.protocols.calibration import CalibrationEligibilityProtocol
from datp_core.detector.scoring.contracts import FixedScoreInvariant, ScoreArtifactManifest, ScoreRecord


@dataclass(frozen=True, slots=True, kw_only=True)
class CalibrationRequest:
    score_manifest: ScoreArtifactManifest
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

    invariant = FixedScoreInvariant.from_manifest(score_manifest)

    evaluation_row_ids_by_client = ClientCollection(
        items=tuple(
            ClientOwned(client=record.scored_client, value=_evaluation_stable_row_ids(record))
            for record in score_manifest.evaluation_records
        )
    )

    decisions = []
    references_items = []

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

        support = calibration_support(record, references, invariant.calibration_score_set_checksum)
        decisions.append(decide_eligibility(support, request.protocol))

    references_collection = ClientCollection(items=tuple(references_items))
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


def _evaluation_stable_row_ids(record: ScoreRecord) -> frozenset[StableRowId]:
    frame = pl.read_parquet(record.path, columns=[ScoreFrameColumn.STABLE_ROW_ID.value])
    values = frame.get_column(ScoreFrameColumn.STABLE_ROW_ID.value).cast(pl.String).to_list()
    return frozenset(StableRowId(value) for value in values)
