from dataclasses import dataclass, fields, is_dataclass, replace
from decimal import Decimal
from enum import Enum
from math import isfinite
from typing import TypeGuard

from blake3 import blake3

from datp_core.application.planning.plan import (
    DraftExecutionPlan,
    DraftPlannedStage,
    ScientificStageGateDecision,
)
from datp_core.domain.artifacts.lineage import (
    CalibrationScoringIdentity,
    CheckpointIdentity,
    CheckpointSelectionIdentity,
    DatasetSourceIdentity,
    EvaluationIdentity,
    FeatureSchemaIdentity,
    FittedPreprocessorIdentity,
    PartitionIdentity,
    ProcessedSplitIdentity,
    ReportIdentity,
    ResultFreezeIdentity,
    SplitIdentity,
    StageDependency,
    StageDependencyCollection,
    StageIdentity,
    StatisticalIdentity,
    TemporalScoringIdentity,
    TestScoringIdentity,
    ThresholdIdentity,
    TrainingIdentity,
)
from datp_core.domain.artifacts.references import ArtifactReferenceCollection, StageFingerprint
from datp_core.domain.errors import AmbiguousPlanError, CyclicPlanError, DomainValidationError
from datp_core.domain.experiments.feasibility import ScientificReadinessResult
from datp_core.domain.experiments.identities import CellId
from datp_core.domain.experiments.specifications import ExperimentCell, ExperimentSpec
from datp_core.domain.runtime.policies import PipelineStage
from datp_core.domain.runtime.seeds import Seed


@dataclass(frozen=True, slots=True, kw_only=True)
class CreateExecutionPlanRequest:
    specifications: tuple[ExperimentSpec, ...]
    scientific_readiness: ScientificReadinessResult


class ExperimentPlanner:
    def create_plan(self, request: CreateExecutionPlanRequest) -> DraftExecutionPlan:
        cells = expand_cells(request=request)
        _reject_cell_id_collisions(cells)
        gate_decision = ScientificStageGateDecision(readiness=request.scientific_readiness)
        stages = _deduplicated_stages(cells=cells, gate_decision=gate_decision)
        dependencies = _dependencies_for(cells=cells, gate_decision=gate_decision)
        return DraftExecutionPlan(
            stages=stages,
            dependencies=dependencies,
            scientific_readiness=request.scientific_readiness,
        )


def expand_cells(*, request: CreateExecutionPlanRequest) -> tuple[ExperimentCell, ...]:
    cells: list[ExperimentCell] = []
    for specification in request.specifications:
        for protocol in specification.profile.authorized_protocols:
            resolved_specification: ExperimentSpec = replace(specification, scientific_protocol=protocol)
            for seed in specification.profile.authorized_seed_plan.values:
                cells.append(
                    _resolved_cell(
                        specification=resolved_specification,
                        seed=seed,
                        scientific_readiness=request.scientific_readiness,
                    )
                )
    return tuple(cells)


def _resolved_cell(
    *,
    specification: ExperimentSpec,
    seed: Seed,
    scientific_readiness: ScientificReadinessResult,
) -> ExperimentCell:
    identities = _stage_identities(specification=specification, seed=seed)
    return ExperimentCell(
        cell_id=_cell_id(specification=specification, seed=seed),
        experiment_id=specification.identity.experiment_id,
        scientific_protocol=specification.scientific_protocol,
        execution_policy=specification.execution_policy,
        artifact_policy=specification.artifact_policy,
        reporting_policy=specification.reporting_policy,
        stage_identities=identities,
        scientific_readiness=scientific_readiness,
    )


def _cell_id(*, specification: ExperimentSpec, seed: Seed) -> CellId:
    digest = _fingerprint(("cell", specification, seed)).value[:16]
    return CellId(value=f"{specification.identity.experiment_id.value}#{digest}")


def _stage_identities(*, specification: ExperimentSpec, seed: Seed) -> StageIdentity:
    protocol = specification.scientific_protocol
    dataset_source = DatasetSourceIdentity(
        value=_fingerprint((PipelineStage.SOURCE_INSPECTION, protocol.track, protocol.dataset))
    )
    feature_schema = FeatureSchemaIdentity(value=_fingerprint(("feature_schema", dataset_source, protocol.dataset)))
    partition = PartitionIdentity(
        value=_fingerprint((PipelineStage.PARTITION, feature_schema, protocol.partitioning, seed))
    )
    split = SplitIdentity(value=_fingerprint((PipelineStage.SPLIT_BUILD, partition, protocol.splits)))
    fitted_preprocessor = FittedPreprocessorIdentity(
        value=_fingerprint((PipelineStage.PREPROCESSOR_FIT, split, protocol.preprocessing))
    )
    processed_split = ProcessedSplitIdentity(
        value=_fingerprint((PipelineStage.SPLIT_MATERIALIZE, split, fitted_preprocessor))
    )
    training = TrainingIdentity(value=_fingerprint((PipelineStage.TRAIN, processed_split, protocol.training, seed)))
    checkpoint = CheckpointIdentity(value=_fingerprint(("scientific_checkpoint", training, protocol.checkpointing)))
    checkpoint_selection = CheckpointSelectionIdentity(
        value=_fingerprint((PipelineStage.CHECKPOINT_SELECT, checkpoint, protocol.checkpoint_selection))
    )
    calibration_scoring = CalibrationScoringIdentity(
        value=_fingerprint((PipelineStage.CALIBRATION_SCORE, checkpoint_selection, protocol.scoring))
    )
    test_scoring = TestScoringIdentity(
        value=_fingerprint((PipelineStage.TEST_SCORE, checkpoint_selection, protocol.scoring))
    )
    temporal_scoring = TemporalScoringIdentity(
        value=_fingerprint((PipelineStage.TEMPORAL_SCORE, checkpoint_selection, protocol.scoring))
    )
    threshold = ThresholdIdentity(
        value=_fingerprint((PipelineStage.THRESHOLD, calibration_scoring, protocol.thresholds))
    )
    evaluation = EvaluationIdentity(
        value=_fingerprint((PipelineStage.EVALUATE, threshold, test_scoring, temporal_scoring, protocol.evaluation))
    )
    statistical = StatisticalIdentity(
        value=_fingerprint((PipelineStage.ANALYZE, evaluation, protocol.statistics, seed))
    )
    resource_cost = _resource_cost_fingerprint(statistical=statistical, resource_costs=protocol.resource_costs)
    result_freeze = ResultFreezeIdentity(value=_fingerprint((PipelineStage.RESULT_FREEZE, statistical, resource_cost)))
    report = ReportIdentity(value=_fingerprint((PipelineStage.REPORT, result_freeze, specification.reporting_policy)))
    return StageIdentity(
        dataset_source=dataset_source,
        feature_schema=feature_schema,
        partition=partition,
        split=split,
        fitted_preprocessor=fitted_preprocessor,
        processed_split=processed_split,
        training=training,
        checkpoint=checkpoint,
        checkpoint_selection=checkpoint_selection,
        calibration_scoring=calibration_scoring,
        test_scoring=test_scoring,
        temporal_scoring=temporal_scoring,
        threshold=threshold,
        evaluation=evaluation,
        statistical=statistical,
        result_freeze=result_freeze,
        report=report,
    )


def _resource_cost_fingerprint(*, statistical: StatisticalIdentity, resource_costs: object) -> StageFingerprint:
    return _fingerprint((PipelineStage.RESOURCE_COST, statistical, resource_costs))


def _fingerprint(value: object) -> StageFingerprint:
    return StageFingerprint(value=blake3(_canonical_bytes(value)).hexdigest())


def _canonical_bytes(value: object) -> bytes:
    primitive = _canonical_primitive(value)
    if primitive is not None:
        return primitive
    if isinstance(value, Enum):
        return _encoded(_type_name(value), _canonical_bytes(value.value))
    if _is_tuple(value):
        return _canonical_tuple(value)
    if is_dataclass(value) and not isinstance(value, type):
        encoded_fields = b"".join(
            _encoded(field.name, _canonical_bytes(getattr(value, field.name))) for field in fields(value)
        )
        return _encoded(_type_name(value), encoded_fields)
    raise DomainValidationError(
        detail="stage fingerprints require canonical typed inputs",
        value=repr(value),
        constraint="primitive, enum, tuple, Decimal, or frozen dataclass input",
    )


def _canonical_primitive(value: object) -> bytes | None:
    scalar = _canonical_scalar(value)
    if scalar is not None:
        return scalar
    if type(value) is float:
        return _canonical_float(value)
    return None


def _canonical_scalar(value: object) -> bytes | None:
    if value is None:
        return b"none"
    if type(value) is bool:
        return b"bool:1" if value else b"bool:0"
    if type(value) is int:
        return f"int:{value}".encode()
    if type(value) is str:
        return _encoded("str", value.encode())
    if type(value) is Decimal:
        return _encoded("decimal", format(value, "f").encode())
    return None


def _canonical_float(value: object) -> bytes:
    if type(value) is not float or not isfinite(value):
        raise DomainValidationError(
            detail="stage fingerprints reject non-finite floating-point inputs",
            value=repr(value),
            constraint="finite canonical quantized float",
        )
    return _encoded("float", format(Decimal(str(value)).quantize(Decimal("0.000000000001")), "f").encode())


def _canonical_tuple(value: tuple[object, ...]) -> bytes:
    return _encoded("tuple", b"".join(_canonical_bytes(item) for item in value))


def _is_tuple(value: object) -> TypeGuard[tuple[object, ...]]:
    return isinstance(value, tuple)


def _encoded(label: str, payload: bytes) -> bytes:
    return label.encode() + b":" + str(len(payload)).encode() + b":" + payload


def _type_name(value: object) -> str:
    value_type = type(value)
    return f"{value_type.__module__}.{value_type.__qualname__}"


def _deduplicated_stages(
    *,
    cells: tuple[ExperimentCell, ...],
    gate_decision: ScientificStageGateDecision,
) -> tuple[DraftPlannedStage, ...]:
    stages_by_key: dict[tuple[PipelineStage, str], DraftPlannedStage] = {}
    for cell in cells:
        for stage in _stages_for_cell(cell=cell, gate_decision=gate_decision):
            stages_by_key.setdefault((stage.stage, stage.stage_fingerprint.value), stage)
    return tuple(stages_by_key.values())


def _dependencies_for(
    *,
    cells: tuple[ExperimentCell, ...],
    gate_decision: ScientificStageGateDecision,
) -> StageDependencyCollection:
    dependencies_by_key: dict[tuple[str, str], StageDependency] = {}
    try:
        for cell in cells:
            stages = _stages_for_cell(cell=cell, gate_decision=gate_decision)
            for upstream, downstream in zip(stages, stages[1:], strict=False):
                dependency = StageDependency(
                    upstream=upstream.stage_fingerprint,
                    downstream=downstream.stage_fingerprint,
                )
                dependencies_by_key.setdefault(
                    (dependency.upstream.value, dependency.downstream.value),
                    dependency,
                )
        return StageDependencyCollection(dependencies=tuple(dependencies_by_key.values()))
    except DomainValidationError as error:
        raise CyclicPlanError(
            detail="draft-stage dependencies must form an acyclic chain", cycle=repr(error)
        ) from error


def _reject_cell_id_collisions(cells: tuple[ExperimentCell, ...]) -> None:
    cells_by_id: dict[str, ExperimentCell] = {}
    for cell in cells:
        existing = cells_by_id.get(cell.cell_id.value)
        if existing is None:
            cells_by_id[cell.cell_id.value] = cell
        elif existing != cell:
            raise AmbiguousPlanError(
                detail="distinct resolved experiment cells cannot share a cell id",
                conflicting_cells=repr((existing, cell)),
            )


def _stages_for_cell(
    *,
    cell: ExperimentCell,
    gate_decision: ScientificStageGateDecision,
) -> tuple[DraftPlannedStage, ...]:
    identities = cell.stage_identities
    resource_cost = _resource_cost_fingerprint(
        statistical=identities.statistical,
        resource_costs=cell.scientific_protocol.resource_costs,
    )
    feasibility_audit = _fingerprint(
        (PipelineStage.FEASIBILITY_AUDIT, identities.dataset_source, cell.scientific_protocol.partitioning)
    )
    stage_specs = (
        (PipelineStage.SOURCE_INSPECTION, identities.dataset_source.value),
        (PipelineStage.FEASIBILITY_AUDIT, feasibility_audit),
        (PipelineStage.PARTITION, identities.partition.value),
        (PipelineStage.SPLIT_BUILD, identities.split.value),
        (PipelineStage.PREPROCESSOR_FIT, identities.fitted_preprocessor.value),
        (PipelineStage.SPLIT_MATERIALIZE, identities.processed_split.value),
        (PipelineStage.TRAIN, identities.training.value),
        (PipelineStage.CHECKPOINT_SELECT, identities.checkpoint_selection.value),
        (PipelineStage.CALIBRATION_SCORE, identities.calibration_scoring.value),
        (PipelineStage.TEST_SCORE, identities.test_scoring.value),
        (PipelineStage.TEMPORAL_SCORE, identities.temporal_scoring.value),
        (PipelineStage.THRESHOLD, identities.threshold.value),
        (PipelineStage.EVALUATE, identities.evaluation.value),
        (PipelineStage.ANALYZE, identities.statistical.value),
        (PipelineStage.RESOURCE_COST, resource_cost),
        (PipelineStage.RESULT_FREEZE, identities.result_freeze.value),
        (PipelineStage.REPORT, identities.report.value),
    )
    return tuple(
        _draft_stage(
            DraftStageRequest(
                stage=stage,
                cell=cell,
                fingerprint=fingerprint,
                gate_decision=gate_decision,
                dependencies=StageDependencyCollection(
                    dependencies=()
                    if index == 0
                    else (StageDependency(upstream=stage_specs[index - 1][1], downstream=fingerprint),)
                ),
            ),
        )
        for index, (stage, fingerprint) in enumerate(stage_specs)
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class DraftStageRequest:
    stage: PipelineStage
    cell: ExperimentCell
    fingerprint: StageFingerprint
    gate_decision: ScientificStageGateDecision
    dependencies: StageDependencyCollection


def _draft_stage(request: DraftStageRequest) -> DraftPlannedStage:
    return DraftPlannedStage(
        stage=request.stage,
        cell_id=request.cell.cell_id,
        stage_fingerprint=request.fingerprint,
        inputs=ArtifactReferenceCollection(references=()),
        dependencies=request.dependencies,
        scientific_gate_decision=request.gate_decision,
    )
