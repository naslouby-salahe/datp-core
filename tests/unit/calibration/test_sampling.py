import pytest
from tests.unit.calibration.helpers import some_client
from tests.unit.learning.federated.helpers import fedavg_coordinate

from datp_core.calibration.models import CalibrationSampleReference
from datp_core.calibration.sampling import build_calibration_replicate, replicate_seed
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values.counts import CalibrationSize, ReplicateIndex, Seed
from datp_core.domain.values.identifiers import StableRowId
from datp_core.domain.values.ratios import ScoreValue

CLIENT_A = some_client("client_a")
CLIENT_B = some_client("client_b")
COORDINATE = fedavg_coordinate(Seed(0))
SIZES = (CalibrationSize(2), CalibrationSize(3), CalibrationSize(10))
REPLICATE_ZERO = ReplicateIndex(0)
REPLICATE_ONE = ReplicateIndex(1)


def _references(count: int, client=CLIENT_A) -> tuple[CalibrationSampleReference, ...]:
    return tuple(
        CalibrationSampleReference(
            client=client, stable_row_id=StableRowId(f"row-{index}"), score=ScoreValue(float(index))
        )
        for index in range(count)
    )


def test_replicate_seed_is_deterministic() -> None:
    first = replicate_seed(Seed(0), CLIENT_A, REPLICATE_ZERO)
    second = replicate_seed(Seed(0), CLIENT_A, REPLICATE_ZERO)
    assert first == second


def test_replicate_seed_differs_across_clients() -> None:
    assert replicate_seed(Seed(0), CLIENT_A, REPLICATE_ZERO) != replicate_seed(Seed(0), CLIENT_B, REPLICATE_ZERO)


def test_replicate_seed_differs_across_replicates() -> None:
    assert replicate_seed(Seed(0), CLIENT_A, REPLICATE_ZERO) != replicate_seed(Seed(0), CLIENT_A, REPLICATE_ONE)


def test_replicate_seed_differs_across_training_seeds() -> None:
    assert replicate_seed(Seed(0), CLIENT_A, REPLICATE_ZERO) != replicate_seed(Seed(1), CLIENT_A, REPLICATE_ZERO)


def test_replicate_index_rejects_negative_values() -> None:
    def build() -> ReplicateIndex:
        return ReplicateIndex(-1)

    with pytest.raises(ValueError, match="replicate index"):
        build()


def test_build_calibration_replicate_is_deterministic_across_repeated_calls() -> None:
    references = _references(5)
    first = build_calibration_replicate(
        client=CLIENT_A,
        coordinate=COORDINATE,
        training_seed=Seed(0),
        replicate_index=REPLICATE_ZERO,
        references=references,
        sizes=SIZES,
    )
    second = build_calibration_replicate(
        client=CLIENT_A,
        coordinate=COORDINATE,
        training_seed=Seed(0),
        replicate_index=REPLICATE_ZERO,
        references=references,
        sizes=SIZES,
    )
    assert first == second


def test_build_calibration_replicate_nests_smaller_inside_larger() -> None:
    references = _references(20)
    manifest = build_calibration_replicate(
        client=CLIENT_A,
        coordinate=COORDINATE,
        training_seed=Seed(0),
        replicate_index=REPLICATE_ZERO,
        references=references,
        sizes=SIZES,
    )
    subsamples = {subsample.size.value: subsample.stable_row_id_set for subsample in manifest.subsamples}
    assert subsamples[2] <= subsamples[3] <= subsamples[10]


def test_build_calibration_replicate_marks_oversized_requests_unavailable() -> None:
    references = _references(5)
    manifest = build_calibration_replicate(
        client=CLIENT_A,
        coordinate=COORDINATE,
        training_seed=Seed(0),
        replicate_index=REPLICATE_ZERO,
        references=references,
        sizes=SIZES,
    )
    assert CalibrationSize(10) in manifest.unavailable_sizes
    assert manifest.unavailable_reason is not None
    produced_sizes = {subsample.size.value for subsample in manifest.subsamples}
    assert produced_sizes == {2, 3}


def test_build_calibration_replicate_rejects_foreign_client_references() -> None:
    references = _references(5, client=CLIENT_B)

    def call():
        return build_calibration_replicate(
            client=CLIENT_A,
            coordinate=COORDINATE,
            training_seed=Seed(0),
            replicate_index=REPLICATE_ZERO,
            references=references,
            sizes=SIZES,
        )

    with pytest.raises(ScientificContractError, match="belong to the replicate's client"):
        call()


def test_build_calibration_replicate_different_replicate_indices_can_differ() -> None:
    references = _references(20)
    first = build_calibration_replicate(
        client=CLIENT_A,
        coordinate=COORDINATE,
        training_seed=Seed(0),
        replicate_index=REPLICATE_ZERO,
        references=references,
        sizes=(CalibrationSize(5),),
    )
    second = build_calibration_replicate(
        client=CLIENT_A,
        coordinate=COORDINATE,
        training_seed=Seed(0),
        replicate_index=REPLICATE_ONE,
        references=references,
        sizes=(CalibrationSize(5),),
    )
    assert first.subsamples[0].stable_row_id_set != second.subsamples[0].stable_row_id_set
