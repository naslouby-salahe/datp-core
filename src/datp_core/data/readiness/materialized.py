"""Sole materialized-dataset readiness implementation."""

from __future__ import annotations

from datp_core.data.contracts.enums import (
    AuditIssueCode,
    AuditSeverity,
    DatasetCapability,
    MaterializedArtifactShape,
    SplitMembership,
)
from datp_core.data.contracts.materialization import (
    ChronologicalGappedSplitConfig,
    RandomFractionalSplitConfig,
    WithinClientChronologicalSplitConfig,
)
from datp_core.data.manifests.summary import MaterializedSplitSummary
from datp_core.data.materialization.models import DatasetMaterializationPlan
from datp_core.data.readiness.models import DatasetAuditIssue, MaterializedAuditReport


def assess_materialized_readiness(
    plan: DatasetMaterializationPlan,
    summary: MaterializedSplitSummary,
) -> MaterializedAuditReport:
    issues: list[DatasetAuditIssue] = []
    if summary.total_rows == 0:
        issues.append(_blocking(AuditIssueCode.MATERIALIZED_EMPTY, "materialized dataset is empty"))
    observed_memberships = tuple(count.membership for count in summary.split_counts)
    for membership in _required_memberships(plan):
        if membership.value not in observed_memberships:
            issues.append(
                _blocking(
                    AuditIssueCode.REQUIRED_SPLIT_MISSING,
                    f"required split membership '{membership.value}' is absent",
                )
            )
    if len(summary.client_ids) != plan.expected_client_count:
        issues.append(
            _blocking(
                AuditIssueCode.CLIENT_COUNT_MISMATCH,
                f"observed {len(summary.client_ids)} clients; expected {plan.expected_client_count}",
            )
        )
    if summary.ineligible_client_ids:
        excluded = plan.eligibility.exclude_ineligible_clients_from_primary_dispersion
        issues.append(
            DatasetAuditIssue(
                code=AuditIssueCode.BENIGN_CALIBRATION_INSUFFICIENT,
                severity=AuditSeverity.WARNING if excluded else AuditSeverity.BLOCKING,
                detail=(
                    "clients below the configured benign calibration minimum"
                    + (" and excluded from primary dispersion: " if excluded else ": ")
                    + ", ".join(summary.ineligible_client_ids)
                ),
            )
        )
    attack_capability = DatasetCapability.ATTACK_EVALUATION in plan.capabilities
    if attack_capability and summary.attack_rows == 0:
        issues.append(
            _blocking(
                AuditIssueCode.ATTACK_CAPABILITY_MISMATCH,
                "attack evaluation is declared but the artifact contains no attack rows",
            )
        )
    if not attack_capability and summary.attack_rows != 0:
        issues.append(
            _blocking(
                AuditIssueCode.ATTACK_CAPABILITY_MISMATCH,
                "artifact contains attack rows although attack evaluation is not declared",
            )
        )
    temporal_capability = DatasetCapability.TEMPORAL_RECALIBRATION in plan.capabilities
    temporal_shape = summary.artifact_shape == MaterializedArtifactShape.EDGE_BENIGN_TEMPORAL.value
    if temporal_capability != temporal_shape:
        issues.append(
            _blocking(
                AuditIssueCode.TEMPORAL_CAPABILITY_MISMATCH,
                "temporal capability and materialized artifact shape disagree",
            )
        )
    if temporal_shape:
        issues.extend(_chronology_issues(summary))
    if plan.eligibility.require_non_empty_benign_test:
        test_membership = SplitMembership.FUTURE_EVALUATION if temporal_shape else SplitMembership.TEST
        for client_id in summary.client_ids:
            if _benign_count(summary, client_id, test_membership) == 0:
                issues.append(
                    _blocking(
                        AuditIssueCode.REQUIRED_SPLIT_MISSING,
                        f"client '{client_id}' has no benign rows in '{test_membership.value}'",
                    )
                )
    if not summary.eligible_client_ids and plan.eligibility.zero_eligible_clients_is_blocking:
        issues.append(
            _blocking(
                AuditIssueCode.BENIGN_CALIBRATION_INSUFFICIENT,
                "no client satisfies the configured eligibility policy",
            )
        )
    return MaterializedAuditReport(issues=tuple(issues))


def _required_memberships(plan: DatasetMaterializationPlan) -> tuple[SplitMembership, ...]:
    split = plan.split
    if isinstance(split, RandomFractionalSplitConfig):
        return tuple(membership for membership, _ in split.ratios.ordered())
    if isinstance(split, ChronologicalGappedSplitConfig):
        return (
            SplitMembership.TRAIN,
            SplitMembership.CALIBRATION,
            SplitMembership.TEST,
        )
    if isinstance(split, WithinClientChronologicalSplitConfig):
        return (
            SplitMembership.HISTORICAL_TRAINING,
            SplitMembership.HISTORICAL_CALIBRATION,
            SplitMembership.FUTURE_RECALIBRATION,
            SplitMembership.FUTURE_EVALUATION,
        )
    raise TypeError(f"unsupported split contract: {type(split).__name__}")


def _chronology_issues(summary: MaterializedSplitSummary) -> tuple[DatasetAuditIssue, ...]:
    issues: list[DatasetAuditIssue] = []
    for chronology in summary.chronology_ranges:
        total = sum(count.row_count for count in summary.client_split_counts if count.client_id == chronology.client_id)
        if chronology.minimum_key != 0 or chronology.maximum_key != total - 1:
            issues.append(
                _blocking(
                    AuditIssueCode.CHRONOLOGY_ORDER_VIOLATION,
                    f"client '{chronology.client_id}' chronology keys are not contiguous from zero",
                )
            )
    return tuple(issues)


def _benign_count(
    summary: MaterializedSplitSummary,
    client_id: str,
    membership: SplitMembership,
) -> int:
    for count in summary.client_split_counts:
        if count.client_id == client_id and count.membership == membership.value:
            return count.benign_count
    return 0


def _blocking(code: AuditIssueCode, detail: str) -> DatasetAuditIssue:
    return DatasetAuditIssue(code=code, severity=AuditSeverity.BLOCKING, detail=detail)
