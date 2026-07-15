from dataclasses import dataclass
from decimal import Decimal

import pytest

from datp_core.application.ports.statistics import RunStatisticalAnalysisRequest
from datp_core.domain.artifacts.references import ArtifactReferenceCollection, StageFingerprint
from datp_core.domain.errors import StatisticsError
from datp_core.domain.evaluation.alert_burden import BootstrapResampleCount
from datp_core.domain.evaluation.statistical_results import (
    ConfidenceLevel,
    ConfirmatoryAnalysisResult,
    DegenerateBootstrapIntervalResult,
    PairedDeltaDirection,
    PairedDeltaResult,
    StatisticalAnalysisSpec,
    StatisticalMethod,
    ValidBootstrapIntervalResult,
)
from datp_core.domain.runtime.seeds import Seed
from datp_core.infrastructure.statistics.scipy_adapter import (
    BcaBootstrapRequest,
    CliffsDeltaRequest,
    JensenShannonRequest,
    SciPyStatisticalProcedureRunner,
    SciPyStatisticsAdapter,
    SpearmanRequest,
    StatisticalInput,
    WilcoxonRequest,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class _Inputs:
    input: StatisticalInput

    def read(self, request: RunStatisticalAnalysisRequest) -> StatisticalInput:
        del request
        return self.input


def test_bca_is_seeded_explicit_and_contains_its_point_estimate() -> None:
    adapter = SciPyStatisticsAdapter()
    request = BcaBootstrapRequest(
        values=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
        confidence=ConfidenceLevel(value=Decimal("0.95")),
        resamples=BootstrapResampleCount(value=500),
        bootstrap_seed=Seed(value=9),
    )

    first = adapter.bca_bootstrap(request)
    second = adapter.bca_bootstrap(request)

    assert isinstance(first, ValidBootstrapIntervalResult)
    assert first == second
    assert first.lower <= first.point_estimate <= first.upper


def test_bca_degeneracy_is_typed_without_percentile_substitution() -> None:
    result = SciPyStatisticsAdapter().bca_bootstrap(
        BcaBootstrapRequest(
            values=(0.1, 0.2),
            confidence=ConfidenceLevel(value=Decimal("0.95")),
            resamples=BootstrapResampleCount(value=500),
            bootstrap_seed=Seed(value=9),
        )
    )

    assert isinstance(result, DegenerateBootstrapIntervalResult)
    assert result.degeneracy_reason == "sample_size_below_bca_minimum"
    assert result.method is StatisticalMethod.BCA_BOOTSTRAP

    insufficient_resamples = SciPyStatisticsAdapter().bca_bootstrap(
        BcaBootstrapRequest(
            values=(0.1, 0.2, 0.3),
            confidence=ConfidenceLevel(value=Decimal("0.95")),
            resamples=BootstrapResampleCount(value=1),
            bootstrap_seed=Seed(value=9),
        )
    )

    assert isinstance(insufficient_resamples, DegenerateBootstrapIntervalResult)
    assert insufficient_resamples.degeneracy_reason == "resamples_below_bca_minimum"


def test_scipy_procedures_and_in_repo_cliffs_delta_return_scalar_results() -> None:
    adapter = SciPyStatisticsAdapter()

    wilcoxon = adapter.wilcoxon(WilcoxonRequest(first=(1.0, 3.0, 5.0), second=(0.0, 2.0, 4.0)))
    spearman = adapter.spearman(SpearmanRequest(first=(1.0, 2.0, 3.0), second=(2.0, 4.0, 6.0)))
    divergence = adapter.jensen_shannon(JensenShannonRequest(first=(0.5, 0.5), second=(1.0, 0.0)))
    cliffs = adapter.cliffs_delta(CliffsDeltaRequest(first=(3.0, 4.0), second=(1.0, 2.0)))

    assert 0 <= wilcoxon.p_value <= 1
    assert spearman.statistic == 1.0
    assert 0 < divergence.value < 1
    assert cliffs.value == 1.0


def test_runner_implements_the_bca_port_with_a_private_input_reader() -> None:
    paired = PairedDeltaResult(
        direction=PairedDeltaDirection.B1_MINUS_B2,
        per_seed_delta=(0.1, 0.2, 0.3, 0.4, 0.5),
        scope_identity=StageFingerprint(value="a" * 64),
    )
    runner = SciPyStatisticalProcedureRunner(
        adapter=SciPyStatisticsAdapter(),
        inputs=_Inputs(input=StatisticalInput(paired_delta=paired, bootstrap_seed=Seed(value=3))),
    )
    request = RunStatisticalAnalysisRequest(
        analysis=StatisticalAnalysisSpec(
            method=StatisticalMethod.BCA_BOOTSTRAP,
            confidence=ConfidenceLevel(value=Decimal("0.95")),
            resamples=BootstrapResampleCount(value=500),
            paired_seed_count=5,
        ),
        input_artifacts=ArtifactReferenceCollection(references=()),
    )

    result = runner.run(request)

    assert isinstance(result, ConfirmatoryAnalysisResult)
    assert result.paired is paired
    assert isinstance(result.interval, ValidBootstrapIntervalResult)
    unsupported_analysis = StatisticalAnalysisSpec(
        method=StatisticalMethod.SPEARMAN,
        confidence=ConfidenceLevel(value=Decimal("0.95")),
        resamples=BootstrapResampleCount(value=500),
        paired_seed_count=5,
    )
    unsupported_request = RunStatisticalAnalysisRequest(
        analysis=unsupported_analysis,
        input_artifacts=ArtifactReferenceCollection(references=()),
    )

    with pytest.raises(StatisticsError, match="statistical procedure"):
        runner.run(unsupported_request)
