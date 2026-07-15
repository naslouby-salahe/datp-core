from hypothesis import given
from hypothesis import strategies as st

from datp_core.domain.experiments.protocols import ScientificProtocolField, ScientificProtocolSpec
from datp_core.domain.runtime.policies import PipelineStage


@given(st.sampled_from(tuple(ScientificProtocolField)))
def test_every_scientific_field_has_only_its_earliest_direct_identity_stage(field: ScientificProtocolField) -> None:
    expected_stage = {
        ScientificProtocolField.TRACK: PipelineStage.SOURCE_INSPECTION,
        ScientificProtocolField.DATASET: PipelineStage.SOURCE_INSPECTION,
        ScientificProtocolField.PARTITIONING: PipelineStage.PARTITION,
        ScientificProtocolField.SPLITS: PipelineStage.SPLIT_BUILD,
        ScientificProtocolField.PREPROCESSING: PipelineStage.PREPROCESSOR_FIT,
        ScientificProtocolField.TRAINING: PipelineStage.TRAIN,
        ScientificProtocolField.CHECKPOINTING: PipelineStage.CHECKPOINT_SELECT,
        ScientificProtocolField.CHECKPOINT_SELECTION: PipelineStage.CHECKPOINT_SELECT,
        ScientificProtocolField.SCORING: PipelineStage.CALIBRATION_SCORE,
        ScientificProtocolField.THRESHOLDS: PipelineStage.THRESHOLD,
        ScientificProtocolField.EVALUATION: PipelineStage.EVALUATE,
        ScientificProtocolField.STATISTICS: PipelineStage.ANALYZE,
        ScientificProtocolField.RESOURCE_COSTS: PipelineStage.RESOURCE_COST,
    }[field]

    assert ScientificProtocolSpec.earliest_identity_stage_for(field) is expected_stage
