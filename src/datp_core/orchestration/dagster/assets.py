"""Dagster assets representing real DATP artifact materializations."""

from dagster import AssetExecutionContext, Output, asset

from datp_core.orchestration.dagster.resources import DatpConfigurationResource


@asset(
    key_prefix=["datp", "project"],
    name="resolved_project_configuration",
    required_resource_keys={"datp_config"},
)
def resolved_project_configuration_asset(context: AssetExecutionContext) -> Output[dict[str, str]]:
    """Root asset materializing resolved project configuration metadata."""
    resource = context.resources.datp_config
    if not isinstance(resource, DatpConfigurationResource):
        raise TypeError("Dagster datp_config resource has the wrong type")
    cfg = resource.get_resolved_config()
    metadata = {
        "scientific_fingerprint": cfg.scientific_fingerprint.value,
        "execution_fingerprint": cfg.execution_fingerprint.value,
        "experiment_count": str(len(cfg.experiments)),
        "dataset_count": str(len(cfg.datasets)),
    }
    return Output(metadata, metadata=metadata)
