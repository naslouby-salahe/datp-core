"""Pure-domain resolution of model/optimizer/batching protocol records."""

import pytest
from pydantic import ValidationError

from datp_core.config.models.protocol_config import ModelArchitectureConfig
from datp_core.config.resolver import resolve_project_configuration
from datp_core.domain.catalogue import BatchingRecord, ModelArchitectureRecord, OptimizerRecord


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
