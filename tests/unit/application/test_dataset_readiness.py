"""Materialized evidence is sufficient to make a training readiness decision."""

from datp_core.application.dataset_audit import AuditDatasetUseCase
from datp_core.composition.root import build_application
from datp_core.domain.fingerprints import compute_payload_checksum
from datp_core.domain.identifiers import DatasetId, DatasetSetupId
from datp_core.domain.splits import MaterializedSplitEvidence, SplitManifest, SplitManifestEntry, SplitMembership


def _evidence(*, attack: bool) -> MaterializedSplitEvidence:
    entries = [
        SplitManifestEntry(
            source_path="source.csv",
            source_row_index=1,
            client_id="c1",
            membership=SplitMembership.TRAIN,
            is_attack=False,
        ),
        SplitManifestEntry(
            source_path="source.csv",
            source_row_index=2,
            client_id="c1",
            membership=SplitMembership.CALIBRATION,
            is_attack=False,
        ),
        SplitManifestEntry(
            source_path="source.csv",
            source_row_index=3,
            client_id="c1",
            membership=SplitMembership.CALIBRATION,
            is_attack=False,
        ),
        SplitManifestEntry(
            source_path="source.csv",
            source_row_index=4,
            client_id="c1",
            membership=SplitMembership.TEST,
            is_attack=attack,
        ),
    ]
    return MaterializedSplitEvidence(
        manifest=SplitManifest(entries=tuple(entries), minimum_benign_calibration_count=2),
        schema_columns=(
            ("split", "string"),
            ("client_id", "string"),
            ("is_attack", "bool"),
            ("source_path", "string"),
            ("source_row_index", "int64"),
        ),
    )


def test_readiness_records_observed_evidence_and_blocks_missing_declared_attack_support() -> None:
    config = build_application().config
    dataset = config.datasets[DatasetId("nbaiot")]
    setup = dataset.setup(DatasetSetupId("natural_devices"))
    audit = AuditDatasetUseCase()

    report = audit.assess_materialization(dataset, setup, _evidence(attack=True), compute_payload_checksum(b"source"))

    assert report.ready_for_training
    assert report.class_counts == {"benign": 3, "attack": 1}
    assert report.projected_eligible_client_ids == ("c1",)
    assert report.attack_evaluable
    assert b'"ready_for_training":true' in report.encode()

    blocked = audit.assess_materialization(dataset, setup, _evidence(attack=False), compute_payload_checksum(b"source"))
    assert not blocked.ready_for_training
    assert blocked.blocking_defects[0].code == "attack_evaluation_unavailable"


def test_readiness_reports_family_taxonomy_availability_per_dataset() -> None:
    config = build_application().config
    audit = AuditDatasetUseCase()

    nbaiot = config.datasets[DatasetId("nbaiot")]
    nbaiot_setup = nbaiot.setup(DatasetSetupId("natural_devices"))
    nbaiot_report = audit.assess_materialization(
        nbaiot, nbaiot_setup, _evidence(attack=True), compute_payload_checksum(b"source")
    )
    assert nbaiot_report.metadata_availability["family_taxonomy"] is True

    edge_iiotset = config.datasets[DatasetId("edge_iiotset")]
    edge_setup = edge_iiotset.setup(DatasetSetupId("sensor_groups"))
    edge_report = audit.assess_materialization(
        edge_iiotset, edge_setup, _evidence(attack=True), compute_payload_checksum(b"source")
    )
    assert edge_report.metadata_availability["family_taxonomy"] is False
