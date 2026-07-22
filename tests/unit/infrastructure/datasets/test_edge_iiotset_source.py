"""Edge-IIoTset source identity and numeric parsing tests."""

from pathlib import Path

import polars as pl

from datp_core.composition.root import build_application
from datp_core.domain.identifiers import DatasetId, MaterializationId
from datp_core.infrastructure.datasets.edge_iiotset import (
    EdgeIIoTsetRow,
    EdgeTimestampedRow,
    encode_edge_chronological_split_as_parquet,
    encode_edge_split_as_parquet,
    fit_edge_train_normalization,
    fit_edge_vocabulary,
    index_edge_benign_sources,
    iter_edge_iiotset_source,
    split_edge_benign_rows,
    split_edge_chronological_rows,
)


def test_edge_normal_groups_define_clients_and_hex_numeric_values_are_accepted(tmp_path: Path) -> None:
    normal = tmp_path / "Normal traffic"
    attack = tmp_path / "Attack traffic"
    source = normal / "Distance" / "distance.csv"
    source.parent.mkdir(parents=True)
    source.write_text("n,c,Attack_label,Attack_type\n0x10,,0,Normal\n")
    result = next(iter_edge_iiotset_source(source, normal, attack, ("n",), ("c",), "Attack_label", "Attack_type"))
    assert isinstance(result, EdgeIIoTsetRow)
    assert result.client_id == "Distance" and result.numeric_values == (16.0,) and not result.is_attack


def test_edge_split_is_benign_only_deduplicated_and_vocabulary_is_train_only(tmp_path: Path) -> None:
    source = tmp_path / "Normal traffic" / "Distance" / "distance.csv"
    rows = tuple(
        EdgeIIoTsetRow(
            client_id="Distance",
            is_attack=False,
            source_path=source,
            source_row_index=index,
            numeric_values=(float(index % 3),),
            categorical_values=(category,),
            multiclass_label="Normal",
        )
        for index, category in ((1, "trainable"), (2, "trainable"), (3, "heldout"), (4, "trainable"))
    ) + (
        EdgeIIoTsetRow(
            client_id=None,
            is_attack=True,
            source_path=tmp_path / "Attack traffic" / "attack.csv",
            source_row_index=1,
            numeric_values=(9.0,),
            categorical_values=("attack",),
            multiclass_label="DDoS",
        ),
    )
    dataset = build_application().config.datasets[DatasetId("edge_iiotset")]
    materialization = next(
        item for item in dataset.materializations if item.identifier == MaterializationId("group_benign")
    )
    split = split_edge_benign_rows(rows, materialization)
    assert split.duplicate_rows_removed == 1 and split.unassigned_attack[0].is_attack
    vocabulary = fit_edge_vocabulary(split.train, ("category",))
    assert "attack" not in vocabulary.categories_by_column[0][1]
    normalization = fit_edge_train_normalization(split.train)
    encoded = pl.read_parquet(encode_edge_split_as_parquet(split, ("numeric",), vocabulary, normalization))
    assert "category=attack" not in encoded.columns
    assert encoded.select("numeric").min().item() >= 0.0


def test_edge_chronological_split_corrects_midnight_rollover_and_excludes_modbus(tmp_path: Path) -> None:
    source = tmp_path / "Normal traffic" / "Distance" / "distance.csv"
    rows = tuple(
        EdgeTimestampedRow(
            row=EdgeIIoTsetRow(
                client_id="Distance",
                is_attack=False,
                source_path=source,
                source_row_index=index,
                numeric_values=(float(index),),
                categorical_values=(None,),
                multiclass_label="Normal",
            ),
            time_of_day_seconds=time,
        )
        for index, time in (
            (1, 86_000.0),
            (2, 10.0),
            (3, 20.0),
            (4, 30.0),
            (5, 40.0),
            (6, 50.0),
            (7, 60.0),
            (8, 70.0),
            (9, 80.0),
            (10, 90.0),
        )
    )
    dataset = build_application().config.datasets[DatasetId("edge_iiotset")]
    materialization = next(
        item for item in dataset.materializations if item.identifier == MaterializationId("group_chronological")
    )
    split = split_edge_chronological_rows(rows, materialization, ("Modbus",))
    assert [row.source_row_index for row in split.historical_train] == [1, 2, 3, 4, 5]
    assert [row.source_row_index for row in split.future_evaluation] == [9, 10]
    assert split.excluded_clients == ("Modbus",)
    vocabulary = fit_edge_vocabulary(split.historical_train, ("category",))
    normalization = fit_edge_train_normalization(split.historical_train)
    encoded = pl.read_parquet(
        encode_edge_chronological_split_as_parquet(split, ("numeric",), vocabulary, normalization)
    )
    assert {"is_attack", "chronology_key"} <= set(encoded.columns)
    assert set(encoded["split"]) == {
        "historical_training",
        "historical_calibration",
        "future_recalibration",
        "future_evaluation",
    }


def test_edge_timestamp_parsing_preserves_time_of_day_without_an_absolute_date(tmp_path: Path) -> None:
    normal = tmp_path / "Normal traffic"
    attack = tmp_path / "Attack traffic"
    source = normal / "Distance" / "distance.csv"
    source.parent.mkdir(parents=True)
    source.write_text("time,n,c,Attack_label,Attack_type\n2022 04:33:56.369336000,1,a,0,Normal\n")
    result = next(
        iter_edge_iiotset_source(source, normal, attack, ("n",), ("c",), "Attack_label", "Attack_type", "time")
    )
    assert isinstance(result, EdgeIIoTsetRow)
    assert result.time_of_day_seconds == 16_436.369336


def test_external_edge_index_counts_rejections_and_exact_canonical_rows(tmp_path: Path) -> None:
    normal = tmp_path / "Normal traffic"
    attack = tmp_path / "Attack traffic"
    source = normal / "Distance" / "distance.csv"
    source.parent.mkdir(parents=True)
    source.write_text("n,c,Attack_label,Attack_type\n1,a,0,Normal\n1,a,0,Normal\nbad,a,0,Normal\n")
    report = index_edge_benign_sources((source,), normal, attack, ("n",), ("c",), "Attack_label", "Attack_type")
    assert (report.source_rows_seen, report.excluded_rows, report.canonical_rows) == (3, 1, 1)
