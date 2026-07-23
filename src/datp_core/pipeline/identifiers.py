"""Strongly typed domain identifiers excluding path-like strings and generic object registries."""

from __future__ import annotations

import re

from attrs import define, field

_HEX64_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


def validate_canonical_identifier(instance: object, attribute: object, value: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"Identifier value must be a string, got {type(value).__name__}")
    if not value or value.strip() != value:
        raise ValueError("Identifier must be non-empty and canonical without whitespace padding")
    if any(char in value for char in ("/", "\\", "\x00")):
        raise ValueError("Identifier must not contain path delimiters or null bytes")


@define(frozen=True, slots=True, order=True)
class _DomainIdentifier:
    value: str = field(validator=validate_canonical_identifier)

    def __str__(self) -> str:
        return self.value


class DatasetId(_DomainIdentifier):
    """Identifier for a dataset (e.g. 'nbaiot', 'ciciot2023', 'edge_iiotset')."""


class PopulationId(_DomainIdentifier):
    """Identifier for a study population (e.g. 'nbaiot_natural_devices')."""


class ExperimentId(_DomainIdentifier):
    """Identifier for a registered experiment (e.g. 'anchor_reproduction')."""


class TrainingProfileId(_DomainIdentifier):
    """Identifier for a model training profile (e.g. 'federated_averaging_anchor')."""


class CheckpointProfileId(_DomainIdentifier):
    """Identifier for a checkpoint selection profile (e.g. 'anchor_terminal_round')."""


class SeedCohortId(_DomainIdentifier):
    """Identifier for a seed cohort definition (e.g. 'datp_core_ten_seed')."""


class EligibilityPolicyId(_DomainIdentifier):
    """Identifier for an eligibility evaluation policy."""


class NormalizationStrategyId(_DomainIdentifier):
    """Identifier for a feature normalization strategy."""


class ThresholdPolicyId(_DomainIdentifier):
    """Identifier for a threshold policy (e.g. 'shared_mean_p95', 'local_p95')."""


class MetricId(_DomainIdentifier):
    """Identifier for an individual evaluation metric (e.g. 'false_positive_rate')."""


class MetricBundleId(_DomainIdentifier):
    """Identifier for a metric collection bundle."""


class StatisticalProfileId(_DomainIdentifier):
    """Identifier for a statistical hypothesis testing protocol."""


class ReportProfileId(_DomainIdentifier):
    """Identifier for a report generation profile."""


class DatasetSetupId(_DomainIdentifier):
    """Identifier for a dataset setup profile (e.g. 'natural_devices')."""


class MaterializationId(_DomainIdentifier):
    """Identifier for a dataset materialization schema."""


class ArtifactId(_DomainIdentifier):
    """Canonical identifier for a persisted DATP artifact."""


class JobId(_DomainIdentifier):
    """Identifier for a DAG execution stage job."""


class RunId(_DomainIdentifier):
    """Identifier for a specific execution run instance."""


class ClientId(_DomainIdentifier):
    """Identifier for a client device or pseudo-client entity."""
