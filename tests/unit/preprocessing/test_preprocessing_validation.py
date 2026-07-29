import numpy as np
import pytest

from datp_core.domain.enums import PartitionRole
from datp_core.domain.errors import LeakageError, ScientificContractError
from datp_core.domain.values import OutcomeLabelSequence
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
    validate_no_partition_overlap(("a", "b"), ("c",), ("d",))
    with pytest.raises(LeakageError, match="overlap"):
        validate_no_partition_overlap(("a", "b"), ("b",), ("c",))


def test_attack_and_nonfinite_guards() -> None:
    validate_no_attack_labels_in_fit(OutcomeLabelSequence(("benign", "benign")), "benign")
    with pytest.raises(LeakageError):
        validate_no_attack_labels_in_fit(OutcomeLabelSequence(("benign", "attack")), "benign")
    validate_finite_matrix(np.asarray([[1.0, 2.0]]), PartitionRole.TRAIN)
    with pytest.raises(ScientificContractError):
        validate_finite_matrix(np.asarray([[1.0, np.nan]]), PartitionRole.TRAIN)
