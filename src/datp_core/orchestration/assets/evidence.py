"""Evidence publication asset delegated to the pipeline."""

from dagster import asset

from datp_core.pipeline.campaign import analyze_confirmatory_campaign


@asset
def confirmatory_evidence(completed_thresholds: tuple[str, ...]) -> str:
    if not completed_thresholds:
        raise ValueError("confirmatory evidence requires completed threshold evaluations")
    return str(analyze_confirmatory_campaign())
