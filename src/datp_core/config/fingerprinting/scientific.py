"""Scientific fingerprint projection assembly and the scientific fingerprint builder.

Absolute filesystem paths are deliberately excluded from the scientific projection;
datasets are projected via their schema id and fingerprint field lists rather than their
resolved (absolute-path-bearing) record.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from datp_core.config.resolution.experiments import ResolvedExperimentCatalogue
from datp_core.config.resolution.protocols import ResolvedProtocols
from datp_core.core.identifiers import DatasetId
from datp_core.data.contracts import ResolvedDataset


class HasItems[K, V](Protocol):
    def items(self) -> Iterable[tuple[K, V]]: ...


def _project[K, V](
    source: HasItems[K, V],
    projection_module: Callable[[object], object],
) -> dict[str, object]:
    return {str(k): projection_module(v) for k, v in sorted(source.items(), key=lambda x: str(x[0]))}


def _sorted_items[K, V](source: HasItems[K, V]) -> dict[str, V]:
    return {str(k): v for k, v in sorted(source.items(), key=lambda x: str(x[0]))}


class DatasetProjection(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
    schema_id: str
    source_layout_contract: object
    field_schema: object
    source_contract: object
    client_identity_contract: object
    setups: object
    materializations: object
    capabilities: Sequence[str]
    fingerprint_source_fields: Sequence[str]
    fingerprint_schema_fields: Sequence[str]
    fingerprint_materialization_fields: Sequence[str]
    fingerprint_client_assignment_fields: Sequence[str]


def _build_dataset_projection(
    dataset: ResolvedDataset,
    projection_module: Callable[[object], object],
) -> DatasetProjection:
    return DatasetProjection(
        schema_id=dataset.schema_id,
        source_layout_contract=projection_module(dataset.source_layout_contract),
        field_schema=projection_module(dataset.field_schema),
        source_contract=projection_module(dataset.source_contract),
        client_identity_contract=projection_module(dataset.client_identity_contract),
        setups=projection_module(dataset.setups),
        materializations=projection_module(dataset.materializations),
        capabilities=tuple(dataset.capabilities),
        fingerprint_source_fields=tuple(dataset.fingerprint_source_fields),
        fingerprint_schema_fields=tuple(dataset.fingerprint_schema_fields),
        fingerprint_materialization_fields=tuple(dataset.fingerprint_materialization_fields),
        fingerprint_client_assignment_fields=tuple(dataset.fingerprint_client_assignment_fields),
    )


class ScientificProjection(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
    datasets: object
    populations: object
    experiments: object
    threshold_policies: object
    seed_cohorts: object
    training_profiles: object
    checkpoint_profiles: object
    model_architectures: object
    optimizers: object
    batching: object
    eligibility_policies: object
    normalization_strategies: object
    metric_bundles: object
    statistical_profiles: object
    metric_definitions: object
    communication_estimation_contract: object
    operational_inputs: object
    report_profiles: object
    communication_estimation: object
    protocol_determinism: object
    normalization_fit_scopes: object
    normalization_leakage_rule: str
    nested_replicate_policy: object
    result_types: object
    evaluation_result_contract: object
    report_defaults: object
    capabilities: Sequence[str]
    suppression_behaviors: Sequence[str]
    population_readiness_rule: object
    eligibility_gates: object
    analysis_conventions: object


def build_scientific_projection(
    *,
    resolved_datasets: dict[DatasetId, ResolvedDataset],
    catalogue: ResolvedExperimentCatalogue,
    protocols: ResolvedProtocols,
    projection_module: Callable[[object], object],
) -> ScientificProjection:
    from datp_core.config.resolution.experiments import experiment_scientific_projection as _sci_proj

    return ScientificProjection(
        datasets=_sorted_items(
            {k: _build_dataset_projection(v, projection_module) for k, v in resolved_datasets.items()}
        ),
        populations=_project(catalogue.populations, projection_module),
        experiments=_sorted_items({k: _sci_proj(v) for k, v in catalogue.experiments.items()}),
        threshold_policies=_project(protocols.threshold_policies, projection_module),
        seed_cohorts=_project(protocols.seed_cohorts, projection_module),
        training_profiles=_project(protocols.training_profiles, projection_module),
        checkpoint_profiles=_project(protocols.checkpoint_profiles, projection_module),
        model_architectures=_project(protocols.model_architectures, projection_module),
        optimizers=_project(protocols.optimizers, projection_module),
        batching=_project(protocols.batching_profiles, projection_module),
        eligibility_policies=_project(protocols.eligibility_policies, projection_module),
        normalization_strategies=_project(protocols.normalization_strategies, projection_module),
        metric_bundles=_project(protocols.metric_bundles, projection_module),
        statistical_profiles=_project(protocols.statistical_profiles, projection_module),
        metric_definitions=projection_module(protocols.metric_definitions),
        communication_estimation_contract=projection_module(protocols.communication_estimation_contract),
        operational_inputs=projection_module(protocols.operational_inputs),
        report_profiles=_project(protocols.report_profiles, projection_module),
        communication_estimation=projection_module(protocols.communication_estimation),
        protocol_determinism=projection_module(protocols.protocol_determinism),
        normalization_fit_scopes=protocols.normalization_fit_scopes,
        normalization_leakage_rule=protocols.normalization_leakage_rule,
        nested_replicate_policy=projection_module(protocols.nested_replicate_policy),
        result_types=_project(protocols.result_types, projection_module),
        evaluation_result_contract=projection_module(protocols.evaluation_result_contract),
        report_defaults=projection_module(protocols.report_defaults),
        capabilities=tuple(sorted(catalogue.capabilities)),
        suppression_behaviors=tuple(sorted(catalogue.suppression_behaviors)),
        population_readiness_rule=catalogue.population_readiness_rule,
        eligibility_gates=_project(catalogue.eligibility_gates, projection_module),
        analysis_conventions=catalogue.analysis_conventions,
    )
