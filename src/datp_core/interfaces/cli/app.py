"""Thin argparse CLI: it delegates all construction and scientific work."""

from __future__ import annotations

import argparse
from pathlib import Path

from ...composition.bootstrap import bootstrap
from ...kernel.ids import ExperimentId
from ...orchestration.planning import build_execution_plan, plan_experiment


def main() -> None:
    parser = argparse.ArgumentParser(prog="datp-core")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("catalogue")
    plan = commands.add_parser("plan")
    plan.add_argument("experiment")
    arguments = parser.parse_args()
    application = bootstrap(arguments.root)
    if arguments.command == "catalogue":
        study = application.configuration.study
        print(
            f"datasets={len(study.datasets)} populations={len(study.populations)} experiments={len(study.experiments)}"
        )
        return
    execution_plan = build_execution_plan(
        plan_experiment(application.configuration, ExperimentId(arguments.experiment))
    )
    print(f"jobs={len(execution_plan.jobs)} fingerprint={execution_plan.plan_fingerprint.hexadecimal}")
