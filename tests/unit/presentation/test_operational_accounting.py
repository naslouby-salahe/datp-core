from datp_core.analysis.operational.communication import ThresholdPayloadKind
from datp_core.presentation.operational_accounting import _disclosures


def test_threshold_stage_disclosures_are_explicit_and_do_not_claim_privacy() -> None:
    disclosures = _disclosures(
        frozenset(
            (
                ThresholdPayloadKind.LOCAL_QUANTILE_TRANSMISSION,
                ThresholdPayloadKind.CLUSTER_FINGERPRINT_TRANSMISSION,
                ThresholdPayloadKind.GROUPED_THRESHOLD_ASSIGNMENT,
            )
        )
    )

    assert disclosures == (
        "threshold=yes; moments=no; fingerprint=yes; sketch=no; family=pre-existing metadata; cluster_assignment=yes"
    )
