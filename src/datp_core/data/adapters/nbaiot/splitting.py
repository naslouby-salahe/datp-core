"""N-BaIoT chronological and random splitting."""

from __future__ import annotations

import math
from pathlib import Path
from random import Random

from datp_core.data.adapters.nbaiot.models import (
    NBaIoTChronologicalBoundaries,
    NBaIoTMaterializedRow,
    NBaIoTSplitRows,
)
from datp_core.data.contracts.enums import SplitMethod
from datp_core.data.contracts.materialization import DatasetMaterialization


def split_nbaiot_chronological_gapped_rows(
    rows: tuple[NBaIoTMaterializedRow, ...],
    train_fraction: float,
    first_gap_fraction: float,
    calibration_fraction: float,
    second_gap_fraction: float,
    test_fraction: float,
) -> NBaIoTSplitRows:
    fractions = (train_fraction, first_gap_fraction,
                 calibration_fraction, second_gap_fraction, test_fraction)
    if any(not 0.0 <= fraction <= 1.0 for fraction in fractions) or not math.isclose(
        sum(fractions), 1.0, rel_tol=0.0, abs_tol=1.0e-12
    ):
        raise ValueError(
            "N-BaIoT chronological split fractions must be probabilities summing exactly to one")
    benign = tuple(row for row in rows if not row.is_attack)
    attack = tuple(row for row in rows if row.is_attack)
    if tuple(sorted(benign, key=lambda row: row.source_row.source_row_index)) != benign:
        raise ValueError("N-BaIoT benign rows must be supplied in ascending source-row order")
    row_count = len(benign)
    train_end = int(train_fraction * row_count)
    first_gap_end = train_end + int(first_gap_fraction * row_count)
    calibration_end = first_gap_end + int(calibration_fraction * row_count)
    second_gap_end = calibration_end + int(second_gap_fraction * row_count)
    return NBaIoTSplitRows(
        train=benign[:train_end],
        calibration=benign[first_gap_end:calibration_end],
        test_benign=benign[second_gap_end:],
        test_attack=attack,
        excluded_gap_rows=benign[train_end:first_gap_end] + benign[calibration_end:second_gap_end],
    )


def calculate_nbaiot_chronological_boundaries(
    row_count: int, materialization: DatasetMaterialization
) -> NBaIoTChronologicalBoundaries:
    if row_count < 0:
        raise ValueError("N-BaIoT source row count cannot be negative")
    if materialization.split_method != SplitMethod.CHRONOLOGICAL_GAPPED:
        raise ValueError(
            "N-BaIoT chronological materialization requires the configured chronological_gapped method")
    train_end = int(float(materialization.ratio("train")) * row_count)
    first_gap_end = train_end + int(float(materialization.ratio("gap_1")) * row_count)
    calibration_end = first_gap_end + int(float(materialization.ratio("calibration")) * row_count)
    second_gap_end = calibration_end + int(float(materialization.ratio("gap_2")) * row_count)
    return NBaIoTChronologicalBoundaries(
        train_end=train_end,
        first_gap_end=first_gap_end,
        calibration_end=calibration_end,
        second_gap_end=second_gap_end,
        row_count=row_count,
    )


def random_fractional_roles(
    row_count: int, materialization: DatasetMaterialization, source_path: Path
) -> tuple[str, ...]:
    if materialization.split_method != SplitMethod.RANDOM_FRACTIONAL or materialization.split_seed is None:
        raise ValueError(
            "N-BaIoT random materialization requires a configured random_fractional split and seed")
    if row_count < 0 or not math.isclose(
        sum(float(materialization.ratio(role)) for role in ("train", "calibration", "test")),
        1.0,
        rel_tol=0.0,
        abs_tol=1.0e-12,
    ):
        raise ValueError("N-BaIoT random split ratios must sum exactly to one")
    indices = list(range(row_count))
    Random(f"{materialization.split_seed.value}:{source_path.as_posix()}").shuffle(indices)
    train_count = int(float(materialization.ratio("train")) * row_count)
    calibration_count = int(float(materialization.ratio("calibration")) * row_count)
    roles = ["test"] * row_count
    for index in indices[:train_count]:
        roles[index] = "train"
    for index in indices[train_count : train_count + calibration_count]:
        roles[index] = "calibration"
    return tuple(roles)


def split_nbaiot_using_resolved_materialization(
    rows: tuple[NBaIoTMaterializedRow, ...], materialization: DatasetMaterialization
) -> NBaIoTSplitRows:
    if materialization.split_method != SplitMethod.CHRONOLOGICAL_GAPPED:
        raise ValueError(
            "N-BaIoT chronological materialization requires the configured chronological_gapped method")
    return split_nbaiot_chronological_gapped_rows(
        rows,
        float(materialization.ratio("train")),
        float(materialization.ratio("gap_1")),
        float(materialization.ratio("calibration")),
        float(materialization.ratio("gap_2")),
        float(materialization.ratio("test")),
    )
