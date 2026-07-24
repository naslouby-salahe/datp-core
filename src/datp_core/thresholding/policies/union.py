"""Closed typed union of all threshold policy records."""

from __future__ import annotations

from datp_core.thresholding.policies.clustering import ClusterThresholdPolicyRecord
from datp_core.thresholding.policies.conformal import SplitConformalThresholdPolicyRecord
from datp_core.thresholding.policies.federated import (
    FederatedFixedCoefficientThresholdPolicyRecord,
    FederatedMatchedExceedanceThresholdPolicyRecord,
)
from datp_core.thresholding.policies.grouped import FamilyMeanThresholdPolicyRecord
from datp_core.thresholding.policies.shared import (
    CentralizedPooledThresholdPolicyRecord,
    LocalQuantileThresholdPolicyRecord,
    SharedMeanThresholdPolicyRecord,
    SharedPooledThresholdPolicyRecord,
    SharedWeightedThresholdPolicyRecord,
)
from datp_core.thresholding.policies.shrinkage import (
    CalibrationFallbackThresholdPolicyRecord,
    LocalGlobalShrinkageThresholdPolicyRecord,
)

ThresholdPolicyRecord = (
    SharedMeanThresholdPolicyRecord
    | SharedPooledThresholdPolicyRecord
    | SharedWeightedThresholdPolicyRecord
    | LocalQuantileThresholdPolicyRecord
    | FamilyMeanThresholdPolicyRecord
    | CentralizedPooledThresholdPolicyRecord
    | ClusterThresholdPolicyRecord
    | SplitConformalThresholdPolicyRecord
    | LocalGlobalShrinkageThresholdPolicyRecord
    | CalibrationFallbackThresholdPolicyRecord
    | FederatedMatchedExceedanceThresholdPolicyRecord
    | FederatedFixedCoefficientThresholdPolicyRecord
)
