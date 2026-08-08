import pytest

from datp_core.analysis.operational.traffic_rates import (
    TrafficRateEvidence,
    TrafficRateGranularity,
    TrafficRateLocatorScheme,
    TrafficRateSourceLocator,
    TrafficRateUnit,
    ValidatedTrafficRateEvidence,
    validate_traffic_rate_evidence,
)
from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import PopulationId, TrafficRateEvidenceType
from datp_core.core.numeric import TrafficRatePerDay


def test_traffic_rate_evidence_requires_per_client_applicability() -> None:
    with pytest.raises(ScientificContractError, match="applicable"):
        ValidatedTrafficRateEvidence(
            TrafficRateEvidenceType.MEASURED,
            PopulationId.NBAIOT_NATURAL_DEVICES,
            TrafficRatePerDay(10),
            "source",
            "audit",
            TrafficRateUnit.BENIGN_DECISIONS_PER_CLIENT_PER_DAY,
            TrafficRateGranularity.PER_CLIENT,
            False,
        )


def test_dataset_derived_traffic_rate_is_accepted() -> None:
    evidence = ValidatedTrafficRateEvidence(
        TrafficRateEvidenceType.DATASET_DERIVED,
        PopulationId.NBAIOT_NATURAL_DEVICES,
        TrafficRatePerDay(10),
        "source",
        "audit",
        TrafficRateUnit.BENIGN_DECISIONS_PER_CLIENT_PER_DAY,
        TrafficRateGranularity.PER_CLIENT,
        True,
    )

    assert validate_traffic_rate_evidence(evidence) is evidence


def test_declared_traffic_rate_evidence_rejects_unavailable_kind() -> None:
    with pytest.raises(ValueError, match="unavailable"):
        TrafficRateEvidence(
            population=PopulationId.NBAIOT_NATURAL_DEVICES,
            rate_per_day=TrafficRatePerDay(10),
            evidence_kind=TrafficRateEvidenceType.UNAVAILABLE,
            source_locator=TrafficRateSourceLocator(
                scheme=TrafficRateLocatorScheme.DATASET_PATH,
                reference="data/canonical/nbaiot",
            ),
            provenance="audit",
            unit=TrafficRateUnit.BENIGN_DECISIONS_PER_CLIENT_PER_DAY,
            granularity=TrafficRateGranularity.PER_CLIENT,
            applicable_to_each_client=True,
        )


def test_declared_traffic_rate_evidence_converts_to_validated_evidence() -> None:
    declared = TrafficRateEvidence(
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        rate_per_day=TrafficRatePerDay(10),
        evidence_kind=TrafficRateEvidenceType.DATASET_DERIVED,
        source_locator=TrafficRateSourceLocator(
            scheme=TrafficRateLocatorScheme.DATASET_PATH,
            reference="data/canonical/nbaiot",
        ),
        provenance="audit",
        unit=TrafficRateUnit.BENIGN_DECISIONS_PER_CLIENT_PER_DAY,
        granularity=TrafficRateGranularity.PER_CLIENT,
        applicable_to_each_client=True,
    )

    validated = declared.to_validated()

    assert validated.source_locator == "dataset_path:data/canonical/nbaiot"
    assert validated.evidence_kind is TrafficRateEvidenceType.DATASET_DERIVED
