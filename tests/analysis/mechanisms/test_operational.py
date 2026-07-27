"""Unit tests for operational resource-cost calculations."""

from __future__ import annotations

from unittest.mock import MagicMock

from datp_core.analysis.mechanisms.operational import analyze_resource_cost
from datp_core.analysis.runtime.context import AnalysisExecutionContext
from datp_core.config.operational_contracts import (
    CheckpointStorageRecord,
    CommunicationEstimationContractRecord,
    FieldEncodingRecord,
    ModelExchangeRecord,
    ThresholdExchangeEntryRecord,
    ThresholdExchangeRecord,
)
from datp_core.core.identifiers import ExperimentId, PopulationId, StatisticalProfileId, ThresholdPolicyId
from datp_core.core.seeding import Seed
from datp_core.experiments import (
    EvaluationSpecRecord,
    ExperimentRecord,
    RecalibrationMode,
    ResourceCostAnalysisRecord,
    RunRequirement,
)
from datp_core.thresholding.policies.shared import SharedMeanThresholdPolicyRecord


def _build_dummy_contract(bytes_per_field: int = 4, direction_count: int = 2) -> CommunicationEstimationContractRecord:
    directions = ("uplink", "downlink") if direction_count == 2 else ("uplink",)
    return CommunicationEstimationContractRecord(
        estimate_basis="communication_contract",
        field_encodings={
            "float32": FieldEncodingRecord(bytes_per_field=bytes_per_field, byte_order="big"),
            "threshold": FieldEncodingRecord(bytes_per_field=bytes_per_field, byte_order="big"),
        },
        threshold_exchange=ThresholdExchangeRecord(
            direction="uplink",
            b1=ThresholdExchangeEntryRecord(
                uplink_fields_per_client=("threshold",),
                downlink_fields_per_client=(),
                candidate_grid_downlink_fields_per_client=(),
                candidate_grid_uplink_fields_per_client_per_candidate=(),
            ),
            b2=ThresholdExchangeEntryRecord(
                uplink_fields_per_client=(),
                downlink_fields_per_client=(),
                candidate_grid_downlink_fields_per_client=(),
                candidate_grid_uplink_fields_per_client_per_candidate=(),
            ),
            b4=ThresholdExchangeEntryRecord(
                uplink_fields_per_client=(),
                downlink_fields_per_client=(),
                candidate_grid_downlink_fields_per_client=(),
                candidate_grid_uplink_fields_per_client_per_candidate=(),
            ),
            federated_summary=ThresholdExchangeEntryRecord(
                uplink_fields_per_client=(),
                downlink_fields_per_client=(),
                candidate_grid_downlink_fields_per_client=(),
                candidate_grid_uplink_fields_per_client_per_candidate=(),
            ),
        ),
        candidate_grid_payload="",
        model_exchange=ModelExchangeRecord(
            field_width="float32",
            directions=directions,
            bytes_per_round_formula="",
        ),
        checkpoint_storage=CheckpointStorageRecord(
            contents=("model_parameters",),
            model_parameter_bytes_formula="parameter_count * bytes_per_param",
        ),
    )


def test_resource_cost_respects_encoding_width_and_directions() -> None:

    contract_4bytes_2dirs = _build_dummy_contract(bytes_per_field=4, direction_count=2)
    contract_8bytes_1dir = _build_dummy_contract(bytes_per_field=8, direction_count=1)

    spec = ResourceCostAnalysisRecord(
        label="resource_test",
        kind="resource_cost",
        result_type="resource_cost_analysis_result",
        statistical_profile=StatisticalProfileId("resource_cost_profile"),
        estimate_basis="communication_contract",
        source_evaluations=("eval_1",),
        produced_fields=("threshold",),
    )

    artifacts = MagicMock()
    # Mock calibration scores frame with 10 clients
    calibration_frame = MagicMock()
    calibration_frame.__getitem__.return_value.n_unique.return_value = 10
    artifacts.calibration_scores.return_value = calibration_frame
    artifacts.checkpoint_parameter_count.return_value = 1000

    policy_mock = MagicMock(spec=SharedMeanThresholdPolicyRecord)
    policy_mock.policy = "shared_threshold"

    eval_spec = EvaluationSpecRecord(
        label="eval_1",
        population_id=PopulationId("pop_1"),
        recalibration_mode=RecalibrationMode.FROZEN,
        threshold_policy_id=ThresholdPolicyId("pol_1"),
        run_requirement=RunRequirement.MANDATORY,
        overrides=None,
    )
    exp = MagicMock(spec=ExperimentRecord)
    exp.identifier = ExperimentId("exp_1")
    exp.evaluations = (eval_spec,)
    exp.population_ids = (PopulationId("pop_1"),)

    ctx1 = AnalysisExecutionContext.model_construct(
        threshold_policies={ThresholdPolicyId("pol_1"): policy_mock},
        seed_cohort=MagicMock(),
        metric_definitions=MagicMock(),
        operational_inputs=MagicMock(),
        communication_estimation_contract=contract_4bytes_2dirs,
        artifacts=artifacts,
        experiment=exp,
        seeds=(Seed(1),),
        statistical_analysis=MagicMock(),
    )

    res1 = analyze_resource_cost(spec, ctx1)[0]
    eval_res1 = res1.seed_results[0].evaluations[0]

    # model_bytes = direction_count (2) * client_count (10) * parameters (1000) * bytes_per_param (4) = 80,000
    assert eval_res1.estimated_model_exchange_bytes_per_round == 80000
    # checkpoint_bytes = parameters (1000) * bytes_per_param (4) = 4000
    assert eval_res1.estimated_checkpoint_storage_bytes == 4000

    # Now change contract to 8 bytes and 1 direction
    ctx2 = AnalysisExecutionContext.model_construct(
        threshold_policies={ThresholdPolicyId("pol_1"): policy_mock},
        seed_cohort=MagicMock(),
        metric_definitions=MagicMock(),
        operational_inputs=MagicMock(),
        communication_estimation_contract=contract_8bytes_1dir,
        artifacts=artifacts,
        experiment=exp,
        seeds=(Seed(1),),
        statistical_analysis=MagicMock(),
    )

    res2 = analyze_resource_cost(spec, ctx2)[0]
    eval_res2 = res2.seed_results[0].evaluations[0]

    # model_bytes = direction_count (1) * client_count (10) * parameters (1000) * bytes_per_param (8) = 80,000
    assert eval_res2.estimated_model_exchange_bytes_per_round == 80000
    # checkpoint_bytes = parameters (1000) * bytes_per_param (8) = 8000
    assert eval_res2.estimated_checkpoint_storage_bytes == 8000
