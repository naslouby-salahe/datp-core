"""Reusable deterministic allocation for controlled Dirichlet and IID populations."""

from dataclasses import dataclass, field
from enum import StrEnum

import numpy as np

from datp_core.artifacts.provenance import Checksum
from datp_core.core.errors import (
    DataIntegrityError,
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import ClientIdentityToken, PopulationId
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
    """Stateful deterministic allocator shared by controlled population builders."""

    population: PopulationId
    client_count: ClientCount
    condition: ControlledPartitionCondition
    seed: Seed
    _generator: np.random.Generator = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._generator = np.random.Generator(np.random.PCG64(self.seed.value))

    def allocate(self, row_count: RowCount) -> tuple[RowCount, ...]:
        """Allocate one stratum while conserving every row exactly once."""
        if row_count.value == 0:
            return tuple(RowCount(0) for _ in range(self.client_count.value))
        proportions = self._proportions()
        counts = hamilton_integer_counts(row_count, proportions)
        if sum(count.value for count in counts) != row_count.value:
            raise DataIntegrityError(
                ErrorMessage("controlled partition allocation failed to conserve stratum rows"),
                subject=self.population,
                reason=ControlledAllocationViolation.STRATUM_ROWS_NOT_CONSERVED,
            )
        return counts

    def permutation(self, row_count: RowCount) -> np.ndarray:
        """Return a deterministic permutation for one ordered source stratum."""
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


def controlled_allocation_checksum(
    client_ids: tuple[ClientIdentityToken, ...],
    counts: tuple[RowCount, ...],
    condition: ControlledPartitionCondition,
    seed: Seed,
) -> Checksum:
    """Checksum the complete controlled allocation identity and resulting counts."""
    concentration = condition.kind.value if condition.concentration is None else str(condition.concentration.value)
    return Checksum.from_text(
        "\n".join(
            (
                condition.kind.value,
                concentration,
                str(seed.value),
                *(c.value for c in client_ids),
                *(str(count.value) for count in counts),
            )
        )
    )
