"""Primary FedProx μ must be selected from terminal training-loss history only (SF-03)."""

from pathlib import Path

import polars as pl
import pytest

from datp_core.core.errors import LeakageError, ScientificContractError
from datp_core.core.numeric import MetricValue
from datp_core.detector.checkpoints.history import schema_pairs
from datp_core.detector.checkpoints.identities import (
    ROUND_SUMMARY_SCHEMA,
    FederatedHistoryAssetName,
    FederatedHistoryColumn,
)
from datp_core.experiments.common.seeds import CONFIRMATORY_SEED_COHORT
from datp_core.experiments.execution.layout import federated_training_directory
from datp_core.experiments.training_stress.run import (
    collect_fedprox_coefficient_terminal_losses,
    fedprox_training_coordinate,
    load_fedprox_primary_coefficient_decision,
    read_terminal_aggregate_training_loss,
    select_primary_fedprox_coefficient_from_artifacts,
    write_fedprox_primary_coefficient_decision,
)
from datp_core.protocols.training import (
    CHECKPOINT_PROTOCOL,
    FEDPROX_COEFFICIENTS,
    require_non_test_fedprox_coefficient_selection_inputs,
)


def _write_round_summary(directory: Path, *, terminal_loss: float) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    maximum = CHECKPOINT_PROTOCOL.maximum_round.value
    rows = [
        {
            FederatedHistoryColumn.ROUND_NUMBER.value: round_number,
            FederatedHistoryColumn.AGGREGATE_LOSS.value: float(terminal_loss + (maximum - round_number) * 0.01),
            FederatedHistoryColumn.UPLOAD_BYTES.value: 1,
            FederatedHistoryColumn.DOWNLOAD_BYTES.value: 1,
            FederatedHistoryColumn.GLOBAL_STATE_CHECKSUM.value: "a" * 64,
            FederatedHistoryColumn.STATE_BYTES.value: 1,
            FederatedHistoryColumn.LOGICAL_ELEMENT_COUNT.value: 5,
        }
        for round_number in range(1, maximum + 1)
    ]
    # Force exact terminal loss at the locked terminal round.
    rows[-1][FederatedHistoryColumn.AGGREGATE_LOSS.value] = float(terminal_loss)
    pl.DataFrame(rows, schema=schema_pairs(ROUND_SUMMARY_SCHEMA), orient="row").write_parquet(
        directory / FederatedHistoryAssetName.ROUND_SUMMARY.value
    )
    # Minimal companion client frame so history_frames can open both required assets.
    client_rows = [
        {
            FederatedHistoryColumn.ROUND_NUMBER.value: maximum,
            FederatedHistoryColumn.CLIENT_ID.value: "device",
            FederatedHistoryColumn.SAMPLE_COUNT.value: 1,
            FederatedHistoryColumn.LOCAL_LOSS.value: float(terminal_loss),
        }
    ]
    from datp_core.detector.checkpoints.identities import CLIENT_ROUNDS_SCHEMA

    pl.DataFrame(client_rows, schema=schema_pairs(CLIENT_ROUNDS_SCHEMA), orient="row").write_parquet(
        directory / FederatedHistoryAssetName.CLIENT_ROUNDS.value
    )


def _populate_grid(output_root: Path, terminal_losses: tuple[float, float, float, float]) -> None:
    for coefficient, loss in zip(FEDPROX_COEFFICIENTS, terminal_losses, strict=True):
        for seed in CONFIRMATORY_SEED_COHORT.values:
            directory = federated_training_directory(
                fedprox_training_coordinate(seed, coefficient),
                output_root,
            )
            _write_round_summary(directory, terminal_loss=loss)


def test_read_terminal_loss_uses_locked_maximum_round(tmp_path: Path) -> None:
    directory = tmp_path / "history"
    _write_round_summary(directory, terminal_loss=0.42)
    loss = read_terminal_aggregate_training_loss(
        directory,
        maximum_round=CHECKPOINT_PROTOCOL.maximum_round,
    )
    assert loss == MetricValue(0.42)


def test_primary_coefficient_is_lowest_mean_terminal_loss(tmp_path: Path) -> None:
    _populate_grid(tmp_path, (1.0, 0.1, 0.5, 0.8))
    decision = select_primary_fedprox_coefficient_from_artifacts(output_root=tmp_path)
    assert decision.primary_coefficient == FEDPROX_COEFFICIENTS[1]
    assert decision.selection_rule == "fedprox_minimum_terminal_training_loss"
    path = write_fedprox_primary_coefficient_decision(
        decision,
        tmp_path / "primary_coefficient_decision.json",
    )
    loaded = load_fedprox_primary_coefficient_decision(path)
    assert loaded == decision
    assert str(FEDPROX_COEFFICIENTS[1].value) in path.read_text(encoding="utf-8")


def test_primary_selection_breaks_ties_with_smallest_coefficient(tmp_path: Path) -> None:
    _populate_grid(tmp_path, (0.2, 0.2, 0.2, 0.2))
    decision = select_primary_fedprox_coefficient_from_artifacts(output_root=tmp_path)
    assert decision.primary_coefficient == FEDPROX_COEFFICIENTS[0]


def test_missing_history_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(ScientificContractError, match="terminal training loss"):
        collect_fedprox_coefficient_terminal_losses(output_root=tmp_path)


def test_selection_inputs_still_reject_held_out_metrics() -> None:
    with pytest.raises(LeakageError, match="held-out evaluation outcomes"):
        require_non_test_fedprox_coefficient_selection_inputs(
            selection_rule=__import__(
                "datp_core.protocols.training",
                fromlist=["FEDPROX_COEFFICIENT_SELECTION_RULE"],
            ).FEDPROX_COEFFICIENT_SELECTION_RULE,
            held_out_metrics=(MetricValue(0.1),),
            attack_labels_present=False,
        )
