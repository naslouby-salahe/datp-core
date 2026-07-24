"""`ProjectConfigurationValidator._validate_experiments` cross-checks every reference an
experiment makes into the rest of the catalogue (training/checkpoint profiles, seed cohorts,
eligibility policies, prerequisites, report profiles, threshold policies, and the
evidence-role/result-type pairing). Prior coverage only exercised one reference type
(`DatasetId`, via a raw `KeyError` from a registry `.get`); this file drives each of the
validator's own descriptive-error cross-reference checks directly, one mutation at a time.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

from datp_core.config.loading import ConfigurationError
from datp_core.config.project import resolve_project_configuration

_CONFIRMATORY_EXPERIMENT = "confirmatory_threshold_scope_effect"


def _mutate_confirmatory_experiment(tmp_path: Path, mutate: Callable[[dict[str, Any]], None]) -> None:
    for name in ("runtime.yaml", "protocols.yaml"):
        shutil.copy(f"configs/{name}", tmp_path / name)
    (tmp_path / "datasets").mkdir()
    for source in Path("configs/datasets").glob("*.yaml"):
        shutil.copy(source, tmp_path / "datasets" / source.name)

    with open("configs/experiments.yaml") as handle:
        experiments = yaml.safe_load(handle)
    target = next(e for e in experiments["experiments"] if e["name"] == _CONFIRMATORY_EXPERIMENT)
    mutate(target)
    (tmp_path / "experiments.yaml").write_text(yaml.safe_dump(experiments, sort_keys=False))


def test_dangling_training_profile_is_rejected(tmp_path: Path) -> None:
    _mutate_confirmatory_experiment(tmp_path, lambda exp: exp.__setitem__("training_profile", "nonexistent"))
    with pytest.raises(ConfigurationError, match="missing training profile"):
        resolve_project_configuration(config_dir=tmp_path)


def test_dangling_seed_cohort_is_rejected(tmp_path: Path) -> None:
    _mutate_confirmatory_experiment(tmp_path, lambda exp: exp.__setitem__("seed_cohort", "nonexistent"))
    with pytest.raises(ConfigurationError, match="missing seed cohort"):
        resolve_project_configuration(config_dir=tmp_path)


def test_dangling_eligibility_policy_is_rejected(tmp_path: Path) -> None:
    _mutate_confirmatory_experiment(tmp_path, lambda exp: exp.__setitem__("eligibility_policy", "nonexistent"))
    with pytest.raises(ConfigurationError, match="missing eligibility policy"):
        resolve_project_configuration(config_dir=tmp_path)


def test_dangling_prerequisite_experiment_is_rejected(tmp_path: Path) -> None:
    _mutate_confirmatory_experiment(
        tmp_path,
        lambda exp: exp.__setitem__("prerequisites", [{"experiment": "nonexistent", "required_outcome": "x"}]),
    )
    with pytest.raises(ConfigurationError, match="unregistered prerequisite"):
        resolve_project_configuration(config_dir=tmp_path)


def test_dangling_report_profile_is_rejected(tmp_path: Path) -> None:
    _mutate_confirmatory_experiment(tmp_path, lambda exp: exp.__setitem__("reports", ["nonexistent"]))
    with pytest.raises(ConfigurationError, match="unregistered report profile"):
        resolve_project_configuration(config_dir=tmp_path)


def test_dangling_evaluation_threshold_policy_is_rejected(tmp_path: Path) -> None:
    def mutate(exp: dict[str, Any]) -> None:
        exp["evaluations"][0]["threshold_policy"] = "nonexistent"

    _mutate_confirmatory_experiment(tmp_path, mutate)
    with pytest.raises(ConfigurationError, match="unregistered threshold policy"):
        resolve_project_configuration(config_dir=tmp_path)


def test_evidence_role_not_permitted_for_the_analysis_result_type_is_rejected(tmp_path: Path) -> None:
    """The `permitted_evidence_roles` safety rail: an experiment cannot emit a result type its own
    evidence role is not permitted to produce (e.g. a non-confirmatory experiment claiming
    `confirmatory_analysis_result`)."""
    _mutate_confirmatory_experiment(tmp_path, lambda exp: exp.__setitem__("evidence_role", "exploratory"))
    with pytest.raises(ConfigurationError, match="does not permit"):
        resolve_project_configuration(config_dir=tmp_path)
