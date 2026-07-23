"""N-BaIoT configured path identity and label semantics."""

from pathlib import Path

import pytest

from datp_core.bootstrap import build_application
from datp_core.pipeline.identifiers import DatasetId, MaterializationId
from datp_core.datasets.common import SourceRow
from datp_core.datasets.nbaiot import (
    calculate_nbaiot_chronological_boundaries,
    materialize_nbaiot_source_row,
    split_nbaiot_chronological_gapped_rows,
    split_nbaiot_using_resolved_materialization,
)


def test_nbaiot_benign_path_derives_client_and_benign_label(tmp_path: Path) -> None:
    root = tmp_path / "N-BaIoT"
    row = SourceRow(source_path=root / "Ennio_Doorbell" / "benign_traffic.csv", source_row_index=1, values=(1.0,))
    result = materialize_nbaiot_source_row(row, root, "benign_traffic.csv", ("gafgyt_attacks", "mirai_attacks"))
    assert result.client_id == "Ennio_Doorbell"
    assert not result.is_attack
    assert result.attack_family is None


def test_nbaiot_attack_path_derives_family_and_rejects_unknown_layout(tmp_path: Path) -> None:
    root = tmp_path / "N-BaIoT"
    attack_row = SourceRow(
        source_path=root / "Ennio_Doorbell" / "mirai_attacks" / "udp.csv", source_row_index=2, values=(1.0,)
    )
    result = materialize_nbaiot_source_row(attack_row, root, "benign_traffic.csv", ("gafgyt_attacks", "mirai_attacks"))
    assert result.is_attack
    assert result.attack_family == "mirai_attacks"
    unknown = SourceRow(source_path=root / "Ennio_Doorbell" / "unknown.csv", source_row_index=3, values=(1.0,))
    with pytest.raises(ValueError, match="does not satisfy"):
        materialize_nbaiot_source_row(unknown, root, "benign_traffic.csv", ("gafgyt_attacks", "mirai_attacks"))


def test_nbaiot_chronological_split_preserves_gaps_and_attack_evaluation_only(tmp_path: Path) -> None:
    root = tmp_path / "N-BaIoT"
    benign = tuple(
        materialize_nbaiot_source_row(
            SourceRow(source_path=root / "device" / "benign_traffic.csv", source_row_index=index, values=(1.0,)),
            root,
            "benign_traffic.csv",
            ("gafgyt_attacks", "mirai_attacks"),
        )
        for index in range(1, 101)
    )
    attack = materialize_nbaiot_source_row(
        SourceRow(source_path=root / "device" / "mirai_attacks" / "udp.csv", source_row_index=1, values=(1.0,)),
        root,
        "benign_traffic.csv",
        ("gafgyt_attacks", "mirai_attacks"),
    )
    split = split_nbaiot_chronological_gapped_rows(benign + (attack,), 0.60, 0.01, 0.20, 0.01, 0.18)
    assert (len(split.train), len(split.calibration), len(split.test_benign), len(split.excluded_gap_rows)) == (
        60,
        20,
        18,
        2,
    )
    assert split.test_attack == (attack,)


def test_nbaiot_split_uses_the_resolved_authored_anchor_ratios(tmp_path: Path) -> None:
    root = tmp_path / "N-BaIoT"
    rows = tuple(
        materialize_nbaiot_source_row(
            SourceRow(source_path=root / "device" / "benign_traffic.csv", source_row_index=index, values=(1.0,)),
            root,
            "benign_traffic.csv",
            ("gafgyt_attacks", "mirai_attacks"),
        )
        for index in range(1, 101)
    )
    dataset = build_application().config.datasets[DatasetId("nbaiot")]
    materialization = next(item for item in dataset.materializations if item.identifier == MaterializationId("anchor"))
    split = split_nbaiot_using_resolved_materialization(rows, materialization)
    assert (len(split.train), len(split.calibration), len(split.test_benign), len(split.excluded_gap_rows)) == (
        60,
        20,
        18,
        2,
    )


def test_nbaiot_resolved_boundaries_assign_gap_roles_before_streaming(tmp_path: Path) -> None:
    dataset = build_application().config.datasets[DatasetId("nbaiot")]
    materialization = next(item for item in dataset.materializations if item.identifier == MaterializationId("anchor"))
    boundaries = calculate_nbaiot_chronological_boundaries(100, materialization)
    assert [boundaries.role_for_benign_index(index) for index in (0, 59, 60, 61, 80, 81, 99)] == [
        "train",
        "train",
        "excluded_gap",
        "calibration",
        "calibration",
        "excluded_gap",
        "test",
    ]
