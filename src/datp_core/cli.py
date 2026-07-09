"""CLI entrypoint: argument parsing, typed command dispatch, and user-facing output."""

from __future__ import annotations

import argparse
import dataclasses
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
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
from datp_core.config.validation import ConfigError
from datp_core.data.manifests import (
    DATASET_REGISTRATIONS,
    DatasetContractError,
    dataset_contract,
    require_raw_dataset_present,
)
from datp_core.data.nbaiot import discover_nbaiot
from datp_core.experiments.anchor import run_fixture_anchor, run_real_anchor
from datp_core.experiments.artifacts import write_manifest
from datp_core.experiments.plan import AnchorPlanError, confirmatory_anchor_plan
from datp_core.experiments.runtime import AnchorRunKind, anchor_run_roots, resolve_anchor_runtime_config
from datp_core.models.scoring import read_score_artifact
from datp_core.thresholding.local import compute_b2_local_threshold
from datp_core.thresholding.shared import AnchorThresholdArtifact, compute_b1_shared_threshold
from datp_core.utils.hardware import select_device_from_env
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
_ANCHOR_SUITE_CLI_ID = "confirmatory-regime-a"


_CONFIG_GROUP_LOADERS = (
    _NamedConfigLoader("datasets", load_dataset_config),
    _NamedConfigLoader("thresholding", load_thresholding_config),
    _NamedConfigLoader("analysis", load_analysis_config),
    _NamedConfigLoader("suites", load_suite_config),
)


def _anchor_suite_config_name(cli_suite_id: str) -> str:
    return cli_suite_id.replace("-", "_")


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


def _cmd_run_smoke(args: argparse.Namespace, paths: RepoPaths) -> int:
    if args.target != "anchor-fixture":
        raise ConfigError(f"unknown smoke target {args.target!r}")
    runtime, _ = resolve_anchor_runtime_config(paths, _anchor_suite_config_name(_ANCHOR_SUITE_CLI_ID))
    output_root, checkpoint_root = anchor_run_roots(paths, runtime, AnchorRunKind.FIXTURE)
    results = run_fixture_anchor(
        seeds=(runtime.seed_plan.seeds[0],),
        output_root=output_root,
        checkpoint_root=checkpoint_root,
        config=runtime,
    )
    print(f"fixture anchor smoke complete: {len(results)} seed")
    return 0


def _cmd_run_mini(args: argparse.Namespace, paths: RepoPaths) -> int:
    runtime, suite_config = resolve_anchor_runtime_config(paths, _anchor_suite_config_name(args.suite))
    if suite_config.mini_seed_count is None:
        raise ConfigError("anchor suite config is missing mini_seed_count")
    if args.seeds != suite_config.mini_seed_count:
        raise ConfigError(f"the anchor mini-run requires {suite_config.mini_seed_count} seeds")
    raw_root = paths.data_raw / dataset_contract(runtime.dataset_id.value).raw_subdirectory
    if not raw_root.is_dir():
        print(f"real anchor mini-run blocked: N-BaIoT raw data is missing at {raw_root}", file=sys.stderr)
        return 2
    output_root, checkpoint_root = anchor_run_roots(paths, runtime, AnchorRunKind.MINI)
    results = run_real_anchor(
        raw_root=raw_root,
        seeds=runtime.seed_plan.seeds[: suite_config.mini_seed_count],
        output_root=output_root,
        checkpoint_root=checkpoint_root,
        config=runtime,
    )
    print(f"real anchor mini-run complete: {len(results)} seeds")
    return 0


def _cmd_plan(args: argparse.Namespace, paths: RepoPaths) -> int:
    runtime, _ = resolve_anchor_runtime_config(paths, _anchor_suite_config_name(args.suite))
    cells = confirmatory_anchor_plan(seeds=runtime.seed_plan.seeds, q=runtime.threshold_q)
    for cell in cells:
        print(f"seed={cell.seed} policy={cell.policy.value} dataset={cell.dataset_id.value} regime={cell.regime.value}")
    return 0


def _cmd_run_thresholds(args: argparse.Namespace, paths: RepoPaths) -> int:
    scores = read_score_artifact(Path(args.score_artifact))
    runtime, _ = resolve_anchor_runtime_config(paths, _anchor_suite_config_name(_ANCHOR_SUITE_CLI_ID))
    thresholds = (
        compute_b1_shared_threshold(scores, q=runtime.threshold_q),
        compute_b2_local_threshold(scores, q=runtime.threshold_q),
    )
    output_path = Path(args.score_artifact).with_name(runtime.artifacts.threshold_filename)
    if output_path.exists():
        raise ConfigError(f"refusing to overwrite threshold artifact {output_path}")
    write_manifest(AnchorThresholdArtifact(score_id=scores.manifest.score_id, thresholds=thresholds), output_path)
    print(f"threshold-only run complete from stored scores: {output_path}")
    return 0


def _cmd_run_full(args: argparse.Namespace, paths: RepoPaths) -> int:
    if not args.confirm_full_run:
        raise ConfigError("full anchor execution requires --confirm-full-run")
    runtime, _ = resolve_anchor_runtime_config(paths, _anchor_suite_config_name(args.suite))
    raw_root = paths.data_raw / dataset_contract(runtime.dataset_id.value).raw_subdirectory
    if not raw_root.is_dir():
        print(f"full anchor run blocked: N-BaIoT raw data is missing at {raw_root}", file=sys.stderr)
        return 2
    output_root, checkpoint_root = anchor_run_roots(paths, runtime, AnchorRunKind.FULL)
    results = run_real_anchor(
        raw_root=raw_root,
        seeds=runtime.seed_plan.seeds,
        output_root=output_root,
        checkpoint_root=checkpoint_root,
        config=runtime,
    )
    print(f"operator-authorized full anchor run complete: {len(results)} seeds")
    return 0


def _cmd_validate_anchor_readiness(_: argparse.Namespace, paths: RepoPaths) -> int:
    try:
        runtime, suite_config = resolve_anchor_runtime_config(paths, _anchor_suite_config_name(_ANCHOR_SUITE_CLI_ID))
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


_PLAIN_COMMANDS = (
    _Command("doctor", _cmd_doctor),
    _Command("validate-config", _cmd_validate_config),
    _Command("show-paths", _cmd_show_paths),
    _Command("list-suites", _cmd_list_suites),
    _Command("validate-layout", _cmd_validate_layout),
    _Command("validate-anchor-readiness", _cmd_validate_anchor_readiness),
)

_ARGUMENT_COMMANDS = (
    _Command("run-smoke", _cmd_run_smoke),
    _Command("run-mini", _cmd_run_mini),
    _Command("plan", _cmd_plan),
    _Command("run-thresholds", _cmd_run_thresholds),
    _Command("run-full", _cmd_run_full),
)

_COMMANDS = _PLAIN_COMMANDS + _ARGUMENT_COMMANDS


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="datp-core", description="DATP journal-extension CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in _PLAIN_COMMANDS:
        subparsers.add_parser(command.name)
    run_smoke = subparsers.add_parser("run-smoke")
    run_smoke.add_argument("target", choices=("anchor-fixture",))
    run_mini = subparsers.add_parser("run-mini")
    run_mini.add_argument("suite", choices=(_ANCHOR_SUITE_CLI_ID,))
    run_mini.add_argument("--seeds", type=int, required=True)
    plan = subparsers.add_parser("plan")
    plan.add_argument("suite", choices=(_ANCHOR_SUITE_CLI_ID,))
    run_thresholds = subparsers.add_parser("run-thresholds")
    run_thresholds.add_argument("score_artifact")
    run_full = subparsers.add_parser("run-full")
    run_full.add_argument("suite", choices=(_ANCHOR_SUITE_CLI_ID,))
    run_full.add_argument("--confirm-full-run", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        paths = resolve_paths()
    except PathResolutionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    handler = next(command.handler for command in _COMMANDS if command.name == args.command)
    try:
        return handler(args, paths)
    except (AnchorPlanError, ConfigError, DatasetContractError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
