from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from datp_core.configuration.models import DatasetFieldSchemaConfig, MulticlassLabelConfig
from datp_core.configuration.models import SweepVariableConfig
from datp_core.configuration.models import LocalQuantileThresholdPolicyConfig
from datp_core.configuration.project import resolve_project_configuration
from datp_core.configuration.loading import ConfigurationError
from datp_core.experiments.models import ConditionSweepRecord, ValueSweepRecord
from datp_core.pipeline.identifiers import DatasetId, ExperimentId


def test_multiclass_label_is_a_strict_typed_model_not_an_untyped_dict() -> None:
    cfg = resolve_project_configuration()
    dataset = cfg.datasets.get(DatasetId("ciciot2023"))
    assert dataset is not None

    with pytest.raises(ValidationError, match="extra_forbidden"):
        MulticlassLabelConfig.model_validate({"column": "Label", "unexpected": "x"})


def test_quantile_estimator_is_required_not_defaulted() -> None:
    with pytest.raises(ValidationError):
        LocalQuantileThresholdPolicyConfig.model_validate(
            {
                "policy": "local_threshold",
                "quantile": 0.95,
                "aggregation_scope": "per_client",
                "aggregation_formula": "identity",
                "sample_weighting": "none",
                "threshold_ownership": "local",
            }
        )


def test_header_required_is_required_not_defaulted() -> None:
    with pytest.raises(ValidationError):
        DatasetFieldSchemaConfig.model_validate(
            {
                "source_column_count": 10,
                "identity_scheme": {
                    "scheme": "path",
                    "components": ["dataset"],
                    "column_derivation": "from_path",
                    "encoding": "utf-8",
                },
                "label_fields": {"binary_label": {"benign": "x", "attack": ["y"]}},
            }
        )


def test_sweep_variable_requires_exactly_one_of_values_or_conditions() -> None:
    with pytest.raises(ValidationError):
        SweepVariableConfig.model_validate({"values": [1, 2], "conditions": [{"name": "a", "allocation": "equal"}]})
    with pytest.raises(ValidationError):
        SweepVariableConfig.model_validate({})


def test_list_of_string_sweep_values_are_retained_losslessly_not_dropped() -> None:
    cfg = resolve_project_configuration()
    experiment = cfg.experiments.get(ExperimentId("cluster_and_family_threshold_mechanism"))
    sweep_by_name = {sweep.name: sweep for sweep in experiment.sweeps}

    subset_sweep = sweep_by_name["fingerprint_feature_subset"]
    assert isinstance(subset_sweep, ValueSweepRecord)
    assert len(subset_sweep.values) == 4
    assert ("mean_error",) in subset_sweep.values
    assert ("mean_error", "std_error", "skew_error", "p95_error") in subset_sweep.values


def test_condition_shaped_sweep_is_resolved_not_dropped() -> None:
    cfg = resolve_project_configuration()
    experiment = cfg.experiments.get(ExperimentId("controlled_heterogeneity_response"))
    sweep_by_name = {sweep.name: sweep for sweep in experiment.sweeps}

    partition_sweep = sweep_by_name["partition_condition"]
    assert isinstance(partition_sweep, ConditionSweepRecord)
    assert len(partition_sweep.conditions) == 6
    names = {c.name for c in partition_sweep.conditions}
    assert "dirichlet_alpha_0_1" in names
    assert "iid_reference" in names


def test_duplicate_experiment_identifier_is_rejected(tmp_path: Path) -> None:
    for name in ("runtime.yaml", "protocols.yaml"):
        shutil.copy(f"configs/{name}", tmp_path / name)
    (tmp_path / "datasets").mkdir()
    for source in Path("configs/datasets").glob("*.yaml"):
        shutil.copy(source, tmp_path / "datasets" / source.name)

    with open("configs/experiments.yaml") as handle:
        experiments = yaml.safe_load(handle)
    duplicate = dict(experiments["experiments"][0])
    experiments["experiments"] = [*experiments["experiments"], duplicate]
    (tmp_path / "experiments.yaml").write_text(yaml.safe_dump(experiments, sort_keys=False))

    with pytest.raises(ConfigurationError, match="Duplicate experiment identifier"):
        resolve_project_configuration(config_dir=tmp_path)
