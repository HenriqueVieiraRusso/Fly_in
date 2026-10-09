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
        if self.max_link_capacity < 1:
            raise ValueError(
                "Max link capacity must be a positive number, "
                f"got {self.max_link_capacity}"
            )

        if self.zone_a == self.zone_b:
            raise ValueError(
                f"A zone can't connect to itself ('{self.zone_a}')"
            )

    @property
    def key(self) -> frozenset[str]:
        """Order-independent identity, so a-b and b-a match."""
        return frozenset((self.zone_a, self.zone_b))

    def other(self, zone_name: str) -> str:
        """Return the zone on the opposite end from `zone_name`."""
        if zone_name == self.zone_a:
            return self.zone_b
        elif zone_name == self.zone_b:
            return self.zone_a
        else:
            raise ValueError(f"'{zone_name}' is not part of this connection")
