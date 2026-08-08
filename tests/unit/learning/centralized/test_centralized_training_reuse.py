"""Centralized training publication reuse must bind the full scientific identity (II-03)."""

from pathlib import Path

from tests.unit.learning.centralized.helpers import (
    AUTOENCODER,
    BATCH_SIZE,
    CHECKPOINT,
    FEATURE_NAMES,
    LEARNING_RATE,
    TRAINING_PROTOCOL,
    benign_frame,
    feature_protocol,
)

from datp_core.artifacts.provenance import Checksum
from datp_core.artifacts.serializers.json import canonical_checksum
from datp_core.core.identifiers import (
    CentralizedModelId,
    PopulationId,
    PreprocessingProtocolId,
    SplitProtocolId,
)
from datp_core.core.numeric import RowCount, Seed, WeightDecay
from datp_core.data.preprocessing.models import CentralizedFittedPreprocessingState
from datp_core.detector.checkpoints.service import candidate_tensor_name
from datp_core.detector.training.centralized import CentralizedArtifactName, CentralizedTrainingCoordinate
from datp_core.detector.training.centralized_publication import (
    CentralizedTrainingPublicationRequest,
    _centralized_training_binding,
    centralized_training_is_reusable,
)


def _fitted_state(path: Path, checksum: Checksum) -> CentralizedFittedPreprocessingState:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"placeholder")
    return CentralizedFittedPreprocessingState(
        protocol=feature_protocol(),
        estimator_path=path,
        estimator_checksum=checksum,
        fit_row_count=RowCount(8),
    )


_DEFAULT_PREPROCESSING_CHECKSUM = Checksum("a" * 64)
_DEFAULT_SPLIT_MANIFEST_CHECKSUM = Checksum("b" * 64)
_DEFAULT_TRAINING_SEED = Seed(0)


def _request(
    tmp_path: Path,
    *,
    preprocessing_checksum: Checksum = _DEFAULT_PREPROCESSING_CHECKSUM,
    split_manifest_checksum: Checksum = _DEFAULT_SPLIT_MANIFEST_CHECKSUM,
    training_seed: Seed = _DEFAULT_TRAINING_SEED,
) -> CentralizedTrainingPublicationRequest:
    return CentralizedTrainingPublicationRequest(
        coordinate=CentralizedTrainingCoordinate(
            population=PopulationId.NBAIOT_NATURAL_DEVICES,
            training_seed=training_seed,
            split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
            preprocessing_identity=PreprocessingProtocolId.CENTRALIZED_POOLED_MIN_MAX,
            model=CentralizedModelId.CENTRALIZED_AUTOENCODER,
        ),
        training_features=benign_frame(RowCount(8)),
        feature_names=FEATURE_NAMES,
        preprocessing_state=_fitted_state(tmp_path / "state.skops", preprocessing_checksum),
        split_manifest_checksum=split_manifest_checksum,
        output_directory=tmp_path,
        training_seed=training_seed,
        autoencoder=AUTOENCODER,
        checkpoint_protocol=CHECKPOINT,
        training_protocol=TRAINING_PROTOCOL,
        learning_rate=LEARNING_RATE,
        batch_size=BATCH_SIZE,
        weight_decay=WeightDecay(0.0),
    )


def _publish_marker(directory: Path, request: CentralizedTrainingPublicationRequest) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / CentralizedArtifactName.MODEL_TENSORS).write_bytes(b"model")
    (directory / CentralizedArtifactName.TRAINING_HISTORY).write_bytes(b"history")
    for candidate in request.checkpoint_protocol.candidates:
        (directory / candidate_tensor_name(candidate)).write_bytes(b"tensor")
    (directory / CentralizedArtifactName.COMPLETE).write_text(
        canonical_checksum(_centralized_training_binding(request, directory)).value,
        encoding="utf-8",
    )


def test_centralized_training_reuse_binds_coordinate_preprocessing_and_split(tmp_path: Path) -> None:
    directory = tmp_path / "run"
    baseline = _request(tmp_path)
    _publish_marker(directory, baseline)

    assert centralized_training_is_reusable(baseline, directory) is True

    changed_preprocessing = _request(tmp_path, preprocessing_checksum=Checksum("f" * 64))
    assert centralized_training_is_reusable(changed_preprocessing, directory) is False

    changed_split = _request(tmp_path, split_manifest_checksum=Checksum("9" * 64))
    assert centralized_training_is_reusable(changed_split, directory) is False

    changed_seed = _request(tmp_path, training_seed=Seed(1))
    assert centralized_training_is_reusable(changed_seed, directory) is False


def test_centralized_training_reuse_requires_all_artifact_parts(tmp_path: Path) -> None:
    directory = tmp_path / "run"
    request = _request(tmp_path)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / CentralizedArtifactName.COMPLETE).write_text("stale", encoding="utf-8")

    assert centralized_training_is_reusable(request, directory) is False
