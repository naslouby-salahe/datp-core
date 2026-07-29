"""Deterministic non-temporal and chronological splits on stable row identities."""

from hashlib import sha256

import numpy as np
import polars as pl

from datp_core.domain.enums import PartitionRole, SplitProtocolId, StageOperationId
from datp_core.domain.errors import DataIntegrityError, LeakageError, ScientificContractError
from datp_core.domain.values import Seed, checksum_text
from datp_core.populations.models import (
    CLIENT_ID_COLUMN,
    ORDER_COLUMN,
    OUTCOME_LABEL_COLUMN,
    PARTITION_ROLE_COLUMN,
    PERM_COLUMN,
    SOURCE_ROW_INDEX_COLUMN,
    STABLE_ROW_ID_COLUMN,
    PopulationOutcomeLabel,
    SplitConstructionRequest,
    SplitManifest,
    SplitManifestDocument,
    assignment_column_names,
    hamilton_integer_counts,
    membership_column_names,
)
from datp_core.protocols.models import FractionalSplitProtocol, TemporalSplitProtocol
from datp_core.protocols.splits import NON_TEMPORAL_SPLIT, TEMPORAL_SPLIT

_BENIGN = PopulationOutcomeLabel.BENIGN
_ATTACK = PopulationOutcomeLabel.ATTACK


def non_temporal_split_protocol() -> FractionalSplitProtocol:
    return NON_TEMPORAL_SPLIT


def temporal_split_protocol() -> TemporalSplitProtocol:
    return TEMPORAL_SPLIT


def split_membership(request: SplitConstructionRequest) -> tuple[pl.DataFrame, SplitManifest]:
    frame = _membership_frame(request.membership)
    _require_membership_schema(frame)
    assignments = _assignments_for_protocol(frame, request)
    _assert_split_invariants(assignments, frame)
    return assignments, _split_manifest(assignments, request)


def _membership_frame(membership: object) -> pl.DataFrame:
    if not isinstance(membership, pl.DataFrame):
        raise TypeError("split construction requires a Polars membership DataFrame")
    return membership


def _assignments_for_protocol(membership: pl.DataFrame, request: SplitConstructionRequest) -> pl.DataFrame:
    match request.split_protocol:
        case SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS:
            return _non_temporal_assignments(membership, request.partition_seed)
        case SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE:
            if request.capture_timestamp_column is None:
                raise ScientificContractError(
                    "temporal splits require a capture-timestamp column",
                    subject=request.population,
                    reason="chronological partitioning cannot invent time",
                )
            return _temporal_assignments(membership, request.capture_timestamp_column)
        case _:
            raise ScientificContractError(
                "unsupported split protocol",
                subject=request.split_protocol,
                reason="split protocol is outside the locked catalogue",
            )


def _non_temporal_assignments(membership: pl.DataFrame, partition_seed: Seed) -> pl.DataFrame:
    protocol = non_temporal_split_protocol()
    ratios = (protocol.training.value, protocol.calibration.value, protocol.evaluation.value)
    roles = (PartitionRole.TRAIN, PartitionRole.CALIBRATION, PartitionRole.EVALUATION)
    pieces: list[pl.DataFrame] = []
    for client_id in membership.get_column(CLIENT_ID_COLUMN).unique().sort().to_list():
        client_rows = membership.filter(pl.col(CLIENT_ID_COLUMN) == client_id)
        benign = client_rows.filter(pl.col(OUTCOME_LABEL_COLUMN) == _BENIGN)
        attack = client_rows.filter(pl.col(OUTCOME_LABEL_COLUMN) == _ATTACK)
        pieces.append(_fractional_role_frame(benign, ratios, roles, partition_seed, str(client_id)))
        if attack.height > 0:
            pieces.append(attack.with_columns(pl.lit(PartitionRole.EVALUATION.value).alias(PARTITION_ROLE_COLUMN)))
    if not pieces:
        return membership.clear().with_columns(pl.lit(None, dtype=pl.String).alias(PARTITION_ROLE_COLUMN))
    return (
        pl.concat(pieces, how="vertical_relaxed")
        .select(assignment_column_names())
        .sort([CLIENT_ID_COLUMN, PARTITION_ROLE_COLUMN, STABLE_ROW_ID_COLUMN])
    )


def _temporal_assignments(membership: pl.DataFrame, capture_timestamp_column: str) -> pl.DataFrame:
    if capture_timestamp_column not in membership.columns:
        raise ScientificContractError(
            "membership lacks capture timestamps for chronological split",
            subject=SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE,
            reason="temporal populations require verified capture timestamps",
        )
    protocol = temporal_split_protocol()
    ratios = (
        protocol.historical_training.value,
        protocol.historical_calibration.value,
        protocol.future_recalibration.value,
        protocol.future_evaluation.value,
    )
    roles = (
        PartitionRole.TRAIN,
        PartitionRole.CALIBRATION,
        PartitionRole.FUTURE_RECALIBRATION,
        PartitionRole.EVALUATION,
    )
    if membership.filter(pl.col(OUTCOME_LABEL_COLUMN) == _ATTACK).height > 0:
        raise LeakageError(
            "temporal populations cannot carry client-assigned attack rows",
            subject=SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE,
            reason="Edge temporal evidence is benign-only",
        )
    pieces = [
        _sequential_role_frame(
            _require_sorted_client_rows(membership, client_id, capture_timestamp_column),
            ratios,
            roles,
        )
        for client_id in membership.get_column(CLIENT_ID_COLUMN).unique().sort().to_list()
    ]
    if not pieces:
        return membership.clear().with_columns(pl.lit(None, dtype=pl.String).alias(PARTITION_ROLE_COLUMN))
    output_columns = assignment_column_names() + ((capture_timestamp_column,) if capture_timestamp_column else ())
    return (
        pl.concat(pieces, how="vertical_relaxed")
        .select(output_columns)
        .sort([CLIENT_ID_COLUMN, PARTITION_ROLE_COLUMN, STABLE_ROW_ID_COLUMN])
    )


def _require_sorted_client_rows(
    membership: pl.DataFrame,
    client_id: object,
    capture_timestamp_column: str,
) -> pl.DataFrame:
    client_rows = membership.filter(pl.col(CLIENT_ID_COLUMN) == client_id).sort(
        [capture_timestamp_column, SOURCE_ROW_INDEX_COLUMN, STABLE_ROW_ID_COLUMN]
    )
    if client_rows.get_column(capture_timestamp_column).null_count() > 0:
        raise ScientificContractError(
            "temporal split encountered null capture timestamps",
            subject=str(client_id),
            reason="chronology-eligible groups must retain verified timestamps",
        )
    return client_rows


def _fractional_role_frame(
    frame: pl.DataFrame,
    ratios: tuple[float, ...],
    roles: tuple[PartitionRole, ...],
    partition_seed: Seed,
    client_id: str,
) -> pl.DataFrame:
    if frame.height == 0:
        return frame.with_columns(pl.lit(None, dtype=pl.String).alias(PARTITION_ROLE_COLUMN))
    ordered = frame.sort(STABLE_ROW_ID_COLUMN)
    permutation = _client_permutation(ordered.height, partition_seed, client_id)
    shuffled = (
        ordered.with_row_index(ORDER_COLUMN)
        .with_columns(pl.Series(PERM_COLUMN, permutation))
        .sort(PERM_COLUMN)
        .drop([ORDER_COLUMN, PERM_COLUMN])
    )
    return _sequential_role_frame(shuffled, ratios, roles)


def _sequential_role_frame(
    ordered: pl.DataFrame,
    ratios: tuple[float, ...],
    roles: tuple[PartitionRole, ...],
) -> pl.DataFrame:
    counts = hamilton_integer_counts(ordered.height, ratios)
    if sum(counts) != ordered.height:
        raise DataIntegrityError(
            "Hamilton allocation failed to conserve rows",
            subject=StageOperationId.SPLIT,
            reason="integer residual allocation must preserve every row",
        )
    role_values: list[str] = []
    for role, count in zip(roles, counts, strict=True):
        role_values.extend([role.value] * count)
    return ordered.with_columns(pl.Series(PARTITION_ROLE_COLUMN, role_values))


def _client_permutation(size: int, partition_seed: Seed, client_id: str) -> np.ndarray:
    material = f"{partition_seed.value}:{client_id}".encode()
    digest = sha256(material).digest()
    seed_value = int.from_bytes(digest[:8], byteorder="big", signed=False)
    generator = np.random.Generator(np.random.PCG64(seed_value))
    return generator.permutation(size)


def _assert_split_invariants(assignments: pl.DataFrame, membership: pl.DataFrame) -> None:
    _require_conserved_identities(assignments, membership)
    train_or_cal = assignments.filter(
        pl.col(PARTITION_ROLE_COLUMN).is_in([PartitionRole.TRAIN, PartitionRole.CALIBRATION])
    )
    if train_or_cal.filter(pl.col(OUTCOME_LABEL_COLUMN) == _ATTACK).height > 0:
        raise LeakageError(
            "attack rows entered training or calibration",
            subject=StageOperationId.SPLIT,
            reason="calibration and training are benign-only",
        )


def _require_conserved_identities(assignments: pl.DataFrame, membership: pl.DataFrame) -> None:
    if assignments.height != membership.height:
        raise DataIntegrityError(
            "split assignments must conserve membership rows",
            subject=StageOperationId.SPLIT,
            reason="every membership row requires exactly one partition role",
        )
    if assignments.get_column(STABLE_ROW_ID_COLUMN).n_unique() != assignments.height:
        raise DataIntegrityError(
            "split assignments contain duplicated stable row identities",
            subject=StageOperationId.SPLIT,
            reason="each row may appear in only one partition",
        )
    membership_ids = membership.get_column(STABLE_ROW_ID_COLUMN).sort()
    assignment_ids = assignments.get_column(STABLE_ROW_ID_COLUMN).sort()
    if not membership_ids.equals(assignment_ids):
        raise DataIntegrityError(
            "split assignments alter membership row identities",
            subject=StageOperationId.SPLIT,
            reason="splits must reuse source-row identities exactly",
        )


def _split_manifest(assignments: pl.DataFrame, request: SplitConstructionRequest) -> SplitManifest:
    def count(role: PartitionRole) -> int:
        return int(assignments.filter(pl.col(PARTITION_ROLE_COLUMN) == role).height)

    ordered = assignments.sort([CLIENT_ID_COLUMN, STABLE_ROW_ID_COLUMN])
    payload = "\n".join(
        (
            request.population.value,
            request.dataset.value,
            str(request.partition_seed.value),
            request.split_protocol.value,
            *ordered.get_column(STABLE_ROW_ID_COLUMN).to_list(),
            *ordered.get_column(PARTITION_ROLE_COLUMN).to_list(),
        )
    )
    document = SplitManifestDocument(
        population=request.population,
        dataset=request.dataset,
        partition_seed=request.partition_seed,
        split_protocol=request.split_protocol,
        assignment_row_count=assignments.height,
        train_row_count=count(PartitionRole.TRAIN),
        calibration_row_count=count(PartitionRole.CALIBRATION),
        evaluation_row_count=count(PartitionRole.EVALUATION),
        future_recalibration_row_count=count(PartitionRole.FUTURE_RECALIBRATION),
        assignment_checksum=checksum_text(payload),
        population_manifest_checksum=request.population_manifest_checksum,
    )
    return SplitManifest(document)


def _require_membership_schema(membership: pl.DataFrame) -> None:
    names = membership_column_names()
    missing = [column for column in names if column not in membership.columns]
    if missing:
        raise DataIntegrityError(
            "membership frame is missing required columns",
            subject=StageOperationId.SPLIT,
            reason="population builders must emit the locked membership schema",
        )
