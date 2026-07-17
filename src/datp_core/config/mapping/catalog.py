from decimal import Decimal
from typing import Literal, assert_never

from datp_core.config.resolver import ResolvedScientificCatalog
from datp_core.config.schemas.catalog import EligibilityCoverageRequiredConfig, ModelProfileConfig
from datp_core.domain.data.datasets import Regime
from datp_core.domain.data.partitioning import DirichletAlpha
from datp_core.domain.errors import ConfigurationError, DomainValidationError
from datp_core.domain.evaluation.alert_burden import CalibrationSampleCount
from datp_core.domain.evaluation.statistical_results import (
    ClaimOutcome,
    CoverageRatio,
    PairedDeltaDirection,
    Probability,
)
from datp_core.domain.experiments.claims import ExperimentRole
from datp_core.domain.experiments.specifications import (
    AbsorptionGateSpec,
    ConfirmatorySignRequirement,
    ManuscriptPlacement,
    ProfileCatalogueSpec,
    RegimeDViabilityGateSpec,
    SuppressionGateSpec,
    TemporalRecoveryGateSpec,
)
from datp_core.domain.learning.models import ActivationFunction, AutoencoderSpec
from datp_core.domain.learning.training import LrSchedulerType, ModelTrainingProfileSpec, OptimizerType
from datp_core.domain.runtime.admissibility import BatchSize
from datp_core.domain.thresholding.federated_statistics import FedStatsK
from datp_core.domain.thresholding.policies import FprTarget, ThresholdPercentile
from datp_core.domain.thresholding.variants import ShrinkageWeight


def map_profile_catalogue(schema: ResolvedScientificCatalog) -> ProfileCatalogueSpec:
    regime_d = _regime_d_coverage(schema=schema)
    thresholds = schema.thresholds
    evaluation = schema.evaluation
    return ProfileCatalogueSpec(
        quantile_grid=tuple(ThresholdPercentile(value=value) for value in thresholds.quantile_grid),
        dirichlet_alpha_grid=tuple(DirichletAlpha(value=value) for value in thresholds.dirichlet_alpha_grid),
        calibration_size_grid=tuple(CalibrationSampleCount(value=value) for value in thresholds.calibration_size_grid),
        shrinkage_weight_grid=tuple(ShrinkageWeight(value=float(value)) for value in thresholds.shrinkage_weight_grid),
        conformal_alpha=FprTarget(value=float(Decimal("1") - thresholds.conformal_percentile)),
        fed_stats_k_grid=tuple(FedStatsK(value=value) for value in thresholds.fed_stats_supplementary_k),
        absorption_gates=AbsorptionGateSpec(
            strongly_useful_fraction=Probability(value=evaluation.absorption_strongly_useful_fraction),
            partial_absorption_fraction=Probability(value=evaluation.absorption_partial_fraction),
            alternative_path_distance=Probability(value=evaluation.alternative_path_distance),
        ),
        temporal_recovery_gate=TemporalRecoveryGateSpec(
            meaningful_recovery_fraction=Probability(value=evaluation.temporal_recovery_fraction)
        ),
        regime_d_viability_gate=RegimeDViabilityGateSpec(
            minimum_eligibility_coverage=CoverageRatio(value=regime_d),
            minimum_calibration_samples=CalibrationSampleCount(value=evaluation.minimum_eligible_calibration_samples),
        ),
        suppression_gate=SuppressionGateSpec(outcome=ClaimOutcome.SUPPRESSED),
        confirmatory_sign_requirement=ConfirmatorySignRequirement(direction=PairedDeltaDirection.B1_MINUS_B2),
        evidence_roles=tuple(ExperimentRole),
        main_placement=ManuscriptPlacement.MAIN,
        supplementary_placement=ManuscriptPlacement.SUPPLEMENT,
    )


def map_model_training_profile_config(schema: ModelProfileConfig, *, input_dim: int) -> ModelTrainingProfileSpec:
    try:
        return ModelTrainingProfileSpec(
            autoencoder=AutoencoderSpec(
                input_dim=input_dim,
                hidden_dims=schema.hidden_dimensions,
                bottleneck_dim=schema.bottleneck_dimension,
                activation=_activation_from_literal(schema.activation),
            ),
            optimizer=_optimizer_from_literal(schema.optimizer),
            learning_rate=float(schema.learning_rate),
            weight_decay=float(schema.weight_decay),
            scheduler=LrSchedulerType.NONE,
            micro_batch_size=BatchSize(value=schema.micro_batch_size),
            local_epochs=schema.local_epochs,
            participation=schema.participation,
            rounds_max=schema.maximum_rounds,
        )
    except DomainValidationError as error:
        raise ConfigurationError(
            detail="model training profile mapping requires the locked core-training architecture and optimizer",
            section="scientific",
            field=f"models.{schema.profile_id}",
            mode="mapping",
        ) from error


def _activation_from_literal(value: Literal["relu"]) -> ActivationFunction:
    match value:
        case "relu":
            return ActivationFunction.RELU
        case _:
            assert_never(value)


def _optimizer_from_literal(value: Literal["adam"]) -> OptimizerType:
    match value:
        case "adam":
            return OptimizerType.ADAM
        case _:
            assert_never(value)


def _regime_d_coverage(*, schema: ResolvedScientificCatalog) -> Decimal:
    for profile in schema.regimes.profiles:
        if profile.regime is Regime.D:
            match profile.eligibility_coverage:
                case EligibilityCoverageRequiredConfig(minimum_fraction=minimum_fraction):
                    return minimum_fraction
                case _:
                    raise ValueError("Regime D must require an eligibility coverage fraction")
    raise ValueError("resolved regime catalogue must contain a Regime D coverage profile")
