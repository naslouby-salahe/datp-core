from decimal import Decimal

from datp_core.config.resolver import ResolvedScientificCatalog
from datp_core.config.schemas.catalog import EligibilityCoverageRequiredConfig
from datp_core.domain.data.datasets import Regime
from datp_core.domain.data.partitioning import DirichletAlpha
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


def _regime_d_coverage(*, schema: ResolvedScientificCatalog) -> Decimal:
    for profile in schema.regimes.profiles:
        if profile.regime is Regime.D:
            match profile.eligibility_coverage:
                case EligibilityCoverageRequiredConfig(minimum_fraction=minimum_fraction):
                    return minimum_fraction
                case _:
                    raise ValueError("Regime D must require an eligibility coverage fraction")
    raise ValueError("resolved regime catalogue must contain a Regime D coverage profile")
