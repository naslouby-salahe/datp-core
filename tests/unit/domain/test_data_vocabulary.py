from datp_core.domain.data.datasets import Dataset, Regime
from datp_core.domain.data.partitioning import ClientDefinitionStrategy
from datp_core.domain.data.splitting import RecalibrationMode, SplitRole, TemporalOutcome


def test_dataset_vocabulary_is_complete_and_stably_serialized() -> None:
    assert {member.name: member.value for member in Dataset} == {
        "N_BAIOT": "n_baiot",
        "CICIOT2023": "ciciot2023",
        "EDGE_IIOTSET": "edge_iiotset",
    }


def test_regime_vocabulary_excludes_rejected_b_b() -> None:
    assert {member.name: member.value for member in Regime} == {
        "A": "a",
        "B_A": "b_a",
        "C": "c",
        "D": "d",
        "D_TEMPORAL": "d_temporal",
    }
    assert not hasattr(Regime, "B_B")


def test_client_definition_vocabulary_is_complete_and_stably_serialized() -> None:
    assert {member.name: member.value for member in ClientDefinitionStrategy} == {
        "NATURAL_DEVICE": "natural_device",
        "FILE_PSEUDO_CLIENT": "file_pseudo_client",
        "DEVICE_CLIENT": "device_client",
        "GROUP_CLIENT": "group_client",
        "DIRICHLET_SYNTHETIC": "dirichlet_synthetic",
    }


def test_split_vocabulary_is_complete_and_stably_serialized() -> None:
    assert {member.name: member.value for member in SplitRole} == {
        "TRAIN": "train",
        "CALIBRATION": "calibration",
        "TEST": "test",
        "TEMPORAL_EVALUATION": "temporal_evaluation",
    }


def test_recalibration_vocabulary_is_complete_and_stably_serialized() -> None:
    assert {member.name: member.value for member in RecalibrationMode} == {
        "FROZEN": "frozen",
        "ONE_SHOT": "one_shot",
    }


def test_temporal_outcome_vocabulary_is_complete_and_stably_serialized() -> None:
    assert {member.name: member.value for member in TemporalOutcome} == {
        "RECAL_HELPS": "recal_helps",
        "RECAL_INSUFFICIENT": "recal_insufficient",
        "NO_MEANINGFUL_DRIFT": "no_meaningful_drift",
    }
