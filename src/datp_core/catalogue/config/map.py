"""Explicit authored-to-domain mapping; Pydantic objects never escape this module."""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from ...kernel.errors import ConfigurationError
from ...kernel.fingerprints import fingerprint
from ...kernel.ids import DatasetId, ExperimentId, PopulationId, RegistryId
from ...kernel.values import FrozenRegistry, PositiveInt, StructuredValue
from ..domain import (
    DatasetDefinition,
    Definition,
    EvaluationDefinition,
    ExperimentDefinition,
    PopulationDefinition,
    ProtocolCatalogue,
    ResolvedConfiguration,
    ResolvedRuntimeCatalogue,
    ResolvedStudyCatalogue,
)
from .bundle import (
    AuthoredConfigBundle,
    AuthoredMapping,
    AuthoredValue,
    DatasetDocumentConfig,
    ExperimentsDocumentConfig,
    ProtocolsDocumentConfig,
    RuntimeDocumentConfig,
)


def _freeze(value: AuthoredValue) -> StructuredValue:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _freeze_mapping(value: AuthoredMapping) -> Mapping[str, StructuredValue]:
    return MappingProxyType({key: _freeze(item) for key, item in value.items()})


def _require_mapping(value: AuthoredValue, location: str) -> AuthoredMapping:
    if not isinstance(value, dict):
        raise ConfigurationError(f"{location} must be a mapping")
    return value


def _require_sequence(value: AuthoredValue | None, location: str) -> list[AuthoredValue]:
    if not isinstance(value, list):
        raise ConfigurationError(f"{location} must be a sequence")
    return value


def _require_string(value: AuthoredValue | None, location: str) -> str:
    if not isinstance(value, str) or not value:
        raise ConfigurationError(f"{location} must be a non-empty string")
    return value


def _string_sequence(value: AuthoredValue | None, location: str) -> tuple[str, ...]:
    return tuple(_require_string(item, location) for item in _require_sequence(value, location))


def _optional_string(mapping: AuthoredMapping, key: str, default: str) -> str:
    value = mapping.get(key)
    if value is None:
        return default
    return _require_string(value, key)


def _registry(values: AuthoredMapping, kind: str) -> FrozenRegistry[RegistryId[object], Definition]:
    items: dict[RegistryId[object], Definition] = {}
    for identifier, raw_value in values.items():
        raw = _require_mapping(raw_value, f"{kind}.{identifier}")
        key = RegistryId[object](identifier)
        items[key] = Definition(
            identifier=key,
            kind=_optional_string(raw, "kind", kind),
            values=_freeze_mapping(raw),
        )
    return FrozenRegistry(_items=items)


def _structured_registry(values: AuthoredMapping, kind: str) -> FrozenRegistry[RegistryId[object], Definition]:
    """Retain configuration sections that deliberately mix definitions and controls."""
    items: dict[RegistryId[object], Definition] = {}
    for identifier, raw_value in values.items():
        key = RegistryId[object](identifier)
        values_mapping = _freeze_mapping(raw_value) if isinstance(raw_value, dict) else {"value": _freeze(raw_value)}
        items[key] = Definition(identifier=key, kind=kind, values=values_mapping)
    return FrozenRegistry(_items=items)


def _dataset_payload(document: DatasetDocumentConfig) -> Mapping[str, StructuredValue]:
    return {
        "schema_version": document.schema_version,
        "dataset": document.dataset,
        "display_name": document.display_name,
        "schema_id": document.schema_id,
        "source_layout": _freeze_mapping(document.source_layout),
        "field_schema": _freeze_mapping(document.field_schema),
        "source_contract": _freeze_mapping(document.source_contract),
        "fingerprint_inputs": _freeze_mapping(document.fingerprint_inputs),
        "eligibility_policy": document.eligibility_policy,
        "materializations": _freeze_mapping(document.materializations),
        "setups": _freeze_mapping(document.setups),
        "client_identity_contract": (
            _freeze_mapping(document.client_identity_contract)
            if document.client_identity_contract is not None
            else None
        ),
    }


def _experiments_payload(document: ExperimentsDocumentConfig) -> Mapping[str, StructuredValue]:
    return {
        "schema_version": document.schema_version,
        "study_populations": _freeze_mapping(document.study_populations),
        "capabilities": tuple(document.capabilities),
        "suppression_behaviors": tuple(document.suppression_behaviors),
        "population_readiness_rule": _freeze_mapping(document.population_readiness_rule),
        "eligibility_gates": _freeze_mapping(document.eligibility_gates),
        "analysis_conventions": _freeze_mapping(document.analysis_conventions),
        "experiments": tuple(_freeze_mapping(experiment) for experiment in document.experiments),
    }


def _protocols_payload(document: ProtocolsDocumentConfig) -> Mapping[str, StructuredValue]:
    return {
        "schema_version": document.schema_version,
        "model_architectures": _freeze_mapping(document.model_architectures),
        "optimizers": _freeze_mapping(document.optimizers),
        "batching": _freeze_mapping(document.batching),
        "determinism": _freeze_mapping(document.determinism),
        "seed_cohorts": _freeze_mapping(document.seed_cohorts),
        "checkpoint_profiles": _freeze_mapping(document.checkpoint_profiles),
        "training_profiles": _freeze_mapping(document.training_profiles),
        "eligibility_policies": _freeze_mapping(document.eligibility_policies),
        "normalization_strategies": _freeze_mapping(document.normalization_strategies),
        "normalization_fit_scopes": _freeze_mapping(document.normalization_fit_scopes),
        "normalization_leakage_rule": document.normalization_leakage_rule,
        "quantile_estimators": _freeze_mapping(document.quantile_estimators),
        "threshold_policy_defaults": _freeze_mapping(document.threshold_policy_defaults),
        "threshold_policies": _freeze_mapping(document.threshold_policies),
        "metric_definitions": _freeze_mapping(document.metric_definitions),
        "metric_bundles": _freeze_mapping(document.metric_bundles),
        "statistical_profiles": _freeze_mapping(document.statistical_profiles),
        "nested_replicate_policy": _freeze_mapping(document.nested_replicate_policy),
        "result_types": _freeze_mapping(document.result_types),
        "evaluation_result_contract": _freeze_mapping(document.evaluation_result_contract),
        "artifact_identity": _freeze_mapping(document.artifact_identity),
        "communication_estimation_contract": _freeze_mapping(document.communication_estimation_contract),
        "report_defaults": _freeze_mapping(document.report_defaults),
        "report_profiles": _freeze_mapping(document.report_profiles),
        "operational_inputs": _freeze_mapping(document.operational_inputs),
    }


def _runtime_payload(document: RuntimeDocumentConfig) -> Mapping[str, StructuredValue]:
    return {
        "schema_version": document.schema_version,
        "roots": _freeze_mapping(document.roots),
        "raw_source_policy": _freeze_mapping(document.raw_source_policy),
        "determinism_enforcement": _freeze_mapping(document.determinism_enforcement),
        "device_policy_rules": _freeze_mapping(document.device_policy_rules),
        "resource_pressure_policy": _freeze_mapping(document.resource_pressure_policy),
        "execution_profiles": _freeze_mapping(document.execution_profiles),
    }


def map_configuration(bundle: AuthoredConfigBundle) -> ResolvedConfiguration:
    dataset_items: dict[DatasetId, DatasetDefinition] = {}
    for authored in bundle.datasets:
        identifier = DatasetId(authored.dataset)
        dataset_items[identifier] = DatasetDefinition(
            identifier=identifier,
            display_name=authored.display_name,
            schema_id=RegistryId(authored.schema_id),
            source_layout=_freeze_mapping(authored.source_layout),
            field_schema=_freeze_mapping(authored.field_schema),
            source_contract=_freeze_mapping(authored.source_contract),
            materializations=_registry(authored.materializations, "materialization"),
            setups=_registry(authored.setups, "dataset_setup"),
        )

    populations: dict[PopulationId, PopulationDefinition] = {}
    for identifier, raw_value in bundle.experiments.study_populations.items():
        values = _require_mapping(raw_value, f"study_populations.{identifier}")
        population_id = PopulationId(identifier)
        populations[population_id] = PopulationDefinition(
            identifier=population_id,
            dataset_id=DatasetId(_require_string(values.get("dataset"), f"{identifier}.dataset")),
            setup_id=RegistryId(_require_string(values.get("setup"), f"{identifier}.setup")),
            metric_bundle_id=RegistryId(_require_string(values.get("metric_bundle"), f"{identifier}.metric_bundle")),
        )

    protocol_groups = {
        "model_architectures": _registry(bundle.protocols.model_architectures, "model_architecture"),
        "optimizers": _registry(bundle.protocols.optimizers, "optimizer"),
        "batching": _registry(bundle.protocols.batching, "batching"),
        "seed_cohorts": _registry(bundle.protocols.seed_cohorts, "seed_cohort"),
        "checkpoint_profiles": _registry(bundle.protocols.checkpoint_profiles, "checkpoint_profile"),
        "training_profiles": _registry(bundle.protocols.training_profiles, "training_profile"),
        "eligibility_policies": _registry(bundle.protocols.eligibility_policies, "eligibility_policy"),
        "quantile_estimators": _registry(bundle.protocols.quantile_estimators, "quantile_estimator"),
        "threshold_policies": _registry(bundle.protocols.threshold_policies, "threshold_policy"),
        "metric_definitions": _structured_registry(bundle.protocols.metric_definitions, "metric"),
        "metric_bundles": _registry(bundle.protocols.metric_bundles, "metric_bundle"),
        "statistical_profiles": _registry(bundle.protocols.statistical_profiles, "statistical_profile"),
        "result_types": _registry(bundle.protocols.result_types, "result_type"),
        "report_profiles": _registry(bundle.protocols.report_profiles, "report_profile"),
        "operational_inputs": _registry(bundle.protocols.operational_inputs, "operational_input"),
    }

    experiments: dict[ExperimentId, ExperimentDefinition] = {}
    for raw in bundle.experiments.experiments:
        identifier = ExperimentId(_require_string(raw.get("name"), "experiment.name"))
        evaluations = tuple(
            EvaluationDefinition(
                identifier=RegistryId(_require_string(item.get("label"), "evaluation.label")),
                threshold_policy_id=RegistryId(
                    _require_string(item.get("threshold_policy"), "evaluation.threshold_policy")
                ),
                values=_freeze_mapping(item),
            )
            for item in (
                _require_mapping(item, "experiment.evaluations item")
                for item in _require_sequence(raw.get("evaluations"), "experiment.evaluations")
            )
        )
        analyses = tuple(
            Definition(
                identifier=RegistryId(_require_string(item.get("label"), "analysis.label")),
                kind=_require_string(item.get("kind"), "analysis.kind"),
                values=_freeze_mapping(item),
            )
            for item in (
                _require_mapping(item, "experiment.analyses item")
                for item in _require_sequence(raw.get("analyses"), "experiment.analyses")
            )
        )
        prerequisites = tuple(
            ExperimentId(_require_string(item.get("experiment"), "prerequisite.experiment"))
            for item in (
                _require_mapping(item, "experiment.prerequisites item")
                for item in _require_sequence(raw.get("prerequisites"), "experiment.prerequisites")
            )
        )
        experiments[identifier] = ExperimentDefinition(
            identifier=identifier,
            display_name=_require_string(raw.get("display_name"), "experiment.display_name"),
            evidence_role=_require_string(raw.get("evidence_role"), "experiment.evidence_role"),
            run_requirement=_require_string(raw.get("run_requirement"), "experiment.run_requirement"),
            population_ids=tuple(
                PopulationId(value) for value in _string_sequence(raw.get("populations"), "experiment.populations")
            ),
            training_profile_id=RegistryId(_require_string(raw.get("training_profile"), "experiment.training_profile")),
            checkpoint_profile_id=RegistryId(
                _require_string(raw.get("checkpoint_profile"), "experiment.checkpoint_profile")
            ),
            seed_cohort_id=RegistryId(_require_string(raw.get("seed_cohort"), "experiment.seed_cohort")),
            eligibility_policy_id=RegistryId(
                _require_string(raw.get("eligibility_policy"), "experiment.eligibility_policy")
            ),
            prerequisite_ids=prerequisites,
            evaluations=evaluations,
            analyses=analyses,
            report_profile_ids=tuple(
                RegistryId(value) for value in _string_sequence(raw.get("reports"), "experiment.reports")
            ),
            values=_freeze_mapping(raw),
        )

    study_payload: Mapping[str, StructuredValue] = {
        "datasets": tuple(_dataset_payload(document) for document in bundle.datasets),
        "experiments": _experiments_payload(bundle.experiments),
        "protocols": _protocols_payload(bundle.protocols),
    }
    runtime_payload = _runtime_payload(bundle.runtime)
    return ResolvedConfiguration(
        study=ResolvedStudyCatalogue(
            schema_version=PositiveInt(1),
            datasets=FrozenRegistry(_items=dataset_items),
            protocols=ProtocolCatalogue(groups=protocol_groups),
            populations=FrozenRegistry(_items=populations),
            experiments=FrozenRegistry(_items=experiments),
            declared_capabilities=frozenset(bundle.experiments.capabilities),
            catalogue_fingerprint=fingerprint(study_payload),
        ),
        runtime=ResolvedRuntimeCatalogue(
            roots=_freeze_mapping(bundle.runtime.roots),
            execution_profiles=_registry(bundle.runtime.execution_profiles, "execution_profile"),
            runtime_fingerprint=fingerprint(runtime_payload),
        ),
    )
