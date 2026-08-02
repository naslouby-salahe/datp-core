from dataclasses import dataclass


@dataclass
class _Box[T]:
    """Single-slot mutable box for `AtomicPublication.write` closures to populate."""

    value: T | None = None
