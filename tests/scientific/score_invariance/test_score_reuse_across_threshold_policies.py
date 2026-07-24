"""Scientific-invariant test for SCIENTIFIC_SOURCE_OF_TRUTH.md's score-reuse rule (`SS6` item 10):
"the same calibration and test score artifacts are reused across B0-B4 within a seed; no
policy-specific retraining or rescoring is permitted." `IdentityBuilder` is the single authority
for job/artifact identity, so the invariant is directly checkable there: calibration/test score
identity must be invariant to which evaluation (and therefore which threshold policy) will later
consume those scores, while evaluation/threshold identity -- which legitimately differs per B0-B4
policy -- must NOT be invariant, or this test would be vacuous.
"""

from __future__ import annotations

import pytest

from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.core.identifiers import ExperimentId
from datp_core.experiments.identity import IdentityBuilder, IdentityKind
from datp_core.experiments.models import ExperimentRecord
from datp_core.pipeline.models import StageJobContext


@pytest.fixture(scope="module")
def _anchor_reproduction(_resolved: ResolvedProjectConfiguration) -> ExperimentRecord:
    return _resolved.experiments.get(ExperimentId("anchor_reproduction"))


def _evaluation_labels(experiment: ExperimentRecord) -> tuple[str, ...]:
    labels = tuple(evaluation.label for evaluation in experiment.evaluations)
    assert len(labels) >= 2, "test requires an experiment with more than one B0-B4 evaluation"
    return labels


def test_anchor_reproduction_defines_multiple_distinct_threshold_policies(
    _anchor_reproduction: ExperimentRecord,
) -> None:
    policies = {evaluation.threshold_policy_id.value for evaluation in _anchor_reproduction.evaluations}
    assert len(policies) >= 2, "the score-reuse invariant is only meaningful across distinct threshold policies"


@pytest.mark.parametrize("kind", [IdentityKind.CALIBRATION_SCORE, IdentityKind.TEST_SCORE])
def test_score_identity_is_invariant_to_evaluation_label(
    _anchor_reproduction: ExperimentRecord, kind: IdentityKind
) -> None:
    labels = _evaluation_labels(_anchor_reproduction)
    job_ids = set()
    artifact_keys = set()
    for label in labels:
        context = StageJobContext(experiment_id=_anchor_reproduction.identifier, seed=0, evaluation_label=label)
        job_ids.add(IdentityBuilder.job_id(kind, context).value)
        key = IdentityBuilder.artifact_key(kind, context)
        artifact_keys.add((key.artifact_id.value, key.kind))
    assert len(job_ids) == 1, f"{kind} job identity must not depend on evaluation_label, got {job_ids}"
    assert len(artifact_keys) == 1, f"{kind} artifact identity must not depend on evaluation_label, got {artifact_keys}"


@pytest.mark.parametrize("kind", [IdentityKind.EVALUATION, IdentityKind.THRESHOLD])
def test_downstream_identity_does_depend_on_evaluation_label(
    _anchor_reproduction: ExperimentRecord, kind: IdentityKind
) -> None:
    labels = _evaluation_labels(_anchor_reproduction)
    job_ids = {
        IdentityBuilder.job_id(
            kind, StageJobContext(experiment_id=_anchor_reproduction.identifier, seed=0, evaluation_label=label)
        ).value
        for label in labels
    }
    assert len(job_ids) == len(labels), (
        f"{kind} identity should differ per evaluation label ({labels}); a collision would mean B0-B4 "
        "evaluations are silently sharing downstream artifacts, not just reusing scores"
    )


def test_score_identity_ignores_threshold_policy_id_field_directly(
    _anchor_reproduction: ExperimentRecord,
) -> None:
    # StageJobContext carries a threshold_policy_id field, but no identity kind (including scores)
    # is spec'd to consume it -- evaluation_label is the sole downstream-policy-carrying field.
    labels = _evaluation_labels(_anchor_reproduction)
    policies = {evaluation.threshold_policy_id for evaluation in _anchor_reproduction.evaluations}
    assert len(policies) >= 2
    first_policy, second_policy = sorted(policies, key=lambda policy_id: policy_id.value)[:2]
    base = StageJobContext(experiment_id=_anchor_reproduction.identifier, seed=0, evaluation_label=labels[0])
    varied = StageJobContext(
        experiment_id=_anchor_reproduction.identifier,
        seed=0,
        evaluation_label=labels[0],
        threshold_policy_id=first_policy if base.threshold_policy_id != first_policy else second_policy,
    )
    assert IdentityBuilder.job_id(IdentityKind.CALIBRATION_SCORE, base) == IdentityBuilder.job_id(
        IdentityKind.CALIBRATION_SCORE, varied
    )
    assert IdentityBuilder.job_id(IdentityKind.TEST_SCORE, base) == IdentityBuilder.job_id(
        IdentityKind.TEST_SCORE, varied
    )
