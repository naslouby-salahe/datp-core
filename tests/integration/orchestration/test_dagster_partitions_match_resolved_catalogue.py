from datp_core.composition.root import build_application
from datp_core.orchestration.dagster.definitions import build_definitions
from datp_core.orchestration.dagster.partitions import experiment_partitions, seed_partitions


def test_partitions_cover_resolved_experiments_and_seed_cohorts() -> None:
    config = build_application().config
    assert set(experiment_partitions(config).get_partition_keys()) == {
        identifier.value for identifier in config.experiments.keys()
    }
    assert set(seed_partitions(config).get_partition_keys()) == {
        str(seed.value) for cohort in config.seed_cohorts.values() for seed in cohort.training_seeds
    }


def test_definition_uses_the_composition_root_configuration_instance() -> None:
    config = build_application().config
    assert build_definitions(config).get_implicit_global_asset_job_def().execute_in_process().success
