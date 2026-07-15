import pytest
from hypothesis import given
from hypothesis import strategies as st

from datp_core.domain.artifacts.references import StageFingerprint
from datp_core.domain.errors import DomainValidationError
from datp_core.domain.experiments.identities import ExperimentId
from datp_core.domain.runtime.seeds import Seed, SeedRole, derive_seed


@given(st.from_regex(r"E-[A-Z]+[0-9]+", fullmatch=True))
def test_experiment_ids_accept_generated_canonical_values(value: str) -> None:
    assert ExperimentId(value=value).value == value


@given(st.text().filter(lambda value: value == "" or not value.startswith("E-")))
def test_experiment_ids_reject_generated_noncanonical_values(value: str) -> None:
    with pytest.raises(DomainValidationError):
        ExperimentId(value=value)


@given(st.integers(min_value=0, max_value=2**63 - 1), st.text(alphabet="0123456789abcdef", min_size=64, max_size=64))
def test_seed_derivation_is_deterministic_for_generated_inputs(experiment_seed: int, fingerprint: str) -> None:
    seed = Seed(value=experiment_seed)
    stage_fingerprint = StageFingerprint(value=fingerprint)
    first_derived_seed = derive_seed(
        experiment_seed=seed,
        role=SeedRole.TRAINING_INIT,
        stage_fingerprint=stage_fingerprint,
    )
    repeated_derived_seed = derive_seed(
        experiment_seed=seed,
        role=SeedRole.TRAINING_INIT,
        stage_fingerprint=stage_fingerprint,
    )

    assert first_derived_seed == repeated_derived_seed
