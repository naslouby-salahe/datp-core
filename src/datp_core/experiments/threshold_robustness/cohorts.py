from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from datp_core.core.numeric import CalibrationSize, ClientCount, NonNegativeIntegerValue, Ratio
from datp_core.data.populations.contracts import ClientIdentity

if TYPE_CHECKING:
    from datp_core.analysis.metrics.federated import CalibrationSizeAblationCell


@dataclass(frozen=True, slots=True, kw_only=True)
class CalibrationSizeCohortCoverage:
    size: CalibrationSize
    feasible_clients: frozenset[ClientIdentity]
    client_count: ClientCount
    coverage: Ratio


@dataclass(frozen=True, slots=True, kw_only=True)
class CalibrationSizeIntersectionCohort:
    compared_sizes: tuple[CalibrationSize, ...]
    intersection_clients: frozenset[ClientIdentity]
    intersection_count: NonNegativeIntegerValue
    per_size_coverage: tuple[CalibrationSizeCohortCoverage, ...]

    def __post_init__(self) -> None:
        if not self.compared_sizes:
            raise ValueError("intersection cohort requires at least one size")
        if len(set(self.compared_sizes)) != len(self.compared_sizes):
            raise ValueError("intersection cohort sizes must be unique")
        if len(self.per_size_coverage) != len(self.compared_sizes):
            raise ValueError("per-size coverage must match compared sizes")
        for coverage in self.per_size_coverage:
            if coverage.size not in self.compared_sizes:
                raise ValueError("coverage size must be in compared sizes")
            if not self.intersection_clients.issubset(coverage.feasible_clients):
                raise ValueError("intersection must be subset of each size's feasible clients")


def compute_intersection_cohort(
    sizes: tuple[CalibrationSize, ...],
    feasible_by_size: dict[CalibrationSize, frozenset[ClientIdentity]],
    total_eligible_count: ClientCount,
) -> CalibrationSizeIntersectionCohort:
    if not sizes:
        raise ValueError("intersection cohort requires at least one size")
    if not all(size in feasible_by_size for size in sizes):
        raise ValueError("all compared sizes must have feasible client sets")
    size_sets = [feasible_by_size[size] for size in sizes]
    intersection: frozenset[ClientIdentity] = size_sets[0]
    for size_set in size_sets[1:]:
        intersection = intersection.intersection(size_set)
    intersection_count = NonNegativeIntegerValue(len(intersection))
    per_size_coverage = tuple(
        CalibrationSizeCohortCoverage(
            size=size,
            feasible_clients=feasible_by_size[size],
            client_count=ClientCount(len(feasible_by_size[size])),
            coverage=Ratio(len(feasible_by_size[size]) / total_eligible_count.value),
        )
        for size in sizes
    )
    return CalibrationSizeIntersectionCohort(
        compared_sizes=sizes,
        intersection_clients=intersection,
        intersection_count=intersection_count,
        per_size_coverage=per_size_coverage,
    )


def extract_feasible_clients_by_size(
    cells: tuple[CalibrationSizeAblationCell, ...],
) -> dict[CalibrationSize, frozenset[ClientIdentity]]:
    feasible_by_size: dict[CalibrationSize, set[ClientIdentity]] = {}
    for cell in cells:
        if cell.calibration_size not in feasible_by_size:
            feasible_by_size[cell.calibration_size] = set()
        feasible_by_size[cell.calibration_size].update(client.client for client in cell.clients)
    return {size: frozenset(clients) for size, clients in feasible_by_size.items()}
