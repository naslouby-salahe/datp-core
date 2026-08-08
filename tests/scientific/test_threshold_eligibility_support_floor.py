"""Threshold construction must receive only clients meeting n_k >= 100."""

from pathlib import Path

import pytest
from tests.unit.calibration.helpers import benign_score_record
from tests.unit.learning.federated.helpers import fedavg_coordinate

from datp_core.artifacts.provenance import Checksum
from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import EvidenceRole, PartitionRole, SplitProtocolId
from datp_core.core.numeric import Seed
from datp_core.detector.scoring.contracts import ScoreArtifactManifest
from datp_core.experiments.execution.evidence import eligible_calibration_scores


def _manifest(tmp_path: Path, calibration_sizes: dict[str, int]) -> ScoreArtifactManifest:
    coordinate = fedavg_coordinate(Seed(0))
    calibration = tuple(
        benign_score_record(
            tmp_path,
            client_id,
            tuple(float(index) for index in range(count)),
            seed=Seed(0),
            partition_role=PartitionRole.CALIBRATION,
        )
        for client_id, count in sorted(calibration_sizes.items())
    )
    evaluation = tuple(
        benign_score_record(
            tmp_path,
            client_id,
            tuple(float(index) for index in range(20)),
            seed=Seed(0),
            partition_role=PartitionRole.EVALUATION,
            row_id_prefix=f"{client_id}-eval",
        )
        for client_id in sorted(calibration_sizes)
    )
    return ScoreArtifactManifest(
        coordinate=coordinate,
        scored_split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
        checkpoint_round=calibration[0].checkpoint_round,
        checkpoint_checksum=Checksum("a" * 64),
        preprocessing_state_set_checksum=Checksum("b" * 64),
        split_manifest_checksum=Checksum("c" * 64),
        calibration_records=calibration,
        evaluation_records=evaluation,
    )


def test_eligible_calibration_scores_excludes_clients_below_minimum_support(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path, {"rich": 150, "poor": 50})
    eligible = eligible_calibration_scores(manifest)
    assert tuple(item.client.client_id for item in eligible) == ("rich",)
    assert all(len(item.scores) >= 100 for item in eligible)


def test_eligible_calibration_scores_fails_when_no_client_meets_support(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path, {"a": 10, "b": 20})
    with pytest.raises(ScientificContractError, match="minimum benign calibration support"):
        eligible_calibration_scores(manifest)


def test_training_stress_test_role_is_authorized_on_nbaiot_natural() -> None:
    from datp_core.core.identifiers import PopulationId
    from datp_core.data.populations.contracts import population_allowed_evidence_roles

    allowed = population_allowed_evidence_roles(PopulationId.NBAIOT_NATURAL_DEVICES)
    assert EvidenceRole.TRAINING_STRESS_TEST in allowed
    assert EvidenceRole.CONFIRMATORY in allowed
    assert EvidenceRole.SUPPORTIVE in allowed
    assert EvidenceRole.EXTERNAL_VALIDATION not in allowed


def test_deployment_fallback_uses_mean_of_eligible_local_thresholds() -> None:
    from tests.unit.thresholding.helpers import client_scores

    from datp_core.analysis.metrics.federated_execution import _deployment_fallback_threshold
    from datp_core.core.identifiers import FederatedThresholdMethod
    from datp_core.core.numeric import Quantile
    from datp_core.protocols.calibration import QuantileProtocol
    from datp_core.thresholds.policies.local import construct_local_threshold
    from datp_core.thresholds.quantiles import unweighted_mean

    eligible = (
        client_scores("client_a", tuple(float(i) for i in range(100))),
        client_scores("client_b", tuple(float(i + 10) for i in range(100))),
    )
    local = construct_local_threshold(
        eligible,
        QuantileProtocol(method=FederatedThresholdMethod.LOCAL_THRESHOLD, quantile=Quantile(0.95)),
    )
    assignments = local.assignments
    fallback = _deployment_fallback_threshold(assignments, local)
    assert fallback is not None
    expected = unweighted_mean(tuple(item.threshold for item in assignments))
    assert fallback.value == expected.value


def test_calibration_size_protocol_locks_declared_size_grid() -> None:
    from datp_core.protocols.calibration import CALIBRATION_SIZE_PROTOCOL

    assert CALIBRATION_SIZE_PROTOCOL.sizes[0].value == 50
