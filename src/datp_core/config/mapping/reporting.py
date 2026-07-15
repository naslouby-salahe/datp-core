from datp_core.config.schemas.reporting import ReportingConfig
from datp_core.domain.experiments.protocols import ReportingPolicy
from datp_core.domain.runtime.seeds import EnumMap, EnumMapEntry


def map_reporting_config(schema: ReportingConfig) -> ReportingPolicy:
    entries = tuple(EnumMapEntry(key=item.artifact_type, value=item.formats) for item in schema.formats)
    return ReportingPolicy(
        tables=schema.tables,
        figures=schema.figures,
        report_artifacts=schema.report_artifacts,
        formats=EnumMap(entries=entries, allowed_keys=schema.report_artifacts, is_sparse=False),
        wording_outcomes=schema.wording_outcomes,
    )
