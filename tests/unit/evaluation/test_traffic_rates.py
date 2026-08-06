import pytest

from datp_core.domain.enums import PopulationId, TrafficRateEvidenceType
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values.ratios import TrafficRatePerDay
from datp_core.evaluation.traffic_rates import (
    TrafficRateGranularity,
    TrafficRateUnit,
    ValidatedTrafficRateEvidence,
    validate_traffic_rate_evidence,
)


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
