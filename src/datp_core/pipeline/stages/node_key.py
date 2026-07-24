"""StageNodeKey -- typed frozen semantic key replacing string-based JobId/ArtifactId."""
from __future__ import annotations

from attrs import define

from datp_core.core.identifiers import ExperimentId, PopulationId, ThresholdPolicyId
from datp_core.pipeline.stages.enums import StageKind


@define(frozen=True, slots=True, kw_only=True, eq=False)
class StageNodeKey:
    experiment: ExperimentId
    stage: StageKind
    seed: int | None = None
    population: PopulationId | None = None
    partition_condition: str | None = None
    evaluation_label: str | None = None
    threshold_policy: ThresholdPolicyId | None = None
    federated_proximal_mu: float | None = None
    ditto_proximal_weight: float | None = None
    threshold_quantile: float | None = None
    shrinkage_weight: float | None = None
    federated_summary_fixed_k: float | None = None
    fingerprint_features: tuple[str, ...] | None = None
    calibration_sample_count: int | None = None
    calibration_replicate: int | None = None
    kind_suffix: str | None = None

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, StageNodeKey):
            return NotImplemented
        return self._identity_tuple == other._identity_tuple

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, StageNodeKey):
            return NotImplemented
        return self._identity_tuple < other._identity_tuple

    def __le__(self, other: object) -> bool:
        if not isinstance(other, StageNodeKey):
            return NotImplemented
        return self._identity_tuple <= other._identity_tuple

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, StageNodeKey):
            return NotImplemented
        return self._identity_tuple > other._identity_tuple

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, StageNodeKey):
            return NotImplemented
        return self._identity_tuple >= other._identity_tuple

    def __hash__(self) -> int:
        return hash(self._identity_tuple)

    @property
    def _identity_tuple(self) -> tuple:
        return (
            self.experiment.value,
            self.stage.value,
            self.seed if self.seed is not None else -1,
            self.population.value if self.population is not None else "",
            self.partition_condition or "",
            self.evaluation_label or "",
            self.threshold_policy.value if self.threshold_policy is not None else "",
            self.federated_proximal_mu if self.federated_proximal_mu is not None else float("-inf"),
            self.ditto_proximal_weight if self.ditto_proximal_weight is not None else float("-inf"),
            self.threshold_quantile if self.threshold_quantile is not None else float("-inf"),
            self.shrinkage_weight if self.shrinkage_weight is not None else float("-inf"),
            self.federated_summary_fixed_k if self.federated_summary_fixed_k is not None else float("-inf"),
            self.fingerprint_features if self.fingerprint_features is not None else (),
            self.calibration_sample_count if self.calibration_sample_count is not None else -1,
            self.calibration_replicate if self.calibration_replicate is not None else -1,
            self.kind_suffix or "",
        )

    @property
    def label(self) -> str:
        """Human-readable label for display and logging."""
        parts = [self.experiment.value, self.stage.value]
        if self.seed is not None:
            parts.append(f"seed_{self.seed}")
        if self.population is not None:
            parts.append(f"population_{self.population.value}")
        if self.partition_condition is not None:
            parts.append(f"condition_{self.partition_condition}")
        if self.evaluation_label is not None:
            parts.append(self.evaluation_label)
        if self.federated_proximal_mu is not None:
            parts.append(f"mu_{self.federated_proximal_mu:.17g}")
        if self.ditto_proximal_weight is not None:
            parts.append(f"lambda_{self.ditto_proximal_weight:.17g}")
        if self.threshold_quantile is not None:
            parts.append(f"q_{self.threshold_quantile:.17g}")
        if self.shrinkage_weight is not None:
            parts.append(f"shrinkage_{self.shrinkage_weight:.17g}")
        if self.federated_summary_fixed_k is not None:
            parts.append(f"fixed_k_{self.federated_summary_fixed_k:.17g}")
        if self.fingerprint_features is not None:
            parts.append("features_" + "+".join(self.fingerprint_features))
        if self.calibration_sample_count is not None:
            parts.append(f"n_{self.calibration_sample_count}")
        if self.calibration_replicate is not None:
            parts.append(f"rep_{self.calibration_replicate}")
        if self.kind_suffix is not None:
            parts.append(self.kind_suffix)
        return ":".join(parts)


def node_path(key: StageNodeKey) -> str:
    base = f"experiments/{key.experiment.value}/{key.stage.value}"
    if key.kind_suffix is not None:
        base += f"/{key.kind_suffix}"
    if key.seed is not None:
        base += f"/seed_{key.seed}"
    if key.evaluation_label is not None:
        base += f"/{key.evaluation_label}"
    if key.threshold_quantile is not None:
        base += f"/q_{key.threshold_quantile:.3f}"
    if key.calibration_sample_count is not None:
        base += f"/n_{key.calibration_sample_count}_rep_{key.calibration_replicate}"
    return base
