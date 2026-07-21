"""Scientific split-manifest validation rules."""

import pytest

from datp_core.domain.splits import SplitManifest, SplitManifestEntry, SplitMembership


def _entry(
    row: int,
    membership: SplitMembership,
    *,
    client: str = "c1",
    attack: bool = False,
    chronology_key: int | None = None,
) -> SplitManifestEntry:
    return SplitManifestEntry(
        source_path="source.csv",
        source_row_index=row,
        client_id=client,
        membership=membership,
        is_attack=attack,
        chronology_key=chronology_key,
    )


def test_manifest_calculates_eligibility_and_counts_from_discrete_rows() -> None:
    manifest = SplitManifest(
        entries=(
            _entry(1, SplitMembership.TRAIN),
            _entry(2, SplitMembership.CALIBRATION),
            _entry(3, SplitMembership.CALIBRATION),
            _entry(4, SplitMembership.TEST, attack=True),
            _entry(5, SplitMembership.TRAIN, client="c2"),
            _entry(6, SplitMembership.CALIBRATION, client="c2"),
            _entry(7, SplitMembership.TEST, client="c2"),
        ),
        minimum_benign_calibration_count=2,
    )

    assert manifest.eligible_client_ids == ("c1",)
    assert manifest.ineligible_client_ids == ("c2",)
    assert manifest.class_counts == {"benign": 6, "attack": 1}
    assert manifest.split_counts == {"calibration": 3, "test": 2, "train": 2}


def test_manifest_rejects_duplicate_row_assignment_and_attack_calibration() -> None:
    with pytest.raises(ValueError, match="only one"):
        SplitManifest(
            entries=(
                _entry(1, SplitMembership.TRAIN),
                _entry(1, SplitMembership.CALIBRATION),
                _entry(2, SplitMembership.TEST),
            ),
            minimum_benign_calibration_count=1,
        )
    with pytest.raises(ValueError, match="Attack rows"):
        SplitManifest(
            entries=(
                _entry(1, SplitMembership.TRAIN),
                _entry(2, SplitMembership.CALIBRATION, attack=True),
                _entry(3, SplitMembership.TEST),
            ),
            minimum_benign_calibration_count=1,
        )


def test_temporal_manifest_rejects_future_leakage() -> None:
    with pytest.raises(ValueError, match="future leakage"):
        SplitManifest(
            entries=(
                _entry(1, SplitMembership.HISTORICAL_TRAINING, chronology_key=2),
                _entry(2, SplitMembership.HISTORICAL_CALIBRATION, chronology_key=1),
                _entry(3, SplitMembership.FUTURE_RECALIBRATION, chronology_key=3),
                _entry(4, SplitMembership.FUTURE_EVALUATION, chronology_key=4),
            ),
            minimum_benign_calibration_count=1,
        )
