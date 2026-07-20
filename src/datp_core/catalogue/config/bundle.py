"""Document-specific Pydantic authored configuration models."""

from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict, field_validator

type AuthoredScalar = str | int | float | bool | None
type AuthoredValue = AuthoredScalar | list[AuthoredValue] | dict[str, AuthoredValue]
type AuthoredMapping = dict[str, AuthoredValue]


class _StrictDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: int

    @field_validator("schema_version")
    @classmethod
    def _schema_v1(cls, value: int) -> int:
        if value != 1:
            raise ValueError("unsupported schema_version; only version 1 is supported")
        return value


class DatasetDocumentConfig(_StrictDocument):
    dataset: str
    display_name: str
    schema_id: str
    source_layout: AuthoredMapping
    field_schema: AuthoredMapping
    source_contract: AuthoredMapping
    fingerprint_inputs: AuthoredMapping
    eligibility_policy: str
    materializations: AuthoredMapping
    setups: AuthoredMapping
    client_identity_contract: AuthoredMapping | None = None


class ExperimentsDocumentConfig(_StrictDocument):
    study_populations: AuthoredMapping
    capabilities: list[str]
    suppression_behaviors: list[str]
    population_readiness_rule: AuthoredMapping
    eligibility_gates: AuthoredMapping
    analysis_conventions: AuthoredMapping
    experiments: list[AuthoredMapping]


class ProtocolsDocumentConfig(_StrictDocument):
    model_architectures: AuthoredMapping
    optimizers: AuthoredMapping
    batching: AuthoredMapping
    determinism: AuthoredMapping
    seed_cohorts: AuthoredMapping
    checkpoint_profiles: AuthoredMapping
    training_profiles: AuthoredMapping
    eligibility_policies: AuthoredMapping
    normalization_strategies: AuthoredMapping
    normalization_fit_scopes: AuthoredMapping
    normalization_leakage_rule: str
    quantile_estimators: AuthoredMapping
    threshold_policy_defaults: AuthoredMapping
    threshold_policies: AuthoredMapping
    metric_definitions: AuthoredMapping
    metric_bundles: AuthoredMapping
    statistical_profiles: AuthoredMapping
    nested_replicate_policy: AuthoredMapping
    result_types: AuthoredMapping
    evaluation_result_contract: AuthoredMapping
    artifact_identity: AuthoredMapping
    communication_estimation_contract: AuthoredMapping
    report_defaults: AuthoredMapping
    report_profiles: AuthoredMapping
    operational_inputs: AuthoredMapping


class RuntimeDocumentConfig(_StrictDocument):
    roots: AuthoredMapping
    raw_source_policy: AuthoredMapping
    determinism_enforcement: AuthoredMapping
    device_policy_rules: AuthoredMapping
    resource_pressure_policy: AuthoredMapping
    execution_profiles: AuthoredMapping


@dataclass(frozen=True, slots=True, kw_only=True)
class ConfigPaths:
    nbaiot: Path
    ciciot2023: Path
    edge_iiotset: Path
    experiments: Path
    protocols: Path
    runtime: Path

    @classmethod
    def under(cls, root: Path) -> "ConfigPaths":
        return cls(
            nbaiot=root / "configs/datasets/nbaiot.yaml",
            ciciot2023=root / "configs/datasets/ciciot2023.yaml",
            edge_iiotset=root / "configs/datasets/edge_iiotset.yaml",
            experiments=root / "configs/experiments.yaml",
            protocols=root / "configs/protocols.yaml",
            runtime=root / "configs/runtime.yaml",
        )


class AuthoredConfigBundle(BaseModel):
    model_config = ConfigDict(frozen=True)
    datasets: tuple[DatasetDocumentConfig, ...]
    experiments: ExperimentsDocumentConfig
    protocols: ProtocolsDocumentConfig
    runtime: RuntimeDocumentConfig
