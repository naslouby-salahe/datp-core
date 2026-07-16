from dataclasses import dataclass

from datp_core.config.schemas.catalog import (
    DatasetCatalogConfig,
    EvaluationCatalogConfig,
    ExperimentCatalogConfig,
    ExperimentProfileReferenceConfig,
    ModelCatalogConfig,
    ProtocolCatalogConfig,
    RegimeCatalogConfig,
    RegimeProfileConfig,
    TestCatalogConfig,
    ThresholdCatalogConfig,
)
from datp_core.config.schemas.execution import ExecutionProfilesConfig
from datp_core.domain.data.datasets import Regime
from datp_core.domain.errors import ConfigurationError


@dataclass(frozen=True, slots=True, kw_only=True)
class ResolvedScientificCatalog:
    protocol: ProtocolCatalogConfig
    datasets: DatasetCatalogConfig
    regimes: RegimeCatalogConfig
    models: ModelCatalogConfig
    thresholds: ThresholdCatalogConfig
    evaluation: EvaluationCatalogConfig
    experiments: ExperimentCatalogConfig
    tests: TestCatalogConfig
    execution: ExecutionProfilesConfig


@dataclass(frozen=True, slots=True, kw_only=True)
class ResolveScientificCatalogRequest:
    protocol: ProtocolCatalogConfig
    datasets: DatasetCatalogConfig
    regimes: RegimeCatalogConfig
    models: ModelCatalogConfig
    thresholds: ThresholdCatalogConfig
    evaluation: EvaluationCatalogConfig
    experiments: ExperimentCatalogConfig
    tests: TestCatalogConfig
    execution: ExecutionProfilesConfig


def resolve_scientific_catalog(request: ResolveScientificCatalogRequest) -> ResolvedScientificCatalog:
    _validate_regime_datasets(datasets=request.datasets, regimes=request.regimes)
    _validate_experiment_references(
        experiments=request.experiments,
        regimes=request.regimes,
        models=request.models,
        thresholds=request.thresholds,
    )
    _validate_execution_references(experiments=request.experiments, tests=request.tests, execution=request.execution)
    return ResolvedScientificCatalog(
        protocol=request.protocol,
        datasets=request.datasets,
        regimes=request.regimes,
        models=request.models,
        thresholds=request.thresholds,
        evaluation=request.evaluation,
        experiments=request.experiments,
        tests=request.tests,
        execution=request.execution,
    )


def _validate_regime_datasets(*, datasets: DatasetCatalogConfig, regimes: RegimeCatalogConfig) -> None:
    authorized_pairs = {
        (profile.dataset, regime) for profile in datasets.profiles for regime in profile.allowed_regimes
    }
    for regime in regimes.profiles:
        if (regime.dataset, regime.regime) not in authorized_pairs:
            raise ConfigurationError(
                detail="regime must reference an authorized dataset profile",
                section="resolver",
                field=regime.regime.value,
                mode="reference_resolution",
            )


def _validate_experiment_references(
    *,
    experiments: ExperimentCatalogConfig,
    regimes: RegimeCatalogConfig,
    models: ModelCatalogConfig,
    thresholds: ThresholdCatalogConfig,
) -> None:
    regime_profiles = {profile.regime: profile for profile in regimes.profiles}
    model_profile_ids = {profile.profile_id for profile in models.profiles}
    threshold_profile_ids = {profile.profile_id for profile in thresholds.b4_profiles}
    experiment_ids: set[str] = set()
    for experiment in experiments.profiles:
        _validate_experiment_id(experiment_id=experiment.experiment_id, known_ids=experiment_ids)
        _validate_experiment_regime(experiment=experiment, regime_profiles=regime_profiles)
        _validate_experiment_profile_reference(
            experiment_id=experiment.experiment_id,
            profile_id=experiment.model_profile_id,
            profile_ids=model_profile_ids,
            kind="model",
        )
        _validate_experiment_profile_reference(
            experiment_id=experiment.experiment_id,
            profile_id=experiment.threshold_profile_id,
            profile_ids=threshold_profile_ids,
            kind="threshold",
        )


def _validate_experiment_id(*, experiment_id: str, known_ids: set[str]) -> None:
    if experiment_id in known_ids:
        raise ConfigurationError(
            detail="experiment catalogue contains duplicate experiment ids",
            section="resolver",
            field=experiment_id,
            mode="reference_resolution",
        )
    known_ids.add(experiment_id)


def _validate_experiment_regime(
    *, experiment: ExperimentProfileReferenceConfig, regime_profiles: dict[Regime, RegimeProfileConfig]
) -> None:
    regime = regime_profiles.get(experiment.regime)
    if regime is None or regime.dataset is not experiment.dataset:
        raise ConfigurationError(
            detail="experiment dataset and regime reference must resolve to one compatible regime profile",
            section="resolver",
            field=experiment.experiment_id,
            mode="reference_resolution",
        )


def _validate_experiment_profile_reference(
    *, experiment_id: str, profile_id: str, profile_ids: set[str], kind: str
) -> None:
    if profile_id not in profile_ids:
        raise ConfigurationError(
            detail=f"experiment references an unknown {kind} profile",
            section="resolver",
            field=experiment_id,
            mode="reference_resolution",
        )


def _validate_execution_references(
    *,
    experiments: ExperimentCatalogConfig,
    tests: TestCatalogConfig,
    execution: ExecutionProfilesConfig,
) -> None:
    profile_ids = {profile.profile_id for profile in execution.profiles}
    references = {experiment.execution_profile_id for experiment in experiments.profiles} | {
        profile.execution_profile_id for profile in tests.profiles
    }
    unknown_profile_ids = references - profile_ids
    if unknown_profile_ids:
        raise ConfigurationError(
            detail="configuration references an unknown execution profile",
            section="resolver",
            field=sorted(unknown_profile_ids)[0],
            mode="reference_resolution",
        )
