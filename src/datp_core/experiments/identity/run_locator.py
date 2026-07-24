"""The single authoritative way to resolve an experiment's run id from resolved configuration.

``execution_run_id`` is a pure string-construction primitive: it embeds whatever source fingerprint
it is given, or none at all. Every actual run directory is created with the source-inventory
fingerprint of the datasets that experiment depends on (see
``ExecuteExperimentUseCase.execute``), so any caller that reconstructs a run id from only the
experiment id and execution fingerprint resolves a different, nonexistent namespace -- it silently
omits the source-fingerprint suffix the real run was stored under. Cross-experiment references
(FedAvg-primary checkpoint lookups, Ditto/FedProx coefficient selection, absorption reference reads,
and any future cross-run read) must resolve the referenced experiment's run id through this
function rather than calling ``execution_run_id`` directly.
"""

from __future__ import annotations

from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.core.identifiers import DatasetId, ExperimentId, RunId
from datp_core.data.sources.inventory import compute_experiment_source_fingerprint
from datp_core.experiments.identity.builder import execution_run_id


def resolve_experiment_run_id(config: ResolvedProjectConfiguration, experiment_id: ExperimentId) -> RunId:
    experiment = config.experiments.get(experiment_id)
    dataset_ids = tuple(
        DatasetId(config.populations.get(population_id).dataset_id.value)
        for population_id in experiment.population_ids
    )
    source_fingerprint = compute_experiment_source_fingerprint(datasets=config.datasets, dataset_ids=dataset_ids)
    return execution_run_id(experiment_id, config.execution_fingerprint.value, source_fingerprint)


__all__ = ["resolve_experiment_run_id"]
