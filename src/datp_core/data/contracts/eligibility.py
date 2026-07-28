"""Eligibility and readiness-gate contracts."""

from __future__ import annotations

from pydantic import PositiveInt

from datp_core.core.identifiers import EligibilityPolicyId
from datp_core.core.numbers import Probability
from datp_core.data.contracts.base import StrictFrozenModel
from datp_core.data.contracts.enums import DatasetCapability
from datp_core.data.contracts.values import GateId


class EligibilityPolicy(StrictFrozenModel):
    identifier: EligibilityPolicyId
    minimum_benign_calibration_count: PositiveInt
    require_non_empty_benign_test: bool
    required_attack_capabilities: tuple[DatasetCapability, ...]
    exclude_ineligible_clients_from_primary_dispersion: bool
    zero_eligible_clients_is_blocking: bool


class ReadinessGate(StrictFrozenModel):
    identifier: GateId
    minimum_eligible_clients: PositiveInt
    minimum_eligible_proportion: Probability
    required_capabilities: tuple[DatasetCapability, ...]
