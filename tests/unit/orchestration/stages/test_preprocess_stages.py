from pathlib import Path

import polars as pl
import pytest

from datp_core.datasets.models import CanonicalPublicationArtifact
from datp_core.datasets.nbaiot.schema import NBAIOT_DEVICE_IDENTITIES, NBAIOT_FEATURE_COLUMNS, NBaIoTDeviceFamily
from datp_core.domain.enums import (
    PopulationId,
    PreprocessingProtocolId,
    PublicationStatus,
    SplitProtocolId,
    StageOperationId,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import Seed
from datp_core.orchestration.stages.preprocess_centralized_reference import (
    PreprocessCentralizedPopulationRequest,
    preprocess_centralized_reference_population_stage,
)
from datp_core.orchestration.stages.preprocess_federated import (
    PreprocessFederatedRequest,
    preprocess_federated_stage,
)


def _family_for(device: str) -> str:
    mapping = {
        "danmini_doorbell": NBaIoTDeviceFamily.DOORBELL.value,
        "ecobee_thermostat": NBaIoTDeviceFamily.THERMOSTAT.value,
        "ennio_doorbell": NBaIoTDeviceFamily.DOORBELL.value,
        "philips_b120n10_baby_monitor": NBaIoTDeviceFamily.BABY_MONITOR.value,
        "provision_pt_737e_security_camera": NBaIoTDeviceFamily.SECURITY_CAMERA.value,
        "provision_pt_838_security_camera": NBaIoTDeviceFamily.SECURITY_CAMERA.value,
        "samsung_snh_1011_n_webcam": NBaIoTDeviceFamily.WEBCAM.value,
        "simplehome_xcs7_1002_wht_security_camera": NBaIoTDeviceFamily.SECURITY_CAMERA.value,
        "simplehome_xcs7_1003_wht_security_camera": NBaIoTDeviceFamily.SECURITY_CAMERA.value,
    }
    return mapping[device]


def _nbaiot_data_root(tmp_path: Path) -> Path:
    data_root = tmp_path / "data"
    canonical = data_root / "canonical" / "nbaiot"
    data = canonical / "data"
    data.mkdir(parents=True)
    rows: list[dict[str, str | int | float | None]] = []
    for device in NBAIOT_DEVICE_IDENTITIES:
        for label, count in (("benign", 30), ("attack", 12)):
            for local in range(count):
                row: dict[str, str | int | float | None] = {
                    "physical_client_id": device,
                    "physical_device_family": _family_for(device),
                    "raw_label": label,
                    "attack_family": None if label == "benign" else "mirai",
                    "attack_subtype": None if label == "benign" else "udp",
                    "source_path": f"{device}/{label}_{local}.csv",
                    "source_row_index": local,
                    "stable_row_id": f"{device}:{label}:{local}",
                }
                for feature_index, feature in enumerate(NBAIOT_FEATURE_COLUMNS):
                    row[feature] = float(local + feature_index)
                rows.append(row)
    pl.DataFrame(rows).write_parquet(data / "part-00000.parquet")
    (canonical / CanonicalPublicationArtifact.COMPLETE.value).write_text("complete\n", encoding="utf-8")
    return data_root


def test_federated_preprocess_publishes_client_local_assets(tmp_path: Path) -> None:
    data_root = _nbaiot_data_root(tmp_path)
    result = preprocess_federated_stage(
        PreprocessFederatedRequest(
            population=PopulationId.NBAIOT_NATURAL_DEVICES,
            partition_seed=Seed(0),
            split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
            preprocessing_identity=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
            data_root=data_root,
            dirichlet_condition=None,
            capture_timestamp_column=None,
        )
    )
    assert result.stage is StageOperationId.PREPROCESS_FEDERATED
    assert result.published_count == 9
    assert result.reused_count == 0
    assert len(result.client_publications) == 9
    for publication in result.client_publications:
        assert publication.publication_status is PublicationStatus.PUBLISHED
        assert publication.result.train_path.is_file()
        assert (publication.result.train_path.parent / "COMPLETE").is_file()

    reused = preprocess_federated_stage(
        PreprocessFederatedRequest(
            population=PopulationId.NBAIOT_NATURAL_DEVICES,
            partition_seed=Seed(0),
            split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
            preprocessing_identity=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
            data_root=data_root,
            dirichlet_condition=None,
            capture_timestamp_column=None,
        )
    )
    assert reused.published_count == 0
    assert reused.reused_count == 9


def test_federated_preprocess_rejects_centralized_identity(tmp_path: Path) -> None:
    with pytest.raises(ScientificContractError, match="federated preprocessing identity"):
        preprocess_federated_stage(
            PreprocessFederatedRequest(
                population=PopulationId.NBAIOT_NATURAL_DEVICES,
                partition_seed=Seed(0),
                split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
                preprocessing_identity=PreprocessingProtocolId.CENTRALIZED_POOLED_MIN_MAX,
                data_root=tmp_path,
                dirichlet_condition=None,
                capture_timestamp_column=None,
            )
        )


def test_federated_preprocess_rejects_temporal_split(tmp_path: Path) -> None:
    with pytest.raises(ScientificContractError, match="future_recalibration"):
        preprocess_federated_stage(
            PreprocessFederatedRequest(
                population=PopulationId.NBAIOT_NATURAL_DEVICES,
                partition_seed=Seed(0),
                split_protocol=SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE,
                preprocessing_identity=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
                data_root=tmp_path,
                dirichlet_condition=None,
                capture_timestamp_column=None,
            )
        )


def test_centralized_preprocess_publishes_pooled_assets(tmp_path: Path) -> None:
    data_root = _nbaiot_data_root(tmp_path)
    result = preprocess_centralized_reference_population_stage(
        PreprocessCentralizedPopulationRequest(
            population=PopulationId.NBAIOT_NATURAL_DEVICES,
            partition_seed=Seed(0),
            split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
            data_root=data_root,
            dirichlet_condition=None,
            capture_timestamp_column=None,
        )
    )
    assert result.stage is StageOperationId.PREPROCESS_CENTRALIZED_REFERENCE
    assert result.publication_status is PublicationStatus.PUBLISHED
    assert result.result.train_path.is_file()
    assert (result.result.train_path.parent / "COMPLETE").is_file()
    assert "centralized_reference" in result.result.train_path.parts
