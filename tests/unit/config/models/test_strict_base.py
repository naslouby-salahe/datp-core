"""Tests for StrictFrozenConfigModel and SchemaVersionOneConfigModel."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from datp_core.config.models._base import SchemaVersionOneConfigModel, StrictFrozenConfigModel


class ExampleStrict(StrictFrozenConfigModel):
    name: str
    count: int


class ExampleSchemaV1(SchemaVersionOneConfigModel):
    label: str


class TestStrictFrozenConfigModel:
    def test_extra_fields_are_rejected(self) -> None:
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            ExampleStrict(name="test", count=1, unknown_field="bad")  # pyright: ignore[reportCallIssue]

    def test_mutation_is_rejected(self) -> None:
        instance = ExampleStrict(name="test", count=1)
        with pytest.raises(ValidationError):
            instance.name = "changed"  # type: ignore[misc]

    def test_extra_fields_in_dict_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ExampleStrict.model_validate({"name": "test", "count": 1, "extra": True})

    def test_coercion_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ExampleStrict(name="test", count="not_an_int")  # type: ignore[arg-type]

    def test_valid_instance_constructs(self) -> None:
        instance = ExampleStrict(name="test", count=42)
        assert instance.name == "test"
        assert instance.count == 42

    def test_missing_required_field_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ExampleStrict(name="test")  # pyright: ignore[reportCallIssue]

    def test_wrong_scalar_type_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ExampleStrict(name=123, count=1)  # type: ignore[arg-type]


class TestSchemaVersionOneConfigModel:
    def test_schema_version_1_accepted(self) -> None:
        instance = ExampleSchemaV1(schema_version=1, label="ok")
        assert instance.schema_version == 1

    def test_schema_version_2_rejected(self) -> None:
        with pytest.raises(ValidationError, match="schema_version"):
            ExampleSchemaV1(schema_version=2, label="bad")  # type: ignore[arg-type]

    def test_schema_version_missing_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ExampleSchemaV1(label="missing schema_version")  # type: ignore[call-arg]

    def test_extra_fields_rejected(self) -> None:
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            ExampleSchemaV1(schema_version=1, label="ok", unknown="bad")  # pyright: ignore[reportCallIssue]


class TestAllSchemaVersionDocumentsParse:
    """Prove all four authored document families parse with schema_version=1."""

    def test_runtime_schema_version_accepted(self) -> None:
        from datp_core.config.models.runtime_config import AuthoredRuntimeConfig

        data = {
            "schema_version": 1,
            "roots": {
                "raw_data": "data/raw",
                "processed_data": "data/processed",
                "manifests": "data/manifests",
                "checkpoints": "data/checkpoints",
                "outputs": "data/outputs",
                "runtime_state": "data/runtime_state",
            },
            "raw_source_policy": {
                "follow_symlink": True,
                "require_resolved_target_readable": True,
                "reject_broken_symlink": True,
                "reject_symlink_loop": True,
                "write_access": "forbidden",
                "create_files_under_raw_root": "forbidden",
            },
            "determinism_enforcement": {
                "strict": {
                    "python_hash_seed": 0,
                    "cublas_workspace_config": ":4096:8",
                    "torch_use_deterministic_algorithms": True,
                    "torch_deterministic_algorithms_warn_only": False,
                    "cudnn_deterministic": True,
                    "cudnn_benchmark": False,
                    "float32_matmul_precision": "highest",
                    "tensorfloat32_matmul": False,
                    "tensorfloat32_cudnn": False,
                    "dataloader_worker_seeding": "deterministic",
                    "file_discovery_order": "sorted",
                    "client_iteration_order": "sorted",
                    "nondeterministic_operation_policy": "forbidden",
                    "recorded_environment_fields": ["gpu_identity"],
                    "unavailable_determinism_policy": "forbidden",
                }
            },
            "device_policy_rules": {
                "cuda_required": {"cpu_fallback": "forbidden"},
                "cpu_only": {"permitted_for_scientific_training_or_scoring": False},
            },
            "resource_pressure_policy": {
                "silent_reduction_of_batch_size": "forbidden",
                "silent_reduction_of_rounds_seeds_clients_or_sample_counts": "forbidden",
                "on_budget_exceeded": "block_execution_and_report",
            },
            "execution_profiles": {
                "test": {
                    "device_policy": "cpu_only",
                    "determinism": "strict",
                    "resource_budget": {"max_ram_gib": 4},
                    "concurrency": {"worker_count": 1},
                    "data_loading": {"chunk_row_count": 1000, "streaming": True},
                    "process_start_method": "spawn",
                    "log_interval_rounds": 1,
                    "atomic_write": True,
                }
            },
        }
        instance = AuthoredRuntimeConfig.model_validate(data)
        assert instance.schema_version == 1

    def test_runtime_schema_version_rejected(self) -> None:
        from datp_core.config.models.runtime_config import AuthoredRuntimeConfig

        with pytest.raises(ValidationError, match="schema_version"):
            AuthoredRuntimeConfig(schema_version=2)  # type: ignore[call-arg]

    def test_experiments_schema_version_accepted(self) -> None:
        from datp_core.config.models.experiment_config import AuthoredExperimentsCatalogueConfig

        data = {
            "schema_version": 1,
            "study_populations": {},
            "capabilities": [],
            "suppression_behaviors": [],
            "population_readiness_rule": {},
            "eligibility_gates": {},
            "analysis_conventions": {},
            "experiments": [],
        }
        instance = AuthoredExperimentsCatalogueConfig.model_validate(data)
        assert instance.schema_version == 1

    def test_experiments_schema_version_rejected(self) -> None:
        from datp_core.config.models.experiment_config import AuthoredExperimentsCatalogueConfig

        with pytest.raises(ValidationError, match="schema_version"):
            AuthoredExperimentsCatalogueConfig(schema_version=99)  # type: ignore[call-arg]

    def test_protocols_schema_version_accepted(self) -> None:
        from datp_core.config.models.protocol_config import AuthoredProtocolsConfig

        data = {
            "schema_version": 1,
            "model_architectures": {},
            "optimizers": {},
            "batching": {},
            "determinism": {
                "seed_domains": [],
                "partition_seed_independent_of_training_seeds": True,
                "checkpoint_selection_uses_no_stochastic_seed": True,
                "derived_seed_algorithm": {},
                "seed_namespaces": {},
                "resolved_seeds_required_in_manifests": [],
            },
            "seed_cohorts": {},
            "checkpoint_profiles": {},
            "training_profiles": {},
            "eligibility_policies": {},
            "normalization_strategies": {},
            "normalization_fit_scopes": {},
            "normalization_leakage_rule": "no_restriction",
            "quantile_estimators": {},
            "threshold_policy_defaults": {
                "source_score_population": "local",
                "eligibility_filter": "none",
                "attack_rows_forbidden_in_calibration": True,
                "non_finite_calibration_score": "reject",
                "empty_client_calibration": "reject",
                "application_scope": "global",
                "required_diagnostic_fields": [],
            },
            "threshold_policies": {},
            "metric_definitions": {
                "prediction_rule": "threshold",
                "per_client_before_aggregation": True,
                "test_rows_only": True,
                "fpr": {},
                "tpr": {},
                "balanced_accuracy": {},
                "macro_f1": {},
                "auroc": {},
                "cross_client_aggregation": {
                    "mean_fpr": {},
                    "standard_deviation_ddof": 1,
                    "cv_fpr": {},
                    "cv_tpr": {},
                    "iqr_fpr": {},
                    "fpr_range": {},
                    "worst_client_fpr": {},
                    "p10_macro_f1": {},
                    "worst_client_ba": {},
                    "jain_index": {},
                    "gini_coefficient": {},
                },
                "threshold_estimation": {
                    "absolute_threshold_error": {},
                    "relative_threshold_error": {},
                    "oracle_definition": "none",
                    "target_exceedance": {},
                    "signed_attainment_error": {},
                    "absolute_attainment_error": {},
                    "threshold_dispersion": {},
                    "threshold_variance_across_replicates": {},
                },
                "heterogeneity_diagnostics": {
                    "pairwise_js_divergence": {
                        "definition": "none",
                        "histogram_bins": 10,
                        "binning_range": "auto",
                        "binning_edges": "auto",
                        "logarithm_base": 2,
                        "empty_bin_handling": "ignore",
                        "pairwise_aggregation": "mean",
                        "unit": "bits",
                        "direction": "lower_is_better",
                        "minimum_client_count": 2,
                    }
                },
                "cluster_diagnostics": {
                    "adjusted_rand_index": {},
                    "within_cluster_dispersion": {},
                    "across_cluster_dispersion": {},
                },
                "precision_policy": {"computation": "float64", "rounding": "none"},
                "metric_statuses": [],
                "forbidden_substitutions": [],
            },
            "metric_bundles": {},
            "nested_replicate_policy": {
                "replicate_values_computed_first": True,
                "summarized_within_seed_before_across_seed_inference": True,
                "seed_level_statistic": "mean",
                "replicates_counted_as_independent_units": False,
                "additional_required_replicate_statistic": "variance",
            },
            "result_types": {},
            "evaluation_result_contract": {
                "per_evaluation_result_type": "none",
                "per_evaluation_eligibility_result_type": "none",
                "per_evaluation_required_records": [],
            },
            "artifact_identity": {
                "hash_function": "sha256",
                "digest_bytes": 32,
                "canonical_serialization": "json",
                "absolute_paths_excluded_from_identity": True,
                "fingerprints": {
                    "source": [],
                    "schema": [],
                    "materialization": [],
                    "client_assignment": [],
                    "model": [],
                    "training": [],
                    "checkpoint": [],
                    "score": [],
                    "threshold": [],
                    "metric": [],
                    "analysis": [],
                },
                "lineage_validation_before_reuse": [],
                "reuse_rejected_when_any_changes": [],
            },
            "communication_estimation_contract": {
                "estimate_basis": "none",
                "field_encodings": {},
                "threshold_exchange": {
                    "direction": "none",
                    "b1": {},
                    "b2": {},
                    "b4": {},
                    "federated_summary": {},
                },
                "candidate_grid_payload": "none",
                "model_exchange": {"field_width": "none", "directions": [], "bytes_per_round_formula": "none"},
                "checkpoint_storage": {"contents": [], "model_parameter_bytes_formula": "none"},
                "filename_match_is_not_lineage_evidence": True,
                "frozen_artifacts_immutable": True,
                "ambiguous_latest_reference": "reject",
            },
            "report_defaults": {
                "ordering": "none",
                "missing_value_policy": "none",
                "table_output_formats": [],
                "figure_output_formats": [],
                "provenance_required_per_artifact": True,
                "analysis_defined_direction_token": "none",
            },
            "operational_inputs": {
                "benign_decision_rate": {
                    "configured": False,
                    "required_fields": [],
                    "finite_value_validation": "none",
                    "non_negative_validation": "none",
                    "unavailable_behavior": "none",
                    "invented_rate_forbidden": True,
                },
            },
            "statistical_profiles": {},
            "report_profiles": {},
        }
        instance = AuthoredProtocolsConfig.model_validate(data)
        assert instance.schema_version == 1

    def test_protocols_schema_version_rejected(self) -> None:
        from datp_core.config.models.protocol_config import AuthoredProtocolsConfig

        with pytest.raises(ValidationError, match="schema_version"):
            AuthoredProtocolsConfig(schema_version=99)  # type: ignore[call-arg]

    def test_dataset_schema_version_accepted(self) -> None:
        from datp_core.config.models.dataset_config import AuthoredDatasetConfig

        data = {
            "schema_version": 1,
            "dataset": "test",
            "display_name": "Test",
            "schema_id": "test_schema",
            "source_layout": {"root": "/"},
            "field_schema": {
                "source_column_count": 1,
                "header_required": False,
                "identity_scheme": {
                    "row_identity": {},
                    "timestamp_field": "ts",
                    "provenance_fields": [],
                },
                "label_fields": {"binary_label": {}},
                "categorical_encoding": "none",
                "leakage_exclusions": [],
            },
            "source_contract": {},
            "fingerprint_inputs": {
                "source": [],
                "schema": [],
                "materialization": [],
                "client_assignment": [],
            },
            "eligibility_policy": "default",
            "materializations": {},
            "setups": {},
        }
        instance = AuthoredDatasetConfig.model_validate(data)
        assert instance.schema_version == 1

    def test_dataset_schema_version_rejected(self) -> None:
        from datp_core.config.models.dataset_config import AuthoredDatasetConfig

        with pytest.raises(ValidationError, match="schema_version"):
            AuthoredDatasetConfig(schema_version=99)  # type: ignore[call-arg]
