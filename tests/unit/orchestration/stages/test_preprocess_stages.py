from pathlib import Path
from shutil import copytree

import polars as pl
import pytest

from datp_core.datasets.models import CanonicalPublicationArtifact
from datp_core.datasets.nbaiot.schema import (
    NBAIOT_DEVICE_IDENTITIES,
    NBAIOT_FEATURE_COLUMNS,
    NBaIoTDeviceFamily,
)
from datp_core.domain.enums import (
    EvidenceRole,
    ExperimentId,
    PopulationId,
    PreprocessingProtocolId,
    PublicationStatus,
    SplitProtocolId,
    StageOperationId,
    TemporalState,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import Seed
from datp_core.orchestration.commands.populations import (
    ConstructPopulationRequest,
    SplitRequest,
)
from datp_core.orchestration.commands.preprocessing import (
    PreprocessCentralizedPopulationRequest,
    PreprocessFederatedArtifactsRequest,
    PreprocessFederatedRequest,
)
from datp_core.orchestration.stages.construct_population import (
    construct_population_stage,
)
from datp_core.orchestration.stages.preprocess_centralized_reference import (
    preprocess_centralized_reference_population_stage,
)
from datp_core.orchestration.stages.preprocess_federated import (
    preprocess_federated_artifacts_stage,
    preprocess_federated_stage,
)
from datp_core.orchestration.stages.split import split_stage
from datp_core.protocols.experiments import ExternalTemporalExecutionIdentity


def _family_for(device: str) -> str:
    mapping = {
        "danmini_doorbell": NBaIoTDeviceFamily.DOORBELL.value,
        "ecobee_thermostat": NBaIoTDeviceFamily.THERMOSTAT.value,
        "ennio_doorbell": NBaIoTDeviceFamily.DOORBELL.value,
        "philips_b120n10_baby_monitor": (
            NBaIoTDeviceFamily.BABY_MONITOR.value
        ),
        "provision_pt_737e_security_camera": (
            NBaIoTDeviceFamily.SECURITY_CAMERA.value
        ),
        "provision_pt_838_security_camera": (
            NBaIoTDeviceFamily.SECURITY_CAMERA.value
        ),
        "samsung_snh_1011_n_webcam": NBaIoTDeviceFamily.WEBCAM.value,
        "simplehome_xcs7_1002_wht_security_camera": (
            NBaIoTDeviceFamily.SECURITY_CAMERA.value
        ),
        "simplehome_xcs7_1003_wht_security_camera": (
            NBaIoTDeviceFamily.SECURITY_CAMERA.value
        ),
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
                    "attack_family": (
                        None if label == "benign" else "mirai"
                    ),
                    "attack_subtype": (
                        None if label == "benign" else "udp"
                    ),
                    "source_path": f"{device}/{label}_{local}.csv",
                    "source_row_index": local,
                    "stable_row_id": f"{device}:{label}:{local}",
                }
                for feature_index, feature in enumerate(
                    NBAIOT_FEATURE_COLUMNS
                ):
                    row[feature] = float(local + feature_index)
                rows.append(row)
    pl.DataFrame(rows).write_parquet(data / "part-00000.parquet")
    (canonical / CanonicalPublicationArtifact.COMPLETE.value).write_text(
        "complete\n",
        encoding="utf-8",
    )
    return data_root


def test_federated_preprocess_publishes_client_local_assets(
    tmp_path: Path,
) -> None:
    data_root = _nbaiot_data_root(tmp_path)
    request = PreprocessFederatedRequest(
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        partition_seed=Seed(0),
        split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
        preprocessing_identity=(
            PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD
        ),
        data_root=data_root,
        dirichlet_condition=None,
        capture_timestamp_column=None,
    )
    result = preprocess_federated_stage(request)
    assert result.stage is StageOperationId.PREPROCESS_FEDERATED
    assert result.published_count == 9
    assert result.reused_count == 0
    assert len(result.client_publications) == 9
    for publication in result.client_publications:
        assert publication.publication_status is PublicationStatus.PUBLISHED
        assert publication.paths.train.is_file()
        assert (publication.paths.train.parent / "COMPLETE").is_file()

    reused = preprocess_federated_stage(request)
    assert reused.published_count == 0
    assert reused.reused_count == 9


def test_federated_preprocess_rejects_centralized_identity(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ScientificContractError,
        match="federated preprocessing identity",
    ):
        preprocess_federated_stage(
            PreprocessFederatedRequest(
                population=PopulationId.NBAIOT_NATURAL_DEVICES,
                partition_seed=Seed(0),
                split_protocol=(
                    SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS
                ),
                preprocessing_identity=(
                    PreprocessingProtocolId.CENTRALIZED_POOLED_MIN_MAX
                ),
                data_root=tmp_path,
                dirichlet_condition=None,
                capture_timestamp_column=None,
            )
        )


def test_artifact_preprocess_selects_matched_static_reference(
    tmp_path: Path,
    edge_temporal_eligible_root: Path,
) -> None:
    data_root = tmp_path / "data"
    canonical_root = data_root / "canonical" / "edge_iiotset"
    copytree(edge_temporal_eligible_root, canonical_root)
    (canonical_root / CanonicalPublicationArtifact.COMPLETE.value).write_text(
        "complete\n",
        encoding="utf-8",
    )
    identity = ExternalTemporalExecutionIdentity(
        experiment=ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
        population=PopulationId.EDGE_TEMPORAL_GROUPS,
        evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
        temporal_state=TemporalState.STATIC_REFERENCE,
    )
    construction = construct_population_stage(
        ConstructPopulationRequest(
            canonical_root=canonical_root,
            population=PopulationId.EDGE_TEMPORAL_GROUPS,
            execution_identity=identity,
            partition_seed=Seed(0),
            split_protocol=SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE,
            output_directory=tmp_path / "population",
            overwrite=False,
        )
    )
    split_stage(
        SplitRequest(
            population=PopulationId.EDGE_TEMPORAL_GROUPS,
            execution_identity=identity,
            population_manifest=construction.population_manifest,
            membership=construction.membership,
            partition_seed=Seed(0),
            output_directory=tmp_path / "split",
            overwrite=False,
            matched_static_reference_manifest=(
                construction.matched_static_reference_manifest
            ),
            matched_static_reference_membership=(
                construction.matched_static_reference_membership
            ),
        )
    )

    result = preprocess_federated_artifacts_stage(
        PreprocessFederatedArtifactsRequest(
            execution_identity=identity,
            population_directory=tmp_path / "population",
            split_directory=tmp_path / "split",
            preprocessing_identity=(
                PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD
            ),
            data_root=data_root,
        )
    )

    assert (
        result.split_protocol
        is SplitProtocolId.RANDOM_FRACTIONAL_STATIC_REFERENCE
    )
    assert result.execution_identity == identity
    assert result.client_publications


def test_centralized_preprocess_publishes_pooled_assets(
    tmp_path: Path,
) -> None:
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
    assert (
        result.stage
        is StageOperationId.PREPROCESS_CENTRALIZED_REFERENCE
    )
    assert result.publication_status is PublicationStatus.PUBLISHED
    assert result.result.paths.train.is_file()
    assert (result.result.paths.train.parent / "COMPLETE").is_file()
    assert "centralized_reference" in result.result.paths.train.parts
