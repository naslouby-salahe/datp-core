"""Resolved scientific protocol graph contract."""

from datp_core.domain.enums import ExperimentId
from datp_core.protocols.anchor_contracts import AnchorDecisionProtocol, ConfirmatoryEndpoint
from datp_core.protocols.models import (
    CalibrationEligibilityProtocol,
    CheckpointProtocol,
    ClusterThresholdProtocol,
    Declaration,
    ExperimentDeclaration,
    FedAvgProtocol,
    PopulationDeclaration,
    StatisticalInferenceProtocol,
    TrafficRateEvidence,
)
from datp_core.protocols.splits import FractionalSplitProtocol, StaticReferenceSplitProtocol, TemporalSplitProtocol


class ResolvedProtocolGraph(Declaration):
    populations: tuple[PopulationDeclaration, ...]
    experiments: tuple[ExperimentDeclaration, ...]
    suppressed_experiment_ids: tuple[ExperimentId, ...]
    temporal_split: TemporalSplitProtocol
    static_reference_split: StaticReferenceSplitProtocol
    non_temporal_split: FractionalSplitProtocol
    checkpoint: CheckpointProtocol
    calibration: CalibrationEligibilityProtocol
    confirmatory_endpoint: ConfirmatoryEndpoint
    confirmatory_inference: StatisticalInferenceProtocol
    anchor: AnchorDecisionProtocol
    traffic_rate_evidence: tuple[TrafficRateEvidence, ...]
    cluster_threshold: ClusterThresholdProtocol
    fedavg_training: FedAvgProtocol
