"""Checkpoint protocol declarations and authoritative non-test selection rule."""

from collections.abc import Sequence

from datp_core.core.errors import LeakageError, ScientificContractError
from datp_core.core.identifiers import (
    CheckpointSelectionRule,
    CheckpointStatus,
    ContractSubject,
)
from datp_core.core.numeric import MetricValue, RoundNumber
from datp_core.detector.checkpoints.contracts import CheckpointProtocol

CHECKPOINT_PROTOCOL = CheckpointProtocol(
    candidates=tuple(RoundNumber(value) for value in (25, 50, 75, 100, 125, 150, 200)),
    maximum_round=RoundNumber(200),
)
CHECKPOINT_SELECTION_RULE = CheckpointSelectionRule.FIXED_TERMINAL_MAXIMUM_ROUND


def require_non_test_checkpoint_selection_inputs(
    *,
    selection_rule: CheckpointSelectionRule,
    held_out_metrics: Sequence[MetricValue] | None,
    attack_labels_present: bool,
    branch_label: str, #TODO:should be a class. Check what already exists. Do not use primitives for this, use something else. Check what already exists
) -> None:
    """Reject test leakage and unsupported selection rules before branch-specific selection."""
    if held_out_metrics is not None:
        raise LeakageError(
            f"held-out evaluation outcomes cannot influence {branch_label} checkpoint selection",
            subject=ContractSubject.HELD_OUT_METRICS,
        )
    if attack_labels_present:
        raise LeakageError(
            f"attack labels cannot influence {branch_label} checkpoint selection",
            subject=ContractSubject.ATTACK_LABELS,
        )
    if selection_rule is not CheckpointSelectionRule.FIXED_TERMINAL_MAXIMUM_ROUND:
        raise ScientificContractError(
            f"unsupported {branch_label} checkpoint selection rule",
            subject=ContractSubject.CHECKPOINT_SELECTION_RULE,
        )


def fixed_terminal_checkpoint_status(
    round_number: RoundNumber,
    maximum_round: RoundNumber,
) -> CheckpointStatus:
    """Map a candidate round onto FIXED_TERMINAL_MAXIMUM_ROUND statuses."""
    if round_number == maximum_round:
        return CheckpointStatus.SELECTED_BY_NON_TEST_RULE
    return CheckpointStatus.STABILITY_EVIDENCE
