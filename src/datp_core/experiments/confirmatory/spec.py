"""Sole confirmatory DATP-Core endpoint and paired-inference specification."""

from enum import StrEnum
from typing import Literal

from pydantic import model_validator

from datp_core.analysis.inference.contracts import (
    PairedInferenceProtocol,
    WilcoxonAlternative,
    WilcoxonComputationPreference,
    WilcoxonZeroMethod,
)
from datp_core.core.contracts import StrictModel
from datp_core.core.identifiers import (
    EffectSizeId,
    EvidenceRole,
    ExperimentId,
    ExperimentReadiness,
    FederatedThresholdMethod,
    IntervalMethod,
    MetricId,
    MultiplicityCorrectionId,
    PopulationId,
    PreprocessingProtocolId,
    StatisticalTestId,
    TrainingModelId,
)
from datp_core.core.numeric import BootstrapReplicateCount, ConfidenceLevel, Ratio
from datp_core.experiments.common.coordinates import ExperimentSpec
from datp_core.experiments.common.seeds import (
    CONFIRMATORY_ANALYSIS_SEED,
    CONFIRMATORY_PAIRED_SEED_COUNT,
    CONFIRMATORY_SEED_COHORT,
    SeedCohort,
)
from datp_core.protocols.metrics import CONFIRMATORY_METRICS


class ConfirmatoryDeltaDirection(StrEnum):
    SHARED_MINUS_LOCAL = "shared_minus_local"


CONFIRMATORY_EXPERIMENT = ExperimentSpec(
    id=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
    role=EvidenceRole.CONFIRMATORY,
    population=PopulationId.NBAIOT_NATURAL_DEVICES,
    training_model=TrainingModelId.FEDAVG_AUTOENCODER,
    preprocessing_protocol=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
    federated_thresholds=(
        FederatedThresholdMethod.SHARED_THRESHOLD,
        FederatedThresholdMethod.LOCAL_THRESHOLD,
    ),
    metrics=CONFIRMATORY_METRICS,
    readiness=ExperimentReadiness.DECLARED,
)

CONFIRMATORY_INFERENCE_PROTOCOL = PairedInferenceProtocol(
    confidence_level=ConfidenceLevel(0.95),
    paired_seed_count=CONFIRMATORY_PAIRED_SEED_COUNT,
    interval_method=IntervalMethod.BCA_PAIRED_ARITHMETIC_MEAN,
    bootstrap_replicates=BootstrapReplicateCount(10_000),
    statistical_test=StatisticalTestId.WILCOXON_SIGNED_RANK,
    wilcoxon_alternative=WilcoxonAlternative.TWO_SIDED,
    wilcoxon_zero_method=WilcoxonZeroMethod.PRATT,
    wilcoxon_computation_preference=WilcoxonComputationPreference.EXACT_PREFERRED,
    effect_size=EffectSizeId.MATCHED_PAIRS_RANK_BISERIAL,
    multiplicity_correction=MultiplicityCorrectionId.HOLM,
    descriptive_lower_quantile=Ratio(0.25),
    descriptive_upper_quantile=Ratio(0.75),
)


class ConfirmatoryEndpoint(StrictModel):
    experiment: Literal[ExperimentId.SHARED_VS_LOCAL_CONFIRMATION]
    population: Literal[PopulationId.NBAIOT_NATURAL_DEVICES]
    training_model: Literal[TrainingModelId.FEDAVG_AUTOENCODER]
    preprocessing_protocol: Literal[PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD]
    shared_threshold: Literal[FederatedThresholdMethod.SHARED_THRESHOLD]
    local_threshold: Literal[FederatedThresholdMethod.LOCAL_THRESHOLD]
    metric: Literal[MetricId.FPR_COEFFICIENT_OF_VARIATION]
    seed_cohort: SeedCohort
    positive_direction: Literal[ConfirmatoryDeltaDirection.SHARED_MINUS_LOCAL]
    inference_protocol: PairedInferenceProtocol

    @model_validator(mode="after")
    def validate_endpoint(self) -> "ConfirmatoryEndpoint":
        if self.seed_cohort != CONFIRMATORY_SEED_COHORT:
            raise ValueError("confirmatory endpoint requires the exact paired ten-seed cohort")
        if self.inference_protocol.paired_seed_count != self.seed_cohort.member_count:
            raise ValueError("confirmatory inference pair count must match the seed cohort")
        return self


CONFIRMATORY_ENDPOINT = ConfirmatoryEndpoint(
    experiment=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
    population=PopulationId.NBAIOT_NATURAL_DEVICES,
    training_model=TrainingModelId.FEDAVG_AUTOENCODER,
    preprocessing_protocol=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
    shared_threshold=FederatedThresholdMethod.SHARED_THRESHOLD,
    local_threshold=FederatedThresholdMethod.LOCAL_THRESHOLD,
    metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
    seed_cohort=CONFIRMATORY_SEED_COHORT,
    positive_direction=ConfirmatoryDeltaDirection.SHARED_MINUS_LOCAL,
    inference_protocol=CONFIRMATORY_INFERENCE_PROTOCOL,
)

CONFIRMATORY_BOOTSTRAP_SEED = CONFIRMATORY_ANALYSIS_SEED
