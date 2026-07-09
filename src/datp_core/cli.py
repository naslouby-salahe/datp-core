"""CLI entrypoint.

Phase 1 exposes safe, read-only commands only: doctor, validate-config,
show-paths, list-suites, validate-layout. There is no training or execution
command yet — Phase 1 never runs heavy work.
"""

from __future__ import annotations

import argparse
import dataclasses
import sys
from collections.abc import Callable, Sequence
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
from datp_core.data.manifests import DATASET_CONTRACTS, DatasetContractError, require_raw_dataset_present
from datp_core.utils.hardware import select_device_from_env
from datp_core.utils.layout import validate_repo_layout
from datp_core.utils.paths import PathResolutionError, RepoPaths, resolve_paths

_ConfigLoader = Callable[[Path], Any]

_TRAINING_LOADERS: dict[str, _ConfigLoader] = {"base_autoencoder.yaml": load_model_architecture_config}
_CONFIG_GROUP_LOADERS: dict[str, _ConfigLoader] = {
    "datasets": load_dataset_config,
    "thresholding": load_thresholding_config,
    "analysis": load_analysis_config,
    "suites": load_suite_config,
}


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
    for path in sorted(suites_dir.glob("*.yaml")):
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
    for group, loader in _CONFIG_GROUP_LOADERS.items():
        for path in sorted((paths.configs / group).glob("*.yaml")):
            exit_code |= _validate_one(path, loader, paths)
    for path in sorted((paths.configs / "training").glob("*.yaml")):
        loader = _TRAINING_LOADERS[path.name] if path.name in _TRAINING_LOADERS else load_training_config
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

    for name, contract in DATASET_CONTRACTS.items():
        try:
            root = require_raw_dataset_present(contract, paths)
            print(f"dataset {name}: present at {root}")
        except DatasetContractError as exc:
            print(f"dataset {name}: MISSING - {exc}")

    layout = validate_repo_layout(paths)
    print(f"layout: {'OK' if layout.passed else 'FAILURES'}")
    for failure in layout.failures:
        print(f"  - {failure}")

    return 0 if layout.passed else 1


_COMMANDS: dict[str, Callable[[argparse.Namespace, RepoPaths], int]] = {
    "doctor": _cmd_doctor,
    "validate-config": _cmd_validate_config,
    "show-paths": _cmd_show_paths,
    "list-suites": _cmd_list_suites,
    "validate-layout": _cmd_validate_layout,
}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="datp-core", description="DATP journal-extension CLI (Phase 1 skeleton).")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in _COMMANDS:
        subparsers.add_parser(name)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        paths = resolve_paths()
    except PathResolutionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return _COMMANDS[args.command](args, paths)


if __name__ == "__main__":
    raise SystemExit(main())
