"""Immutable analysis execution context — sole authority for evaluation lookups,
``StageJobContext`` construction, and typed domain operations.

Capability modules must use this context instead of constructing
``StageJobContext`` manually, calling ``getattr(policy, …)``, or performing
``next(item for item in …)`` searches.
"""

from __future__ import annotations

from attrs import define

from datp_core.analysis.contracts import QuantileThresholdPolicy
from datp_core.analysis.errors import InvalidAnalysisConfigurationError
from datp_core.analysis.runtime.artifacts import AnalysisArtifactRepository
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.core.identifiers import ThresholdPolicyId
from datp_core.core.seeding import Seed
from datp_core.experiments import EvaluationSpecRecord, ExperimentRecord
from datp_core.pipeline.stages.context import StageJobContext


@define(frozen=True, slots=True, kw_only=True)
class AnalysisExecutionContext:
    """Immutable context holding resolved configuration and artifact access for one analysis run.

    Every capability entry-point receives one instance of this context. No
    capability may construct ``StageJobContext`` directly, resolve artifact
    paths, or call ``getattr(policy, …)`` — those operations belong here.
    """

    config: ResolvedProjectConfiguration
    artifacts: AnalysisArtifactRepository
    experiment: ExperimentRecord
    seeds: tuple[Seed, ...]

    # ------------------------------------------------------------------
    # Evaluation lookups (replaces free functions + next(…) searches)
    # ------------------------------------------------------------------

    def evaluation(self, label: str) -> EvaluationSpecRecord:
        """Return the evaluation spec for *label*."""
        try:
            return next(item for item in self.experiment.evaluations if item.label == label)
        except StopIteration:
            raise InvalidAnalysisConfigurationError(
                f"Experiment '{self.experiment.display_name}' has no evaluation labelled '{label}'"
            ) from None

    def threshold_policy_id(self, evaluation_label: str) -> ThresholdPolicyId:
        """Return the typed threshold-policy identifier for an evaluation."""
        return self.evaluation(evaluation_label).threshold_policy_id

    def quantile_for_evaluation(self, evaluation_label: str) -> float:
        """Return the quantile of the threshold policy bound to *evaluation_label*.

        Raises ``InvalidAnalysisConfigurationError`` when the policy does not
        expose a quantile.
        """
        policy = self.config.threshold_policies.get(self.threshold_policy_id(evaluation_label))
        if not isinstance(policy, QuantileThresholdPolicy):
            raise InvalidAnalysisConfigurationError(
                f"Evaluation '{evaluation_label}' does not bind a quantile threshold policy"
            )
        return policy.quantile

    # ------------------------------------------------------------------
    # StageJobContext factories (replaces duplicated _evaluation_context())
    # ------------------------------------------------------------------

    def evaluation_context(
        self,
        label: str,
        seed: int,
        *,
        partition_condition: str | None = None,
        proximal_mu: float | None = None,
        ditto_weight: float | None = None,
        threshold_quantile: float | None = None,
        shrinkage_weight: float | None = None,
        calibration_sample_count: int | None = None,
        calibration_replicate: int | None = None,
        fingerprint_features: tuple[str, ...] | None = None,
    ) -> StageJobContext:
        """Construct a ``StageJobContext`` with complete evaluation metadata.

        This is the **only** place ``StageJobContext`` may be instantiated for
        analysis work.  Capabilities that need a variant (e.g.  score-only or
        calibration-only context) must call this method with the appropriate
        overrides rather than constructing the dataclass themselves.
        """
        evaluation = self.evaluation(label)
        return StageJobContext(
            experiment_id=self.experiment.identifier,
            seed=seed,
            evaluation_label=label,
            population_id=evaluation.population_id,
            recalibration_mode=evaluation.recalibration_mode,
            partition_condition=partition_condition,
            federated_proximal_mu=proximal_mu,
            ditto_proximal_weight=ditto_weight,
            threshold_quantile=threshold_quantile,
            shrinkage_weight=shrinkage_weight,
            calibration_sample_count=calibration_sample_count,
            calibration_replicate=calibration_replicate,
            fingerprint_features=fingerprint_features,
        )
