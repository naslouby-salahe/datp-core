"""CLI entrypoint for foundation checks and narrowly scoped Phase 2 anchor commands."""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from datp_core.config.loader import (
    load_analysis_config,
    load_dataset_config,
    load_model_architecture_config,
    load_suite_config,
    load_thresholding_config,
    load_training_config,
)
from datp_core.config.schemas import SuiteConfig
from datp_core.config.validation import ConfigError
from datp_core.data.manifests import (
    DATASET_REGISTRATIONS,
    DatasetContractError,
    dataset_contract,
    raw_dataset_root,
    require_raw_dataset_present,
)
from datp_core.data.nbaiot import discover_nbaiot
from datp_core.domain.regimes import Regime
from datp_core.domain.seeds import SeedPlan, SeedRole
from datp_core.experiments.anchor import (
    AnchorRuntimeConfig,
    AnchorSplitConfig,
    FixtureDataConfig,
    run_fixture_anchor,
    run_real_anchor,
)
from datp_core.experiments.plan import AnchorPlanError, confirmatory_anchor_plan
from datp_core.federation.fedavg import FedAvgConfig
from datp_core.models.scoring import read_score_artifact
from datp_core.thresholding.local import compute_b2_local_threshold
from datp_core.thresholding.shared import compute_b1_shared_threshold
from datp_core.utils.hardware import select_device, select_device_from_env
from datp_core.utils.layout import validate_repo_layout
from datp_core.utils.paths import PathResolutionError, RepoPaths, resolve_paths

_ConfigLoader = Callable[[Path], Any]


@dataclass(frozen=True)
class _NamedConfigLoader:
    name: str
    loader: _ConfigLoader


@dataclass(frozen=True)
class _Command:
    name: str
    handler: Callable[[argparse.Namespace, RepoPaths], int]


_TRAINING_LOADERS = (_NamedConfigLoader("base_autoencoder.yaml", load_model_architecture_config),)
_YAML_PATTERN = "*.yaml"
_ANCHOR_SUITE_NAME = "confirmatory_regime_a"


class AnchorRunKind(StrEnum):
    FIXTURE = "fixture"
    MINI = "mini"
    FULL = "full"


_CONFIG_GROUP_LOADERS = (
    _NamedConfigLoader("datasets", load_dataset_config),
    _NamedConfigLoader("thresholding", load_thresholding_config),
    _NamedConfigLoader("analysis", load_analysis_config),
    _NamedConfigLoader("suites", load_suite_config),
)


def _cmd_show_paths(_: argparse.Namespace, paths: RepoPaths) -> int:
    for field_info in dataclasses.fields(paths):
        print(f"{field_info.name}: {getattr(paths, field_info.name)}")
    return 0


def _cmd_list_suites(_: argparse.Namespace, paths: RepoPaths) -> int:
    suites_dir = paths.configs / "suites"
    if not suites_dir.is_dir():
        print("no configs/suites directory found", file=sys.stderr)
        return 1
    exit_code = 0
    for path in sorted(suites_dir.glob(_YAML_PATTERN)):
        try:
            config = load_suite_config(path)
        except ConfigError as exc:
            print(f"{path.name}: INVALID ({exc})")
            exit_code = 1
            continue
        print(f"{config.name}: status={config.status.value} runnable={config.is_runnable}")
    return exit_code


def _cmd_validate_config(_: argparse.Namespace, paths: RepoPaths) -> int:
    exit_code = 0
    for config_group in _CONFIG_GROUP_LOADERS:
        for path in sorted((paths.configs / config_group.name).glob(_YAML_PATTERN)):
            exit_code |= _validate_one(path, config_group.loader, paths)
    for path in sorted((paths.configs / "training").glob(_YAML_PATTERN)):
        loader = next(
            (entry.loader for entry in _TRAINING_LOADERS if entry.name == path.name),
            load_training_config,
        )
        exit_code |= _validate_one(path, loader, paths)
    return exit_code


def _validate_one(path: Path, loader: _ConfigLoader, paths: RepoPaths) -> int:
    try:
        loader(path)
    except ConfigError as exc:
        print(f"FAIL {path.relative_to(paths.repo_root)}: {exc}")
        return 1
    print(f"OK   {path.relative_to(paths.repo_root)}")
    return 0


def _cmd_validate_layout(_: argparse.Namespace, paths: RepoPaths) -> int:
    result = validate_repo_layout(paths)
    for check in result.checks:
        print(f"checked: {check}")
    if result.passed:
        print("layout: OK")
        return 0
    print("layout: FAILURES", file=sys.stderr)
    for failure in result.failures:
        print(f"  - {failure}", file=sys.stderr)
    return 1


def _cmd_doctor(_: argparse.Namespace, paths: RepoPaths) -> int:
    print(f"repo_root: {paths.repo_root}")

    device = select_device_from_env()
    print(
        f"device: requested={device.requested.value} resolved={device.resolved.value} "
        f"cuda_available={device.cuda_available}"
    )

    for registration in DATASET_REGISTRATIONS:
        try:
            root = require_raw_dataset_present(registration.contract, paths)
            print(f"dataset {registration.name}: present at {root}")
        except DatasetContractError as exc:
            print(f"dataset {registration.name}: MISSING - {exc}")

    layout = validate_repo_layout(paths)
    print(f"layout: {'OK' if layout.passed else 'FAILURES'}")
    for failure in layout.failures:
        print(f"  - {failure}")

    return 0 if layout.passed else 1


_COMMANDS = (
    _Command("doctor", _cmd_doctor),
    _Command("validate-config", _cmd_validate_config),
    _Command("show-paths", _cmd_show_paths),
    _Command("list-suites", _cmd_list_suites),
    _Command("validate-layout", _cmd_validate_layout),
)


def _anchor_runtime_config(paths: RepoPaths, suite_name: str) -> tuple[AnchorRuntimeConfig, SuiteConfig]:
    suite = load_suite_config(paths.configs / "suites" / f"{suite_name}.yaml")
    if any(
        value is None
        for value in (
            suite.dataset_config,
            suite.training_config,
            suite.model_config,
            suite.thresholding_config,
            suite.expected_client_count,
            suite.artifact_layout,
        )
    ):
        raise ConfigError("anchor suite config is incomplete")
    assert suite.dataset_config is not None
    assert suite.training_config is not None
    assert suite.model_config is not None
    assert suite.thresholding_config is not None
    assert suite.expected_client_count is not None
    assert suite.artifact_layout is not None
    training = load_training_config(paths.configs / "training" / suite.training_config)
    architecture = load_model_architecture_config(paths.configs / "training" / suite.model_config)
    dataset = load_dataset_config(paths.configs / "datasets" / suite.dataset_config)
    thresholding = load_thresholding_config(paths.configs / "thresholding" / suite.thresholding_config)
    if any(
        value is None
        for value in (
            training.rounds,
            training.local_epochs,
            training.learning_rate,
            training.momentum,
            training.weight_decay,
            training.full_participation,
            training.device,
            training.fixture_client_count,
            training.fixture_benign_rows,
            training.fixture_attack_rows,
            training.fixture_feature_count,
            training.fixture_benign_mean_step,
            training.fixture_attack_mean,
            training.fixture_feature_std,
            architecture.hidden_dim,
            dataset.train_fraction,
            dataset.calibration_fraction,
        )
    ):
        raise ConfigError("anchor runtime config is incomplete")
    assert training.rounds is not None
    assert training.local_epochs is not None
    assert training.learning_rate is not None
    assert training.momentum is not None
    assert training.weight_decay is not None
    assert training.full_participation is not None
    assert training.device is not None
    assert training.fixture_client_count is not None
    assert training.fixture_benign_rows is not None
    assert training.fixture_attack_rows is not None
    assert training.fixture_feature_count is not None
    assert training.fixture_benign_mean_step is not None
    assert training.fixture_attack_mean is not None
    assert training.fixture_feature_std is not None
    assert architecture.hidden_dim is not None
    assert dataset.train_fraction is not None
    assert dataset.calibration_fraction is not None
    select_device(training.device, strict=True)
    if len(thresholding.q_values) != 1:
        raise ConfigError("anchor threshold config requires exactly one quantile")
    if suite.regimes != (Regime.A,):
        raise ConfigError("anchor suite must declare exactly Regime A")
    return AnchorRuntimeConfig(
        dataset_id=dataset.dataset_id,
        regime=suite.regimes[0],
        seed_plan=SeedPlan(seeds=training.seed_plan, role=SeedRole.TRAIN),
        hidden_dim=architecture.hidden_dim,
        device=training.device,
        fedavg=FedAvgConfig(
            rounds=training.rounds,
            local_epochs=training.local_epochs,
            learning_rate=training.learning_rate,
            momentum=training.momentum,
            weight_decay=training.weight_decay,
            full_participation=training.full_participation,
        ),
        split=AnchorSplitConfig(
            train_fraction=dataset.train_fraction,
            calibration_fraction=dataset.calibration_fraction,
        ),
        threshold_q=thresholding.q_values[0],
        expected_client_count=suite.expected_client_count,
        fixture=FixtureDataConfig(
            fixture_client_count=training.fixture_client_count,
            benign_rows=training.fixture_benign_rows,
            attack_rows=training.fixture_attack_rows,
            feature_count=training.fixture_feature_count,
            benign_mean_step=training.fixture_benign_mean_step,
            attack_mean=training.fixture_attack_mean,
            feature_std=training.fixture_feature_std,
        ),
        artifacts=suite.artifact_layout,
    ), suite


def _anchor_run_roots(paths: RepoPaths, runtime: AnchorRuntimeConfig, run_kind: AnchorRunKind) -> tuple[Path, Path]:
    run_root_name = f"{runtime.artifacts.run_root_prefix}-{run_kind.value}"
    return paths.outputs / run_root_name, paths.checkpoints / "fedavg" / runtime.dataset_id.value / run_root_name


def _cmd_run_smoke(args: argparse.Namespace, paths: RepoPaths) -> int:
    if args.target != "anchor-fixture":
        raise ConfigError(f"unknown smoke target {args.target!r}")
    runtime, _ = _anchor_runtime_config(paths, _ANCHOR_SUITE_NAME)
    output_root, checkpoint_root = _anchor_run_roots(paths, runtime, AnchorRunKind.FIXTURE)
    results = run_fixture_anchor(
        seeds=(runtime.seed_plan.seeds[0],),
        output_root=output_root,
        checkpoint_root=checkpoint_root,
        config=runtime,
    )
    print(f"fixture anchor smoke complete: {len(results)} seed")
    return 0


def _cmd_run_mini(args: argparse.Namespace, paths: RepoPaths) -> int:
    if args.suite != "confirmatory-regime-a":
        raise ConfigError(f"unknown mini-run suite {args.suite!r}")
    runtime, suite_config = _anchor_runtime_config(paths, args.suite.replace("-", "_"))
    if suite_config.mini_seed_count is None:
        raise ConfigError("anchor suite config is missing mini_seed_count")
    if args.seeds != suite_config.mini_seed_count:
        raise ConfigError(f"the anchor mini-run requires {suite_config.mini_seed_count} seeds")
    raw_root = raw_dataset_root(dataset_contract(runtime.dataset_id.value), paths)
    if not raw_root.is_dir():
        print(f"real anchor mini-run blocked: N-BaIoT raw data is missing at {raw_root}", file=sys.stderr)
        return 2
    results = run_real_anchor(
        raw_root=raw_root,
        seeds=runtime.seed_plan.seeds[: suite_config.mini_seed_count],
        output_root=_anchor_run_roots(paths, runtime, AnchorRunKind.MINI)[0],
        checkpoint_root=_anchor_run_roots(paths, runtime, AnchorRunKind.MINI)[1],
        config=runtime,
    )
    print(f"real anchor mini-run complete: {len(results)} seeds")
    return 0


def _cmd_plan(args: argparse.Namespace, paths: RepoPaths) -> int:
    if args.suite != "confirmatory-regime-a":
        raise AnchorPlanError(f"unknown plan suite {args.suite!r}")
    runtime, _ = _anchor_runtime_config(paths, args.suite.replace("-", "_"))
    cells = confirmatory_anchor_plan(seeds=runtime.seed_plan.seeds, q=runtime.threshold_q)
    for cell in cells:
        print(f"seed={cell.seed} policy={cell.policy.value} dataset={cell.dataset_id.value} regime={cell.regime.value}")
    return 0


def _cmd_run_thresholds(args: argparse.Namespace, paths: RepoPaths) -> int:
    scores = read_score_artifact(Path(args.score_artifact))
    runtime, _ = _anchor_runtime_config(paths, _ANCHOR_SUITE_NAME)
    thresholds = (
        compute_b1_shared_threshold(scores, q=runtime.threshold_q),
        compute_b2_local_threshold(scores, q=runtime.threshold_q),
    )
    output_path = Path(args.score_artifact).with_name(runtime.artifacts.threshold_filename)
    if output_path.exists():
        raise ConfigError(f"refusing to overwrite threshold artifact {output_path}")
    output_path.write_text(
        json.dumps(
            {
                threshold.policy.value: {
                    "score_id": threshold.score_id,
                    "q": threshold.q,
                    "shared": threshold.shared_threshold,
                }
                for threshold in thresholds
            },
            indent=2,
            sort_keys=True,
        )
    )
    print(f"threshold-only run complete from stored scores: {output_path}")
    return 0


def _cmd_run_full(args: argparse.Namespace, paths: RepoPaths) -> int:
    if not args.confirm_full_run:
        raise ConfigError("full anchor execution requires --confirm-full-run")
    runtime, _ = _anchor_runtime_config(paths, args.suite.replace("-", "_"))
    raw_root = raw_dataset_root(dataset_contract(runtime.dataset_id.value), paths)
    if not raw_root.is_dir():
        print(f"full anchor run blocked: N-BaIoT raw data is missing at {raw_root}", file=sys.stderr)
        return 2
    results = run_real_anchor(
        raw_root=raw_root,
        seeds=runtime.seed_plan.seeds,
        output_root=_anchor_run_roots(paths, runtime, AnchorRunKind.FULL)[0],
        checkpoint_root=_anchor_run_roots(paths, runtime, AnchorRunKind.FULL)[1],
        config=runtime,
    )
    print(f"operator-authorized full anchor run complete: {len(results)} seeds")
    return 0


def _cmd_validate_anchor_readiness(_: argparse.Namespace, paths: RepoPaths) -> int:
    try:
        runtime, suite_config = _anchor_runtime_config(paths, _ANCHOR_SUITE_NAME)
        if suite_config.expected_client_count is None:
            raise ConfigError("anchor suite config is missing expected_client_count")
        raw_root = require_raw_dataset_present(dataset_contract(runtime.dataset_id.value), paths)
        inventory = discover_nbaiot(raw_root)
        device_count = len({record.device_id for record in inventory.files if record.device_id is not None})
        if device_count != suite_config.expected_client_count:
            raise DatasetContractError(
                f"Regime A requires {suite_config.expected_client_count} physical devices; "
                f"inventory found {device_count}"
            )
    except (ConfigError, DatasetContractError) as exc:
        print(f"anchor readiness: BLOCKED - {exc}")
        return 2
    print(f"anchor readiness: READY for an operator-authorized full {len(runtime.seed_plan.seeds)}-seed run")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="datp-core", description="DATP journal-extension CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in _COMMANDS:
        subparsers.add_parser(command.name)
    run_smoke = subparsers.add_parser("run-smoke")
    run_smoke.add_argument("target", choices=("anchor-fixture",))
    run_mini = subparsers.add_parser("run-mini")
    run_mini.add_argument("suite", choices=("confirmatory-regime-a",))
    run_mini.add_argument("--seeds", type=int, required=True)
    plan = subparsers.add_parser("plan")
    plan.add_argument("suite", choices=("confirmatory-regime-a",))
    run_thresholds = subparsers.add_parser("run-thresholds")
    run_thresholds.add_argument("score_artifact")
    run_full = subparsers.add_parser("run-full")
    run_full.add_argument("suite", choices=("confirmatory-regime-a",))
    run_full.add_argument("--confirm-full-run", action="store_true")
    subparsers.add_parser("validate-anchor-readiness")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        paths = resolve_paths()
    except PathResolutionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    for command in _COMMANDS:
        if command.name == args.command:
            return command.handler(args, paths)
    try:
        if args.command == "run-smoke":
            return _cmd_run_smoke(args, paths)
        if args.command == "run-mini":
            return _cmd_run_mini(args, paths)
        if args.command == "plan":
            return _cmd_plan(args, paths)
        if args.command == "run-thresholds":
            return _cmd_run_thresholds(args, paths)
        if args.command == "run-full":
            return _cmd_run_full(args, paths)
        if args.command == "validate-anchor-readiness":
            return _cmd_validate_anchor_readiness(args, paths)
    except (AnchorPlanError, ConfigError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
