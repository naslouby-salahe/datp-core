from dataclasses import dataclass, field
from enum import StrEnum

import numpy as np

from datp_core.core.errors import (
    DataIntegrityError,
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import PopulationId
from datp_core.core.numeric import ClientCount, Ratio, RowCount, Seed
from datp_core.data.populations.contracts import ControlledPartitionKind

from .contracts import ControlledPartitionCondition
from .splits import hamilton_integer_counts


class ControlledAllocationViolation(StrEnum):
    STRATUM_ROWS_NOT_CONSERVED = "stratum_rows_not_conserved"
    DIRICHLET_CONCENTRATION_MISSING = "dirichlet_concentration_missing"
    UNSUPPORTED_PARTITION_KIND = "unsupported_partition_kind"


@dataclass(slots=True)
class ControlledPartitionAllocator:
    population: PopulationId
    client_count: ClientCount
    condition: ControlledPartitionCondition
    seed: Seed
    _generator: np.random.Generator = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._generator = np.random.Generator(np.random.PCG64(self.seed.value))

    def allocate(
        self,
        row_count: RowCount,
        *,
        minimum_per_client: RowCount | None = None,
    ) -> tuple[RowCount, ...]:
        if row_count.value == 0:
            return tuple(RowCount(0) for _ in range(self.client_count.value))
        minimum = minimum_per_client or RowCount(0)
        reserved_rows = minimum.value * self.client_count.value
        if reserved_rows > row_count.value:
            raise DataIntegrityError(
                ErrorMessage("minimum client allocation exceeds available stratum rows"),
                subject=self.population,
                reason=ControlledAllocationViolation.STRATUM_ROWS_NOT_CONSERVED,
            )
        proportions = self._proportions()
        counts = tuple(
            minimum.plus(count)
            for count in hamilton_integer_counts(RowCount(row_count.value - reserved_rows), proportions)
        )
        if sum(count.value for count in counts) != row_count.value:
            raise DataIntegrityError(
                ErrorMessage("controlled partition allocation failed to conserve stratum rows"),
                subject=self.population,
                reason=ControlledAllocationViolation.STRATUM_ROWS_NOT_CONSERVED,
            )
        return counts

    def permutation(self, row_count: RowCount) -> np.ndarray:
        return self._generator.permutation(row_count.value)

    def _proportions(self) -> tuple[Ratio, ...]:
        match self.condition.kind:
            case ControlledPartitionKind.IID:
                share = 1.0 / self.client_count.value
                return tuple(Ratio(share) for _ in range(self.client_count.value))
            case ControlledPartitionKind.DIRICHLET:
                concentration = self.condition.concentration
                if concentration is None:
                    raise ScientificContractError(
                        ErrorMessage("Dirichlet construction requires a concentration"),
                        subject=self.population,
                        reason=ControlledAllocationViolation.DIRICHLET_CONCENTRATION_MISSING,
                    )
                alpha = np.full(self.client_count.value, concentration.value, dtype=np.float64)
                return tuple(Ratio(value) for value in self._generator.dirichlet(alpha))
        raise ScientificContractError(
            ErrorMessage("unsupported controlled partition kind"),
            subject=self.condition.kind,
            reason=ControlledAllocationViolation.UNSUPPORTED_PARTITION_KIND,
        )
