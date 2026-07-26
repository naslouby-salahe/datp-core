"""CICIoT2023 exact deduplication and deterministic random splitting."""

from __future__ import annotations

import hashlib
import math
import struct
from random import Random

from datp_core.data.adapters.ciciot2023.models import (
    CICIoT2023DeduplicationResult,
    CICIoT2023MaterializedRow,
    CICIoT2023SplitRows,
)
from datp_core.data.contracts.enums import SplitMethod
from datp_core.data.contracts.materialization import DatasetMaterialization


def _validate_split_ratios(materialization: DatasetMaterialization) -> tuple[float, float, float]:
    train_ratio = float(materialization.ratio("train"))
    calibration_ratio = float(materialization.ratio("calibration"))
    test_ratio = float(materialization.ratio("test"))
    if not math.isclose(train_ratio + calibration_ratio + test_ratio, 1.0, rel_tol=0.0, abs_tol=1.0e-12):
        raise ValueError("CICIoT2023 random split ratios must sum exactly to one")
    return train_ratio, calibration_ratio, test_ratio


def canonicalize_and_split_ciciot2023_rows(
    rows: tuple[CICIoT2023MaterializedRow, ...], materialization: DatasetMaterialization
) -> CICIoT2023SplitRows:
    if materialization.split_method != SplitMethod.RANDOM_FRACTIONAL:
        raise ValueError("CICIoT2023 materialization requires the configured random_fractional split")
    if materialization.split_seed is None:
        raise ValueError("CICIoT2023 random split requires an explicit configured split seed")
    train_ratio, calibration_ratio, test_ratio = _validate_split_ratios(materialization)

    ordered_rows = tuple(sorted(rows, key=_provenance_key))
    equivalence_classes: dict[tuple[tuple[float, ...], bool], list[CICIoT2023MaterializedRow]] = {}
    labels_by_feature_hash: dict[str, set[bool]] = {}
    for row in ordered_rows:
        if not all(math.isfinite(value) for value in row.source_row.values):
            raise ValueError("CICIoT2023 source rows must contain only finite numeric model features")
        feature_hash = _feature_hash(row.source_row.values)
        labels_by_feature_hash.setdefault(feature_hash, set()).add(row.identity.is_attack)
        key = (row.source_row.values, row.identity.is_attack)
        equivalence_classes.setdefault(key, []).append(row)

    canonical_rows = tuple(
        group[0] for _, group in sorted(equivalence_classes.items(), key=lambda item: _provenance_key(item[1][0]))
    )
    deduplication = CICIoT2023DeduplicationResult(
        canonical_rows=canonical_rows,
        duplicate_rows_removed=len(ordered_rows) - len(canonical_rows),
        conflicting_label_feature_group_count=sum(len(labels) > 1 for labels in labels_by_feature_hash.values()),
    )

    benign_classes = [
        group
        for _, group in sorted(equivalence_classes.items(), key=lambda item: _equivalence_hash(item[0]))
        if not group[0].identity.is_attack
    ]
    generator = Random(materialization.split_seed.value)
    generator.shuffle(benign_classes)
    train: list[CICIoT2023MaterializedRow] = []
    calibration: list[CICIoT2023MaterializedRow] = []
    test: list[CICIoT2023MaterializedRow] = [
        group[0]
        for _, group in sorted(equivalence_classes.items(), key=lambda item: _equivalence_hash(item[0]))
        if group[0].identity.is_attack
    ]
    for group in benign_classes:
        draw = generator.random()
        canonical = group[0]
        if draw < train_ratio:
            train.append(canonical)
        elif draw < train_ratio + calibration_ratio:
            calibration.append(canonical)
        else:
            test.append(canonical)
    return CICIoT2023SplitRows(
        train=tuple(sorted(train, key=_provenance_key)),
        calibration=tuple(sorted(calibration, key=_provenance_key)),
        test=tuple(sorted(test, key=_provenance_key)),
        deduplication=deduplication,
    )


def _provenance_key(row: CICIoT2023MaterializedRow) -> tuple[str, int]:
    return (row.identity.source_path.as_posix(), row.identity.source_row_index)


def _feature_hash(values: tuple[float, ...]) -> str:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(_serialize_features(values))
    return digest.hexdigest()


def _equivalence_hash(equivalence_key: tuple[tuple[float, ...], bool]) -> str:
    feature_values, is_attack = equivalence_key
    digest = hashlib.blake2b(digest_size=32)
    digest.update(bytes((is_attack,)))
    digest.update(_serialize_features(feature_values))
    return digest.hexdigest()


def _serialize_features(values: tuple[float, ...]) -> bytes:
    return struct.pack(f"!{len(values)}d", *values)
