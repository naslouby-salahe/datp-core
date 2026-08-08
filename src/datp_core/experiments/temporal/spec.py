"""Immutable temporal score, deployment provenance, and decision contracts."""

from pydantic import model_validator

from datp_core.artifacts.provenance import Checksum
from datp_core.artifacts.serializers.json import canonical_checksum
from datp_core.core.contracts import StrictModel
from datp_core.core.errors import ScientificContractError, UnresolvedScientificValueError
from datp_core.core.identifiers import EvidenceRole, PartitionRole, SplitProtocolId, TemporalState
from datp_core.core.numeric import MetricValue, Ratio
from datp_core.protocols.inference import ClientIdentityContract, ScoreArtifactManifest, TrainingCoordinateContract
from datp_core.protocols.seeds import SeedCohort


class TemporalFutureIdentity(StrictModel):
    split_protocol: SplitProtocolId
    evaluation_role: PartitionRole
    coordinate_checksum: Checksum
    checkpoint_checksum: Checksum
    preprocessing_state_set_checksum: Checksum
    split_manifest_checksum: Checksum
    evaluation_score_set_checksum: Checksum


class TemporalDeploymentProvenance(StrictModel):
    """Immutable calibration/evaluation binding for one temporal deployment state."""

    state: TemporalState
    split_protocol: SplitProtocolId
    calibration_role: PartitionRole
    evaluation_role: PartitionRole
    coordinate_checksum: Checksum
    checkpoint_checksum: Checksum
    preprocessing_state_set_checksum: Checksum
    split_manifest_checksum: Checksum
    calibration_score_set_checksum: Checksum
    evaluation_score_set_checksum: Checksum

    @model_validator(mode="after")
    def validate_binding(self) -> "TemporalDeploymentProvenance":
        if (self.calibration_role, self.evaluation_role) != temporal_partition_roles(self.state):
            raise ValueError("temporal deployment state has an invalid partition binding")
        if self.split_protocol is not temporal_split_protocol(self.state):
            raise ValueError(f"{self.state.name.lower()} requires its designated split protocol")
        return self

    @property
    def future_identity(self) -> TemporalFutureIdentity:
        return TemporalFutureIdentity(
            split_protocol=self.split_protocol,
            evaluation_role=self.evaluation_role,
            coordinate_checksum=self.coordinate_checksum,
            checkpoint_checksum=self.checkpoint_checksum,
            preprocessing_state_set_checksum=self.preprocessing_state_set_checksum,
            split_manifest_checksum=self.split_manifest_checksum,
            evaluation_score_set_checksum=self.evaluation_score_set_checksum,
        )

    @classmethod
    def from_score_manifest[CoordinateT: TrainingCoordinateContract, ClientT: ClientIdentityContract](
        cls,
        state: TemporalState,
        manifest: ScoreArtifactManifest[CoordinateT, ClientT],
    ) -> "TemporalDeploymentProvenance":
        calibration_role, evaluation_role = temporal_partition_roles(state)
        if not manifest.records_for(calibration_role) or not manifest.records_for(evaluation_role):
            raise ScientificContractError(
                "temporal provenance requires non-empty calibration and evaluation score sets",
                subject=state,
            )
        return cls(
            state=state,
            split_protocol=manifest.scored_split_protocol,
            calibration_role=calibration_role,
            evaluation_role=evaluation_role,
            coordinate_checksum=canonical_checksum(manifest.coordinate),
            checkpoint_checksum=manifest.checkpoint_checksum,
            preprocessing_state_set_checksum=manifest.preprocessing_state_set_checksum,
            split_manifest_checksum=manifest.split_manifest_checksum,
            calibration_score_set_checksum=manifest.score_set_checksum(calibration_role),
            evaluation_score_set_checksum=manifest.score_set_checksum(evaluation_role),
        )

    def validate_score_manifest[
        CoordinateT: TrainingCoordinateContract,
        ClientT: ClientIdentityContract,
    ](
        self,
        manifest: ScoreArtifactManifest[CoordinateT, ClientT],
    ) -> None:
        if TemporalDeploymentProvenance.from_score_manifest(self.state, manifest) != self:
            raise ScientificContractError(
                "temporal deployment provenance does not match immutable score artifacts",
                subject=self.state,
                reason="calibration, evaluation, model, preprocessing, or split evidence changed",
            )


def validate_frozen_recalibrated_pair(
    frozen: TemporalDeploymentProvenance,
    recalibrated: TemporalDeploymentProvenance,
) -> None:
    """Require identical future detector and evaluation evidence across recalibration states."""
    if frozen.state is not TemporalState.FROZEN_FUTURE or recalibrated.state is not TemporalState.RECALIBRATED_FUTURE:
        raise ScientificContractError(
            "temporal comparison requires frozen and recalibrated future states",
            subject=EvidenceRole.TEMPORAL_BOUNDARY,
        )
    if frozen.future_identity != recalibrated.future_identity:
        raise ScientificContractError(
            "frozen and recalibrated future must share detector, split, and evaluation scores",
            subject=EvidenceRole.TEMPORAL_BOUNDARY,
        )


def temporal_partition_roles(state: TemporalState) -> tuple[PartitionRole, PartitionRole]:
    match state:
        case TemporalState.STATIC_REFERENCE | TemporalState.FROZEN_FUTURE:
            return PartitionRole.CALIBRATION, PartitionRole.EVALUATION
        case TemporalState.RECALIBRATED_FUTURE:
            return PartitionRole.FUTURE_RECALIBRATION, PartitionRole.EVALUATION
    raise ValueError(f"unsupported temporal state: {state}")


def temporal_split_protocol(state: TemporalState) -> SplitProtocolId:
    match state:
        case TemporalState.STATIC_REFERENCE:
            return SplitProtocolId.RANDOM_FRACTIONAL_STATIC_REFERENCE
        case TemporalState.FROZEN_FUTURE | TemporalState.RECALIBRATED_FUTURE:
            return SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE
    raise ValueError(f"unsupported temporal state: {state}")


class TemporalDecisionProtocol(StrictModel):
    """Explicit temporal interpretation thresholds and publication guards."""

    drift_excess_materiality_threshold: MetricValue
    material_recovery_ratio_minimum: Ratio
    seed_cohort: SeedCohort
    undefined_recovery_when_drift_not_material: bool
    mixed_seed_publication_support: bool
    require_full_seed_provenance: bool
    require_uncertainty_for_supported: bool

    @model_validator(mode="after")
    def validate_protocol(self) -> "TemporalDecisionProtocol":
        if self.drift_excess_materiality_threshold.value <= 0.0:
            raise ValueError("temporal drift-excess materiality threshold must be positive")
        if self.material_recovery_ratio_minimum.value <= 0.0:
            raise ValueError("temporal material recovery-ratio minimum must be positive")
        if self.seed_cohort.member_count.value < 2:
            raise ValueError("temporal publication decisions require a multi-seed cohort")
        if not self.undefined_recovery_when_drift_not_material:
            raise ValueError("temporal protocol must leave recovery undefined when drift is non-material")
        if self.mixed_seed_publication_support:
            raise ValueError("mixed-seed temporal evidence cannot support a publication claim")
        if not self.require_full_seed_provenance:
            raise ValueError("temporal publication requires full per-seed provenance")
        return self


def require_temporal_decision_protocol() -> TemporalDecisionProtocol:
    raise UnresolvedScientificValueError(
        "the master roadmap requires a pre-specified positive drift-excess materiality threshold and a criterion "
        "for a meaningful recovery portion, but does not declare either numeric value",
        subject=EvidenceRole.TEMPORAL_BOUNDARY,
    )
