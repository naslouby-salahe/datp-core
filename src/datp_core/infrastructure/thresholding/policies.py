from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from datp_core.application.ports.thresholding import (
    AssignThresholdRequest,
    ConstructThresholdsRequest,
    ThresholdConstructionResult,
    ThresholdConstructor,
    ThresholdStrategy,
)
from datp_core.domain.errors import ThresholdError
from datp_core.domain.experiments.identities import ClientId
from datp_core.domain.learning.scores import ClientMap, ClientMapEntry, ThresholdAssignmentSet
from datp_core.domain.mathematics.quantiles import exact_quantile, exact_weighted_quantile
from datp_core.domain.thresholding.clustering import ClusterAssignmentArtifact
from datp_core.domain.thresholding.policies import (
    ClusterThresholdSpec,
    CoreThresholdPolicy,
    FamilyThresholdSpec,
    LocalThresholdSpec,
    SharedThresholdConstruction,
    SharedThresholdSpec,
    ThresholdAssignment,
    ThresholdPercentile,
    ThresholdValue,
    unweighted_shared_threshold,
)
from datp_core.infrastructure.thresholding.quantiles import CalibrationScoreReader


class FamilyMembershipReader(Protocol):
    def members(self, *, family_manifest: str, client_id: ClientId) -> tuple[ClientId, ...]: ...


class ClusterAssignmentReader(Protocol):
    def read(self, *, assignment_identity: str) -> ClusterAssignmentArtifact: ...


@dataclass(frozen=True, slots=True, kw_only=True)
class SharedThresholdStrategy(ThresholdStrategy):
    reader: CalibrationScoreReader

    def assign(self, request: AssignThresholdRequest) -> ThresholdAssignment:
        specification = request.construction
        if type(specification) is not SharedThresholdSpec:
            raise unexpected_construction(request)
        require_assignment_subject(request=request, expected=CoreThresholdPolicy.B1)
        require_fpr_target(request=request, percentile=specification.percentile)
        local_values = local_threshold_values(request=request, reader=self.reader, percentile=specification.percentile)
        eligible_local = eligible_threshold_values(request=request, local_values=local_values)
        shared_value = _shared_value(
            construction=specification.construction,
            context=_SharedThresholdContext(
                request=request,
                local_values=eligible_local,
                reader=self.reader,
                percentile=specification.percentile,
            ),
        )
        return assignment_from_values(request=request, values=tuple(shared_value for _ in local_values))


@dataclass(frozen=True, slots=True, kw_only=True)
class LocalThresholdStrategy(ThresholdStrategy):
    reader: CalibrationScoreReader

    def assign(self, request: AssignThresholdRequest) -> ThresholdAssignment:
        specification = request.construction
        if type(specification) is not LocalThresholdSpec:
            raise unexpected_construction(request)
        require_assignment_subject(request=request, expected=CoreThresholdPolicy.B2)
        require_fpr_target(request=request, percentile=specification.percentile)
        local_values = local_threshold_values(request=request, reader=self.reader, percentile=specification.percentile)
        fallback = unweighted_shared_threshold(
            local_thresholds=eligible_threshold_values(request=request, local_values=local_values)
        )
        values = tuple(
            local_value if client_id in request.eligible_clients.eligible_clients else fallback
            for client_id, local_value in zip(roster_clients(request), local_values, strict=True)
        )
        return assignment_from_values(request=request, values=values)


@dataclass(frozen=True, slots=True, kw_only=True)
class FamilyThresholdStrategy(ThresholdStrategy):
    reader: CalibrationScoreReader
    family_memberships: FamilyMembershipReader

    def assign(self, request: AssignThresholdRequest) -> ThresholdAssignment:
        specification = request.construction
        if type(specification) is not FamilyThresholdSpec:
            raise unexpected_construction(request)
        require_assignment_subject(request=request, expected=CoreThresholdPolicy.B3)
        require_fpr_target(request=request, percentile=specification.percentile)
        local_values = local_threshold_values(request=request, reader=self.reader, percentile=specification.percentile)
        values_by_client = dict(zip(roster_clients(request), local_values, strict=True))
        fallback = unweighted_shared_threshold(
            local_thresholds=eligible_threshold_values(request=request, local_values=local_values)
        )
        family_context = _FamilyThresholdContext(
            request=request,
            values_by_client=values_by_client,
            fallback=fallback,
            family_memberships=self.family_memberships,
        )
        values = tuple(
            _family_value(
                client_id=client_id,
                specification=specification,
                context=family_context,
            )
            for client_id in roster_clients(request)
        )
        return assignment_from_values(request=request, values=values)


@dataclass(frozen=True, slots=True, kw_only=True)
class ClusterThresholdStrategy(ThresholdStrategy):
    reader: CalibrationScoreReader
    assignments: ClusterAssignmentReader

    def assign(self, request: AssignThresholdRequest) -> ThresholdAssignment:
        specification = request.construction
        if type(specification) is not ClusterThresholdSpec:
            raise unexpected_construction(request)
        require_assignment_subject(request=request, expected=CoreThresholdPolicy.B4)
        require_fpr_target(request=request, percentile=specification.percentile)
        assignment = self.assignments.read(
            assignment_identity=specification.aggregation.cluster_assignment_identity.value
        )
        local_values = local_threshold_values(request=request, reader=self.reader, percentile=specification.percentile)
        values_by_client = dict(zip(roster_clients(request), local_values, strict=True))
        fallback = unweighted_shared_threshold(
            local_thresholds=eligible_threshold_values(request=request, local_values=local_values)
        )
        values = _cluster_mean_values(
            request=request,
            assignment=assignment,
            values_by_client=values_by_client,
            fallback=fallback,
        )
        return assignment_from_values(request=request, values=values)


@dataclass(frozen=True, slots=True, kw_only=True)
class ExactThresholdConstructor(ThresholdConstructor):
    shared: SharedThresholdStrategy
    local: LocalThresholdStrategy
    family: FamilyThresholdStrategy
    cluster: ClusterThresholdStrategy
    variants: ThresholdStrategy
    fed_stats: ThresholdStrategy

    def construct(self, request: ConstructThresholdsRequest) -> ThresholdConstructionResult:
        assign_request = AssignThresholdRequest(
            calibration_scores=request.calibration_scores,
            construction=request.construction,
            eligible_clients=request.eligible_clients,
            assignment_metadata=request.assignment_metadata,
        )
        strategy = _strategy_for(construction=request.construction, constructor=self)
        return ThresholdConstructionResult(assignment=strategy.assign(assign_request))


def _strategy_for(*, construction: object, constructor: ExactThresholdConstructor) -> ThresholdStrategy:
    if type(construction) is SharedThresholdSpec:
        return constructor.shared
    if type(construction) is LocalThresholdSpec:
        return constructor.local
    if type(construction) is FamilyThresholdSpec:
        return constructor.family
    if type(construction) is ClusterThresholdSpec:
        return constructor.cluster
    from datp_core.domain.thresholding.federated_statistics import FedStatsBenignThresholdSpec

    if type(construction) is FedStatsBenignThresholdSpec:
        return constructor.fed_stats
    return constructor.variants


def local_threshold_values(
    *,
    request: AssignThresholdRequest,
    reader: CalibrationScoreReader,
    percentile: ThresholdPercentile,
) -> tuple[ThresholdValue, ...]:
    return tuple(
        ThresholdValue(
            value=exact_quantile(
                values=reader.read(calibration_scores=request.calibration_scores, client_index=index),
                percentile=percentile,
            )
        )
        for index, _ in enumerate(roster_clients(request))
    )


def eligible_threshold_values(
    *, request: AssignThresholdRequest, local_values: tuple[ThresholdValue, ...]
) -> tuple[ThresholdValue, ...]:
    values = tuple(
        value
        for client_id, value in zip(roster_clients(request), local_values, strict=True)
        if client_id in request.eligible_clients.eligible_clients
    )
    if not values:
        raise ThresholdError(
            detail="threshold construction requires eligible calibration clients",
            policy="threshold",
            missing_field="eligible clients",
        )
    return values


def _shared_value(
    *,
    construction: SharedThresholdConstruction,
    context: _SharedThresholdContext,
) -> ThresholdValue:
    if construction is SharedThresholdConstruction.MEAN:
        return unweighted_shared_threshold(local_thresholds=context.local_values)
    scores = _eligible_score_groups(context)
    if construction is SharedThresholdConstruction.POOLED:
        return _pooled_shared_value(scores=scores, percentile=context.percentile)
    return _weighted_shared_value(context=context, scores=scores)


def _eligible_score_groups(context: _SharedThresholdContext) -> tuple[tuple[float, ...], ...]:
    eligible_indexes = tuple(
        index
        for index, client_id in enumerate(roster_clients(context.request))
        if client_id in context.request.eligible_clients.eligible_clients
    )
    return tuple(
        context.reader.read(calibration_scores=context.request.calibration_scores, client_index=index)
        for index in eligible_indexes
    )


def _pooled_shared_value(*, scores: tuple[tuple[float, ...], ...], percentile: ThresholdPercentile) -> ThresholdValue:
    return ThresholdValue(
        value=exact_quantile(
            values=tuple(score for group in scores for score in group),
            percentile=percentile,
        )
    )


def _weighted_shared_value(
    *, context: _SharedThresholdContext, scores: tuple[tuple[float, ...], ...]
) -> ThresholdValue:
    weighted_value = exact_weighted_quantile(
        values=tuple(value.value for value in context.local_values),
        weights=tuple(len(group) for group in scores),
        percentile=context.percentile,
    )
    return ThresholdValue(value=weighted_value)


def _family_value(
    *,
    client_id: ClientId,
    specification: FamilyThresholdSpec,
    context: _FamilyThresholdContext,
) -> ThresholdValue:
    if client_id not in context.request.eligible_clients.eligible_clients:
        return context.fallback
    members = context.family_memberships.members(
        family_manifest=specification.family_manifest_identity.value,
        client_id=client_id,
    )
    local_values = tuple(
        context.values_by_client[member]
        for member in members
        if member in context.request.eligible_clients.eligible_clients
    )
    if not local_values:
        raise ThresholdError(
            detail="family threshold has no eligible family members",
            policy="family",
            missing_field="eligible family",
        )
    return unweighted_shared_threshold(local_thresholds=local_values)


def _cluster_mean_values(
    *,
    request: AssignThresholdRequest,
    assignment: ClusterAssignmentArtifact,
    values_by_client: dict[ClientId, ThresholdValue],
    fallback: ThresholdValue,
) -> tuple[ThresholdValue, ...]:
    members_by_cluster = {
        cluster_index: tuple(
            entry.client_id for entry in assignment.assignments if entry.cluster_index == cluster_index
        )
        for cluster_index in range(3)
    }
    cluster_values = {
        cluster_index: unweighted_shared_threshold(
            local_thresholds=tuple(
                values_by_client[client_id]
                for client_id in members
                if client_id in request.eligible_clients.eligible_clients
            )
        )
        for cluster_index, members in members_by_cluster.items()
        if any(client_id in request.eligible_clients.eligible_clients for client_id in members)
    }
    label_by_client = {entry.client_id: entry.cluster_index for entry in assignment.assignments}
    cluster_context = _ClusterThresholdContext(
        eligible_clients=request.eligible_clients.eligible_clients,
        labels=label_by_client,
        cluster_values=cluster_values,
        fallback=fallback,
    )
    return tuple(
        _cluster_value(
            client_id=client_id,
            context=cluster_context,
        )
        for client_id in roster_clients(request)
    )


def _cluster_value(
    *,
    client_id: ClientId,
    context: _ClusterThresholdContext,
) -> ThresholdValue:
    if client_id not in context.eligible_clients:
        return context.fallback
    label = context.labels.get(client_id)
    if label is None:
        return context.fallback
    return context.cluster_values.get(label, context.fallback)


@dataclass(frozen=True, slots=True, kw_only=True)
class _SharedThresholdContext:
    request: AssignThresholdRequest
    local_values: tuple[ThresholdValue, ...]
    reader: CalibrationScoreReader
    percentile: ThresholdPercentile


@dataclass(frozen=True, slots=True, kw_only=True)
class _FamilyThresholdContext:
    request: AssignThresholdRequest
    values_by_client: dict[ClientId, ThresholdValue]
    fallback: ThresholdValue
    family_memberships: FamilyMembershipReader


@dataclass(frozen=True, slots=True, kw_only=True)
class _ClusterThresholdContext:
    eligible_clients: tuple[ClientId, ...]
    labels: dict[ClientId, int]
    cluster_values: dict[int, ThresholdValue]
    fallback: ThresholdValue


def assignment_from_values(
    *, request: AssignThresholdRequest, values: tuple[ThresholdValue, ...]
) -> ThresholdAssignment:
    roster = request.calibration_scores.per_client.values.roster
    return ThresholdAssignment(
        policy=request.assignment_metadata.policy,
        per_client_tau=ThresholdAssignmentSet(
            values=ClientMap(
                roster=roster,
                entries=tuple(
                    ClientMapEntry(client_id=client_id, value=value)
                    for client_id, value in zip(roster.client_ids, values, strict=True)
                ),
            )
        ),
        calibration_score_artifact_id=request.calibration_scores.artifact_id,
        threshold_identity=request.assignment_metadata.threshold_identity,
        eligible_client_set_identity=request.eligible_clients.identity,
        fallback_fingerprint=request.assignment_metadata.fallback_fingerprint,
    )


def require_assignment_subject(*, request: AssignThresholdRequest, expected: object) -> None:
    if request.assignment_metadata.policy is not expected:
        raise ThresholdError(
            detail="threshold construction must use its declared policy, variant, or comparator identity",
            policy=type(request.construction).__name__,
            missing_field="matching assignment identity",
        )


def require_fpr_target(*, request: AssignThresholdRequest, percentile: ThresholdPercentile) -> None:
    if request.assignment_metadata.fpr_target.value != 1 - percentile.value:
        raise ThresholdError(
            detail="threshold construction target must equal one minus its declared percentile",
            policy=type(request.construction).__name__,
            missing_field="matching FPR target",
        )


def roster_clients(request: AssignThresholdRequest) -> tuple[ClientId, ...]:
    return request.calibration_scores.per_client.values.roster.client_ids


def unexpected_construction(request: AssignThresholdRequest) -> ThresholdError:
    return ThresholdError(
        detail="threshold strategy received an incompatible construction specification",
        policy=type(request.construction).__name__,
        missing_field="matching threshold strategy",
    )
