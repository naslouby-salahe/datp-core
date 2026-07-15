from dataclasses import dataclass

from datp_core.domain.data.splitting import SplitRole
from datp_core.domain.errors import SplitError
from datp_core.infrastructure.data.partitioning import ClientPartitionStream


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientSplitStream:
    partition: ClientPartitionStream
    split_role: SplitRole


def stable_client_split_order(splits: tuple[ClientSplitStream, ...]) -> tuple[ClientSplitStream, ...]:
    destinations = tuple((split.partition.client_id, split.split_role) for split in splits)
    if len(set(destinations)) != len(destinations):
        duplicate = next(destination for destination in destinations if destinations.count(destination) > 1)
        raise SplitError(
            dataset="unresolved",
            regime="unresolved",
            coverage=f"{duplicate[0].value}/{duplicate[1].value}",
            detail="each client and split role must have one source stream",
        )
    return tuple(
        sorted(
            splits,
            key=lambda split: (split.partition.client_id.value, tuple(SplitRole).index(split.split_role)),
        )
    )
