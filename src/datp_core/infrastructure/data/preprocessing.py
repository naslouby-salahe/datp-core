from dataclasses import dataclass

from datp_core.domain.data.preprocessing import (
    FittedStatisticPolicy,
    NormalizationStrategy,
    PreprocessingSpec,
)
from datp_core.domain.errors import PreprocessingError
from datp_core.infrastructure.data.streaming import (
    ParquetBatchStream,
    StreamingColumnStatistics,
    StreamingNumericProfile,
    numeric_column_profile,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class FittedNumericPreprocessor:
    strategy: NormalizationStrategy
    statistics: tuple[StreamingColumnStatistics, ...]
    training_row_order_checksum: str


@dataclass(frozen=True, slots=True, kw_only=True)
class TwoPassNumericPreprocessor:
    training: ParquetBatchStream
    feature_columns: tuple[str, ...]
    preprocessing: PreprocessingSpec

    def fit(self) -> FittedNumericPreprocessor:
        _validate_supported_preprocessing(self)
        first_pass = _numeric_profile_or_error(self)
        second_pass = _numeric_profile_or_error(self)
        if first_pass != second_pass:
            raise _preprocessing_error(self, "training source changed between the two fixed streaming passes")
        return FittedNumericPreprocessor(
            strategy=self.preprocessing.strategy,
            statistics=first_pass.statistics,
            training_row_order_checksum=first_pass.row_order_checksum,
        )


def _validate_supported_preprocessing(preprocessor: TwoPassNumericPreprocessor) -> None:
    if preprocessor.training.batch_rows != preprocessor.preprocessing.chunking.preprocessing_chunk_rows:
        raise _preprocessing_error(
            preprocessor,
            "training scanner batch rows differ from the frozen preprocessing chunk",
        )
    if preprocessor.preprocessing.fitted_stat_policy is not FittedStatisticPolicy.EXACT_TWO_PASS:
        raise _preprocessing_error(
            preprocessor,
            "numeric streaming fitting requires the exact two-pass statistic policy",
        )
    if preprocessor.preprocessing.strategy is NormalizationStrategy.ROBUST:
        raise _preprocessing_error(preprocessor, "exact robust fitting requires its dedicated bounded algorithm")


def _numeric_profile_or_error(preprocessor: TwoPassNumericPreprocessor) -> StreamingNumericProfile:
    try:
        return numeric_column_profile(preprocessor.training, preprocessor.feature_columns)
    except (TypeError, ValueError) as error:
        raise _preprocessing_error(preprocessor, str(error)) from error


def _preprocessing_error(preprocessor: TwoPassNumericPreprocessor, detail: str) -> PreprocessingError:
    return PreprocessingError(
        detail=detail,
        strategy=preprocessor.preprocessing.strategy.value,
        scope=preprocessor.preprocessing.scope.value,
    )
