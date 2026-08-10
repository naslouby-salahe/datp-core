"""Deterministic non-temporal, temporal, and static-reference splits on stable row identities."""

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from math import floor, fsum

import numpy as np
import polars as pl

from datp_core.core.errors import (
    DataIntegrityError,
    ErrorMessage,
    LeakageError,
    ScientificContractError,
)
from datp_core.core.identifiers import (
    CaptureTimestampColumn,
    ClientIdentityToken,
    ContractSubject,
    PartitionRole,
    SplitProtocolId,
    StageOperationId,
)
from datp_core.core.numeric import Ratio, RowCount, Seed, floats_absolutely_close
from datp_core.data.populations.protocols import (
    FRACTION_TOTAL_ABSOLUTE_TOLERANCE,
    HISTORICAL_TEMPORAL_GAP_SPLIT,
    NON_TEMPORAL_SPLIT,
    STATIC_REFERENCE_SPLIT,
    TEMPORAL_SPLIT,
    UNIT_FRACTION_TOTAL,
    FractionalSplitProtocol,
    HistoricalTemporalGapSplitProtocol,
    StaticReferenceSplitProtocol,
    TemporalSplitProtocol,
)

from .contracts import (
    CLIENT_ID_COLUMN,
    ORDER_COLUMN,
    OUTCOME_LABEL_COLUMN,
    PARTITION_ROLE_COLUMN,
    PERM_COLUMN,
    SOURCE_ROW_INDEX_COLUMN,
    STABLE_ROW_ID_COLUMN,
    PopulationOutcomeLabel,
    SplitConstructionRequest,
    SplitManifestDocument,
    TemporalSplitViolation,
    assignment_column_names,
    membership_column_names,
)
from .integrity import validate_no_future_history_leakage


class SplitConstructionViolation(StrEnum):
    UNSUPPORTED_SPLIT_PROTOCOL = "unsupported_split_protocol"
    MISSING_MEMBERSHIP_CAPTURE_TIMESTAMPS = "missing_membership_capture_timestamps"
    TEMPORAL_ATTACK_ROWS_PRESENT = "temporal_attack_rows_present"
    NULL_CAPTURE_TIMESTAMPS = "null_capture_timestamps"
    HAMILTON_ROWS_NOT_CONSERVED = "hamilton_rows_not_conserved"
    ATTACK_ROWS_IN_FIT_ROLES = "attack_rows_in_fit_roles"
    ASSIGNMENT_ROWS_NOT_CONSERVED = "assignment_rows_not_conserved"
    ASSIGNMENT_DUPLICATE_STABLE_ROW_IDENTITIES = "assignment_duplicate_stable_row_identities"
    ASSIGNMENT_IDENTITY_ALTERED = "assignment_identity_altered"
    MISSING_REQUIRED_COLUMNS = "missing_required_columns"


_BENIGN = PopulationOutcomeLabel.BENIGN
_ATTACK = PopulationOutcomeLabel.ATTACK


@dataclass(frozen=True, slots=True, eq=False)
class SplitMembershipResult:
    """Validated role assignments and their manifest for one population membership."""

    assignments: pl.DataFrame
    manifest: SplitManifestDocument


def non_temporal_split_protocol() -> FractionalSplitProtocol:
    return NON_TEMPORAL_SPLIT


def temporal_split_protocol() -> TemporalSplitProtocol:
    return TEMPORAL_SPLIT


def static_reference_split_protocol() -> StaticReferenceSplitProtocol:
    return STATIC_REFERENCE_SPLIT


def historical_temporal_gap_split_protocol() -> HistoricalTemporalGapSplitProtocol:
    return HISTORICAL_TEMPORAL_GAP_SPLIT


def hamilton_integer_counts(
    total: RowCount,
    ratios: tuple[Ratio, ...],
) -> tuple[RowCount, ...]:
    """Largest-remainder (Hamilton) integer allocation.

    For non-negative integer ``total`` and ratios that sum to one:

    1. compute raw shares ``total * ratio_i``;
    2. assign each role ``floor(raw_i)``;
    3. distribute the residual ``total - sum(floors)`` by descending fractional part;
    4. break fractional ties by ascending role index.

    The result conserves every row exactly once and never depends on library defaults.
    """
    _require_hamilton_inputs(total, ratios)
    total_value = total.value
    raw = tuple(total_value * ratio.value for ratio in ratios)
    floors = tuple(floor(value) for value in raw)
    residual = total_value - sum(floors)
    order = sorted(
        range(len(ratios)),
        key=lambda index: (-(raw[index] - floors[index]), index),
    )
    extras = [0] * len(ratios)
    for index in order[:residual]:
        extras[index] = 1
    return tuple(RowCount(floor_value + extra) for floor_value, extra in zip(floors, extras, strict=True))


def split_membership(
    request: SplitConstructionRequest,
) -> SplitMembershipResult:
    frame = request.membership
    _require_membership_schema(frame)
    assignments = _assignments_for_protocol(frame, request)
    _assert_split_invariants(assignments, frame)
    return SplitMembershipResult(
        assignments=assignments,
        manifest=_split_manifest(assignments, request),
    )


def _assignments_for_protocol(
    membership: pl.DataFrame,
    request: SplitConstructionRequest,
) -> pl.DataFrame:
    match request.split_protocol:
        case SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS:
            return _non_temporal_assignments(
                membership,
                request.partition_seed,
            )
        case SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE:
            if request.capture_timestamp_column is None:
                raise ScientificContractError(
                    ErrorMessage("temporal splits require a capture-timestamp column"),
                    subject=request.population,
                    reason=TemporalSplitViolation.CAPTURE_TIMESTAMP_UNAVAILABLE,
                )
            return _temporal_assignments(
                membership,
                request.capture_timestamp_column,
            )
        case SplitProtocolId.RANDOM_FRACTIONAL_STATIC_REFERENCE:
            return _static_reference_assignments(
                membership,
                request.partition_seed,
            )
        case SplitProtocolId.HISTORICAL_TEMPORAL_GAP:
            return _historical_gap_assignments(membership)
        case _:
            raise ScientificContractError(
                ErrorMessage("unsupported split protocol"),
                subject=request.split_protocol,
                reason=SplitConstructionViolation.UNSUPPORTED_SPLIT_PROTOCOL,
            )


def _non_temporal_assignments(
    membership: pl.DataFrame,
    partition_seed: Seed,
) -> pl.DataFrame:
    protocol = non_temporal_split_protocol()
    ratios = (
        protocol.training,
        protocol.calibration,
        protocol.evaluation,
    )
    roles = (
        PartitionRole.TRAIN,
        PartitionRole.CALIBRATION,
        PartitionRole.EVALUATION,
    )
    pieces: list[pl.DataFrame] = []
    for client_id in membership.get_column(CLIENT_ID_COLUMN).unique().sort().to_list():
        client_rows = membership.filter(pl.col(CLIENT_ID_COLUMN) == client_id)
        benign = client_rows.filter(pl.col(OUTCOME_LABEL_COLUMN) == _BENIGN)
        attack = client_rows.filter(pl.col(OUTCOME_LABEL_COLUMN) == _ATTACK)
        pieces.append(
            _fractional_role_frame(
                benign,
                ratios,
                roles,
                partition_seed,
                ClientIdentityToken(client_id),
            )
        )
        if attack.height > 0:
            pieces.append(attack.with_columns(pl.lit(PartitionRole.EVALUATION.value).alias(PARTITION_ROLE_COLUMN)))
    if not pieces:
        return membership.clear().with_columns(pl.lit(None, dtype=pl.String).alias(PARTITION_ROLE_COLUMN))
    return (
        pl.concat(pieces, how="vertical_relaxed")
        .select(assignment_column_names())
        .sort(
            [
                CLIENT_ID_COLUMN,
                PARTITION_ROLE_COLUMN,
                STABLE_ROW_ID_COLUMN,
            ]
        )
    )


def _temporal_assignments(
    membership: pl.DataFrame,
    capture_timestamp_column: CaptureTimestampColumn,
) -> pl.DataFrame:
    if capture_timestamp_column not in membership.columns:
        raise ScientificContractError(
            ErrorMessage("membership lacks capture timestamps for chronological split"),
            subject=SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE,
            reason=SplitConstructionViolation.MISSING_MEMBERSHIP_CAPTURE_TIMESTAMPS,
        )
    protocol = temporal_split_protocol()
    ratios = (
        protocol.historical_training,
        protocol.historical_calibration,
        protocol.future_recalibration,
        protocol.future_evaluation,
    )
    roles = (
        PartitionRole.TRAIN,
        PartitionRole.CALIBRATION,
        PartitionRole.FUTURE_RECALIBRATION,
        PartitionRole.EVALUATION,
    )
    if membership.filter(pl.col(OUTCOME_LABEL_COLUMN) == _ATTACK).height > 0:
        raise LeakageError(
            ErrorMessage("temporal populations cannot carry client-assigned attack rows"),
            subject=SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE,
            reason=SplitConstructionViolation.TEMPORAL_ATTACK_ROWS_PRESENT,
        )
    pieces = [
        _sequential_role_frame(
            _require_sorted_client_rows(
                membership,
                ClientIdentityToken(client_id),
                capture_timestamp_column,
            ),
            ratios,
            roles,
        )
        for client_id in (membership.get_column(CLIENT_ID_COLUMN).unique().sort().to_list())
    ]
    if not pieces:
        return membership.clear().with_columns(pl.lit(None, dtype=pl.String).alias(PARTITION_ROLE_COLUMN))
    output_columns = assignment_column_names() + ((capture_timestamp_column,) if capture_timestamp_column else ())
    assignments = (
        pl.concat(pieces, how="vertical_relaxed")
        .select(output_columns)
        .sort(
            [
                CLIENT_ID_COLUMN,
                PARTITION_ROLE_COLUMN,
                STABLE_ROW_ID_COLUMN,
            ]
        )
    )
    validate_no_future_history_leakage(assignments, capture_timestamp_column)
    return assignments


def _static_reference_assignments(
    membership: pl.DataFrame,
    partition_seed: Seed,
) -> pl.DataFrame:
    """Randomize the same temporal inventory without temporal ordering."""
    if membership.filter(pl.col(OUTCOME_LABEL_COLUMN) == _ATTACK).height > 0:
        raise LeakageError(
            ErrorMessage("the matched static reference is benign-only"),
            subject=SplitProtocolId.RANDOM_FRACTIONAL_STATIC_REFERENCE,
        )
    protocol = static_reference_split_protocol()
    ratios = (
        protocol.training,
        protocol.calibration,
        protocol.reserve,
        protocol.evaluation,
    )
    roles = (
        PartitionRole.TRAIN,
        PartitionRole.CALIBRATION,
        PartitionRole.STATIC_REFERENCE_RESERVE,
        PartitionRole.EVALUATION,
    )
    pieces = [
        _fractional_role_frame(
            membership.filter(pl.col(CLIENT_ID_COLUMN) == client_id),
            ratios,
            roles,
            partition_seed,
            ClientIdentityToken(client_id),
        )
        for client_id in (membership.get_column(CLIENT_ID_COLUMN).unique().sort().to_list())
    ]
    if not pieces:
        return membership.clear().with_columns(pl.lit(None, dtype=pl.String).alias(PARTITION_ROLE_COLUMN))
    return (
        pl.concat(pieces, how="vertical_relaxed")
        .select(assignment_column_names())
        .sort(
            [
                CLIENT_ID_COLUMN,
                PARTITION_ROLE_COLUMN,
                STABLE_ROW_ID_COLUMN,
            ]
        )
    )


def _historical_gap_assignments(membership: pl.DataFrame) -> pl.DataFrame:
    """Legacy-exact chronological 60/1/20/1/18 split with discarded guard gaps.

    Reproduces the historical DATP N-BaIoT preparation: per client, benign rows
    are ordered by their canonical source-row index (file row order) and sliced
    into train, a 1% guard gap, calibration, a second 1% guard gap, and the
    evaluation remainder. Guard gaps receive the DISCARDED role so the split
    conserves every membership row, but never enter model input, calibration,
    scoring, or evaluation. Attack rows are assigned to evaluation.
    """
    protocol = historical_temporal_gap_split_protocol()
    pieces: list[pl.DataFrame] = []
    for client_id in membership.get_column(CLIENT_ID_COLUMN).unique().sort().to_list():
        client_rows = membership.filter(pl.col(CLIENT_ID_COLUMN) == client_id)
        benign = client_rows.filter(pl.col(OUTCOME_LABEL_COLUMN) == _BENIGN)
        attack = client_rows.filter(pl.col(OUTCOME_LABEL_COLUMN) == _ATTACK)
        pieces.append(_historical_gap_role_frame(benign, protocol))
        if attack.height > 0:
            pieces.append(attack.with_columns(pl.lit(PartitionRole.EVALUATION.value).alias(PARTITION_ROLE_COLUMN)))
    if not pieces:
        return membership.clear().with_columns(pl.lit(None, dtype=pl.String).alias(PARTITION_ROLE_COLUMN))
    return (
        pl.concat(pieces, how="vertical_relaxed")
        .select(assignment_column_names())
        .sort(
            [
                CLIENT_ID_COLUMN,
                PARTITION_ROLE_COLUMN,
                STABLE_ROW_ID_COLUMN,
            ]
        )
    )


def _historical_gap_role_frame(
    benign: pl.DataFrame,
    protocol: HistoricalTemporalGapSplitProtocol,
) -> pl.DataFrame:
    if benign.height == 0:
        return benign.with_columns(pl.lit(None, dtype=pl.String).alias(PARTITION_ROLE_COLUMN))
    ordered = benign.sort([SOURCE_ROW_INDEX_COLUMN, STABLE_ROW_ID_COLUMN])
    count = ordered.height
    n_train = floor(count * protocol.training.value)
    n_gap1 = floor(count * protocol.gap1.value)
    n_cal = floor(count * protocol.calibration.value)
    n_gap2 = floor(count * protocol.gap2.value)
    declared = n_train + n_gap1 + n_cal + n_gap2
    if declared > count:
        raise DataIntegrityError(
            ErrorMessage("historical temporal-gap split declared rows exceed client row count"),
            subject=StageOperationId.SPLIT,
            reason=SplitConstructionViolation.HAMILTON_ROWS_NOT_CONSERVED,
        )
    counts = (n_train, n_gap1, n_cal, n_gap2, count - declared)
    roles = (
        PartitionRole.TRAIN,
        PartitionRole.DISCARDED,
        PartitionRole.CALIBRATION,
        PartitionRole.DISCARDED,
        PartitionRole.EVALUATION,
    )
    role_values: list[str] = []
    for role, role_count in zip(roles, counts, strict=True):
        role_values.extend([role.value] * role_count)
    if sum(counts) != count:
        raise DataIntegrityError(
            ErrorMessage("historical temporal-gap allocation failed to conserve rows"),
            subject=StageOperationId.SPLIT,
            reason=SplitConstructionViolation.HAMILTON_ROWS_NOT_CONSERVED,
        )
    return ordered.with_columns(pl.Series(PARTITION_ROLE_COLUMN, role_values))


def _require_sorted_client_rows(
    membership: pl.DataFrame,
    client_id: ClientIdentityToken,
    capture_timestamp_column: CaptureTimestampColumn,
) -> pl.DataFrame:
    client_rows = membership.filter(pl.col(CLIENT_ID_COLUMN) == client_id.value).sort(
        [
            capture_timestamp_column,
            SOURCE_ROW_INDEX_COLUMN,
            STABLE_ROW_ID_COLUMN,
        ]
    )
    if client_rows.get_column(capture_timestamp_column).null_count() > 0:
        raise ScientificContractError(
            ErrorMessage(f"temporal split encountered null capture timestamps for client {client_id.value}"),
            subject=ContractSubject.CLIENT_IDENTITY,
            reason=SplitConstructionViolation.NULL_CAPTURE_TIMESTAMPS,
        )
    return client_rows


def _fractional_role_frame(
    frame: pl.DataFrame,
    ratios: tuple[Ratio, ...],
    roles: tuple[PartitionRole, ...],
    partition_seed: Seed,
    client_id: ClientIdentityToken,
) -> pl.DataFrame:
    if frame.height == 0:
        return frame.with_columns(pl.lit(None, dtype=pl.String).alias(PARTITION_ROLE_COLUMN))
    ordered = frame.sort(STABLE_ROW_ID_COLUMN)
    permutation = _client_permutation(
        RowCount(ordered.height),
        partition_seed,
        client_id,
    )
    shuffled = (
        ordered.with_row_index(ORDER_COLUMN)
        .with_columns(pl.Series(PERM_COLUMN, permutation))
        .sort(PERM_COLUMN)
        .drop([ORDER_COLUMN, PERM_COLUMN])
    )
    return _sequential_role_frame(shuffled, ratios, roles)


def _sequential_role_frame(
    ordered: pl.DataFrame,
    ratios: tuple[Ratio, ...],
    roles: tuple[PartitionRole, ...],
) -> pl.DataFrame:
    counts = hamilton_integer_counts(RowCount(ordered.height), ratios)
    if sum(count.value for count in counts) != ordered.height:
        raise DataIntegrityError(
            ErrorMessage("Hamilton allocation failed to conserve rows"),
            subject=StageOperationId.SPLIT,
            reason=SplitConstructionViolation.HAMILTON_ROWS_NOT_CONSERVED,
        )
    role_values: list[str] = []
    for role, count in zip(roles, counts, strict=True):
        role_values.extend([role.value] * count.value)
    return ordered.with_columns(pl.Series(PARTITION_ROLE_COLUMN, role_values))


def _client_permutation(
    size: RowCount,
    partition_seed: Seed,
    client_id: ClientIdentityToken,
) -> np.ndarray:
    material = f"{partition_seed.value}:{client_id.value}".encode()
    digest = sha256(material).digest()
    seed_value = int.from_bytes(
        digest[:8],
        byteorder="big",
        signed=False,
    )
    generator = np.random.Generator(np.random.PCG64(seed_value))
    return generator.permutation(size.value)


def _assert_split_invariants(
    assignments: pl.DataFrame,
    membership: pl.DataFrame,
) -> None:
    _require_conserved_identities(assignments, membership)
    train_or_cal = assignments.filter(
        pl.col(PARTITION_ROLE_COLUMN).is_in([PartitionRole.TRAIN, PartitionRole.CALIBRATION])
    )
    if train_or_cal.filter(pl.col(OUTCOME_LABEL_COLUMN) == _ATTACK).height > 0:
        raise LeakageError(
            ErrorMessage("attack rows entered training or calibration"),
            subject=StageOperationId.SPLIT,
            reason=SplitConstructionViolation.ATTACK_ROWS_IN_FIT_ROLES,
        )


def _require_conserved_identities(
    assignments: pl.DataFrame,
    membership: pl.DataFrame,
) -> None:
    if assignments.height != membership.height:
        raise DataIntegrityError(
            ErrorMessage("split assignments must conserve membership rows"),
            subject=StageOperationId.SPLIT,
            reason=SplitConstructionViolation.ASSIGNMENT_ROWS_NOT_CONSERVED,
        )
    if assignments.get_column(STABLE_ROW_ID_COLUMN).n_unique() != assignments.height:
        raise DataIntegrityError(
            ErrorMessage("split assignments contain duplicated stable row identities"),
            subject=StageOperationId.SPLIT,
            reason=SplitConstructionViolation.ASSIGNMENT_DUPLICATE_STABLE_ROW_IDENTITIES,
        )
    membership_ids = membership.get_column(STABLE_ROW_ID_COLUMN).sort()
    assignment_ids = assignments.get_column(STABLE_ROW_ID_COLUMN).sort()
    if not membership_ids.equals(assignment_ids):
        raise DataIntegrityError(
            ErrorMessage("split assignments alter membership row identities"),
            subject=StageOperationId.SPLIT,
            reason=SplitConstructionViolation.ASSIGNMENT_IDENTITY_ALTERED,
        )


def _split_manifest(
    assignments: pl.DataFrame,
    request: SplitConstructionRequest,
) -> SplitManifestDocument:
    def count(role: PartitionRole) -> RowCount:
        return RowCount(int(assignments.filter(pl.col(PARTITION_ROLE_COLUMN) == role).height))

    return SplitManifestDocument(
        population=request.population,
        dataset=request.dataset,
        partition_seed=request.partition_seed,
        split_protocol=request.split_protocol,
        assignment_row_count=RowCount(assignments.height),
        train_row_count=count(PartitionRole.TRAIN),
        calibration_row_count=count(PartitionRole.CALIBRATION),
        evaluation_row_count=count(PartitionRole.EVALUATION),
        future_recalibration_row_count=count(PartitionRole.FUTURE_RECALIBRATION),
        static_reference_reserve_row_count=count(PartitionRole.STATIC_REFERENCE_RESERVE),
        discarded_row_count=count(PartitionRole.DISCARDED),
    )


def _require_membership_schema(membership: pl.DataFrame) -> None:
    names = membership_column_names()
    missing = [column for column in names if column not in membership.columns]
    if missing:
        raise DataIntegrityError(
            ErrorMessage("membership frame is missing required columns"),
            subject=StageOperationId.SPLIT,
            reason=SplitConstructionViolation.MISSING_REQUIRED_COLUMNS,
        )


def _require_hamilton_inputs(
    total: RowCount,
    ratios: tuple[Ratio, ...],
) -> None:
    if total.value < 0:
        raise ValueError("Hamilton allocation requires a non-negative total")
    if not ratios or any(ratio.value < 0 for ratio in ratios):
        raise ValueError("Hamilton allocation requires non-negative ratios that sum to one")
    if not floats_absolutely_close(
        fsum(ratio.value for ratio in ratios),
        UNIT_FRACTION_TOTAL,
        FRACTION_TOTAL_ABSOLUTE_TOLERANCE,
    ):
        raise ValueError("Hamilton allocation requires non-negative ratios that sum to one")
