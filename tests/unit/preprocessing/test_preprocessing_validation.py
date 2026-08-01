import numpy as np
import pytest

from datp_core.domain.enums import PartitionRole, SplitProtocolId
from datp_core.domain.errors import LeakageError, ScientificContractError
from datp_core.domain.values import OutcomeLabelSequence
from datp_core.populations.models import PopulationOutcomeLabel
from datp_core.preprocessing.validation import (
    validate_finite_matrix,
    validate_no_attack_labels_in_fit,
    validate_no_partition_overlap,
    validate_train_only_fit,
)


def test_train_only_and_overlap_guards() -> None:
    validate_train_only_fit(PartitionRole.TRAIN)
    with pytest.raises(LeakageError):
        validate_train_only_fit(PartitionRole.CALIBRATION)
    validate_no_partition_overlap(
        {
            PartitionRole.TRAIN: ("a", "b"),
            PartitionRole.CALIBRATION: ("c",),
            PartitionRole.EVALUATION: ("d",),
        },
        split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
    )
    with pytest.raises(LeakageError, match="overlap"):
        validate_no_partition_overlap(
            {
                PartitionRole.TRAIN: ("a", "b"),
                PartitionRole.CALIBRATION: ("b",),
                PartitionRole.EVALUATION: ("c",),
            },
            split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
        )


def test_attack_and_nonfinite_guards() -> None:
    validate_no_attack_labels_in_fit(OutcomeLabelSequence(("benign", "benign")), PopulationOutcomeLabel.BENIGN)
    with pytest.raises(LeakageError):
        validate_no_attack_labels_in_fit(OutcomeLabelSequence(("benign", "attack")), PopulationOutcomeLabel.BENIGN)
    validate_finite_matrix(np.asarray([[1.0, 2.0]]), PartitionRole.TRAIN)
    with pytest.raises(ScientificContractError):
        validate_finite_matrix(np.asarray([[1.0, np.nan]]), PartitionRole.TRAIN)
