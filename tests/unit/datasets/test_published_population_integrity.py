from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import patch

import polars as pl
import pytest

from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import (
    DatasetId,
    EvidenceRole,
    ExperimentId,
    PopulationId,
    SplitProtocolId,
    TemporalState,
)
from datp_core.core.numeric import Seed
from datp_core.data.populations.contracts import PopulationManifest, SplitManifestDocument
from datp_core.data.populations.publication import (
    ConstructPublishedPopulationRequest,
    ConstructPublishedSplitRequest,
    _validate_loaded_population,
    _validate_loaded_split,
)
from datp_core.experiments.common.coordinates import ExternalTemporalExecutionIdentity


def _temporal_identity() -> ExternalTemporalExecutionIdentity:
    return ExternalTemporalExecutionIdentity(
        experiment=ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
        population=PopulationId.EDGE_TEMPORAL_CLIENTS,
        evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
        temporal_state=TemporalState.FROZEN_FUTURE,
    )


def _population_request(seed: Seed | None = None) -> ConstructPublishedPopulationRequest:
    partition_seed = Seed(7) if seed is None else seed
    return ConstructPublishedPopulationRequest(
        canonical_root=Path("canonical"),
        population=PopulationId.EDGE_TEMPORAL_CLIENTS,
        execution_identity=_temporal_identity(),
        partition_seed=partition_seed,
        split_protocol=SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE,
        output_directory=Path("published"),
        overwrite=False,
    )


def _population_manifest(seed: Seed | None = None) -> SimpleNamespace:
    partition_seed = Seed(7) if seed is None else seed
    return SimpleNamespace(
        document=SimpleNamespace(
            population=PopulationId.EDGE_TEMPORAL_CLIENTS,
            dataset=DatasetId.EDGE_IIOTSET,
            partition_seed=partition_seed,
            split_protocol=SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE,
        )
    )


def test_cached_population_rejects_coordinate_drift_before_using_artifacts() -> None:
    with pytest.raises(ScientificContractError, match="coordinates disagree"):
        _validate_loaded_population(
            cast(PopulationManifest, _population_manifest(Seed(8))),
            pl.DataFrame(),
            None,
            None,
            None,
            _population_request(),
        )


def test_cached_temporal_population_requires_chronology_evidence() -> None:
    with patch("datp_core.data.populations.publication.validate_population_manifest"):
        with pytest.raises(ScientificContractError, match="chronology diagnostics"):
            _validate_loaded_population(
                cast(PopulationManifest, _population_manifest()),
                pl.DataFrame(),
                None,
                None,
                None,
                _population_request(),
            )


def test_cached_split_rejects_seed_drift_before_using_assignments() -> None:
    population_manifest = _population_manifest()
    request = ConstructPublishedSplitRequest(
        population=PopulationId.EDGE_TEMPORAL_CLIENTS,
        execution_identity=_temporal_identity(),
        population_manifest=cast(PopulationManifest, population_manifest),
        membership=pl.DataFrame(),
        partition_seed=Seed(7),
        output_directory=Path("split"),
        overwrite=False,
    )
    stale_split = SimpleNamespace(
        population=PopulationId.EDGE_TEMPORAL_CLIENTS,
        dataset=DatasetId.EDGE_IIOTSET,
        partition_seed=Seed(8),
        split_protocol=SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE,
    )
    with pytest.raises(ScientificContractError, match="coordinates disagree"):
        _validate_loaded_split(pl.DataFrame(), cast(SplitManifestDocument, stale_split), None, None, request)
