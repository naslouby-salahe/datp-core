from dataclasses import dataclass
from math import ceil

from datp_core.application.ports.thresholding import AssignThresholdRequest, ThresholdStrategy
from datp_core.domain.errors import ThresholdError
from datp_core.domain.experiments.identities import ClientId
from datp_core.domain.thresholding.clustering import ClusterAssignmentArtifact
from datp_core.domain.thresholding.policies import (
    FprTarget,
    ThresholdAssignment,
    ThresholdPercentile,
    ThresholdValue,
    unweighted_shared_threshold,
)
from datp_core.domain.thresholding.variants import (
    CalibrationSizeFallbackThresholdSpec,
    ConformalThresholdSpec,
    RobustClusterMedianThresholdSpec,
    ShrinkageThresholdSpec,
    ThresholdVariant,
)
from datp_core.infrastructure.thresholding.policies import (
    ClusterAssignmentReader,
    assignment_from_values,
    eligible_threshold_values,
    local_threshold_values,
    require_assignment_subject,
    require_fpr_target,
    roster_clients,
    unexpected_construction,
)
from datp_core.infrastructure.thresholding.quantiles import CalibrationScoreReader


@dataclass(frozen=True, slots=True, kw_only=True)
class VariantThresholdStrategy(ThresholdStrategy):
    reader: CalibrationScoreReader
    assignments: ClusterAssignmentReader

    def assign(self, request: AssignThresholdRequest) -> ThresholdAssignment:
        specification = request.construction
        if type(specification) is ShrinkageThresholdSpec:
            return self._shrinkage(request=request, specification=specification)
        if type(specification) is CalibrationSizeFallbackThresholdSpec:
            return self._calibration_size_fallback(request=request, specification=specification)
        if type(specification) is ConformalThresholdSpec:
            return self._conformal(request=request, specification=specification)
        if type(specification) is RobustClusterMedianThresholdSpec:
            return self._robust_cluster_median(request=request, specification=specification)
        raise unexpected_construction(request)

    def _shrinkage(
        self,
        *,
        request: AssignThresholdRequest,
        specification: ShrinkageThresholdSpec,
    ) -> ThresholdAssignment:
        require_assignment_subject(request=request, expected=ThresholdVariant.SHRINKAGE_LGS)
        require_fpr_target(request=request, percentile=specification.percentile)
        local_values = local_threshold_values(request=request, reader=self.reader, percentile=specification.percentile)
        global_value = unweighted_shared_threshold(
            local_thresholds=eligible_threshold_values(request=request, local_values=local_values)
        )
        values = tuple(
            ThresholdValue(
                value=specification.shrinkage_weight.value * local_value.value
                + (1 - specification.shrinkage_weight.value) * global_value.value
            )
            if client_id in request.eligible_clients.eligible_clients
            else global_value
            for client_id, local_value in zip(roster_clients(request), local_values, strict=True)
        )
        return assignment_from_values(request=request, values=values)

    def _calibration_size_fallback(
        self,
        *,
        request: AssignThresholdRequest,
        specification: CalibrationSizeFallbackThresholdSpec,
    ) -> ThresholdAssignment:
        require_assignment_subject(request=request, expected=ThresholdVariant.CALIB_SIZE_FALLBACK)
        require_fpr_target(request=request, percentile=specification.percentile)
        local_values = local_threshold_values(
            request=request,
            reader=self.reader,
            percentile=specification.percentile,
        )
        global_value = unweighted_shared_threshold(
            local_thresholds=eligible_threshold_values(request=request, local_values=local_values)
        )
        values = tuple(
            local_value if client_id in request.eligible_clients.eligible_clients else global_value
            for client_id, local_value in zip(roster_clients(request), local_values, strict=True)
        )
        return assignment_from_values(request=request, values=values)

    def _conformal(
        self,
        *,
        request: AssignThresholdRequest,
        specification: ConformalThresholdSpec,
    ) -> ThresholdAssignment:
        percentile = specification.conformal_split.percentile
        require_assignment_subject(request=request, expected=ThresholdVariant.CONFORMAL_B2)
        require_fpr_target(request=request, percentile=percentile)
        values = tuple(
            _conformal_value(
                scores=self.reader.read(calibration_scores=request.calibration_scores, client_index=index),
                percentile=percentile,
            )
            for index, _ in enumerate(roster_clients(request))
        )
        fallback = unweighted_shared_threshold(
            local_thresholds=tuple(
                value
                for client_id, value in zip(roster_clients(request), values, strict=True)
                if client_id in request.eligible_clients.eligible_clients
            )
        )
        assigned = tuple(
            value if client_id in request.eligible_clients.eligible_clients else fallback
            for client_id, value in zip(roster_clients(request), values, strict=True)
        )
        return assignment_from_values(request=request, values=assigned)

    def _robust_cluster_median(
        self,
        *,
        request: AssignThresholdRequest,
        specification: RobustClusterMedianThresholdSpec,
    ) -> ThresholdAssignment:
        assignment = self.assignments.read(assignment_identity=specification.canonical_assignment_identity.value)
        require_assignment_subject(request=request, expected=ThresholdVariant.ROBUST_CLUSTER_MEDIAN_B4)
        percentile = _percentile_from_target(request.assignment_metadata.fpr_target)
        local_values = local_threshold_values(request=request, reader=self.reader, percentile=percentile)
        values_by_client = dict(zip(roster_clients(request), local_values, strict=True))
        fallback = unweighted_shared_threshold(
            local_thresholds=eligible_threshold_values(request=request, local_values=local_values)
        )
        label_by_client = {entry.client_id: entry.cluster_index for entry in assignment.assignments}
        cluster_context = _ClusterMedianContext(
            label_by_client=label_by_client,
            assignment=assignment,
            values_by_client=values_by_client,
            eligible_clients=request.eligible_clients.eligible_clients,
            fallback=fallback,
        )
        values = tuple(
            _cluster_median(
                client_id=client_id,
                context=cluster_context,
            )
            for client_id in roster_clients(request)
        )
        return assignment_from_values(request=request, values=values)


def _percentile_from_target(target: FprTarget) -> ThresholdPercentile:
    return ThresholdPercentile(value=1 - target.value)


def _conformal_value(*, scores: tuple[float, ...], percentile: ThresholdPercentile) -> ThresholdValue:
    if not scores:
        raise ThresholdError(
            detail="conformal threshold requires calibration scores",
            policy="conformal",
            missing_field="scores",
        )
    ordered = tuple(sorted(scores))
    index = min(ceil((len(ordered) + 1) * percentile.value) - 1, len(ordered) - 1)
    return ThresholdValue(value=ordered[index])


@dataclass(frozen=True, slots=True, kw_only=True)
class _ClusterMedianContext:
    label_by_client: dict[ClientId, int]
    assignment: ClusterAssignmentArtifact
    values_by_client: dict[ClientId, ThresholdValue]
    eligible_clients: tuple[ClientId, ...]
    fallback: ThresholdValue


def _cluster_median(*, client_id: ClientId, context: _ClusterMedianContext) -> ThresholdValue:
    if client_id not in context.eligible_clients:
        return context.fallback
    label = context.label_by_client.get(client_id)
    if label is None:
        return context.fallback
    members = tuple(
        context.values_by_client[entry.client_id]
        for entry in context.assignment.assignments
        if entry.cluster_index == label and entry.client_id in context.eligible_clients
    )
    if not members:
        return context.fallback
    ordered = tuple(sorted(value.value for value in members))
    return ThresholdValue(value=ordered[len(ordered) // 2])
