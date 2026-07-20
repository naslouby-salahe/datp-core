"""Pure-domain resolution of model/optimizer/batching protocol records."""

import pytest
from pydantic import ValidationError

from datp_core.config.models.protocol_config import EligibilityPolicyConfig, ModelArchitectureConfig
from datp_core.config.resolver import resolve_project_configuration
from datp_core.domain.catalogue import (
    BatchingRecord,
    EligibilityPolicyRecord,
    MetricBundleRecord,
    ModelArchitectureRecord,
    NormalizationStrategyRecord,
    OptimizerRecord,
    QuantileEstimatorRecord,
)
from datp_core.domain.identifiers import EligibilityPolicyId


def test_resolved_config_holds_pure_domain_protocol_records() -> None:
    cfg = resolve_project_configuration()

    model = cfg.model_architectures["fixed_autoencoder"]
    assert isinstance(model, ModelArchitectureRecord)
    assert tuple(dim.value for dim in model.hidden_dims) == (80, 40, 20)
    assert model.activation == "relu"
    assert model.initialization_seeded_by == "training_seed"
    assert model.anomaly_score_orientation == "higher_score_means_more_anomalous"

    optimizer = cfg.optimizers["adam_default"]
    assert isinstance(optimizer, OptimizerRecord)
    assert optimizer.learning_rate.value == pytest.approx(0.001)
    assert optimizer.weight_decay.value == pytest.approx(0.0)
    assert optimizer.amsgrad is False

    batching = cfg.batching_profiles["standard"]
    assert isinstance(batching, BatchingRecord)
    assert batching.micro_batch_size.value == 256
    assert batching.effective_batch_size.value == 256


def test_resolved_config_holds_pure_eligibility_normalization_quantile_metric_records() -> None:
    cfg = resolve_project_configuration()

    eligibility = cfg.eligibility_policies[EligibilityPolicyId("primary_analysis")]
    assert isinstance(eligibility, EligibilityPolicyRecord)
    assert eligibility.minimum_benign_calibration_count.value == 100
    assert eligibility.ineligible_client_deployment_fallback.reported_status == "unavailable_ineligible_client"
    assert eligibility.ineligible_client_deployment_fallback.enters_primary_dispersion is False

    assert all(isinstance(n, NormalizationStrategyRecord) for n in cfg.normalization_strategies.values())
    assert all(isinstance(q, QuantileEstimatorRecord) for q in cfg.quantile_estimators.values())
    assert all(isinstance(m, MetricBundleRecord) for m in cfg.metric_bundles.values())


def test_eligibility_fallback_subdocument_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        EligibilityPolicyConfig.model_validate(
            {
                "minimum_benign_calibration_count": 100,
                "determined_before_test_evaluation": True,
                "identical_across_policies_in_one_comparison": True,
                "fpr_evaluable_requires_non_empty_benign_test_denominator": True,
                "attack_evaluable_requires": ["valid_per_client_attack_assignment"],
                "ineligible_clients_excluded_from_primary_dispersion": True,
                "ineligible_client_deployment_fallback": {
                    "threshold_source": "the_shared_threshold_of_the_evaluated_policys_own_eligible_population",
                    "shared_construction": "unweighted_arithmetic_mean_of_eligible_local_quantiles",
                    "reported_status": "unavailable_ineligible_client",
                    "enters_primary_dispersion": False,
                    "unexpected": "x",
                },
                "zero_eligible_clients_behavior": "typed_unavailable_ineligible_population",
            }
        )


def test_model_architecture_subdocuments_reject_unknown_fields() -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        ModelArchitectureConfig.model_validate(
            {
                "kind": "dense_autoencoder",
                "input_dimension": {
                    "resolution": "from_materialized_post_encoding_feature_schema",
                    "declared_per_dataset": False,
                    "validation": "must_equal_materialization_post_encoding_feature_count",
                    "unexpected": "x",
                },
                "hidden_dims": [80, 40, 20],
                "bottleneck_dim": "last_hidden_dim",
                "decoder": {
                    "construction": "mirrors_encoder_dimensions_in_reverse",
                    "final_layer_output_dim": "input_dimension",
                },
                "activation": "relu",
                "activation_placement": "after_every_linear_layer_except_the_final_decoder_layer",
                "output_activation": "identity",
                "normalization_layers": "none",
                "bias": True,
                "parameter_initialization": {
                    "weight": "kaiming_uniform_fan_in_leaky_relu_negative_slope_sqrt_5",
                    "bias": "uniform_symmetric_one_over_sqrt_fan_in",
                    "applied_to": "every_linear_layer",
                    "seeded_by": "training_seed",
                },
                "reconstruction_objective": "mse",
                "training_loss_reduction": "mean_over_all_elements_of_the_batch",
                "anomaly_score": {
                    "definition": "per_row_mean_of_squared_feature_reconstruction_error",
                    "orientation": "higher_score_means_more_anomalous",
                },
                "precision": "fp32",
            }
        )
