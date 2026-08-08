from pathlib import Path

import pytest

from datp_core.artifacts.provenance import Checksum
from datp_core.core.errors import ArtifactIntegrityError
from datp_core.core.identifiers import (
    CheckpointStatus,
    PopulationId,
    PreprocessingProtocolId,
    SplitProtocolId,
    TrainingModelId,
)
from datp_core.core.numeric import BatchSize, DirichletConcentration, FeatureCount, MetricValue, RoundNumber, Seed
from datp_core.data.populations.contracts import ControlledPartitionKind
from datp_core.detector.checkpoints.contracts import CheckpointProtocol
from datp_core.detector.checkpoints.identities import CandidateManifestKind
from datp_core.detector.checkpoints.publication import build_manifest, validate_manifest
from datp_core.detector.training.contracts import AutoencoderArchitecture, AutoencoderProtocol
from datp_core.detector.training.models import CheckpointCandidate, FederatedTrainingCoordinate

_CHECKPOINT_PROTOCOL = CheckpointProtocol(candidates=(RoundNumber(1),), maximum_round=RoundNumber(1))
_AUTOENCODER = AutoencoderProtocol(widths=AutoencoderArchitecture((FeatureCount(4), FeatureCount(2), FeatureCount(4))))
_BATCH_SIZE = BatchSize(4)
_PREPROCESSING_CHECKSUM = Checksum("a" * 64)
_SPLIT_CHECKSUM = Checksum("b" * 64)
_DEFAULT_SEED = Seed(0)


def _coordinate(
    *,
    seed: Seed = _DEFAULT_SEED,
    controlled_partition_kind: ControlledPartitionKind | None = None,
    dirichlet_concentration: DirichletConcentration | None = None,
) -> FederatedTrainingCoordinate:
    return FederatedTrainingCoordinate(
        population=PopulationId.NBAIOT_DIRICHLET_CLIENTS,
        training_seed=seed,
        split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
        preprocessing_identity=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        model=TrainingModelId.FEDAVG_AUTOENCODER,
        model_coefficient=None,
        controlled_partition_kind=controlled_partition_kind,
        dirichlet_concentration=dirichlet_concentration,
    )


def _candidates(coordinate: FederatedTrainingCoordinate) -> tuple[CheckpointCandidate, ...]:
    return tuple(
        CheckpointCandidate(
            coordinate=coordinate,
            round_number=round_number,
            client=None,
            tensor_path=Path(f"round_{round_number.value}.safetensors"),
            tensor_checksum=Checksum("c" * 64),
            mean_training_loss=MetricValue(0.1),
            status=CheckpointStatus.SELECTED_BY_NON_TEST_RULE,
            preprocessing_state_set_checksum=_PREPROCESSING_CHECKSUM,
            split_manifest_checksum=_SPLIT_CHECKSUM,
        )
        for round_number in _CHECKPOINT_PROTOCOL.candidates
    )


def _validate(manifest, coordinate: FederatedTrainingCoordinate) -> None:
    validate_manifest(
        manifest,
        kind=CandidateManifestKind.GLOBAL,
        coordinate=coordinate,
        checkpoint_protocol=_CHECKPOINT_PROTOCOL,
        autoencoder=_AUTOENCODER,
        batch_size=_BATCH_SIZE,
        preprocessing_state_set_checksum=_PREPROCESSING_CHECKSUM,
        split_manifest_checksum=_SPLIT_CHECKSUM,
    )


def test_manifest_stores_the_controlled_partition_coordinate() -> None:
    dirichlet_coordinate = _coordinate(
        controlled_partition_kind=ControlledPartitionKind.DIRICHLET,
        dirichlet_concentration=DirichletConcentration(0.1),
    )
    manifest = build_manifest(
        kind=CandidateManifestKind.GLOBAL,
        coordinate=dirichlet_coordinate,
        candidates=_candidates(dirichlet_coordinate),
        checkpoint_protocol=_CHECKPOINT_PROTOCOL,
        autoencoder=_AUTOENCODER,
        batch_size=_BATCH_SIZE,
        preprocessing_state_set_checksum=_PREPROCESSING_CHECKSUM,
        split_manifest_checksum=_SPLIT_CHECKSUM,
    )
    assert manifest.coordinate_controlled_partition_kind is ControlledPartitionKind.DIRICHLET
    assert manifest.coordinate_dirichlet_concentration == DirichletConcentration(0.1)


def test_matching_severity_coordinate_validates_successfully() -> None:
    coordinate = _coordinate(
        controlled_partition_kind=ControlledPartitionKind.DIRICHLET,
        dirichlet_concentration=DirichletConcentration(0.1),
    )
    manifest = build_manifest(
        kind=CandidateManifestKind.GLOBAL,
        coordinate=coordinate,
        candidates=_candidates(coordinate),
        checkpoint_protocol=_CHECKPOINT_PROTOCOL,
        autoencoder=_AUTOENCODER,
        batch_size=_BATCH_SIZE,
        preprocessing_state_set_checksum=_PREPROCESSING_CHECKSUM,
        split_manifest_checksum=_SPLIT_CHECKSUM,
    )
    _validate(manifest, coordinate)


def test_iid_manifest_cannot_be_reused_for_a_dirichlet_request() -> None:
    iid_coordinate = _coordinate(controlled_partition_kind=ControlledPartitionKind.IID)
    manifest = build_manifest(
        kind=CandidateManifestKind.GLOBAL,
        coordinate=iid_coordinate,
        candidates=_candidates(iid_coordinate),
        checkpoint_protocol=_CHECKPOINT_PROTOCOL,
        autoencoder=_AUTOENCODER,
        batch_size=_BATCH_SIZE,
        preprocessing_state_set_checksum=_PREPROCESSING_CHECKSUM,
        split_manifest_checksum=_SPLIT_CHECKSUM,
    )
    dirichlet_request_coordinate = _coordinate(
        controlled_partition_kind=ControlledPartitionKind.DIRICHLET,
        dirichlet_concentration=DirichletConcentration(0.1),
    )
    with pytest.raises(ArtifactIntegrityError, match="coordinate does not match"):
        _validate(manifest, dirichlet_request_coordinate)


def test_one_dirichlet_severity_manifest_cannot_be_reused_for_another_severity() -> None:
    low_alpha_coordinate = _coordinate(
        controlled_partition_kind=ControlledPartitionKind.DIRICHLET,
        dirichlet_concentration=DirichletConcentration(0.1),
    )
    manifest = build_manifest(
        kind=CandidateManifestKind.GLOBAL,
        coordinate=low_alpha_coordinate,
        candidates=_candidates(low_alpha_coordinate),
        checkpoint_protocol=_CHECKPOINT_PROTOCOL,
        autoencoder=_AUTOENCODER,
        batch_size=_BATCH_SIZE,
        preprocessing_state_set_checksum=_PREPROCESSING_CHECKSUM,
        split_manifest_checksum=_SPLIT_CHECKSUM,
    )
    high_alpha_coordinate = _coordinate(
        controlled_partition_kind=ControlledPartitionKind.DIRICHLET,
        dirichlet_concentration=DirichletConcentration(0.3),
    )
    with pytest.raises(ArtifactIntegrityError, match="coordinate does not match"):
        _validate(manifest, high_alpha_coordinate)
