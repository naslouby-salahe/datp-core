import pytest
from hypothesis import given
from hypothesis import strategies as st

from datp_core.domain.errors import DomainValidationError
from datp_core.domain.learning.training import (
    ClientBatchPartitioning,
    OptimizerStepSemantics,
    TrainingBatchSpec,
)
from datp_core.domain.runtime.admissibility import BatchSize, GradientAccumulationSteps


@given(st.integers(min_value=1, max_value=512), st.integers(min_value=1, max_value=32))
def test_effective_batch_accepts_only_the_exact_generated_product(
    micro_batch_size: int, accumulation_steps: int
) -> None:
    expected = micro_batch_size * accumulation_steps
    specification = TrainingBatchSpec(
        micro_batch_size=BatchSize(value=micro_batch_size),
        gradient_accumulation_steps=GradientAccumulationSteps(value=accumulation_steps),
        effective_batch_size=BatchSize(value=expected),
        dataloader_batch_size=BatchSize(value=micro_batch_size),
        client_batch_partitioning=ClientBatchPartitioning.WHOLE_CLIENT,
        optimizer_step_semantics=OptimizerStepSemantics.AFTER_GRADIENT_ACCUMULATION,
    )

    assert specification.effective_batch_size.value == expected
    with pytest.raises(DomainValidationError):
        TrainingBatchSpec(
            micro_batch_size=BatchSize(value=micro_batch_size),
            gradient_accumulation_steps=GradientAccumulationSteps(value=accumulation_steps),
            effective_batch_size=BatchSize(value=expected + 1),
            dataloader_batch_size=BatchSize(value=micro_batch_size),
            client_batch_partitioning=ClientBatchPartitioning.WHOLE_CLIENT,
            optimizer_step_semantics=OptimizerStepSemantics.AFTER_GRADIENT_ACCUMULATION,
        )
