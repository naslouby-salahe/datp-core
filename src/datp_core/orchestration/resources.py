"""Dagster resources exposing protocol-owned paths without scientific logic."""

from dagster import ConfigurableResource

from datp_core.protocols.runtime import DATA_ROOT, OUTPUTS_ROOT


class PipelinePaths(ConfigurableResource):
    data_root: str
    outputs_root: str


PIPELINE_PATHS = PipelinePaths(data_root=str(DATA_ROOT), outputs_root=str(OUTPUTS_ROOT))
