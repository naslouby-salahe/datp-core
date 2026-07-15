from __future__ import annotations

import argparse
from collections.abc import Sequence
from typing import assert_never

from rich.console import Console

from datp_core.composition.root import (
    PHASE_ONE_COMMAND_USE_CASE,
    BoundaryExitCode,
    CompositionCommand,
    CompositionCommandFailure,
    CompositionCommandSuccess,
    CompositionCommandUseCase,
    RunCompositionCommandRequest,
)


def main(arguments: Sequence[str] | None = None) -> int:
    return invoke_command(
        arguments=arguments,
        use_case=PHASE_ONE_COMMAND_USE_CASE,
        console=Console(),
    )


def invoke_command(
    *,
    arguments: Sequence[str] | None,
    use_case: CompositionCommandUseCase,
    console: Console,
) -> int:
    request = _parse_run_command(arguments)
    result = use_case.execute_command(request)
    match result:
        case CompositionCommandSuccess(message=message):
            console.print(message)
            return BoundaryExitCode.SUCCESS
        case CompositionCommandFailure(error=error) as failure:
            console.print(f"[red]{error}[/red]")
            return failure.exit_code
        case _:
            assert_never(result)


def _parse_run_command(arguments: Sequence[str] | None) -> RunCompositionCommandRequest:
    parser = argparse.ArgumentParser(prog="datp-core")
    parser.add_argument("command", choices=(CompositionCommand.RUN.value,))
    parsed = parser.parse_args(arguments)
    return RunCompositionCommandRequest(command=CompositionCommand(parsed.command))
