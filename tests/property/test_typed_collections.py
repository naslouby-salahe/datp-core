import pytest
from hypothesis import given
from hypothesis import strategies as st

from datp_core.domain.errors import DomainValidationError
from datp_core.domain.experiments.identities import ClientId
from datp_core.domain.learning.scores import ClientMap, ClientMapEntry, ClientRoster


@given(st.lists(st.text(alphabet="abc123-", min_size=1, max_size=8), min_size=1, max_size=8, unique=True))
def test_client_map_preserves_canonical_roster_order(values: list[str]) -> None:
    ordered = tuple(sorted(values))
    roster = ClientRoster(client_ids=tuple(ClientId(value=value) for value in ordered))
    entries = tuple(ClientMapEntry(client_id=ClientId(value=value), value=value) for value in ordered)
    assert ClientMap(roster=roster, entries=entries).entries == entries


@given(st.lists(st.text(alphabet="abc123-", min_size=1, max_size=8), min_size=2, max_size=8, unique=True))
def test_client_roster_rejects_generated_noncanonical_order(values: list[str]) -> None:
    ordered = sorted(values)
    reversed_values = tuple(reversed(ordered))
    if reversed_values != tuple(ordered):
        with pytest.raises(DomainValidationError):
            ClientRoster(client_ids=tuple(ClientId(value=value) for value in reversed_values))
