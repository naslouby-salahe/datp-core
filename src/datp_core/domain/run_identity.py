"""Stable execution-run identity shared by artifact producers and consumers."""

from datp_core.domain.identifiers import ExperimentId, RunId


def execution_run_id(experiment_id: ExperimentId, execution_fingerprint: str) -> RunId:
    return RunId(f"run_{experiment_id.value}_{execution_fingerprint[:12]}")
