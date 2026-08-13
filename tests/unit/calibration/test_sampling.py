from hashlib import sha256

import pytest

from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import (
    ClientIdentityToken,
    DatasetId,
    PopulationId,
    PopulationIdentityKind,
    PreprocessingProtocolId,
    SplitProtocolId,
    StableRowId,
    TrainingModelId,
)
from datp_core.core.numeric import CalibrationSize, ReplicateIndex, RowCount, ScoreValue, Seed
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.training.contracts import FederatedTrainingCoordinate
from datp_core.thresholds.calibration.eligibility import CalibrationSampleReference
from datp_core.thresholds.calibration.sampling import (
    CalibrationReplicateManifest,
    CalibrationSubsample,
    build_calibration_replicate,
    replicate_seed,
)


def _coordinate() -> FederatedTrainingCoordinate:
    return FederatedTrainingCoordinate(
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        training_seed=Seed(17),
        split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
        preprocessing_identity=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        model=TrainingModelId.FEDAVG_AUTOENCODER,
        model_coefficient=None,
    )


def _client() -> ClientIdentity:
    return ClientIdentity(
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        client_id=ClientIdentityToken("device_a"),
        identity_kind=PopulationIdentityKind.PHYSICAL_DEVICES,
    )


def test_replicate_seed_uses_the_roadmap_sha256_identity_contract() -> None:
    client = _client()
    material = b"DATP-Core|CALIBRATION_SUBSAMPLE|nbaiot|nbaiot_natural_devices|17|device_a|3"
    expected = int.from_bytes(sha256(material).digest()[:8], byteorder="big", signed=False) % (2**32)

    assert replicate_seed(DatasetId.NBAIOT, Seed(17), client, ReplicateIndex(3)) == Seed(expected)
    assert replicate_seed(DatasetId.CICIOT2023, Seed(17), client, ReplicateIndex(3)) != Seed(expected)


def test_nested_subsamples_are_deterministic_prefixes_of_one_pcg64_permutation() -> None:
    client = _client()
    coordinate = _coordinate()
    references = tuple(
        CalibrationSampleReference(client, StableRowId(f"row:{index}"), ScoreValue(float(index))) for index in range(8)
    )
    first = build_calibration_replicate(
        client=client,
        dataset=DatasetId.NBAIOT,
        coordinate=coordinate,
        training_seed=coordinate.training_seed,
        replicate_index=ReplicateIndex(0),
        references=references,
        sizes=(CalibrationSize(3), CalibrationSize(5)),
    )
    second = build_calibration_replicate(
        client=client,
        dataset=DatasetId.NBAIOT,
        coordinate=coordinate,
        training_seed=coordinate.training_seed,
        replicate_index=ReplicateIndex(0),
        references=references,
        sizes=(CalibrationSize(3), CalibrationSize(5)),
    )

    assert first == second
    assert first.subsamples[0].stable_row_id_set.issubset(first.subsamples[1].stable_row_id_set)


def test_calibration_manifest_rejects_coordinate_seed_and_subsample_identity_drift() -> None:
    client = _client()
    coordinate = _coordinate()
    references = tuple(
        CalibrationSampleReference(client, StableRowId(f"row:{index}"), ScoreValue(float(index))) for index in range(3)
    )
    subsample = CalibrationSubsample(
        size=CalibrationSize(3),
        replicate_index=ReplicateIndex(1),
        references=references,
    )

    with pytest.raises(ScientificContractError, match="training seed must match"):
        CalibrationReplicateManifest(
            client=client,
            coordinate=coordinate,
            training_seed=Seed(18),
            replicate_index=ReplicateIndex(0),
            full_calibration_count=RowCount(3),
            subsamples=(),
            unavailable_sizes=(),
            unavailable_reason=None,
        )
    with pytest.raises(ScientificContractError, match="replicate indices must match"):
        CalibrationReplicateManifest(
            client=client,
            coordinate=coordinate,
            training_seed=coordinate.training_seed,
            replicate_index=ReplicateIndex(0),
            full_calibration_count=RowCount(3),
            subsamples=(subsample,),
            unavailable_sizes=(),
            unavailable_reason=None,
        )
