from pathlib import Path

from datp_core.config.compose import ComposeTestConfigurationRequest, compose_test_configuration
from datp_core.config.locking import ProtocolLockVerificationMode
from datp_core.domain.experiments.specifications import ProfileCatalogueSpec


def composed_profile_catalogue() -> ProfileCatalogueSpec:
    return compose_test_configuration(
        ComposeTestConfigurationRequest(
            configuration_root=Path(__file__).resolve().parents[2] / "configs",
            test_profile_id="unit",
            protocol_lock_mode=ProtocolLockVerificationMode.REQUIRED,
        )
    ).profile_catalogue
