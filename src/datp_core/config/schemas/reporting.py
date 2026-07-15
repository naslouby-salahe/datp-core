from pydantic import BaseModel, ConfigDict

from datp_core.domain.artifacts.keys import SerializationFormat
from datp_core.domain.evaluation.statistical_results import ClaimOutcome
from datp_core.domain.experiments.protocols import FigureType, ReportArtifactType, TableType


class ReportingSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ReportingFormatConfig(ReportingSchema):
    artifact_type: ReportArtifactType
    formats: tuple[SerializationFormat, ...]


class ReportingConfig(ReportingSchema):
    tables: tuple[TableType, ...]
    figures: tuple[FigureType, ...]
    report_artifacts: tuple[ReportArtifactType, ...]
    formats: tuple[ReportingFormatConfig, ...]
    wording_outcomes: tuple[ClaimOutcome, ...]
