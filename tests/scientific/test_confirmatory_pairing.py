from datp_core.analysis.contrasts import FixedScorePairProvenance, PairedContrast
from datp_core.analysis.inference.bootstrap.contracts import BcaOutcome
from datp_core.analysis.inference.bootstrap.estimation import paired_bca_interval
from datp_core.analysis.preparation import ConfirmatoryAnalysisRequest, prepare_confirmatory_analysis
from datp_core.artifacts.provenance import Checksum
from datp_core.core.identifiers import (
    AvailabilityStatus,
    EvidenceRole,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    PreprocessingProtocolId,
    SplitProtocolId,
    TrainingModelId,
)
from datp_core.core.numeric import MetricValue, Seed
from datp_core.detector.training.contracts import FederatedTrainingCoordinate
from datp_core.experiments.confirmatory.spec import CONFIRMATORY_INFERENCE_PROTOCOL


def test_confirmatory_bca_blocks_nine_pairs() -> None:
    result = paired_bca_interval(
        tuple(_contrast(seed) for seed in range(9)),
        protocol=CONFIRMATORY_INFERENCE_PROTOCOL,
        analysis_seed=Seed(17),
    )
    assert result.outcome is BcaOutcome.BLOCKED
    assert result.point_estimate is not None


def test_pairing_rejects_a_seed_independent_design_change() -> None:
    values = [_contrast(seed) for seed in range(10)]
    changed = values[-1]
    values[-1] = changed.model_copy(
        update={
            "coordinate": FederatedTrainingCoordinate(
                population=changed.coordinate.population,
                training_seed=changed.coordinate.training_seed,
                split_protocol=changed.coordinate.split_protocol,
                preprocessing_identity=PreprocessingProtocolId.FEDERATED_POOLED_MIN_MAX,
                model=changed.coordinate.model,
                model_coefficient=None,
            )
        }
    )
    result = paired_bca_interval(
        tuple(values),
        protocol=CONFIRMATORY_INFERENCE_PROTOCOL,
        analysis_seed=Seed(17),
    )
    assert result.outcome is BcaOutcome.BLOCKED


def test_invalid_contrasts_block_all_dependent_statistics() -> None:
    document = prepare_confirmatory_analysis(
        ConfirmatoryAnalysisRequest(
            contrasts=tuple(_contrast(seed) for seed in range(9)),
            inference_protocol=CONFIRMATORY_INFERENCE_PROTOCOL,
            analysis_seed=Seed(17),
        )
    )
    assert document.decision.decision.value == "blocked"
    assert document.wilcoxon.availability is AvailabilityStatus.UNAVAILABLE
    assert document.rank_biserial.availability is AvailabilityStatus.UNAVAILABLE
    assert document.multiplicity_result is None
    assert document.unavailable_reason is not None


def _fixed_score() -> FixedScorePairProvenance:
    checksum = Checksum("b" * 64)
    return FixedScorePairProvenance(
        model_checksum=checksum,
        preprocessing_checksum=checksum,
        selected_checkpoint_checksum=checksum,
        split_manifest_checksum=checksum,
        calibration_score_checksum=checksum,
        evaluation_score_checksum=checksum,
        evaluation_label_checksum=checksum,
        source_row_checksum=checksum,
        score_order_checksum=checksum,
        client_inventory_checksum=checksum,
        eligibility_cohort_checksum=checksum,
    )


def _contrast(seed: int) -> PairedContrast:
    return PairedContrast(
        coordinate=FederatedTrainingCoordinate(
            population=PopulationId.NBAIOT_NATURAL_DEVICES,
            training_seed=Seed(seed),
            split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
            preprocessing_identity=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
            model=TrainingModelId.FEDAVG_AUTOENCODER,
            model_coefficient=None,
        ),
        evidence_role=EvidenceRole.CONFIRMATORY,
        metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
        left_method=FederatedThresholdMethod.SHARED_THRESHOLD,
        right_method=FederatedThresholdMethod.LOCAL_THRESHOLD,
        left_value=MetricValue(0.03 + seed / 10_000),
        right_value=MetricValue(0.02),
        fixed_score=_fixed_score(),
    )
