"""Resolution of quantile estimators, threshold policy defaults, and the closed threshold-policy
discriminated union into their domain records."""

from __future__ import annotations

from datp_core.config.authored.protocols import AuthoredProtocolsConfig
from datp_core.config.authored.protocols.thresholds import (
    CalibrationFallbackPolicyConfig,
    CentralizedPooledThresholdPolicyConfig,
    ClusterThresholdPolicyConfig,
    FamilyMeanThresholdPolicyConfig,
    FederatedFixedCoefficientPolicyConfig,
    FederatedMatchedExceedancePolicyConfig,
    LocalGlobalShrinkagePolicyConfig,
    LocalQuantileThresholdPolicyConfig,
    SharedMeanThresholdPolicyConfig,
    SharedPooledThresholdPolicyConfig,
    SharedWeightedThresholdPolicyConfig,
    SplitConformalThresholdPolicyConfig,
    ThresholdPolicyDefaultsConfig,
    TypedThresholdPolicyConfig,
)
from datp_core.config.errors import ConfigurationError
from datp_core.core.identifiers import ThresholdPolicyId
from datp_core.thresholding.policies.clustering import (
    ClusterFingerprintConfiguration,
    ClusterStandardizationConfiguration,
    ClusterThresholdPolicyRecord,
    KMeansConfiguration,
)
from datp_core.thresholding.policies.common import QuantileEstimatorRecord, ThresholdPolicyDefaultsRecord
from datp_core.thresholding.policies.conformal import SplitConformalThresholdPolicyRecord
from datp_core.thresholding.policies.enums import ClusterAggregation, ThresholdOwnership
from datp_core.thresholding.policies.federated import (
    CandidateGrid,
    ExceedanceExchange,
    FederatedFixedCoefficientThresholdPolicyRecord,
    FederatedMatchedExceedanceThresholdPolicyRecord,
    SelectionRules,
)
from datp_core.thresholding.policies.grouped import FamilyMeanThresholdPolicyRecord
from datp_core.thresholding.policies.shared import (
    CentralizedPooledThresholdPolicyRecord,
    LocalQuantileThresholdPolicyRecord,
    SharedMeanThresholdPolicyRecord,
    SharedPooledThresholdPolicyRecord,
    SharedWeightedThresholdPolicyRecord,
)
from datp_core.thresholding.policies.shrinkage import (
    CalibrationFallbackThresholdPolicyRecord,
    LocalGlobalShrinkageThresholdPolicyRecord,
    PermittedWeightRange,
    WeightFormulaConstants,
)
from datp_core.thresholding.policies.union import ThresholdPolicyRecord

_THRESHOLD_POLICY_RECORD_TYPES: dict[type[TypedThresholdPolicyConfig], type[ThresholdPolicyRecord]] = {
    SharedMeanThresholdPolicyConfig: SharedMeanThresholdPolicyRecord,
    SharedPooledThresholdPolicyConfig: SharedPooledThresholdPolicyRecord,
    SharedWeightedThresholdPolicyConfig: SharedWeightedThresholdPolicyRecord,
    LocalQuantileThresholdPolicyConfig: LocalQuantileThresholdPolicyRecord,
    FamilyMeanThresholdPolicyConfig: FamilyMeanThresholdPolicyRecord,
    CentralizedPooledThresholdPolicyConfig: CentralizedPooledThresholdPolicyRecord,
    ClusterThresholdPolicyConfig: ClusterThresholdPolicyRecord,
    SplitConformalThresholdPolicyConfig: SplitConformalThresholdPolicyRecord,
    LocalGlobalShrinkagePolicyConfig: LocalGlobalShrinkageThresholdPolicyRecord,
    CalibrationFallbackPolicyConfig: CalibrationFallbackThresholdPolicyRecord,
    FederatedMatchedExceedancePolicyConfig: FederatedMatchedExceedanceThresholdPolicyRecord,
    FederatedFixedCoefficientPolicyConfig: FederatedFixedCoefficientThresholdPolicyRecord,
}


def resolve_threshold_policy(cfg: TypedThresholdPolicyConfig) -> ThresholdPolicyRecord:
    """Convert an authored threshold-policy variant into its pure domain record, losslessly."""
    record_type = _THRESHOLD_POLICY_RECORD_TYPES.get(type(cfg))
    if record_type is None:
        raise ConfigurationError(f"Unsupported authored threshold policy configuration: {type(cfg).__name__}")
    if isinstance(cfg, ClusterThresholdPolicyConfig):
        return ClusterThresholdPolicyRecord(
            policy=cfg.policy,
            quantile=cfg.quantile,
            quantile_estimator=cfg.quantile_estimator,
            canonical=cfg.canonical,
            exploratory=cfg.exploratory,
            aggregation=ClusterAggregation(cfg.aggregation),
            cluster_count=cfg.cluster_count,
            aggregated_quantity=cfg.aggregated_quantity,
            aggregation_formula=cfg.aggregation_formula,
            median_estimator=cfg.median_estimator,
            sample_weighting=cfg.sample_weighting,
            client_accumulation_order=cfg.client_accumulation_order,
            fingerprint=ClusterFingerprintConfiguration(
                features=tuple(cfg.fingerprint_features),
                estimators=cfg.fingerprint_estimators,
                degenerate_client_rules=cfg.fingerprint_degenerate_client_rules,
                non_finite_value_behavior=cfg.fingerprint_non_finite_value_behavior,
            ),
            standardization=ClusterStandardizationConfiguration.from_config(cfg.standardization),
            client_ordering_before_fit=cfg.client_ordering_before_fit,
            kmeans=KMeansConfiguration(
                random_seed=int(cfg.clustering["random_seed"]),
                initialization_runs=int(cfg.clustering["initialization_runs"]),
                maximum_iterations=int(cfg.clustering["maximum_iterations"]),
                convergence_tolerance=float(cfg.clustering["convergence_tolerance"]),
            ),
            label_canonicalization=cfg.label_canonicalization,
            insufficient_eligible_clients_behavior=cfg.insufficient_eligible_clients_behavior,
            degenerate_fingerprint_matrix_behavior=cfg.degenerate_fingerprint_matrix_behavior,
            required_diagnostics=tuple(cfg.required_diagnostics),
            threshold_ownership=ThresholdOwnership(cfg.threshold_ownership),
        )
    if isinstance(cfg, (LocalGlobalShrinkagePolicyConfig, CalibrationFallbackPolicyConfig)):
        permitted_weight_range = PermittedWeightRange.from_config(cfg.permitted_weight_range)
        if isinstance(cfg, CalibrationFallbackPolicyConfig):
            return CalibrationFallbackThresholdPolicyRecord(
                policy=cfg.policy,
                quantile=cfg.quantile,
                quantile_estimator=cfg.quantile_estimator,
                local_reference=cfg.local_reference,
                global_reference=cfg.global_reference,
                interpolation_formula=cfg.interpolation_formula,
                weight_semantics=cfg.weight_semantics,
                weight_scope=cfg.weight_scope,
                permitted_weight_range=permitted_weight_range,
                threshold_ownership=ThresholdOwnership(cfg.threshold_ownership),
                weight_formula=cfg.weight_formula,
                weight_formula_constants=WeightFormulaConstants.from_config(cfg.weight_formula_constants),
                weight_monotone_in_calibration_count=cfg.weight_monotone_in_calibration_count,
                clamping=cfg.clamping,
                zero_calibration_behavior=cfg.zero_calibration_behavior,
                minimum_calibration_behavior=cfg.minimum_calibration_behavior,
                effective_lambda_reporting=cfg.effective_lambda_reporting,
                fallback_frequency_reporting=cfg.fallback_frequency_reporting,
            )
        return LocalGlobalShrinkageThresholdPolicyRecord(
            policy=cfg.policy,
            quantile=cfg.quantile,
            quantile_estimator=cfg.quantile_estimator,
            local_reference=cfg.local_reference,
            global_reference=cfg.global_reference,
            interpolation_formula=cfg.interpolation_formula,
            weight_semantics=cfg.weight_semantics,
            weight_scope=cfg.weight_scope,
            permitted_weight_range=permitted_weight_range,
            threshold_ownership=ThresholdOwnership(cfg.threshold_ownership),
            shrinkage_weight_grid=tuple(cfg.shrinkage_weight_grid),
            shrinkage_weight=cfg.shrinkage_weight,
            shrinkage_weight_resolution=cfg.shrinkage_weight_resolution,
            out_of_range_weight_behavior=cfg.out_of_range_weight_behavior,
            effective_lambda_reporting=cfg.effective_lambda_reporting,
        )
    if isinstance(cfg, FederatedMatchedExceedancePolicyConfig):
        return FederatedMatchedExceedanceThresholdPolicyRecord(
            policy=cfg.policy,
            mode=cfg.mode,
            quantile=cfg.quantile,
            primary_comparator=cfg.primary_comparator,
            client_message=dict(cfg.client_message),
            global_mean_formula=cfg.global_mean_formula,
            within_term_formula=cfg.within_term_formula,
            between_term_formula=cfg.between_term_formula,
            pooled_variance_formula=cfg.pooled_variance_formula,
            between_term_mandatory=cfg.between_term_mandatory,
            between_ratio_formula=cfg.between_ratio_formula,
            between_ratio_zero_denominator_behavior=cfg.between_ratio_zero_denominator_behavior,
            global_standard_deviation_formula=cfg.global_standard_deviation_formula,
            client_accumulation_order=cfg.client_accumulation_order,
            zero_total_count_behavior=cfg.zero_total_count_behavior,
            candidate_grid=CandidateGrid.from_config(cfg.candidate_grid),
            exceedance_exchange=ExceedanceExchange.from_config(
                {k: tuple(v) if isinstance(v, list) else v for k, v in cfg.exceedance_exchange.items()}
            ),
            selection=SelectionRules.from_config(cfg.selection),
            required_diagnostics=tuple(cfg.required_diagnostics),
            threshold_ownership=ThresholdOwnership(cfg.threshold_ownership),
        )
    return record_type(**cfg.model_dump())


def resolve_threshold_policies(authored: AuthoredProtocolsConfig) -> dict[ThresholdPolicyId, ThresholdPolicyRecord]:
    return {
        ThresholdPolicyId(tp_key): resolve_threshold_policy(tp_cfg)
        for tp_key, tp_cfg in authored.threshold_policies.items()
    }


def resolve_quantile_estimators(authored: AuthoredProtocolsConfig) -> dict[str, QuantileEstimatorRecord]:
    return {
        k: QuantileEstimatorRecord(
            identifier=k,
            sort_order=v.sort_order,
            index_formula=v.index_formula,
            interpolation=v.interpolation,
            single_element_behavior=v.single_element_behavior,
            empty_input_behavior=v.empty_input_behavior,
            non_finite_input_behavior=v.non_finite_input_behavior,
            tie_behavior=v.tie_behavior,
        )
        for k, v in authored.quantile_estimators.items()
    }


def resolve_threshold_policy_defaults(cfg: ThresholdPolicyDefaultsConfig) -> ThresholdPolicyDefaultsRecord:
    return ThresholdPolicyDefaultsRecord(
        source_score_population=cfg.source_score_population,
        eligibility_filter=cfg.eligibility_filter,
        attack_rows_forbidden_in_calibration=cfg.attack_rows_forbidden_in_calibration,
        non_finite_calibration_score=cfg.non_finite_calibration_score,
        empty_client_calibration=cfg.empty_client_calibration,
        application_scope=cfg.application_scope,
        required_diagnostic_fields=tuple(cfg.required_diagnostic_fields),
    )
