"""Connection model for the Fly-in drone network."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Connection:
    """A bidirectional link between two zones.

    Attributes:
        zone_a: Name of the first zone.
        zone_b: Name of the second zone.
        max_link_capacity: Max drones traversing at once.
    """

    zone_a: str
    zone_b: str
    max_link_capacity: int = 1

    def __post_init__(self) -> None:
        """Validate fields right after construction."""
        # TODO: raise ValueError if max_link_capacity < 1
        # TODO: raise ValueError if zone_a == zone_b (self-loop)
        pass

    @property
    def key(self) -> frozenset[str]:
        """Order-independent identity, so a-b and b-a match."""
        return frozenset((self.zone_a, self.zone_b))

    def other(self, zone_name: str) -> str:
        """Return the zone on the opposite end from `zone_name`."""
        if zone_name == self.zone_a:
            return self.zone_b
        if zone_name == self.zone_b:
            return self.zone_a
        raise ValueError(f"'{zone_name}' is not part of this connection")
