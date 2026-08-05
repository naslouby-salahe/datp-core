"""Dagster lifecycle hooks limited to operational logging."""

from dagster import HookContext, failure_hook


@failure_hook
def log_pipeline_failure(context: HookContext) -> None:
    context.log.error(f"DATP-Core pipeline step failed: {context.op.name}")
