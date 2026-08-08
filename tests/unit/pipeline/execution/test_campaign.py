import pytest

from datp_core.datasets.partitioning.contracts import ClientIdentity
from datp_core.domain.enums import (
    FederatedThresholdMethod,
    PopulationId,
    PopulationIdentityKind,
    PreprocessingProtocolId,
    SplitProtocolId,
    TrainingModelId,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values.checksums import checksum_text
from datp_core.domain.values.counts import Seed
from datp_core.domain.values.ratios import DittoRegularization, ScoreValue
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.pipeline.execution.engine import build_campaign
from datp_core.pipeline.planning import expand_experiment_plan
from datp_core.protocols.calibration import CANONICAL_QUANTILE, QuantileProtocol
from datp_core.protocols.experiments import EXPERIMENTS
from datp_core.protocols.seeds import CONFIRMATORY_SEED_COHORT
from datp_core.protocols.training import DITTO_TRAINING_PROTOCOLS, resolve_ditto_protocol
from datp_core.thresholding.methods.local import construct_local_threshold
from datp_core.thresholding.methods.shared import construct_shared_threshold
from datp_core.thresholding.quantiles import ClientBenignCalibrationScores, unweighted_mean


def test_campaign_contains_only_executable_plan_entries() -> None:
    plan = expand_experiment_plan(declarations=EXPERIMENTS, seed_cohort=CONFIRMATORY_SEED_COHORT)
    campaign = build_campaign(plan)
    assert all(entry.ordinal == index for index, entry in enumerate(campaign.entries))
    assert campaign.digest.value


def test_ditto_training_protocol_resolves_every_declared_regularization() -> None:
    for protocol in DITTO_TRAINING_PROTOCOLS:
        assert resolve_ditto_protocol(protocol.regularization) is protocol


def test_ditto_training_protocol_rejects_an_undeclared_regularization() -> None:
    with pytest.raises(ScientificContractError, match="regularization"):
        resolve_ditto_protocol(DittoRegularization(999.0))


def _ditto_personalized_coordinate() -> FederatedTrainingCoordinate:
    return FederatedTrainingCoordinate(
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        training_seed=Seed(0),
        split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
        preprocessing_identity=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        model=TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER,
        model_coefficient=DITTO_TRAINING_PROTOCOLS[0].regularization,
    )


def _ditto_client(client_id: str) -> ClientIdentity:
    return ClientIdentity(PopulationId.NBAIOT_NATURAL_DEVICES, client_id, PopulationIdentityKind.PHYSICAL_DEVICES)


def test_ditto_shared_threshold_accepts_distinct_personalized_model_checksums() -> None:
    coordinate = _ditto_personalized_coordinate()
    eligible = tuple(
        ClientBenignCalibrationScores(
            _ditto_client(f"device-{index}"),
            coordinate,
            tuple(ScoreValue(value) for value in scores),
            checksum_text(f"calibration-manifest-{index}"),
            checksum_text(f"distinct-personalized-model-{index}"),
        )
        for index, scores in enumerate(
            (
                (0.1, 0.2, 0.3, 0.4, 0.5),
                (1.0, 1.1, 1.2, 1.3, 1.4),
                (2.0, 2.5, 3.0, 3.5, 4.0),
            )
        )
    )

    local = construct_local_threshold(
        eligible,
        QuantileProtocol(method=FederatedThresholdMethod.LOCAL_THRESHOLD, quantile=CANONICAL_QUANTILE),
    )
    shared = construct_shared_threshold(
        eligible,
        QuantileProtocol(method=FederatedThresholdMethod.SHARED_THRESHOLD, quantile=CANONICAL_QUANTILE),
    )

    assert len(local.assignments) == len(eligible)
    assert len({assignment.threshold.value for assignment in local.assignments}) == len(eligible)
    assert shared.shared_threshold.value == pytest.approx(
        unweighted_mean(tuple(item.value for item in local.local_quantiles)).value
    )
    assert all(
        assignment.threshold.value == pytest.approx(shared.shared_threshold.value) for assignment in shared.assignments
    )
