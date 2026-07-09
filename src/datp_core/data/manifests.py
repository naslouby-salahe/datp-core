"""Dataset contracts (docs/protocol/artifact_contracts.md #1).

A dataset contract is the complete set of facts a loader must verify before
any preprocessing runs. This module only holds the contract data and a raw-
path presence check; no loading, preprocessing, or caching is implemented in
Phase 1.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from datp_core.domain.datasets import DatasetId
from datp_core.domain.partitions import CALIBRATION_MIN_ELIGIBLE_ROWS, SplitType
from datp_core.domain.regimes import Regime
from datp_core.utils.paths import RepoPaths


class DatasetContractError(RuntimeError):
    """Raised when a raw dataset required by a contract is missing."""


class DatasetOutputArtifact(StrEnum):
    COVERAGE_GATE_REPORT = "coverage_gate_report"
    PREPROCESSED_PER_CLIENT_TENSORS = "preprocessed_per_client_tensors"
    PREPROCESSED_PER_DEVICE_TENSORS = "preprocessed_per_device_tensors"
    PREPROCESSED_PER_FILE_TENSORS = "preprocessed_per_file_tensors"
    REJECTION_RECORD = "rejection_record"
    SPLIT_MANIFEST = "split_manifest"


@dataclass(frozen=True)
class DatasetContract:
    dataset_id: DatasetId
    regimes: tuple[Regime, ...]
    raw_subdirectory: str
    client_identity_source: str
    split_type: SplitType
    label_source: str
    metadata_feasibility_requirement: str | None
    rejected: bool
    rejection_rule: str | None
    expected_output_artifacts: tuple[DatasetOutputArtifact, ...]
    calibration_min_eligible_rows: int

    def __post_init__(self) -> None:
        if self.rejected and not self.rejection_rule:
            raise ValueError("a rejected dataset contract must state its rejection_rule")
        if not self.rejected and self.rejection_rule:
            raise ValueError("only a rejected dataset contract may set rejection_rule")
        if not self.regimes:
            raise ValueError("a dataset contract must cover at least one regime")


@dataclass(frozen=True)
class DatasetRegistration:
    name: str
    contract: DatasetContract


DATASET_REGISTRATIONS: tuple[DatasetRegistration, ...] = (
    DatasetRegistration(
        "nbaiot",
        DatasetContract(
            dataset_id=DatasetId.N_BAIOT,
            regimes=(Regime.A, Regime.C),
            raw_subdirectory="N-BaIoT",
            client_identity_source="filename-encoded physical device (9 devices)",
            split_type=SplitType.CHRONOLOGICAL_GAPPED,
            label_source="row provenance (filename) yields benign-vs-attack-family",
            metadata_feasibility_requirement=None,
            rejected=False,
            rejection_rule=None,
            expected_output_artifacts=(
                DatasetOutputArtifact.PREPROCESSED_PER_DEVICE_TENSORS,
                DatasetOutputArtifact.SPLIT_MANIFEST,
            ),
            calibration_min_eligible_rows=CALIBRATION_MIN_ELIGIBLE_ROWS,
        ),
    ),
    DatasetRegistration(
        "ciciot2023_file_level",
        DatasetContract(
            dataset_id=DatasetId.CICIOT2023,
            regimes=(Regime.B_A,),
            raw_subdirectory="ciciot2023",
            client_identity_source="the file itself (63 file-defined pseudo-clients)",
            split_type=SplitType.RANDOM_SHUFFLE_SEQUENTIAL,
            label_source="in-row attack-family label column",
            metadata_feasibility_requirement=None,
            rejected=False,
            rejection_rule=None,
            expected_output_artifacts=(
                DatasetOutputArtifact.PREPROCESSED_PER_FILE_TENSORS,
                DatasetOutputArtifact.SPLIT_MANIFEST,
            ),
            calibration_min_eligible_rows=CALIBRATION_MIN_ELIGIBLE_ROWS,
        ),
    ),
    DatasetRegistration(
        "ciciot2023_rejected_b_b",
        DatasetContract(
            dataset_id=DatasetId.CICIOT2023,
            regimes=(Regime.B_B_REJECTED_NO_METADATA,),
            raw_subdirectory="ciciot2023",
            client_identity_source="none available",
            split_type=SplitType.FEASIBILITY_PENDING,
            label_source="in-row attack-family label column",
            metadata_feasibility_requirement="MAC / device / IP / capture-source / timestamp columns",
            rejected=True,
            rejection_rule=(
                "metadata columns absent on the available CSV artifact; no pseudo-client "
                "substitute, no PCAP-reprocessing branch, no invented device identity (SB-28)"
            ),
            expected_output_artifacts=(DatasetOutputArtifact.REJECTION_RECORD,),
            calibration_min_eligible_rows=CALIBRATION_MIN_ELIGIBLE_ROWS,
        ),
    ),
    DatasetRegistration(
        "edge_iiotset",
        DatasetContract(
            dataset_id=DatasetId.EDGE_IIOTSET,
            regimes=(Regime.D, Regime.D_TEMPORAL),
            raw_subdirectory="edge_iiotset",
            client_identity_source="device-client or group-client, decided by the P6-T02 feasibility audit",
            split_type=SplitType.FEASIBILITY_PENDING,
            label_source="in-row attack-type label column",
            metadata_feasibility_requirement=(
                "device/group identity column presence; timestamp column presence for D-temporal"
            ),
            rejected=False,
            rejection_rule=None,
            expected_output_artifacts=(
                DatasetOutputArtifact.PREPROCESSED_PER_CLIENT_TENSORS,
                DatasetOutputArtifact.SPLIT_MANIFEST,
                DatasetOutputArtifact.COVERAGE_GATE_REPORT,
            ),
            calibration_min_eligible_rows=CALIBRATION_MIN_ELIGIBLE_ROWS,
        ),
    ),
)


def dataset_contract(name: str) -> DatasetContract:
    for registration in DATASET_REGISTRATIONS:
        if registration.name == name:
            return registration.contract
    raise DatasetContractError(f"unknown dataset registration {name!r}")


def raw_dataset_root(contract: DatasetContract, repo_paths: RepoPaths) -> Path:
    return repo_paths.data_raw / contract.raw_subdirectory


def require_raw_dataset_present(contract: DatasetContract, repo_paths: RepoPaths) -> Path:
    """Raise if the raw dataset directory is absent; never create it."""
    root = raw_dataset_root(contract, repo_paths)
    if not root.is_dir():
        raise DatasetContractError(
            f"raw dataset missing for {contract.dataset_id.value}: expected directory {root} "
            "(raw data is never created automatically)"
        )
    return root


def contract_to_dict(contract: DatasetContract) -> dict[str, Any]:
    data = asdict(contract)
    data["dataset_id"] = contract.dataset_id.value
    data["regimes"] = [r.value for r in contract.regimes]
    data["split_type"] = contract.split_type.value
    data["expected_output_artifacts"] = [artifact.value for artifact in contract.expected_output_artifacts]
    return data


def contract_from_dict(data: Mapping[str, Any]) -> DatasetContract:
    return DatasetContract(
        dataset_id=DatasetId(data["dataset_id"]),
        regimes=tuple(Regime(r) for r in data["regimes"]),
        raw_subdirectory=data["raw_subdirectory"],
        client_identity_source=data["client_identity_source"],
        split_type=SplitType(data["split_type"]),
        label_source=data["label_source"],
        metadata_feasibility_requirement=data.get("metadata_feasibility_requirement"),
        rejected=data["rejected"],
        rejection_rule=data.get("rejection_rule"),
        expected_output_artifacts=tuple(
            DatasetOutputArtifact(artifact) for artifact in data["expected_output_artifacts"]
        ),
        calibration_min_eligible_rows=data["calibration_min_eligible_rows"],
    )
