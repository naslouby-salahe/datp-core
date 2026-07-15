from dataclasses import dataclass
from enum import StrEnum


class FeasibilityStatus(StrEnum):
    FEASIBLE = "feasible"
    GATED = "gated"
    PENDING_VERIFICATION = "pending_verification"
    REJECTED = "rejected"


class RejectionReason(StrEnum):
    B_B_NO_METADATA = "B_B_REJECTED_NO_METADATA"
    TEMPORAL_NO_TIMESTAMPS = "TEMPORAL_REJECTED_NO_TIMESTAMPS"
    FEDBN_NO_BATCHNORM = "fedbn_no_batchnorm"
    LARIDI_ANOMALY_LABELED = "laridi_anomaly_labeled"
    MIA_NO_LITERATURE = "mia_no_literature"
    STREAMING_DRIFT_SCOPE = "streaming_drift_scope"
    BYZANTINE_CONFORMAL_SCOPE = "byzantine_conformal_scope"
    BROAD_PFL_LIMIT = "broad_pfl_limit"


class ReuseIncompatibilityReason(StrEnum):
    SOURCE_MISMATCH = "source_mismatch"
    SCHEMA_MISMATCH = "schema_mismatch"
    PARTITION_MISMATCH = "partition_mismatch"
    SPLIT_MISMATCH = "split_mismatch"
    PREPROCESSOR_MISMATCH = "preprocessor_mismatch"
    TRAINING_MISMATCH = "training_mismatch"
    CHECKPOINT_MISMATCH = "checkpoint_mismatch"
    SCORING_MISMATCH = "scoring_mismatch"
    SCORE_SCHEMA_MISMATCH = "score_schema_mismatch"
    CLIENT_ROSTER_MISMATCH = "client_roster_mismatch"
    ROW_ORDER_MISMATCH = "row_order_mismatch"
    PRECISION_MISMATCH = "precision_mismatch"
    BATCH_PROFILE_MISMATCH = "batch_profile_mismatch"


class BlockingReason(StrEnum):
    MISSING_SOURCE = "missing_source"
    FAILED_ANCHOR_GATE = "failed_anchor_gate"
    FAILED_FEASIBILITY = "failed_feasibility"
    UNRESOLVED_SCIENTIFIC_DECISION = "unresolved_scientific_decision"
    INVALID_LINEAGE = "invalid_lineage"
    REQUIRED_HARDWARE_UNAVAILABLE = "required_hardware_unavailable"
    INSUFFICIENT_STORAGE = "insufficient_storage"


@dataclass(frozen=True, slots=True, kw_only=True)
class ScientificReadinessResult:
    blockers: tuple[BlockingReason, ...]

    def __post_init__(self) -> None:
        if any(type(reason) is not BlockingReason for reason in self.blockers) or len(set(self.blockers)) != len(
            self.blockers
        ):
            from datp_core.domain.errors import DomainValidationError

            raise DomainValidationError(
                detail="scientific readiness must retain each typed blocker exactly once",
                value=repr(self.blockers),
                constraint="unique tuple[BlockingReason, ...]",
            )

    @property
    def is_ready(self) -> bool:
        return not self.blockers
