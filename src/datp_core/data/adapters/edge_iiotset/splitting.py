"""Edge-IIoTset random benign splitting and chronological splitting."""

from __future__ import annotations

import math
from random import Random

from datp_core.data.adapters.edge_iiotset.models import (
    EdgeChronologicalSplitRows,
    EdgeIIoTsetRow,
    EdgeIIoTsetSplitRows,
    EdgeTimestampedRow,
)
from datp_core.data.contracts.enums import SplitMethod
from datp_core.data.contracts.materialization import DatasetMaterialization


def _provenance_key(row: EdgeIIoTsetRow) -> tuple[str, int]:
    return (row.source_path.as_posix(), row.source_row_index)


def _edge_content_hash(row: EdgeIIoTsetRow) -> str:
    import hashlib

    return hashlib.blake2b(repr((row.numeric_values, row.categorical_values)).encode(), digest_size=32).hexdigest()


def split_edge_benign_rows(
    rows: tuple[EdgeIIoTsetRow, ...], materialization: DatasetMaterialization
) -> EdgeIIoTsetSplitRows:
    if materialization.split_method != SplitMethod.RANDOM_FRACTIONAL or materialization.split_seed is None:
        raise ValueError("Edge-IIoTset benign materialization requires configured random_fractional split and seed")
    train_ratio = float(materialization.ratio("train"))
    calibration_ratio = float(materialization.ratio("calibration"))
    recalibration_ratio = (
        float(materialization.ratio("recalibration_reference"))
        if any(role == "recalibration_reference" for role, _ in materialization.split_ratios)
        else 0.0
    )
    test_ratio = float(materialization.ratio("test"))
    if not math.isclose(
        train_ratio + calibration_ratio + recalibration_ratio + test_ratio, 1.0, rel_tol=0.0, abs_tol=1.0e-12
    ):
        raise ValueError("Edge-IIoTset split ratios must sum exactly to one")
    attacks = tuple(row for row in rows if row.is_attack)
    benign_by_client: dict[str, list[EdgeIIoTsetRow]] = {}
    for row in rows:
        if row.is_attack:
            continue
        if row.client_id is None:
            raise ValueError("Edge-IIoTset benign rows require a configured normal-group client identity")
        benign_by_client.setdefault(row.client_id, []).append(row)
    train: list[EdgeIIoTsetRow] = []
    calibration: list[EdgeIIoTsetRow] = []
    recalibration_reference: list[EdgeIIoTsetRow] = []
    test: list[EdgeIIoTsetRow] = []
    duplicates = 0
    for client_id, client_rows in sorted(benign_by_client.items()):
        canonical: dict[tuple[tuple[float, ...], tuple[str | None, ...]], EdgeIIoTsetRow] = {}
        for row in sorted(client_rows, key=_provenance_key):
            key = (row.numeric_values, row.categorical_values)
            if key in canonical:
                duplicates += 1
            else:
                canonical[key] = row
        ordered = sorted(canonical.values(), key=_edge_content_hash)
        generator = Random(f"{materialization.split_seed.value}:{client_id}")
        for row in ordered:
            draw = generator.random()
            if draw < train_ratio:
                train.append(row)
            elif draw < train_ratio + calibration_ratio:
                calibration.append(row)
            elif draw < train_ratio + calibration_ratio + recalibration_ratio:
                recalibration_reference.append(row)
            else:
                test.append(row)
    return EdgeIIoTsetSplitRows(
        train=tuple(sorted(train, key=_provenance_key)),
        calibration=tuple(sorted(calibration, key=_provenance_key)),
        test=tuple(sorted(test, key=_provenance_key)),
        unassigned_attack=attacks,
        duplicate_rows_removed=duplicates,
        recalibration_reference=tuple(sorted(recalibration_reference, key=_provenance_key)),
    )


def _chronological_split_index(index: int, boundaries: list[int]) -> int:
    if index < boundaries[0]:
        return 0
    if index < boundaries[1]:
        return 1
    if index < boundaries[2]:
        return 2
    return 3


def split_edge_chronological_rows(
    rows: tuple[EdgeTimestampedRow, ...], materialization: DatasetMaterialization, excluded_clients: tuple[str, ...]
) -> EdgeChronologicalSplitRows:
    if materialization.split_method != SplitMethod.WITHIN_CLIENT_CHRONOLOGICAL:
        raise ValueError("Edge-IIoTset chronological setup requires the configured within_client_chronological method")
    fractions = tuple(
        float(materialization.chronological_ratio(role))
        for role in ("historical_train", "historical_calibration", "future_recalibration", "future_evaluation")
    )
    if not math.isclose(sum(fractions), 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError("Edge-IIoTset chronological fractions must sum exactly to one")
    grouped: dict[str, list[EdgeTimestampedRow]] = {}
    for timestamped in rows:
        if timestamped.row.is_attack or timestamped.row.client_id is None:
            raise ValueError("Edge-IIoTset chronological split accepts assigned benign rows only")
        if not math.isfinite(timestamped.time_of_day_seconds) or not 0 <= timestamped.time_of_day_seconds < 86_400:
            raise ValueError("Edge-IIoTset time-of-day values must be finite seconds within one day")
        grouped.setdefault(timestamped.row.client_id, []).append(timestamped)
    roles: tuple[list[EdgeIIoTsetRow], list[EdgeIIoTsetRow], list[EdgeIIoTsetRow], list[EdgeIIoTsetRow]] = (
        [], [], [], []
    )
    for client_id, client_rows in sorted(grouped.items()):
        if client_id in excluded_clients:
            continue
        corrected: list[tuple[float, EdgeIIoTsetRow]] = []
        offset = 0.0
        previous: float | None = None
        for item in sorted(client_rows, key=lambda value: _provenance_key(value.row)):
            if previous is not None and item.time_of_day_seconds < previous:
                offset += 86_400
            corrected.append((item.time_of_day_seconds + offset, item.row))
            previous = item.time_of_day_seconds
        ordered = [row for _, row in sorted(corrected, key=lambda value: (value[0], _provenance_key(value[1])))]
        boundaries = [int(sum(fractions[: index + 1]) * len(ordered)) for index in range(3)]
        for index, row in enumerate(ordered):
            roles[_chronological_split_index(index, boundaries)].append(row)
    return EdgeChronologicalSplitRows(
        historical_train=tuple(roles[0]),
        historical_calibration=tuple(roles[1]),
        future_recalibration=tuple(roles[2]),
        future_evaluation=tuple(roles[3]),
        excluded_clients=tuple(sorted(set(excluded_clients))),
    )
