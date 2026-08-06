"""Shared Typer validation for declared scientific command options."""

import typer

from datp_core.datasets.partitioning.contracts import (
    ControlledPartitionCondition,
    ControlledPartitionKind,
    dirichlet_condition,
    iid_condition,
)
from datp_core.domain.enums import PreprocessingProtocolId
from datp_core.domain.values.counts import Seed
from datp_core.domain.values.ratios import DirichletConcentration
from datp_core.protocols.populations import DIRICHLET_CONCENTRATIONS
from datp_core.protocols.seeds import BOUNDED_EVIDENCE_SEED_COHORT, CONFIRMATORY_SEED_COHORT

_DECLARED_DIRICHLET_VALUES = frozenset(item.value for item in DIRICHLET_CONCENTRATIONS)
_DECLARED_CONFIRMATORY_SEEDS = frozenset(item.value for item in CONFIRMATORY_SEED_COHORT.values)
_DECLARED_BOUNDED_EVIDENCE_SEEDS = frozenset(item.value for item in BOUNDED_EVIDENCE_SEED_COHORT.values)
FEDERATED_PREPROCESSING_IDENTITIES = frozenset(
    (
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        PreprocessingProtocolId.FEDERATED_POOLED_MIN_MAX,
    )
)


def declared_confirmatory_seed(value: int) -> Seed:
    if value not in _DECLARED_CONFIRMATORY_SEEDS:
        raise typer.BadParameter(
            f"training-seed must be one of the declared confirmatory seeds: {_allowed(_DECLARED_CONFIRMATORY_SEEDS)}"
        )
    return Seed(value)


def declared_bounded_evidence_seed(value: int) -> Seed:
    if value not in _DECLARED_BOUNDED_EVIDENCE_SEEDS:
        raise typer.BadParameter(
            f"partition-seed must be one of the declared bounded-evidence seeds: "
            f"{_allowed(_DECLARED_BOUNDED_EVIDENCE_SEEDS)}"
        )
    return Seed(value)


def require_federated_preprocessing(identity: PreprocessingProtocolId) -> PreprocessingProtocolId:
    if identity not in FEDERATED_PREPROCESSING_IDENTITIES:
        allowed = ", ".join(sorted(item.value for item in FEDERATED_PREPROCESSING_IDENTITIES))
        raise typer.BadParameter(f"preprocessing-identity must be one of: {allowed}")
    return identity


def controlled_partition_condition(
    partition_kind: ControlledPartitionKind | None,
    concentration: float | None,
) -> ControlledPartitionCondition | None:
    if partition_kind is None:
        if concentration is not None:
            raise typer.BadParameter("concentration requires --partition-kind dirichlet")
        return None
    if partition_kind is ControlledPartitionKind.IID:
        if concentration is not None:
            raise typer.BadParameter("IID construction must not carry a concentration")
        return iid_condition()
    if concentration is None:
        raise typer.BadParameter("Dirichlet construction requires --concentration")
    if concentration not in _DECLARED_DIRICHLET_VALUES:
        raise typer.BadParameter(
            f"concentration must be one of the declared Dirichlet grid values: {_allowed(_DECLARED_DIRICHLET_VALUES)}"
        )
    return dirichlet_condition(DirichletConcentration(concentration))


def _allowed(values: frozenset[int | float]) -> str:
    return ", ".join(str(value) for value in sorted(values))
