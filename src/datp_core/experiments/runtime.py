"""Anchor runtime configuration resolution.

Turns a suite name into one fully-resolved, non-optional :class:`AnchorRuntimeConfig`
by loading and cross-checking every config group it depends on. CLI code must call
:func:`resolve_anchor_runtime_config` rather than assembling the runtime config itself.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import TypeVar

from datp_core.config.loader import (
    load_dataset_config,
    load_model_architecture_config,
    load_suite_config,
    load_thresholding_config,
    load_training_config,
)
from datp_core.config.schemas import SuiteConfig
from datp_core.config.validation import ConfigError
from datp_core.domain.regimes import Regime
from datp_core.domain.seeds import SeedPlan, SeedRole
from datp_core.experiments.anchor import AnchorRuntimeConfig, AnchorSplitConfig, FixtureDataConfig
from datp_core.federation.fedavg import FedAvgConfig
from datp_core.utils.hardware import select_device
from datp_core.utils.paths import RepoPaths

_T = TypeVar("_T")


class AnchorRunKind(StrEnum):
    FIXTURE = "fixture"
    MINI = "mini"
    FULL = "full"


def _require(value: _T | None, message: str) -> _T:
    if value is None:
        raise ConfigError(message)
    return value


def resolve_anchor_runtime_config(paths: RepoPaths, suite_name: str) -> tuple[AnchorRuntimeConfig, SuiteConfig]:
    suite = load_suite_config(paths.configs / "suites" / f"{suite_name}.yaml")
    dataset_config_name = _require(suite.dataset_config, "anchor suite config is missing dataset_config")
    training_config_name = _require(suite.training_config, "anchor suite config is missing training_config")
    model_config_name = _require(suite.model_config, "anchor suite config is missing model_config")
    thresholding_config_name = _require(suite.thresholding_config, "anchor suite config is missing thresholding_config")
    expected_client_count = _require(
        suite.expected_client_count, "anchor suite config is missing expected_client_count"
    )
    artifact_layout = _require(suite.artifact_layout, "anchor suite config is missing artifact_layout")

    training = load_training_config(paths.configs / "training" / training_config_name)
    architecture = load_model_architecture_config(paths.configs / "training" / model_config_name)
    dataset = load_dataset_config(paths.configs / "datasets" / dataset_config_name)
    thresholding = load_thresholding_config(paths.configs / "thresholding" / thresholding_config_name)

    rounds = _require(training.rounds, "anchor training config is missing rounds")
    local_epochs = _require(training.local_epochs, "anchor training config is missing local_epochs")
    learning_rate = _require(training.learning_rate, "anchor training config is missing learning_rate")
    momentum = _require(training.momentum, "anchor training config is missing momentum")
    weight_decay = _require(training.weight_decay, "anchor training config is missing weight_decay")
    full_participation = _require(training.full_participation, "anchor training config is missing full_participation")
    device = _require(training.device, "anchor training config is missing device")
    fixture_client_count = _require(
        training.fixture_client_count, "anchor training config is missing fixture_client_count"
    )
    fixture_benign_rows = _require(
        training.fixture_benign_rows, "anchor training config is missing fixture_benign_rows"
    )
    fixture_attack_rows = _require(
        training.fixture_attack_rows, "anchor training config is missing fixture_attack_rows"
    )
    fixture_feature_count = _require(
        training.fixture_feature_count, "anchor training config is missing fixture_feature_count"
    )
    fixture_benign_mean_step = _require(
        training.fixture_benign_mean_step, "anchor training config is missing fixture_benign_mean_step"
    )
    fixture_attack_mean = _require(
        training.fixture_attack_mean, "anchor training config is missing fixture_attack_mean"
    )
    fixture_feature_std = _require(
        training.fixture_feature_std, "anchor training config is missing fixture_feature_std"
    )
    hidden_dim = _require(architecture.hidden_dim, "anchor model architecture config is missing hidden_dim")
    train_fraction = _require(dataset.train_fraction, "anchor dataset config is missing train_fraction")
    calibration_fraction = _require(
        dataset.calibration_fraction, "anchor dataset config is missing calibration_fraction"
    )

    select_device(device, strict=True)
    if len(thresholding.q_values) != 1:
        raise ConfigError("anchor threshold config requires exactly one quantile")
    if suite.regimes != (Regime.A,):
        raise ConfigError("anchor suite must declare exactly Regime A")

    runtime = AnchorRuntimeConfig(
        dataset_id=dataset.dataset_id,
        regime=suite.regimes[0],
        seed_plan=SeedPlan(seeds=training.seed_plan, role=SeedRole.TRAIN),
        hidden_dim=hidden_dim,
        device=device,
        fedavg=FedAvgConfig(
            rounds=rounds,
            local_epochs=local_epochs,
            learning_rate=learning_rate,
            momentum=momentum,
            weight_decay=weight_decay,
            full_participation=full_participation,
        ),
        split=AnchorSplitConfig(
            train_fraction=train_fraction,
            calibration_fraction=calibration_fraction,
        ),
        threshold_q=thresholding.q_values[0],
        expected_client_count=expected_client_count,
        fixture=FixtureDataConfig(
            fixture_client_count=fixture_client_count,
            benign_rows=fixture_benign_rows,
            attack_rows=fixture_attack_rows,
            feature_count=fixture_feature_count,
            benign_mean_step=fixture_benign_mean_step,
            attack_mean=fixture_attack_mean,
            feature_std=fixture_feature_std,
        ),
        artifacts=artifact_layout,
    )
    return runtime, suite


def anchor_run_roots(paths: RepoPaths, runtime: AnchorRuntimeConfig, run_kind: AnchorRunKind) -> tuple[Path, Path]:
    run_root_name = f"{runtime.artifacts.run_root_prefix}-{run_kind.value}"
    return paths.outputs / run_root_name, paths.checkpoints / "fedavg" / runtime.dataset_id.value / run_root_name
