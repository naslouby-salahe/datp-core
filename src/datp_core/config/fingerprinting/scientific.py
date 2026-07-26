"""Scientific fingerprint projection assembly and the scientific fingerprint builder.

Absolute filesystem paths are deliberately excluded from the scientific projection;
datasets are projected via their schema id and fingerprint field lists rather than their
resolved (absolute-path-bearing) record.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Protocol

from attrs import define

from datp_core.config.resolution.experiments import ResolvedExperimentCatalogue
from datp_core.config.resolution.protocols import ResolvedProtocols
from datp_core.core.hashing import CanonicalProjection
from datp_core.core.identifiers import DatasetId
from datp_core.data.contracts import ResolvedDataset


class HasItems[K, V](Protocol):
    def items(self) -> Iterable[tuple[K, V]]: ...


def _project[K, V](
    source: HasItems[K, V],
    projection_module: Callable[[object], CanonicalProjection],
) -> dict[str, CanonicalProjection]:
    return {str(k): projection_module(v) for k, v in sorted(source.items(), key=lambda x: str(x[0]))}


def _sorted_items[K, V](source: HasItems[K, V]) -> dict[str, V]:
    return {str(k): v for k, v in sorted(source.items(), key=lambda x: str(x[0]))}


@define(frozen=True, slots=True, kw_only=True)
class DatasetProjection:
    schema_id: str
    source_layout_contract: CanonicalProjection
    field_schema: CanonicalProjection
    source_contract: CanonicalProjection
    client_identity_contract: CanonicalProjection
    setups: CanonicalProjection
    materializations: CanonicalProjection
    capabilities: Sequence[str]
    fingerprint_source_fields: Sequence[str]
    fingerprint_schema_fields: Sequence[str]
    fingerprint_materialization_fields: Sequence[str]
    fingerprint_client_assignment_fields: Sequence[str]


def _build_dataset_projection(
    dataset: ResolvedDataset,
    projection_module: Callable[[object], CanonicalProjection],
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


@define(frozen=True, slots=True, kw_only=True)
class ScientificProjection:
    datasets: Mapping[str, DatasetProjection]
    populations: Mapping[str, CanonicalProjection]
    experiments: Mapping[str, CanonicalProjection]
    threshold_policies: Mapping[str, CanonicalProjection]
    seed_cohorts: Mapping[str, CanonicalProjection]
    training_profiles: Mapping[str, CanonicalProjection]
    checkpoint_profiles: Mapping[str, CanonicalProjection]
    model_architectures: Mapping[str, CanonicalProjection]
    optimizers: Mapping[str, CanonicalProjection]
    batching: Mapping[str, CanonicalProjection]
    eligibility_policies: Mapping[str, CanonicalProjection]
    normalization_strategies: Mapping[str, CanonicalProjection]
    quantile_estimators: Mapping[str, CanonicalProjection]
    metric_bundles: Mapping[str, CanonicalProjection]
    statistical_profiles: Mapping[str, CanonicalProjection]
    metric_definitions: CanonicalProjection
    communication_estimation_contract: CanonicalProjection
    operational_inputs: CanonicalProjection
    report_profiles: Mapping[str, CanonicalProjection]
    communication_estimation: CanonicalProjection
    protocol_determinism: CanonicalProjection
    normalization_fit_scopes: Mapping[str, str]
    normalization_leakage_rule: str
    threshold_policy_defaults: CanonicalProjection
    nested_replicate_policy: CanonicalProjection
    result_types: Mapping[str, CanonicalProjection]
    evaluation_result_contract: CanonicalProjection
    report_defaults: CanonicalProjection
    capabilities: Sequence[str]
    suppression_behaviors: Sequence[str]
    population_readiness_rule: Mapping[str, str | bool]
    eligibility_gates: Mapping[str, CanonicalProjection]
    analysis_conventions: Mapping[str, str]


def build_scientific_projection(
    *,
    resolved_datasets: dict[DatasetId, ResolvedDataset],
    catalogue: ResolvedExperimentCatalogue,
    protocols: ResolvedProtocols,
    projection_module: Callable[[object], CanonicalProjection],
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
        quantile_estimators=_project(protocols.quantile_estimators, projection_module),
        metric_bundles=_project(protocols.metric_bundles, projection_module),
        statistical_profiles=_project(protocols.statistical_profiles, projection_module),
        metric_definitions=projection_module(protocols.metric_definitions),
        communication_estimation_contract=projection_module(protocols.communication_estimation_contract),
        operational_inputs=projection_module(protocols.operational_inputs),
        report_profiles=_project(protocols.report_profiles, projection_module),
        communication_estimation=projection_module(protocols.communication_estimation),
        protocol_determinism=projection_module(protocols.protocol_determinism),
        normalization_fit_scopes=dict(sorted(protocols.normalization_fit_scopes.items())),
        normalization_leakage_rule=protocols.normalization_leakage_rule,
        threshold_policy_defaults=projection_module(protocols.threshold_policy_defaults),
        nested_replicate_policy=projection_module(protocols.nested_replicate_policy),
        result_types=_project(protocols.result_types, projection_module),
        evaluation_result_contract=projection_module(protocols.evaluation_result_contract),
        report_defaults=projection_module(protocols.report_defaults),
        capabilities=tuple(sorted(catalogue.capabilities)),
        suppression_behaviors=tuple(sorted(catalogue.suppression_behaviors)),
        population_readiness_rule=dict(sorted(catalogue.population_readiness_rule.items())),
        eligibility_gates=_project(catalogue.eligibility_gates, projection_module),
        analysis_conventions=dict(sorted(catalogue.analysis_conventions.items())),
    )
