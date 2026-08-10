"""Checkpoint protocol declarations and authoritative non-test selection rule."""

from collections.abc import Sequence

from datp_core.core.errors import (
    ErrorMessage,
    LeakageError,
    ScientificContractError,
)
from datp_core.core.identifiers import (
    CheckpointSelectionRule,
    CheckpointStatus,
    ContractSubject,
    ProcessedDataBranch,
)
from datp_core.core.numeric import MetricValue, RoundNumber
from datp_core.detector.checkpoints.contracts import CheckpointProtocol, ConvergenceProtocol

CHECKPOINT_PROTOCOL = CheckpointProtocol(
    candidates=tuple(RoundNumber(value) for value in (25, 50, 75, 100, 125, 150, 200)),
    maximum_round=RoundNumber(200),
)
CHECKPOINT_SELECTION_RULE = CheckpointSelectionRule.FIXED_TERMINAL_MAXIMUM_ROUND
ANCHOR_CHECKPOINT_PROTOCOL = CheckpointProtocol(
    candidates=(RoundNumber(150),),
    maximum_round=RoundNumber(150),
    convergence=ConvergenceProtocol(
        rounds_initial=RoundNumber(40),
        relative_threshold=0.005,
        window=10,
    ),
)
ANCHOR_CHECKPOINT_SELECTION_RULE = CheckpointSelectionRule.FINAL_COMPLETED_ROUND
RETAINED_CHECKPOINT_STATUSES = frozenset(
    {
        CheckpointStatus.CANDIDATE,
        CheckpointStatus.STABILITY_EVIDENCE,
        CheckpointStatus.SELECTED_BY_NON_TEST_RULE,
    }
)


def require_non_test_checkpoint_selection_inputs(
    *,
    selection_rule: CheckpointSelectionRule,
    held_out_metrics: Sequence[MetricValue] | None,
    attack_labels_present: bool,
    branch: ProcessedDataBranch,
) -> None:
    """Reject test leakage and unsupported selection rules before branch-specific selection."""
    if held_out_metrics is not None:
        raise LeakageError(
            ErrorMessage(f"held-out evaluation outcomes cannot influence {branch.value} checkpoint selection"),
            subject=ContractSubject.HELD_OUT_METRICS,
        )
    if attack_labels_present:
        raise LeakageError(
            ErrorMessage(f"attack labels cannot influence {branch.value} checkpoint selection"),
            subject=ContractSubject.ATTACK_LABELS,
        )
    if selection_rule not in (
        CheckpointSelectionRule.FIXED_TERMINAL_MAXIMUM_ROUND,
        CheckpointSelectionRule.FINAL_COMPLETED_ROUND,
    ):
        raise ScientificContractError(
            ErrorMessage(f"unsupported {branch.value} checkpoint selection rule"),
            subject=ContractSubject.CHECKPOINT_SELECTION_RULE,
        )
