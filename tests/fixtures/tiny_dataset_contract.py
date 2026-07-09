"""Tiny synthetic dataset contract fixture, isolated from DATASET_CONTRACTS and real raw data."""

from __future__ import annotations

from datp_core.data.manifests import DatasetContract, DatasetOutputArtifact
from datp_core.domain.datasets import DatasetId
from datp_core.domain.partitions import CALIBRATION_MIN_ELIGIBLE_ROWS, SplitType
from datp_core.domain.regimes import Regime


def tiny_dataset_contract() -> DatasetContract:
    return DatasetContract(
        dataset_id=DatasetId.N_BAIOT,
        regimes=(Regime.A,),
        raw_subdirectory="tiny_fixture_dataset",
        client_identity_source="synthetic fixture clients",
        split_type=SplitType.CHRONOLOGICAL_GAPPED,
        label_source="synthetic fixture label",
        metadata_feasibility_requirement=None,
        rejected=False,
        rejection_rule=None,
        expected_output_artifacts=(DatasetOutputArtifact.SPLIT_MANIFEST,),
        calibration_min_eligible_rows=CALIBRATION_MIN_ELIGIBLE_ROWS,
    )
