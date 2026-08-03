"""Command-line entry points for reproducible DATP-Core operations."""

from dataclasses import dataclass
from pathlib import Path

import polars as pl
import typer

from datp_core.analysis.models import PairedContrast
from datp_core.artifacts.coordinates import canonical_root_under
from datp_core.datasets.catalogue import dataset_binding
from datp_core.domain.enums import (
    ControlledPartitionKind,
    DatasetId,
    EvidenceRole,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    PreprocessingProtocolId,
    SplitProtocolId,
    TrainingModelId,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import (
    Checksum,
    ClientCount,
    DirichletConcentration,
    FamilyIdentity,
    FeatureNameSequence,
    MetricValue,
    ProximalCoefficient,
    Seed,
    checksum_file,
)
from datp_core.evaluation.controls import FixedScoreEvidence
from datp_core.evaluation.models import MetricStatus
from datp_core.learning.federated.models import FederatedTrainingCoordinate, PreparedClientProvenance
from datp_core.learning.federated.training import preprocessing_state_set_checksum
from datp_core.orchestration.stages.analyze import AnalyzeRequest, analyze_stage
from datp_core.orchestration.stages.construct_federated_thresholds import (
    ConstructFederatedThresholdsRequest,
    construct_federated_thresholds_stage,
)
from datp_core.orchestration.stages.evaluate_federated import (
    EvaluateFederatedRequest,
    FederatedEvaluationAssetName,
    build_federated_evaluation_inputs,
    evaluate_federated_stage,
)
from datp_core.orchestration.stages.materialize import (
    MaterializeCanonicalDatasetsRequest,
    materialize_canonical_datasets_stage,
)
from datp_core.orchestration.stages.preprocess_centralized_reference import (
    PreprocessCentralizedPopulationRequest,
    preprocess_centralized_reference_population_stage,
)
from datp_core.orchestration.stages.preprocess_federated import (
    PreprocessFederatedRequest,
    PreprocessFederatedResult,
    preprocess_federated_stage,
)
from datp_core.orchestration.stages.score_federated import ScoreFederatedRequest, score_federated_stage
from datp_core.orchestration.stages.select_federated_checkpoint import (
    SelectFederatedCheckpointRequest,
    select_federated_checkpoint_stage,
)
from datp_core.orchestration.stages.train_federated import TrainFedAvgRequest, train_fedavg_stage
from datp_core.populations.capabilities import population_capabilities
from datp_core.populations.catalogue import (
    PopulationConstructionRequest,
    PopulationConstructionResult,
    construct_population,
    resolve_population,
)
from datp_core.populations.models import (
    ClientIdentity,
    ControlledPartitionCondition,
    SplitConstructionRequest,
    SplitManifestDocument,
    dirichlet_condition,
    iid_condition,
)
from datp_core.populations.splits import split_membership
from datp_core.preprocessing.models import ClientPreprocessPublication
from datp_core.protocols.calibration import CANONICAL_QUANTILE
from datp_core.protocols.populations import DIRICHLET_CONCENTRATIONS
from datp_core.protocols.runtime import DATA_ROOT, OUTPUTS_ROOT
from datp_core.protocols.seeds import CONFIRMATORY_SEED_COHORT
from datp_core.protocols.statistics import BOOTSTRAP_REPLICATE_COUNT, CONFIRMATORY_INFERENCE_PROTOCOL
from datp_core.protocols.training import (
    BATCH_SIZE,
    CHECKPOINT_PROTOCOL,
    FEDAVG_TRAINING_PROTOCOL,
    LEARNING_RATE,
    NBAIOT_AUTOENCODER,
)
from datp_core.scoring.generation import ClientScoringInput
from datp_core.scoring.models import FixedScoreInvariant, ScoreArtifactManifest
from datp_core.thresholding.dispatch import ThresholdConstructionRequest
from datp_core.thresholding.quantiles import ClientBenignCalibrationScores

app = typer.Typer(no_args_is_help=True)

_DECLARED_DIRICHLET_VALUES = frozenset(item.value for item in DIRICHLET_CONCENTRATIONS)
_FEDERATED_PREPROCESSING_IDENTITIES = frozenset(
    {
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        PreprocessingProtocolId.FEDERATED_POOLED_MIN_MAX,
    }
)


@dataclass(frozen=True, slots=True)
class ConfirmatorySeedContext:
    """Immutable inputs that must stay aligned for one confirmatory seed."""

    coordinate: FederatedTrainingCoordinate
    construction: PopulationConstructionResult
    preprocessing: PreprocessFederatedResult
    split_manifest: SplitManifestDocument
    state_set_checksum: Checksum
    training_directory: Path


@dataclass(frozen=True, slots=True)
class ConfirmatoryThresholdInputs:
    """Fixed score and calibration inputs shared by threshold scopes in one seed."""

    scores: ScoreArtifactManifest
    eligible: tuple[ClientBenignCalibrationScores, ...]
    family_by_client: tuple[tuple[ClientIdentity, FamilyIdentity], ...]
    previous_evidence: FixedScoreEvidence | None


@app.callback()
def command_group() -> None:
    """Reproducible DATP-Core operations."""


@app.command("materialize-canonical-datasets")
def materialize_canonical_datasets() -> None:
    """Publish or reuse every audited dataset under the fixed data root."""
    result = materialize_canonical_datasets_stage(
        MaterializeCanonicalDatasetsRequest(
            data_root=DATA_ROOT,
            datasets=tuple(DatasetId),
        )
    )
    for publication in result.publications:
        typer.echo(
            f"{publication.dataset.value} {publication.publication_status.value} "
            f"rows={publication.row_count} assets={len(publication.assets)}"
        )


@app.command("preprocess-federated")
# Typer exposes each independent scientific protocol field as an explicit option.
# pylint: disable=too-many-positional-arguments
def preprocess_federated(
    population: PopulationId = typer.Option(..., help="Locked population identity."),
    partition_seed: int = typer.Option(..., help="Non-negative partition seed value."),
    split_protocol: SplitProtocolId = typer.Option(..., help="Locked split protocol identity."),
    preprocessing_identity: PreprocessingProtocolId = typer.Option(
        ...,
        help="Federated preprocessing identity.",
    ),
    partition_kind: ControlledPartitionKind | None = typer.Option(
        None,
        help="Required for controlled populations.",
    ),
    concentration: float | None = typer.Option(
        None,
        help="Dirichlet concentration from the declared grid when partition-kind is dirichlet.",
    ),
) -> None:
    """Construct partitions and publish federated processed assets under data/processed."""
    if preprocessing_identity not in _FEDERATED_PREPROCESSING_IDENTITIES:
        allowed = ", ".join(sorted(identity.value for identity in _FEDERATED_PREPROCESSING_IDENTITIES))
        raise typer.BadParameter(
            f"preprocessing-identity must be one of: {allowed}",
            param_hint="--preprocessing-identity",
        )

    condition = _controlled_partition_condition(partition_kind, concentration)
    result = preprocess_federated_stage(
        PreprocessFederatedRequest(
            population=population,
            partition_seed=Seed(partition_seed),
            split_protocol=split_protocol,
            preprocessing_identity=preprocessing_identity,
            data_root=DATA_ROOT,
            dirichlet_condition=condition,
            capture_timestamp_column=None,
        )
    )
    typer.echo(
        f"{result.stage.value} population={result.population.value} dataset={result.dataset.value} "
        f"seed={result.partition_seed.value} split={result.split_protocol.value} "
        f"preprocessing={result.preprocessing_identity.value} "
        f"clients={len(result.client_publications)} "
        f"published={result.published_count} reused={result.reused_count}"
    )
    for publication in result.client_publications:
        typer.echo(
            f"  {publication.client_identity.value} {publication.publication_status.value} "
            f"train={publication.train_row_count} "
            f"calibration={publication.calibration_row_count} "
            f"evaluation={publication.evaluation_row_count}"
        )


# pylint: enable=too-many-positional-arguments
@app.command("preprocess-centralized-reference")
def preprocess_centralized_reference(
    population: PopulationId = typer.Option(..., help="Locked population identity."),
    partition_seed: int = typer.Option(..., help="Non-negative partition seed value."),
    split_protocol: SplitProtocolId = typer.Option(..., help="Locked split protocol identity."),
    partition_kind: ControlledPartitionKind | None = typer.Option(
        None,
        help="Required for controlled populations.",
    ),
    concentration: float | None = typer.Option(
        None,
        help="Dirichlet concentration from the declared grid when partition-kind is dirichlet.",
    ),
) -> None:
    """Construct partitions and publish centralized-reference processed assets under data/processed."""
    condition = _controlled_partition_condition(partition_kind, concentration)
    result = preprocess_centralized_reference_population_stage(
        PreprocessCentralizedPopulationRequest(
            population=population,
            partition_seed=Seed(partition_seed),
            split_protocol=split_protocol,
            data_root=DATA_ROOT,
            dirichlet_condition=condition,
            capture_timestamp_column=None,
        )
    )
    typer.echo(
        f"{result.stage.value} population={result.population.value} dataset={result.dataset.value} "
        f"seed={result.partition_seed.value} "
        f"preprocessing={result.preprocessing_identity.value} "
        f"status={result.publication_status.value} "
        f"train={result.result.train_path} "
        f"calibration={result.result.calibration_path} "
        f"evaluation={result.result.evaluation_path}"
    )


@app.command("run-confirmatory-seed")
def run_confirmatory_seed(
    training_seed: int = typer.Option(..., min=0, help="One declared non-negative training seed."),
) -> None:
    """Run the canonical N-BaIoT FedAvg path for one seed."""
    _run_confirmatory_seed(Seed(training_seed))


@app.command("run-confirmatory-grid")
def run_confirmatory_grid() -> None:
    """Run the declared ten-seed confirmatory grid without expanding its protocol."""
    for training_seed in CONFIRMATORY_SEED_COHORT.values:
        _run_confirmatory_seed(training_seed)


@app.command("analyze-confirmatory-grid")
def analyze_confirmatory_grid() -> None:
    """Publish the declared paired inference from completed seed evaluations."""
    result = analyze_stage(
        AnalyzeRequest(
            contrasts=tuple(_confirmatory_contrast(seed) for seed in CONFIRMATORY_SEED_COHORT.values),
            inference_protocol=CONFIRMATORY_INFERENCE_PROTOCOL,
            bootstrap_replicates=BOOTSTRAP_REPLICATE_COUNT,
            analysis_seed=Seed(31),
            output_directory=OUTPUTS_ROOT / "confirmatory" / "nbaiot_natural_devices" / "analysis",
            overwrite=False,
        )
    )
    typer.echo(
        f"analysis={result.publication_status.value} decision={result.decision.decision.value} "
        f"estimate={result.interval.point_estimate.value if result.interval.point_estimate else 'unavailable'}"
    )


def _run_confirmatory_seed(training_seed: Seed) -> None:
    context = _prepare_confirmatory_seed(training_seed)
    _evaluate_confirmatory_threshold_methods(context, _score_confirmatory_seed(context))


def _prepare_confirmatory_seed(training_seed: Seed) -> ConfirmatorySeedContext:
    population = PopulationId.NBAIOT_NATURAL_DEVICES
    split_protocol = SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS
    preprocessing_identity = PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD
    coordinate = FederatedTrainingCoordinate(
        population=population,
        training_seed=training_seed,
        split_protocol=split_protocol,
        preprocessing_identity=preprocessing_identity,
        model=TrainingModelId.FEDAVG_AUTOENCODER,
        model_coefficient=None,
    )
    construction = construct_population(
        PopulationConstructionRequest(
            population,
            canonical_root_under(DATA_ROOT, DatasetId.NBAIOT),
            training_seed,
            split_protocol,
            None,
        )
    )
    _, split_manifest = split_membership(
        SplitConstructionRequest(
            construction.membership,
            population,
            DatasetId.NBAIOT,
            training_seed,
            split_protocol,
            construction.manifest.document.membership_checksum,
        )
    )
    preprocessing = preprocess_federated_stage(
        PreprocessFederatedRequest(
            population,
            training_seed,
            split_protocol,
            preprocessing_identity,
            DATA_ROOT,
            None,
            None,
        )
    )
    identity_kind = resolve_population(population).declaration.identity_kind
    state_set_checksum = preprocessing_state_set_checksum(
        tuple(
            PreparedClientProvenance(
                client=ClientIdentity(population, item.client_identity.value, identity_kind),
                preprocessing_checksum=item.result.fitted_state.estimator_checksum,
            )
            for item in preprocessing.client_publications
        )
    )
    return ConfirmatorySeedContext(
        coordinate=coordinate,
        construction=construction,
        preprocessing=preprocessing,
        split_manifest=split_manifest,
        state_set_checksum=state_set_checksum,
        training_directory=_federated_training_directory(coordinate),
    )


def _score_confirmatory_seed(context: ConfirmatorySeedContext) -> ScoreArtifactManifest:
    training = train_fedavg_stage(
        TrainFedAvgRequest(
            context.coordinate,
            context.preprocessing.client_publications,
            ClientCount(len(context.construction.manifest.document.accepted_clients)),
            NBAIOT_AUTOENCODER,
            FEDAVG_TRAINING_PROTOCOL,
            CHECKPOINT_PROTOCOL,
            context.coordinate.training_seed,
            BATCH_SIZE,
            LEARNING_RATE,
            context.split_manifest.assignment_checksum,
            context.training_directory,
            False,
        )
    )
    selected = select_federated_checkpoint_stage(
        SelectFederatedCheckpointRequest(
            context.coordinate,
            None,
            training.candidates,
            CHECKPOINT_PROTOCOL,
            context.state_set_checksum,
            context.split_manifest.assignment_checksum,
            None,
            False,
        )
    ).decision.selected
    return score_federated_stage(
        ScoreFederatedRequest(
            selected,
            NBAIOT_AUTOENCODER,
            FeatureNameSequence(dataset_binding(DatasetId.NBAIOT).schema.feature_columns),
            _client_scoring_inputs(context.preprocessing.client_publications, context.construction.manifest.clients),
            BATCH_SIZE,
            context.training_directory / "scores",
            context.state_set_checksum,
            context.split_manifest.assignment_checksum,
            False,
        )
    ).result.manifest


def _evaluate_confirmatory_threshold_methods(context: ConfirmatorySeedContext, scores: ScoreArtifactManifest) -> None:
    inputs = ConfirmatoryThresholdInputs(
        scores=scores,
        eligible=_eligible_calibration_scores(scores),
        family_by_client=_family_identities(
            context.construction.manifest.clients, context.construction.manifest.family_by_client
        ),
        previous_evidence=None,
    )
    for method in population_capabilities(context.coordinate.population).valid_threshold_methods:
        inputs = _evaluate_confirmatory_threshold_method(context, inputs, method)


def _evaluate_confirmatory_threshold_method(
    context: ConfirmatorySeedContext,
    inputs: ConfirmatoryThresholdInputs,
    method: FederatedThresholdMethod,
) -> ConfirmatoryThresholdInputs:
    threshold = construct_federated_thresholds_stage(
        ConstructFederatedThresholdsRequest(
            ThresholdConstructionRequest(
                method,
                context.coordinate,
                CANONICAL_QUANTILE,
                population_capabilities(context.coordinate.population),
                inputs.eligible,
                inputs.family_by_client,
            ),
            _confirmatory_seed_directory(context.coordinate.training_seed) / "thresholds" / method.value,
            False,
        )
    ).result
    if threshold.__class__.__name__ == "ThresholdUnavailableResult":
        typer.echo(f"seed={context.coordinate.training_seed.value} {method.value}=unavailable")
        return inputs
    evaluation_inputs = build_federated_evaluation_inputs(inputs.scores, method)
    evaluation = evaluate_federated_stage(
        EvaluateFederatedRequest(
            inputs.scores,
            threshold,
            evaluation_inputs.cohort,
            evaluation_inputs.fixed_score_evidence,
            inputs.previous_evidence,
            EvidenceRole.CONFIRMATORY,
            (),
            (),
            (),
            None,
            _confirmatory_seed_directory(context.coordinate.training_seed) / "evaluations" / method.value,
            False,
        )
    )
    typer.echo(f"seed={context.coordinate.training_seed.value} {method.value}={evaluation.publication_status.value}")
    return ConfirmatoryThresholdInputs(
        scores=inputs.scores,
        eligible=inputs.eligible,
        family_by_client=inputs.family_by_client,
        previous_evidence=evaluation_inputs.fixed_score_evidence,
    )


def _eligible_calibration_scores(score_manifest: ScoreArtifactManifest) -> tuple[ClientBenignCalibrationScores, ...]:
    invariant = FixedScoreInvariant.from_manifest(score_manifest)
    return tuple(
        ClientBenignCalibrationScores(
            record.scored_client,
            score_manifest.coordinate,
            tuple(float(value) for value in pl.read_parquet(record.path)["reconstruction_error"].to_list()),
            checksum_file(record.path),
            invariant.calibration_score_set_checksum,
        )
        for record in sorted(score_manifest.calibration_records)
    )


def _client_scoring_inputs(
    publications: tuple[ClientPreprocessPublication, ...], clients: tuple[ClientIdentity, ...]
) -> tuple[ClientScoringInput, ...]:
    return tuple(
        ClientScoringInput(
            _client_with_id(clients, publication.client_identity.value),
            pl.read_parquet(publication.result.calibration_path),
            pl.read_parquet(publication.result.evaluation_path),
        )
        for publication in publications
    )


def _family_identities(
    clients: tuple[ClientIdentity, ...], family_by_client: tuple[tuple[str, str], ...]
) -> tuple[tuple[ClientIdentity, FamilyIdentity], ...]:
    return tuple(
        (_client_with_id(clients, client_id), FamilyIdentity(family)) for client_id, family in family_by_client
    )


def _client_with_id(clients: tuple[ClientIdentity, ...], client_id: str) -> ClientIdentity:
    client = next((candidate for candidate in clients if candidate.client_id == client_id), None)
    if client is None:
        raise ScientificContractError(f"population manifest is missing client {client_id}")
    return client


def _confirmatory_contrast(training_seed: Seed) -> PairedContrast:
    from json import loads

    shared = loads(
        _evaluation_path(training_seed, FederatedThresholdMethod.SHARED_THRESHOLD).read_text(encoding="utf-8")
    )
    local = loads(_evaluation_path(training_seed, FederatedThresholdMethod.LOCAL_THRESHOLD).read_text(encoding="utf-8"))
    if shared["score_coordinate"] != local["score_coordinate"]:
        raise ScientificContractError("paired evaluation documents use different training coordinates")
    shared_value = _population_metric(shared, MetricId.FPR_COEFFICIENT_OF_VARIATION)
    local_value = _population_metric(local, MetricId.FPR_COEFFICIENT_OF_VARIATION)
    return PairedContrast(
        coordinate=_deserialize_coordinate(shared["score_coordinate"]),
        evidence_role=EvidenceRole.CONFIRMATORY,
        metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
        left_method=FederatedThresholdMethod.SHARED_THRESHOLD,
        right_method=FederatedThresholdMethod.LOCAL_THRESHOLD,
        left_value=shared_value,
        right_value=local_value,
    )


def _evaluation_path(training_seed: Seed, method: FederatedThresholdMethod) -> Path:
    path = (
        _confirmatory_seed_directory(training_seed)
        / "evaluations"
        / method.value
        / FederatedEvaluationAssetName.DOCUMENT
    )
    if not path.is_file():
        raise ScientificContractError(f"missing completed evaluation document: {path}")
    return path


def _deserialize_coordinate(data: dict) -> FederatedTrainingCoordinate:
    return FederatedTrainingCoordinate(
        population=PopulationId(data["population"]),
        training_seed=Seed(data["training_seed"]),
        split_protocol=SplitProtocolId(data["split_protocol"]),
        preprocessing_identity=PreprocessingProtocolId(data["preprocessing_identity"]),
        model=TrainingModelId(data["model"]),
        model_coefficient=_deserialize_model_coefficient(data.get("model_coefficient")),
    )


def _deserialize_model_coefficient(value: float | None) -> ProximalCoefficient | None:
    if value is None:
        return None
    return ProximalCoefficient(value)


def _population_metric(document: dict, metric: MetricId) -> MetricValue:
    population = document["population"]
    result = next((item for item in population["metrics"] if item["metric"] == metric.value), None)
    if result is None:
        raise ScientificContractError(f"required confirmatory metric is missing: {metric.value}")
    if result["status"] != MetricStatus.AVAILABLE.value:
        raise ScientificContractError(f"required confirmatory metric is unavailable: {metric.value}")
    if result["value"] is None:
        raise ScientificContractError(f"required confirmatory metric is unavailable: {metric.value}")
    return MetricValue(result["value"])


def _federated_training_directory(coordinate: FederatedTrainingCoordinate) -> Path:
    return (
        OUTPUTS_ROOT
        / "federated"
        / coordinate.population.value
        / str(coordinate.training_seed.value)
        / coordinate.split_protocol.value
        / coordinate.preprocessing_identity.value
        / coordinate.model.value
    )


def _confirmatory_seed_directory(training_seed: Seed) -> Path:
    return OUTPUTS_ROOT / "confirmatory" / "nbaiot_natural_devices" / str(training_seed.value)


def main() -> None:
    app()


def _controlled_partition_condition(
    partition_kind: ControlledPartitionKind | None,
    concentration: float | None,
) -> ControlledPartitionCondition | None:
    if partition_kind is None:
        if concentration is not None:
            raise typer.BadParameter(
                f"concentration requires --partition-kind {ControlledPartitionKind.DIRICHLET.value}",
                param_hint="--concentration",
            )
        return None
    match partition_kind:
        case ControlledPartitionKind.IID:
            if concentration is not None:
                raise typer.BadParameter(
                    "IID construction must not carry a concentration",
                    param_hint="--concentration",
                )
            return iid_condition()
        case ControlledPartitionKind.DIRICHLET:
            if concentration is None:
                raise typer.BadParameter(
                    f"--partition-kind {ControlledPartitionKind.DIRICHLET.value} requires --concentration",
                    param_hint="--concentration",
                )
            if concentration not in _DECLARED_DIRICHLET_VALUES:
                allowed = ", ".join(str(value) for value in sorted(_DECLARED_DIRICHLET_VALUES))
                raise typer.BadParameter(
                    f"concentration must be one of the declared Dirichlet grid values: {allowed}",
                    param_hint="--concentration",
                )
            try:
                return dirichlet_condition(DirichletConcentration(concentration))
            except ValueError as error:
                raise typer.BadParameter(str(error), param_hint="--concentration") from error
    raise ScientificContractError(
        "unsupported controlled partition kind",
        subject=partition_kind,
    )


if __name__ == "__main__":
    main()
