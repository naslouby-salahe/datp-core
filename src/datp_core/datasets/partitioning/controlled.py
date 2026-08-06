"""Reusable deterministic allocation for controlled Dirichlet and IID populations."""

from dataclasses import dataclass, field

import numpy as np

from datp_core.datasets.partitioning.contracts import ControlledPartitionKind
from datp_core.domain.enums import PopulationId
from datp_core.domain.errors import DataIntegrityError, ScientificContractError
from datp_core.domain.values.checksums import Checksum, checksum_text
from datp_core.domain.values.counts import ClientCount, RowCount, Seed

from .contracts import ControlledPartitionCondition
from .splits import hamilton_integer_counts


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
        counts = tuple(RowCount(value) for value in hamilton_integer_counts(row_count.value, proportions))
        if sum(count.value for count in counts) != row_count.value:
            raise DataIntegrityError(
                "controlled partition allocation failed to conserve stratum rows",
                subject=self.population,
                reason="Hamilton residual allocation must preserve every row",
            )
        return counts

    def permutation(self, row_count: RowCount) -> np.ndarray:
        """Return a deterministic permutation for one ordered source stratum."""
        return self._generator.permutation(row_count.value)

    def _proportions(self) -> tuple[float, ...]:
        match self.condition.kind:
            case ControlledPartitionKind.IID:
                share = 1.0 / self.client_count.value
                return tuple(share for _ in range(self.client_count.value))
            case ControlledPartitionKind.DIRICHLET:
                concentration = self.condition.concentration
                if concentration is None:
                    raise ScientificContractError(
                        "Dirichlet construction requires a concentration",
                        subject=self.population,
                        reason="concentration cannot be invented",
                    )
                alpha = np.full(self.client_count.value, concentration.value, dtype=np.float64)
                return tuple(float(value) for value in self._generator.dirichlet(alpha))
        raise ScientificContractError(
            "unsupported controlled partition kind",
            subject=self.condition.kind,
            reason="only Dirichlet and IID constructions are authorized",
        )


def controlled_allocation_checksum(
    client_ids: tuple[str, ...],
    counts: tuple[RowCount, ...],
    condition: ControlledPartitionCondition,
    seed: Seed,
) -> Checksum:
    """Checksum the complete controlled allocation identity and resulting counts."""
    concentration = condition.kind.value if condition.concentration is None else str(condition.concentration.value)
    return checksum_text(
        "\n".join(
            (
                condition.kind.value,
                concentration,
                str(seed.value),
                *client_ids,
                *(str(count.value) for count in counts),
            )
        )
    )
