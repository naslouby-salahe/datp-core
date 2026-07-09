import pytest

from datp_core.data.manifests import (
    DATASET_CONTRACTS,
    DatasetContractError,
    contract_from_dict,
    contract_to_dict,
    require_raw_dataset_present,
)
from datp_core.domain.datasets import DatasetId
from datp_core.domain.regimes import Regime
from datp_core.utils.paths import RepoPaths


def test_nbaiot_supports_regime_a_and_c():
    contract = DATASET_CONTRACTS["nbaiot"]
    assert contract.dataset_id is DatasetId.N_BAIOT
    assert contract.regimes == (Regime.A, Regime.C)


def test_ciciot2023_file_level_supports_b_a_only():
    contract = DATASET_CONTRACTS["ciciot2023_file_level"]
    assert contract.dataset_id is DatasetId.CICIOT2023
    assert contract.regimes == (Regime.B_A,)
    assert contract.rejected is False


def test_ciciot2023_b_b_requires_metadata_feasibility_and_is_rejected():
    contract = DATASET_CONTRACTS["ciciot2023_rejected_b_b"]
    assert contract.regimes == (Regime.B_B_REJECTED_NO_METADATA,)
    assert contract.rejected is True
    assert contract.metadata_feasibility_requirement is not None
    assert contract.rejection_rule is not None


def test_edge_iiotset_supports_regime_d():
    contract = DATASET_CONTRACTS["edge_iiotset"]
    assert contract.dataset_id is DatasetId.EDGE_IIOTSET
    assert Regime.D in contract.regimes
    assert Regime.D_TEMPORAL in contract.regimes


def test_rejected_contract_requires_rejection_rule():
    with pytest.raises(ValueError):
        DATASET_CONTRACTS["nbaiot"].__class__(
            dataset_id=DatasetId.N_BAIOT,
            regimes=(Regime.A,),
            raw_subdirectory="nbaiot",
            client_identity_source="x",
            split_type=DATASET_CONTRACTS["nbaiot"].split_type,
            label_source="x",
            metadata_feasibility_requirement=None,
            rejected=True,
            rejection_rule=None,
            expected_output_artifacts=(),
        )


def test_missing_raw_path_is_reported_not_created(tmp_path):
    repo_paths = RepoPaths(
        repo_root=tmp_path,
        configs=tmp_path / "configs",
        data=tmp_path / "data",
        data_raw=tmp_path / "data" / "raw",
        data_preprocessed=tmp_path / "data" / "preprocessed",
        data_manifests=tmp_path / "data" / "manifests",
        checkpoints=tmp_path / "checkpoints",
        outputs=tmp_path / "outputs",
        results=tmp_path / "results",
        outputs_logs=tmp_path / "outputs" / "logs",
        outputs_scores=tmp_path / "outputs" / "scores",
        outputs_metrics=tmp_path / "outputs" / "metrics",
        outputs_manifests=tmp_path / "outputs" / "manifests",
        outputs_tables=tmp_path / "outputs" / "tables",
        outputs_figures=tmp_path / "outputs" / "figures",
    )
    contract = DATASET_CONTRACTS["nbaiot"]
    with pytest.raises(DatasetContractError):
        require_raw_dataset_present(contract, repo_paths)
    assert not (tmp_path / "data" / "raw" / "nbaiot").exists()


def test_dataset_contract_serializes_and_deserializes():
    for contract in DATASET_CONTRACTS.values():
        data = contract_to_dict(contract)
        restored = contract_from_dict(data)
        assert restored == contract
