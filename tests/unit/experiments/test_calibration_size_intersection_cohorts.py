import pytest

from datp_core.core.identifiers import PopulationId, PopulationIdentityKind
from datp_core.core.numeric import CalibrationSize, ClientCount, NonNegativeIntegerValue, Ratio
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.experiments.threshold_robustness.cohorts import (
    CalibrationSizeCohortCoverage,
    CalibrationSizeIntersectionCohort,
    compute_intersection_cohort,
)


def _client(client_id: str) -> ClientIdentity:
    return ClientIdentity(
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        client_id=client_id,
        identity_kind=PopulationIdentityKind.PHYSICAL_DEVICES,
    )


def test_intersection_cohort_with_complete_overlap() -> None:
    clients = frozenset([_client("c1"), _client("c2"), _client("c3")])
    sizes = (CalibrationSize(100), CalibrationSize(250), CalibrationSize(500))
    feasible_by_size = {size: clients for size in sizes}
    total_eligible = ClientCount(3)
    cohort = compute_intersection_cohort(sizes, feasible_by_size, total_eligible)
    assert cohort.intersection_clients == clients
    assert cohort.intersection_count.value == 3
    assert len(cohort.per_size_coverage) == 3
    for coverage in cohort.per_size_coverage:
        assert coverage.feasible_clients == clients
        assert coverage.client_count.value == 3
        assert coverage.coverage.value == 1.0


def test_intersection_cohort_with_partial_overlap() -> None:
    c1 = _client("c1")
    c2 = _client("c2")
    c3 = _client("c3")
    c4 = _client("c4")
    size50 = CalibrationSize(50)
    size100 = CalibrationSize(100)
    size250 = CalibrationSize(250)
    feasible_by_size = {
        size50: frozenset([c1, c2, c3, c4]),
        size100: frozenset([c1, c2, c3]),
        size250: frozenset([c1, c2]),
    }
    sizes = (size50, size100, size250)
    total_eligible = ClientCount(4)
    cohort = compute_intersection_cohort(sizes, feasible_by_size, total_eligible)
    assert cohort.intersection_clients == frozenset([c1, c2])
    assert cohort.intersection_count.value == 2
    assert cohort.per_size_coverage[0].client_count.value == 4
    assert cohort.per_size_coverage[1].client_count.value == 3
    assert cohort.per_size_coverage[2].client_count.value == 2


def test_intersection_cohort_with_no_overlap() -> None:
    size100 = CalibrationSize(100)
    size250 = CalibrationSize(250)
    feasible_by_size = {
        size100: frozenset([_client("c1"), _client("c2")]),
        size250: frozenset([_client("c3"), _client("c4")]),
    }
    sizes = (size100, size250)
    total_eligible = ClientCount(4)
    cohort = compute_intersection_cohort(sizes, feasible_by_size, total_eligible)
    assert cohort.intersection_clients == frozenset()
    assert cohort.intersection_count.value == 0


def test_intersection_cohort_validates_unique_sizes() -> None:
    size100 = CalibrationSize(100)
    clients = frozenset([_client("c1")])
    with pytest.raises(ValueError, match="sizes must be unique"):
        CalibrationSizeIntersectionCohort(
            compared_sizes=(size100, size100),
            intersection_clients=clients,
            intersection_count=NonNegativeIntegerValue(1),
            per_size_coverage=(
                CalibrationSizeCohortCoverage(
                    size=size100,
                    feasible_clients=clients,
                    client_count=ClientCount(1),
                    coverage=Ratio(1.0),
                ),
            ),
        )


def test_intersection_cohort_validates_coverage_size_membership() -> None:
    size100 = CalibrationSize(100)
    size250 = CalibrationSize(250)
    clients = frozenset([_client("c1")])
    with pytest.raises(ValueError, match="coverage size must be in compared sizes"):
        CalibrationSizeIntersectionCohort(
            compared_sizes=(size100,),
            intersection_clients=clients,
            intersection_count=NonNegativeIntegerValue(1),
            per_size_coverage=(
                CalibrationSizeCohortCoverage(
                    size=size250,
                    feasible_clients=clients,
                    client_count=ClientCount(1),
                    coverage=Ratio(1.0),
                ),
            ),
        )


def test_intersection_cohort_validates_intersection_subset() -> None:
    size100 = CalibrationSize(100)
    c1 = _client("c1")
    c2 = _client("c2")
    with pytest.raises(ValueError, match="intersection must be subset"):
        CalibrationSizeIntersectionCohort(
            compared_sizes=(size100,),
            intersection_clients=frozenset([c1, c2]),
            intersection_count=NonNegativeIntegerValue(2),
            per_size_coverage=(
                CalibrationSizeCohortCoverage(
                    size=size100,
                    feasible_clients=frozenset([c1]),
                    client_count=ClientCount(1),
                    coverage=Ratio(1.0),
                ),
            ),
        )
