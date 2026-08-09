"""Composition gate: paired contrasts require fixed-score identity (SF-05)."""

from dataclasses import replace
from types import SimpleNamespace

import pytest
from tests.unit.evaluation.test_fixed_score import _evidence
from tests.unit.learning.federated.helpers import fedavg_coordinate

from datp_core.analysis.contrasts import build_paired_contrast
from datp_core.artifacts.provenance import Checksum
from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import EvidenceRole, FederatedThresholdMethod, MetricId
from datp_core.core.numeric import MetricValue, Seed


def _document(
    method: FederatedThresholdMethod,
    *,
    score_checksum: Checksum | None = None,
    checkpoint_checksum: Checksum | None = None,
    split_checksum: Checksum | None = None,
) -> SimpleNamespace:
    evidence = _evidence(method, MetricValue(0.8))
    if score_checksum is not None:
        evidence = replace(
            evidence,
            evaluation=replace(evidence.evaluation, score_checksum=score_checksum),
        )
    if checkpoint_checksum is not None:
        evidence = replace(
            evidence,
            detector=replace(evidence.detector, selected_checkpoint_checksum=checkpoint_checksum),
        )
    checksum = Checksum("d" * 64)
    return SimpleNamespace(
        score_coordinate=fedavg_coordinate(Seed(8)),
        score_checkpoint_checksum=evidence.detector.selected_checkpoint_checksum,
        preprocessing_state_set_checksum=evidence.detector.preprocessing_checksum,
        split_manifest_checksum=split_checksum or checksum,
        threshold_method=method,
        evidence_role=EvidenceRole.CONFIRMATORY,
        fixed_score_evidence=evidence,
    )


def test_build_paired_contrast_accepts_fixed_score_matched_documents() -> None:
    left = _document(FederatedThresholdMethod.SHARED_THRESHOLD)
    right = _document(FederatedThresholdMethod.LOCAL_THRESHOLD)
    contrast = build_paired_contrast(
        left=left,  # type: ignore[arg-type]
        right=right,  # type: ignore[arg-type]
        metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
        left_value=MetricValue(0.4),
        right_value=MetricValue(0.2),
        evidence_role=EvidenceRole.CONFIRMATORY,
    )
    assert contrast.delta == MetricValue(0.2)
    assert contrast.left_method is FederatedThresholdMethod.SHARED_THRESHOLD
    assert contrast.right_method is FederatedThresholdMethod.LOCAL_THRESHOLD
    assert contrast.fixed_score.model_checksum == left.fixed_score_evidence.detector.model_checksum


def test_build_paired_contrast_rejects_score_checksum_mismatch() -> None:
    left = _document(FederatedThresholdMethod.SHARED_THRESHOLD)
    right = _document(
        FederatedThresholdMethod.LOCAL_THRESHOLD,
        score_checksum=Checksum("e" * 64),
    )
    left_value = MetricValue(0.4)
    right_value = MetricValue(0.2)
    with pytest.raises(ScientificContractError):
        build_paired_contrast(
            left=left,  # type: ignore[arg-type]
            right=right,  # type: ignore[arg-type]
            metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
            left_value=left_value,
            right_value=right_value,
            evidence_role=EvidenceRole.CONFIRMATORY,
        )


def test_build_paired_contrast_rejects_checkpoint_mismatch() -> None:
    left = _document(FederatedThresholdMethod.SHARED_THRESHOLD)
    right = _document(
        FederatedThresholdMethod.LOCAL_THRESHOLD,
        checkpoint_checksum=Checksum("f" * 64),
    )
    left_value = MetricValue(0.4)
    right_value = MetricValue(0.2)
    with pytest.raises(ScientificContractError):
        build_paired_contrast(
            left=left,  # type: ignore[arg-type]
            right=right,  # type: ignore[arg-type]
            metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
            left_value=left_value,
            right_value=right_value,
            evidence_role=EvidenceRole.CONFIRMATORY,
        )


def test_build_paired_contrast_rejects_split_manifest_mismatch() -> None:
    left = _document(FederatedThresholdMethod.SHARED_THRESHOLD)
    right = _document(
        FederatedThresholdMethod.LOCAL_THRESHOLD,
        split_checksum=Checksum("c" * 64),
    )
    left_value = MetricValue(0.4)
    right_value = MetricValue(0.2)
    with pytest.raises(ScientificContractError, match="split-manifest"):
        build_paired_contrast(
            left=left,  # type: ignore[arg-type]
            right=right,  # type: ignore[arg-type]
            metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
            left_value=left_value,
            right_value=right_value,
            evidence_role=EvidenceRole.CONFIRMATORY,
        )
