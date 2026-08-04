from datp_core.pipeline.campaign import build_campaign
from datp_core.pipeline.planning import expand_experiment_plan


def test_campaign_contains_only_executable_plan_entries() -> None:
    plan = expand_experiment_plan()
    campaign = build_campaign(plan)
    assert all(entry.ordinal == index for index, entry in enumerate(campaign.entries))
    assert campaign.digest
