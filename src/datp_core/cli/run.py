"""Pipeline execution CLI adapters."""

from __future__ import annotations

from typing import Annotated

import typer

from datp_core.datasets.edge_iiotset.schema import EDGE_NUMERIC_FEATURE_COLUMNS
from datp_core.domain.enums import (
    ControlledPartitionKind,
    DatasetId,
    EvidenceRole,
    ExperimentId,
    PopulationId,
    PreprocessingProtocolId,
    SplitProtocolId,
    TemporalState,
)
from datp_core.domain.values import DirichletConcentration, FeatureName, FeatureNameSequence, Seed
from datp_core.pipeline.campaign import (
    analyze_confirmatory_campaign,
    run_confirmatory_campaign,
    run_confirmatory_seed,
    run_published_seed,
    run_temporal_future_pair,
)
from datp_core.pipeline.fit_preprocessing import (
    FitCentralizedPopulationPreprocessingRequest,
    FitFederatedPreprocessingRequest,
    fit_centralized_population_preprocessing,
    fit_federated_preprocessing,
)
from datp_core.pipeline.materialize_dataset import MaterializeDatasetRequest, materialize_dataset
from datp_core.populations.models import ControlledPartitionCondition, dirichlet_condition, iid_condition
from datp_core.protocols.experiments import ExternalTemporalExecutionIdentity
from datp_core.protocols.populations import DIRICHLET_CONCENTRATIONS
from datp_core.protocols.runtime import DATA_ROOT
from datp_core.protocols.seeds import CONFIRMATORY_SEED_COHORT
from datp_core.protocols.training import EDGE_IIOTSET_NUMERIC_AUTOENCODER

app = typer.Typer(no_args_is_help=True)
_DECLARED_DIRICHLET_VALUES = frozenset(item.value for item in DIRICHLET_CONCENTRATIONS)
_DECLARED_CONFIRMATORY_SEEDS = frozenset(item.value for item in CONFIRMATORY_SEED_COHORT.values)
_DECLARED_BOUNDED_EVIDENCE_PARTITION_SEEDS = frozenset({0})
_FEDERATED_PREPROCESSING_IDENTITIES = frozenset(
    (
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        PreprocessingProtocolId.FEDERATED_POOLED_MIN_MAX,
    )
)
_EDGE_FEATURE_NAMES = FeatureNameSequence(tuple(FeatureName(name) for name in EDGE_NUMERIC_FEATURE_COLUMNS))


@app.command("materialize-datasets")
def materialize_datasets() -> None:
    result = materialize_dataset(MaterializeDatasetRequest(data_root=DATA_ROOT, datasets=tuple(DatasetId)))
    for publication in result.publications:
        typer.echo(
            f"{publication.dataset.value} {publication.publication_status.value} "
            f"rows={publication.row_count} assets={len(publication.assets)}"
        )


@app.command("preprocess-federated")
def preprocess_federated(
    population: Annotated[PopulationId, typer.Option()],
    partition_seed: Annotated[int, typer.Option(min=0)],
    split_protocol: Annotated[SplitProtocolId, typer.Option()],
    preprocessing_identity: Annotated[PreprocessingProtocolId, typer.Option()],
    partition_kind: Annotated[ControlledPartitionKind | None, typer.Option()] = None,
    concentration: Annotated[float | None, typer.Option()] = None,
) -> None:
    if preprocessing_identity not in _FEDERATED_PREPROCESSING_IDENTITIES:
        allowed = ", ".join(sorted(item.value for item in _FEDERATED_PREPROCESSING_IDENTITIES))
        raise typer.BadParameter(f"preprocessing-identity must be one of: {allowed}")
    result = fit_federated_preprocessing(
        FitFederatedPreprocessingRequest(
            population=population,
            partition_seed=Seed(partition_seed),
            split_protocol=split_protocol,
            preprocessing_identity=preprocessing_identity,
            data_root=DATA_ROOT,
            dirichlet_condition=_controlled_partition_condition(partition_kind, concentration),
            capture_timestamp_column=None,
        )
    )
    typer.echo(
        f"population={result.population.value} dataset={result.dataset.value} "
        f"published={result.published_count} reused={result.reused_count}"
    )


@app.command("preprocess-centralized")
def preprocess_centralized(
    population: Annotated[PopulationId, typer.Option()],
    partition_seed: Annotated[int, typer.Option(min=0)],
    split_protocol: Annotated[SplitProtocolId, typer.Option()],
    partition_kind: Annotated[ControlledPartitionKind | None, typer.Option()] = None,
    concentration: Annotated[float | None, typer.Option()] = None,
) -> None:
    result = fit_centralized_population_preprocessing(
        FitCentralizedPopulationPreprocessingRequest(
            population=population,
            partition_seed=Seed(partition_seed),
            split_protocol=split_protocol,
            data_root=DATA_ROOT,
            dirichlet_condition=_controlled_partition_condition(partition_kind, concentration),
            capture_timestamp_column=None,
        )
    )
    typer.echo(
        f"population={result.population.value} dataset={result.dataset.value} status={result.publication_status.value}"
    )


@app.command("confirmatory-seed")
def confirmatory_seed(training_seed: Annotated[int, typer.Option(min=0)]) -> None:
    if training_seed not in _DECLARED_CONFIRMATORY_SEEDS:
        allowed = ", ".join(str(value) for value in sorted(_DECLARED_CONFIRMATORY_SEEDS))
        raise typer.BadParameter(f"training-seed must be one of the declared confirmatory seeds: {allowed}")
    completed = run_confirmatory_seed(Seed(training_seed))
    typer.echo(f"seed={training_seed} thresholds={','.join(item.value for item in completed)}")


@app.command("confirmatory-campaign")
def confirmatory_campaign() -> None:
    completed = run_confirmatory_campaign()
    typer.echo(f"seeds={len(completed)}")


@app.command("analyze-confirmatory")
def analyze_confirmatory() -> None:
    typer.echo(str(analyze_confirmatory_campaign()))


@app.command("external-validation-seed")
def external_validation_seed(
    partition_seed: Annotated[int, typer.Option(min=0)],
    preprocessing_identity: Annotated[PreprocessingProtocolId, typer.Option()],
) -> None:
    _require_declared_bounded_evidence_seed(partition_seed)
    identity = ExternalTemporalExecutionIdentity(
        experiment=ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION,
        population=PopulationId.EDGE_SENSOR_GROUPS,
        evidence_role=EvidenceRole.EXTERNAL_VALIDATION,
        temporal_state=None,
    )
    completed = run_published_seed(
        execution_identity=identity,
        dataset=DatasetId.EDGE_IIOTSET,
        partition_seed=Seed(partition_seed),
        training_seed=Seed(partition_seed),
        preprocessing_identity=preprocessing_identity,
        autoencoder=EDGE_IIOTSET_NUMERIC_AUTOENCODER,
        feature_names=_EDGE_FEATURE_NAMES,
    )
    typer.echo(f"seed={partition_seed} thresholds={','.join(item.value for item in completed)}")


@app.command("temporal-static-reference-seed")
def temporal_static_reference_seed(
    partition_seed: Annotated[int, typer.Option(min=0)],
    preprocessing_identity: Annotated[PreprocessingProtocolId, typer.Option()],
) -> None:
    """Run the independent static-reference detector for one-shot temporal recalibration."""
    _require_declared_bounded_evidence_seed(partition_seed)
    identity = ExternalTemporalExecutionIdentity(
        experiment=ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
        population=PopulationId.EDGE_TEMPORAL_GROUPS,
        evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
        temporal_state=TemporalState.STATIC_REFERENCE,
    )
    completed = run_published_seed(
        execution_identity=identity,
        dataset=DatasetId.EDGE_IIOTSET,
        partition_seed=Seed(partition_seed),
        training_seed=Seed(partition_seed),
        preprocessing_identity=preprocessing_identity,
        autoencoder=EDGE_IIOTSET_NUMERIC_AUTOENCODER,
        feature_names=_EDGE_FEATURE_NAMES,
    )
    typer.echo(
        f"seed={partition_seed} temporal_state=static_reference thresholds={','.join(item.value for item in completed)}"
    )


@app.command("temporal-future-pair-seed")
def temporal_future_pair_seed(
    partition_seed: Annotated[int, typer.Option(min=0)],
    preprocessing_identity: Annotated[PreprocessingProtocolId, typer.Option()],
) -> None:
    """Train one shared historical detector once and evaluate it under frozen-future and
    recalibrated-future calibration windows (only the calibration window differs)."""
    _require_declared_bounded_evidence_seed(partition_seed)
    results = run_temporal_future_pair(
        partition_seed=Seed(partition_seed),
        training_seed=Seed(partition_seed),
        preprocessing_identity=preprocessing_identity,
        autoencoder=EDGE_IIOTSET_NUMERIC_AUTOENCODER,
        feature_names=_EDGE_FEATURE_NAMES,
    )
    for state, completed in results.items():
        thresholds = ",".join(item.value for item in completed)
        typer.echo(f"seed={partition_seed} temporal_state={state.value} thresholds={thresholds}")


def _require_declared_bounded_evidence_seed(partition_seed: int) -> None:
    if partition_seed not in _DECLARED_BOUNDED_EVIDENCE_PARTITION_SEEDS:
        allowed = ", ".join(str(value) for value in sorted(_DECLARED_BOUNDED_EVIDENCE_PARTITION_SEEDS))
        raise typer.BadParameter(f"partition-seed must be one of the declared bounded-evidence seeds: {allowed}")


def _controlled_partition_condition(
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
        allowed = ", ".join(str(value) for value in sorted(_DECLARED_DIRICHLET_VALUES))
        raise typer.BadParameter(f"concentration must be one of the declared Dirichlet grid values: {allowed}")
    return dirichlet_condition(DirichletConcentration(concentration))
