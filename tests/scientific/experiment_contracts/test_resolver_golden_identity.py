from __future__ import annotations

import os
from pathlib import Path

import pytest

from datp_core.config.loading import RuntimeBootstrapSettings
from datp_core.config.project import ResolvedProjectConfiguration, resolve_project_configuration
from datp_core.core.identifiers import DatasetId


def test_scientific_fingerprint_is_stable(_resolved: ResolvedProjectConfiguration) -> None:
    # Golden hash updated after four str-to-enum typing tightenings: `recalibration_mode`
    # (`EvaluationSpecRecord`/`StageJobContext`), `ClusterThresholdPolicyRecord.aggregation`,
    # every `*ThresholdPolicyRecord.threshold_ownership`, and `StatisticalProfileRecord.method`
    # (now `StatisticalMethod`) -- an enum leaf canonicalizes differently from a plain string in
    # `canonicalize_value` (core/hashing.py). The underlying authored values are unchanged; only
    # their resolved Python representation is now a validated enum instead of an unvalidated string.
    assert _resolved.scientific_fingerprint.value == (
        "efa04eec9187ab5785b09f298df311737e15b43327e7224e4aead08b56130aee"
    )


def test_execution_fingerprint_is_stable(_resolved: ResolvedProjectConfiguration) -> None:
    assert _resolved.execution_fingerprint.value == ("723ed7d2d53daf3a8e8976213202852dfcadb311013e54113b75774e465b71c2")


def test_registry_cardinality(_resolved: ResolvedProjectConfiguration) -> None:
    r = _resolved
    assert len(r.datasets) == 3
    assert len(r.populations) == 7
    assert len(r.experiments) == 23
    assert len(r.training_profiles) > 0
    assert len(r.checkpoint_profiles) > 0
    assert len(r.seed_cohorts) > 0
    assert len(r.statistical_profiles) > 0
    assert len(r.threshold_policies) == 14
    assert len(r.model_architectures) > 0
    assert len(r.optimizers) > 0
    assert len(r.batching_profiles) > 0
    assert len(r.eligibility_policies) > 0
    assert len(r.normalization_strategies) > 0
    assert len(r.quantile_estimators) > 0
    assert len(r.metric_bundles) > 0
    assert len(r.report_profiles) > 0
    assert len(r.result_types) > 0
    assert len(r.eligibility_gates._items) > 0  # pyright: ignore[reportPrivateUsage]


def test_dataset_key_order(_resolved: ResolvedProjectConfiguration) -> None:
    keys = [str(k) for k in _resolved.datasets._items]  # pyright: ignore[reportPrivateUsage]
    assert keys == ["ciciot2023", "edge_iiotset", "nbaiot"]


def test_population_key_order(_resolved: ResolvedProjectConfiguration) -> None:
    keys = [str(k) for k in _resolved.populations._items]  # pyright: ignore[reportPrivateUsage]
    assert keys == [
        "nbaiot_natural_devices",
        "nbaiot_anchor_natural_devices",
        "nbaiot_dirichlet_heterogeneity",
        "ciciot2023_file_pseudo_clients",
        "edge_iiotset_sensor_groups",
        "edge_iiotset_chronological_groups",
        "edge_iiotset_static_reference_groups",
    ]


def test_experiment_key_order(_resolved: ResolvedProjectConfiguration) -> None:
    keys = [str(k) for k in _resolved.experiments._items]  # pyright: ignore[reportPrivateUsage]
    assert len(keys) == 23
    assert keys[0] == "anchor_reproduction"
    assert keys[-1] == "operational_alert_burden"


def test_scientific_projection_includes_all_sections(_resolved: ResolvedProjectConfiguration) -> None:
    sp = _resolved.scientific_projection
    assert isinstance(sp, dict)
    expected = {
        "datasets",
        "populations",
        "experiments",
        "threshold_policies",
        "seed_cohorts",
        "training_profiles",
        "checkpoint_profiles",
        "model_architectures",
        "optimizers",
        "batching",
        "eligibility_policies",
        "normalization_strategies",
        "quantile_estimators",
        "metric_bundles",
        "statistical_profiles",
        "metric_definitions",
        "artifact_identity",
        "communication_estimation_contract",
        "operational_inputs",
        "report_profiles",
        "communication_estimation",
        "protocol_determinism",
        "normalization_fit_scopes",
        "normalization_leakage_rule",
        "threshold_policy_defaults",
        "nested_replicate_policy",
        "result_types",
        "evaluation_result_contract",
        "report_defaults",
        "capabilities",
        "suppression_behaviors",
        "population_readiness_rule",
        "eligibility_gates",
        "analysis_conventions",
    }
    assert set(sp.keys()) == expected


def test_execution_projection_includes_all_sections(_resolved: ResolvedProjectConfiguration) -> None:
    ep = _resolved.execution_projection
    assert isinstance(ep, dict)
    expected = {
        "scientific_fingerprint",
        "active_execution_profile",
        "determinism",
        "device_policy",
        "resource_pressure",
        "raw_source_policy",
    }
    assert set(ep.keys()) == expected


def test_no_pydantic_objects_in_resolved_state(_resolved: ResolvedProjectConfiguration) -> None:
    from pydantic import BaseModel

    def _check(obj: object, path: str = "root") -> None:
        if isinstance(obj, BaseModel):
            raise AssertionError(f"Pydantic at {path}: {type(obj).__name__}")
        if isinstance(obj, dict):
            for k, v in obj.items():
                _check(v, f"{path}.{k}")
        elif isinstance(obj, (list, tuple)):
            for i, v in enumerate(obj):
                _check(v, f"{path}[{i}]")
        elif hasattr(obj, "__dict__") and not isinstance(obj, (str, int, float, bool, type(None), type)):
            for attr_name in sorted(dir(obj)):
                if attr_name.startswith("_"):
                    continue
                try:
                    _check(getattr(obj, attr_name), f"{path}.{attr_name}")
                except Exception:
                    pass

    _check(_resolved)


def test_repeated_resolution_is_identical() -> None:
    os.environ.setdefault("DATP_EXECUTION_PROFILE", "scientific")
    r1 = resolve_project_configuration(
        config_dir=Path("configs"),
        bootstrap_settings=RuntimeBootstrapSettings(),  # pyright: ignore[reportCallIssue]
    )
    r2 = resolve_project_configuration(
        config_dir=Path("configs"),
        bootstrap_settings=RuntimeBootstrapSettings(),  # pyright: ignore[reportCallIssue]
    )
    assert r1.scientific_fingerprint == r2.scientific_fingerprint
    assert r1.execution_fingerprint == r2.execution_fingerprint
    assert r1.scientific_projection == r2.scientific_projection
    assert r1.execution_projection == r2.execution_projection


def test_cross_reference_error_preserves_context(_resolved: ResolvedProjectConfiguration) -> None:
    with pytest.raises(KeyError):
        _resolved.datasets.get(DatasetId("nonexistent_dataset"))
