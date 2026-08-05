from pathlib import Path

import polars as pl
import pytest

from datp_core.datasets.nbaiot.populations import construct_nbaiot_dirichlet_clients
from datp_core.datasets.partitioning.contracts import (
    DirichletPartitionDiagnosticsDocument,
    dirichlet_condition,
    iid_condition,
)
from datp_core.domain.enums import SplitProtocolId
from datp_core.domain.values import DirichletConcentration, Seed

_CONCENTRATIONS = (0.1, 0.3, 0.5, 1.0, 10.0)


@pytest.mark.parametrize("seed", [Seed(0), Seed(1), Seed(2), Seed(3), Seed(4)])
@pytest.mark.parametrize("alpha", _CONCENTRATIONS)
def test_dirichlet_never_drops_or_duplicates_rows(seed: Seed, alpha: float, nbaiot_canonical_root: Path) -> None:
    construction = construct_nbaiot_dirichlet_clients(
        nbaiot_canonical_root,
        partition_seed=seed,
        condition=dirichlet_condition(DirichletConcentration(alpha)),
        split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
    )
    membership, diagnostics = construction.membership, construction.diagnostics
    assert isinstance(diagnostics, DirichletPartitionDiagnosticsDocument)
    assert membership.get_column("stable_row_id").n_unique() == membership.height
    assert sum(diagnostics.client_row_counts) == membership.height
    assert membership.group_by("stable_row_id").len().filter(pl.col("len") != 1).height == 0


def test_iid_conserves_rows(nbaiot_canonical_root: Path) -> None:
    construction = construct_nbaiot_dirichlet_clients(
        nbaiot_canonical_root,
        partition_seed=Seed(0),
        condition=iid_condition(),
        split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
    )
    diagnostics = construction.diagnostics
    assert isinstance(diagnostics, DirichletPartitionDiagnosticsDocument)
    assert sum(diagnostics.client_row_counts) == construction.membership.height
