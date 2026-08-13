from types import SimpleNamespace
from typing import cast

import pytest

from datp_core.analysis.metrics.federated import FederatedEvaluationDocument
from datp_core.analysis.operational.communication import ThresholdPayloadKind
from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import FederatedThresholdMethod
from datp_core.core.numeric import Seed
from datp_core.presentation.operational_accounting import _disclosures, _require_one_threshold_accounting_cohort


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


def test_threshold_stage_accounting_rejects_mixed_detector_cohorts_and_duplicate_cells() -> None:
    def document(method: FederatedThresholdMethod, seed: int, *, model: str = "fedavg") -> SimpleNamespace:
        return SimpleNamespace(
            threshold_method=method,
            score_coordinate=SimpleNamespace(
                population="nbaiot",
                split_protocol="non_temporal",
                preprocessing_identity="local_standard",
                model=model,
                model_coefficient=None,
                training_seed=Seed(seed),
            ),
        )

    with pytest.raises(ScientificContractError, match="one population, split, preprocessing, and detector cohort"):
        _require_one_threshold_accounting_cohort(
            cast(
                tuple[FederatedEvaluationDocument, ...],
                (
                    document(FederatedThresholdMethod.SHARED_THRESHOLD, 0),
                    document(FederatedThresholdMethod.LOCAL_THRESHOLD, 0, model="fedprox"),
                ),
            )
        )
    with pytest.raises(ScientificContractError, match="cannot repeat a policy/seed cell"):
        _require_one_threshold_accounting_cohort(
            cast(
                tuple[FederatedEvaluationDocument, ...],
                (
                    document(FederatedThresholdMethod.SHARED_THRESHOLD, 0),
                    document(FederatedThresholdMethod.SHARED_THRESHOLD, 0),
                ),
            )
        )
