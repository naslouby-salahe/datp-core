"""Pipeline execution CLI adapters."""

from __future__ import annotations

from typing import Annotated

import typer

from datp_core.datasets.partitioning.contracts import (
    ControlledPartitionCondition,
    ControlledPartitionKind,
    dirichlet_condition,
    iid_condition,
)
from datp_core.datasets.service import DatasetMaterializationRequest
from datp_core.datasets.service import materialize_datasets as publish_datasets
from datp_core.domain.enums import (
    DatasetId,
    PopulationId,
    PreprocessingProtocolId,
    SplitProtocolId,
)
from datp_core.domain.values.counts import Seed
from datp_core.domain.values.ratios import DirichletConcentration, DittoRegularization
from datp_core.pipeline.workflows.centralized import run_centralized_reference_seed
from datp_core.pipeline.workflows.confirmatory import (
    analyze_confirmatory_campaign,
    run_confirmatory_campaign,
    run_confirmatory_seed,
)
from datp_core.pipeline.workflows.external import run_ciciot_boundary_seed, run_external_validation_seed
from datp_core.pipeline.workflows.personalization import run_ditto_stress_test_seed
from datp_core.pipeline.workflows.temporal import run_temporal_campaign, run_temporal_seed
from datp_core.preprocessing.centralized import (
    CentralizedPopulationPreprocessingRequest,
    preprocess_centralized_population,
)
from datp_core.preprocessing.models import FederatedPreprocessingRequest
from datp_core.preprocessing.service import preprocess_federated
from datp_core.protocols.populations import DIRICHLET_CONCENTRATIONS
from datp_core.protocols.seeds import BOUNDED_EVIDENCE_SEED_COHORT, CONFIRMATORY_SEED_COHORT
from datp_core.protocols.training import DITTO_TRAINING_PROTOCOLS
from datp_core.runtime.configuration import DATA_ROOT

app = typer.Typer(no_args_is_help=True)
_DECLARED_DIRICHLET_VALUES = frozenset(item.value for item in DIRICHLET_CONCENTRATIONS)
_DECLARED_CONFIRMATORY_SEEDS = frozenset(item.value for item in CONFIRMATORY_SEED_COHORT.values)
_DECLARED_BOUNDED_EVIDENCE_PARTITION_SEEDS = frozenset(item.value for item in BOUNDED_EVIDENCE_SEED_COHORT.values)
_FEDERATED_PREPROCESSING_IDENTITIES = frozenset(
    (
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        PreprocessingProtocolId.FEDERATED_POOLED_MIN_MAX,
    )
)


@app.command("materialize-datasets")
def materialize_datasets() -> None:
    result = publish_datasets(DatasetMaterializationRequest(data_root=DATA_ROOT, datasets=tuple(DatasetId)))
    for publication in result.publications:
        typer.echo(
            f"{publication.dataset.value} {publication.publication_status.value} "
            f"rows={publication.row_count} assets={len(publication.assets)}"
        )


@app.command("preprocess-federated")
def preprocess_federated_command(
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
    result = preprocess_federated(
        FederatedPreprocessingRequest(
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
def preprocess_centralized_command(
    population: Annotated[PopulationId, typer.Option()],
    partition_seed: Annotated[int, typer.Option(min=0)],
    split_protocol: Annotated[SplitProtocolId, typer.Option()],
    partition_kind: Annotated[ControlledPartitionKind | None, typer.Option()] = None,
    concentration: Annotated[float | None, typer.Option()] = None,
) -> None:
    result = preprocess_centralized_population(
        CentralizedPopulationPreprocessingRequest(
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
    _require_confirmatory_seed(training_seed)
    result = run_confirmatory_seed(Seed(training_seed))
    typer.echo(f"seed={training_seed} thresholds={','.join(item.value for item in result.completed_threshold_methods)}")


@app.command("confirmatory-campaign")
def confirmatory_campaign() -> None:
    result = run_confirmatory_campaign()
    typer.echo(f"seeds={len(result.seeds)}")


@app.command("analyze-confirmatory")
def analyze_confirmatory() -> None:
    typer.echo(str(analyze_confirmatory_campaign()))


@app.command("centralized-reference-seed")
def centralized_reference_seed(training_seed: Annotated[int, typer.Option(min=0)]) -> None:
    _require_confirmatory_seed(training_seed)
    evaluation = run_centralized_reference_seed(Seed(training_seed))
    typer.echo(
        f"seed={training_seed} status={evaluation.publication_status.value} "
        f"threshold={evaluation.evaluation.threshold.value}"
    )


@app.command("ditto-stress-test-seed")
def ditto_stress_test_seed(
    training_seed: Annotated[int, typer.Option(min=0)],
    regularization: Annotated[float, typer.Option()],
) -> None:
    _require_confirmatory_seed(training_seed)
    declared = frozenset(protocol.regularization.value for protocol in DITTO_TRAINING_PROTOCOLS)
    if regularization not in declared:
        allowed = ", ".join(str(value) for value in sorted(declared))
        raise typer.BadParameter(f"regularization must be one of the declared Ditto values: {allowed}")
    result = run_ditto_stress_test_seed(
        training_seed=Seed(training_seed),
        regularization=DittoRegularization(regularization),
    )
    typer.echo(
        f"seed={training_seed} regularization={regularization} "
        f"shared_threshold={result.shared_threshold.shared_threshold.value} "
        f"clients={len(result.shared_threshold_metrics)}"
    )


@app.command("edge-benign-equity-seed")
def edge_benign_equity_seed(partition_seed: Annotated[int, typer.Option(min=0)]) -> None:
    _require_declared_bounded_evidence_seed(partition_seed)
    result = run_external_validation_seed(Seed(partition_seed))
    typer.echo(
        f"seed={partition_seed} population={result.population.value} thresholds="
        f"{','.join(item.value for item in result.completed_threshold_methods)}"
    )


@app.command("ciciot-file-client-boundary-seed")
def ciciot_file_client_boundary_seed(partition_seed: Annotated[int, typer.Option(min=0)]) -> None:
    _require_declared_bounded_evidence_seed(partition_seed)
    result = run_ciciot_boundary_seed(Seed(partition_seed))
    typer.echo(
        f"seed={partition_seed} population={result.population.value} thresholds="
        f"{','.join(item.value for item in result.completed_threshold_methods)}"
    )


@app.command("temporal-evidence-seed")
def temporal_evidence_seed(partition_seed: Annotated[int, typer.Option(min=0)]) -> None:
    _require_declared_bounded_evidence_seed(partition_seed)
    result = run_temporal_seed(Seed(partition_seed))
    for analysis in result.analyses:
        recovery_ratio = analysis.recovery.recovery_ratio
        ratio = "undefined" if recovery_ratio is None else str(recovery_ratio.value)
        typer.echo(
            f"seed={partition_seed} method={analysis.method.value} "
            f"drift_excess={analysis.recovery.drift_excess.value} "
            f"recovered_amount={analysis.recovery.recovered_amount.value} "
            f"recovery_ratio={ratio}"
        )


@app.command("temporal-evidence-campaign")
def temporal_evidence_campaign() -> None:
    result = run_temporal_campaign()
    methods = tuple(item.method for item in result.seeds[0].analyses) if result.seeds else ()
    typer.echo(f"seeds={len(result.seeds)} methods={','.join(method.value for method in methods)}")


def _require_confirmatory_seed(training_seed: int) -> None:
    if training_seed not in _DECLARED_CONFIRMATORY_SEEDS:
        allowed = ", ".join(str(value) for value in sorted(_DECLARED_CONFIRMATORY_SEEDS))
        raise typer.BadParameter(f"training-seed must be one of the declared confirmatory seeds: {allowed}")


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
