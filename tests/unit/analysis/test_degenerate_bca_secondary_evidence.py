from types import SimpleNamespace
from typing import cast

from datp_core.analysis.contrasts import ConfirmatoryDescriptiveEffects, PairedContrast, PairedContrasts
from datp_core.analysis.inference.bootstrap.contracts import BcaReason, BootstrapInterval
from datp_core.analysis.preparation import ConfirmatoryAnalysisRequest, prepare_confirmatory_analysis
from datp_core.core.numeric import MetricValue
from datp_core.detector.training.contracts import FederatedTrainingCoordinate
from datp_core.experiments.common.seeds import CONFIRMATORY_ANALYSIS_SEED, CONFIRMATORY_SEED_COHORT
from datp_core.experiments.confirmatory.spec import CONFIRMATORY_INFERENCE_PROTOCOL


def test_degenerate_bca_retains_valid_secondary_statistics(monkeypatch) -> None:
    contrasts = PairedContrasts.model_construct(
        values=tuple(
            PairedContrast.model_construct(
                left_value=MetricValue(1.0),
                right_value=MetricValue(0.0),
                coordinate=cast(FederatedTrainingCoordinate, SimpleNamespace(training_seed=seed)),
            )
            for seed in CONFIRMATORY_SEED_COHORT.values
        )
    )
    interval = BootstrapInterval.degenerate(
        protocol=CONFIRMATORY_INFERENCE_PROTOCOL,
        analysis_seed=CONFIRMATORY_ANALYSIS_SEED,
        point_estimate=MetricValue(1.0),
        reason=BcaReason.IDENTICAL_PAIRED_DELTAS,
    )
    monkeypatch.setattr("datp_core.analysis.preparation.validate_confirmatory_contrasts", lambda values, _: values)
    monkeypatch.setattr("datp_core.analysis.preparation.paired_bca_interval", lambda *args, **kwargs: interval)

    document = prepare_confirmatory_analysis(
        ConfirmatoryAnalysisRequest(
            contrasts=contrasts,
            descriptive_effects=ConfirmatoryDescriptiveEffects.model_construct(values=()),
            inference_protocol=CONFIRMATORY_INFERENCE_PROTOCOL,
            analysis_seed=CONFIRMATORY_ANALYSIS_SEED,
        )
    )

    assert document.decision.decision.value == "confirmatory_inference_unavailable"
    assert document.wilcoxon.p_value is not None
    assert document.rank_biserial.value is not None
    assert document.exact_sign_test is not None
    assert document.multiplicity_result is not None
    assert document.unavailable_reason == BcaReason.IDENTICAL_PAIRED_DELTAS.value
