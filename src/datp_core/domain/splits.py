"""Immutable row-level split manifests and their scientific validation rules."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import Enum


class SplitMembership(Enum):
    TRAIN = "train"
    CALIBRATION = "calibration"
    TEST = "test"
    RECALIBRATION_REFERENCE = "recalibration_reference"
    HISTORICAL_TRAINING = "historical_training"
    HISTORICAL_CALIBRATION = "historical_calibration"
    FUTURE_RECALIBRATION = "future_recalibration"
    FUTURE_EVALUATION = "future_evaluation"


@dataclass(frozen=True, slots=True, kw_only=True)
class MaterializedSplitEvidence:
    """Observed schema and immutable row allocation extracted from one payload."""

    manifest: SplitManifest
    schema_columns: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        if not self.schema_columns:
            raise ValueError("Materialized split evidence requires a non-empty schema")


@dataclass(frozen=True, slots=True, kw_only=True)
class SplitManifestEntry:
    source_path: str
    source_row_index: int
    client_id: str
    membership: SplitMembership
    is_attack: bool
    chronology_key: int | None = None

    def __post_init__(self) -> None:
        if not self.source_path:
            raise ValueError("A split manifest entry requires a source path")
        if self.source_row_index < 1:
            raise ValueError("A split manifest row index must be positive")
        if not self.client_id:
            raise ValueError("A split manifest entry requires a client identifier")

    @property
    def row_identity(self) -> tuple[str, int]:
        return self.source_path, self.source_row_index


@dataclass(frozen=True, slots=True, kw_only=True)
class SplitManifest:
    entries: tuple[SplitManifestEntry, ...]
    minimum_benign_calibration_count: int

    def __post_init__(self) -> None:
        if not self.entries:
            raise ValueError("A split manifest cannot be empty")
        if self.minimum_benign_calibration_count < 1:
            raise ValueError("minimum_benign_calibration_count must be positive")
        if len({entry.row_identity for entry in self.entries}) != len(self.entries):
            raise ValueError("A source row may appear in only one split-manifest entry")
        memberships = {entry.membership for entry in self.entries}
        if memberships <= _STANDARD_MEMBERSHIPS:
            _validate_standard_manifest(self.entries, memberships)
        elif memberships <= _STATIC_REFERENCE_MEMBERSHIPS:
            _validate_static_reference_manifest(self.entries, memberships)
        elif memberships <= _TEMPORAL_MEMBERSHIPS:
            _validate_temporal_manifest(self.entries, memberships)
        else:
            raise ValueError("A split manifest cannot mix standard and temporal memberships")

    @property
    def client_ids(self) -> tuple[str, ...]:
        return tuple(sorted({entry.client_id for entry in self.entries}))

    @property
    def eligible_client_ids(self) -> tuple[str, ...]:
        counts = Counter(
            entry.client_id
            for entry in self.entries
            if entry.membership in {SplitMembership.CALIBRATION, SplitMembership.HISTORICAL_CALIBRATION}
            and not entry.is_attack
        )
        return tuple(
            sorted(
                client_id for client_id in self.client_ids if counts[client_id] >= self.minimum_benign_calibration_count
            )
        )

    @property
    def ineligible_client_ids(self) -> tuple[str, ...]:
        eligible = set(self.eligible_client_ids)
        return tuple(client_id for client_id in self.client_ids if client_id not in eligible)

    @property
    def split_counts(self) -> dict[str, int]:
        return dict(sorted(Counter(entry.membership.value for entry in self.entries).items()))

    @property
    def class_counts(self) -> dict[str, int]:
        return {
            "benign": sum(not entry.is_attack for entry in self.entries),
            "attack": sum(entry.is_attack for entry in self.entries),
        }

    @property
    def client_row_counts(self) -> dict[str, int]:
        return dict(sorted(Counter(entry.client_id for entry in self.entries).items()))


_STANDARD_MEMBERSHIPS = {SplitMembership.TRAIN, SplitMembership.CALIBRATION, SplitMembership.TEST}
_STATIC_REFERENCE_MEMBERSHIPS = {
    SplitMembership.TRAIN,
    SplitMembership.CALIBRATION,
    SplitMembership.RECALIBRATION_REFERENCE,
    SplitMembership.TEST,
}
_TEMPORAL_MEMBERSHIPS = {
    SplitMembership.HISTORICAL_TRAINING,
    SplitMembership.HISTORICAL_CALIBRATION,
    SplitMembership.FUTURE_RECALIBRATION,
    SplitMembership.FUTURE_EVALUATION,
}


def _validate_standard_manifest(entries: tuple[SplitManifestEntry, ...], memberships: set[SplitMembership]) -> None:
    if memberships != _STANDARD_MEMBERSHIPS:
        raise ValueError("A standard split manifest requires train, calibration, and test memberships")
    if any(entry.is_attack and entry.membership is not SplitMembership.TEST for entry in entries):
        raise ValueError("Attack rows may not enter standard training or calibration memberships")
    _validate_client_support(entries, SplitMembership.TRAIN, SplitMembership.CALIBRATION)


def _validate_static_reference_manifest(
    entries: tuple[SplitManifestEntry, ...], memberships: set[SplitMembership]
) -> None:
    if memberships != _STATIC_REFERENCE_MEMBERSHIPS:
        raise ValueError("A static-reference split manifest requires all four configured memberships")
    if any(entry.is_attack for entry in entries):
        raise ValueError("Static-reference Edge rows must remain benign and unassigned to attack clients")
    _validate_client_support(entries, SplitMembership.TRAIN, SplitMembership.CALIBRATION)


def _validate_temporal_manifest(entries: tuple[SplitManifestEntry, ...], memberships: set[SplitMembership]) -> None:
    if memberships != _TEMPORAL_MEMBERSHIPS:
        raise ValueError("A temporal split manifest requires all four chronological memberships")
    if any(entry.chronology_key is None for entry in entries):
        raise ValueError("Temporal split manifests require a chronology key for every row")
    if any(
        entry.is_attack
        and entry.membership in {SplitMembership.HISTORICAL_TRAINING, SplitMembership.HISTORICAL_CALIBRATION}
        for entry in entries
    ):
        raise ValueError("Attack rows may not enter temporal training or calibration memberships")
    _validate_client_support(entries, SplitMembership.HISTORICAL_TRAINING, SplitMembership.HISTORICAL_CALIBRATION)
    order = {membership: index for index, membership in enumerate(SplitMembership)}
    for client_id in {entry.client_id for entry in entries}:
        client_entries = sorted(
            (entry for entry in entries if entry.client_id == client_id), key=lambda entry: entry.chronology_key or 0
        )
        memberships_in_order = [order[entry.membership] for entry in client_entries]
        if memberships_in_order != sorted(memberships_in_order):
            raise ValueError(f"Temporal split manifest has future leakage for client '{client_id}'")


def _validate_client_support(
    entries: tuple[SplitManifestEntry, ...],
    training_membership: SplitMembership,
    calibration_membership: SplitMembership,
) -> None:
    clients = {entry.client_id for entry in entries}
    for client_id in clients:
        client_memberships = {entry.membership for entry in entries if entry.client_id == client_id}
        if training_membership not in client_memberships or calibration_membership not in client_memberships:
            raise ValueError(f"Client '{client_id}' lacks required training or calibration membership")
