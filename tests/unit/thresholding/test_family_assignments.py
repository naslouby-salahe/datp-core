"""Family-assignment validation tests — FamilyAssignments model and engine integration."""

from __future__ import annotations

import pytest

from datp_core.core.identifiers import ClientId, PopulationId, ThresholdPolicyId
from datp_core.thresholding.engine import ThresholdEngine
from datp_core.thresholding.enums import ThresholdPolicyKind
from datp_core.thresholding.models import (
    BenignCalibrationScores,
    FamilyAssignments,
    ThresholdConfigurationError,
    ThresholdConstructionRequest,
)
from datp_core.thresholding.policies import QuantilePolicy


def _calibration(client_ids: list[str]) -> tuple[BenignCalibrationScores, ...]:
    return tuple(
        BenignCalibrationScores(client_id=ClientId(cid), values=(1.0, 2.0, 3.0))
        for cid in client_ids
    )


def _request(
    calibration_ids: list[str],
    assignment_pairs: list[tuple[str, str]],
) -> ThresholdConstructionRequest:
    return ThresholdConstructionRequest(
        policy_id=ThresholdPolicyId("test"),
        policy=QuantilePolicy(kind=ThresholdPolicyKind.FAMILY_MEAN, quantile=0.95),
        calibration=_calibration(calibration_ids),
        population_id=PopulationId("test"),
        family_assignments=FamilyAssignments(
            mapping=tuple((ClientId(cid), label) for cid, label in assignment_pairs),
        ),
    )


def _engine() -> ThresholdEngine:
    return ThresholdEngine()


class TestFamilyAssignmentsModel:
    """Direct FamilyAssignments model validation."""

    def test_duplicate_client_raises_configuration_error(self) -> None:
        mapping = (
            (ClientId("c1"), "A"),
            (ClientId("c1"), "A"),
        )
        with pytest.raises(ThresholdConfigurationError, match="Duplicate"):
            FamilyAssignments(mapping=mapping)

    def test_blank_label_raises_configuration_error(self) -> None:
        mapping = ((ClientId("c1"), ""),)
        with pytest.raises(ThresholdConfigurationError, match="blank"):
            FamilyAssignments(mapping=mapping)

    def test_reordered_input_produces_identical_results(self) -> None:
        fa1 = FamilyAssignments(
            mapping=(
                (ClientId("c2"), "B"),
                (ClientId("c1"), "A"),
            ),
        )
        fa2 = FamilyAssignments(
            mapping=(
                (ClientId("c1"), "A"),
                (ClientId("c2"), "B"),
            ),
        )
        assert fa1.mapping == fa2.mapping
        assert fa1.mapping[0][0] == ClientId("c1")
        assert fa1.mapping[1][0] == ClientId("c2")


class TestEngineFamilyValidation:
    """Engine integration — calibration-to-assignment cross-validation."""

    def test_exact_complete_mapping_succeeds(self) -> None:
        req = _request(
            calibration_ids=["c1", "c2"],
            assignment_pairs=[("c1", "A"), ("c2", "B")],
        )
        result = _engine().construct(req)
        assert len(result.values) == 2

    def test_single_client_mapping_succeeds(self) -> None:
        req = _request(
            calibration_ids=["c1"],
            assignment_pairs=[("c1", "A")],
        )
        result = _engine().construct(req)
        assert len(result.values) == 1

    def test_missing_client_raises_configuration_error(self) -> None:
        req = _request(
            calibration_ids=["c1", "c2"],
            assignment_pairs=[("c1", "A")],
        )
        engine = _engine()
        with pytest.raises(ThresholdConfigurationError, match="missing"):
            engine.construct(req)

    def test_extra_client_raises_configuration_error(self) -> None:
        req = _request(
            calibration_ids=["c1"],
            assignment_pairs=[("c1", "A"), ("c2", "B")],
        )
        engine = _engine()
        with pytest.raises(ThresholdConfigurationError, match="not in calibration"):
            engine.construct(req)
