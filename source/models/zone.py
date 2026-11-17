from dataclasses import dataclass
from enum import Enum


class ZoneType(Enum):
    """Kinds of zones, each with a cost to enter."""

    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"

    @property
    def movement_cost(self) -> int:
        """Return the number of turns needed to enter this zone type.

        Raises:
            ValueError: If the zone is blocked and cannot be entered.
        """
        if self is ZoneType.BLOCKED:
            raise ValueError("Blocked zones cannot be entered")
        if self is ZoneType.RESTRICTED:
            return 2
        return 1

    @classmethod
    def from_string(cls, value: str) -> "ZoneType":
        """Convert a string from the map file into a ZoneType.

        Raises:
            ValueError: If the string is not a valid zone type.
        """
        try:
            return cls(value)
        except ValueError:
            valid = ", ".join(zone_type.value for zone_type in cls)
            raise ValueError(
                f"Invalid zone type '{value}' (expected one of: {valid})"
            ) from None


@dataclass(frozen=True)
class Zone:
    """A single zone (hub) in the network.

    Attributes:
        name: Unique zone name (no dashes or spaces).
        x: Integer x coordinate.
        y: Integer y coordinate.
        zone_type: Type of the zone.
        color: Optional color name used for display.
        max_drones: Max drones allowed at once (ignored for start/end).
        is_start: True if start hub.
        is_end: True the end hub.
    """

    name: str
    x: int
    y: int
    zone_type: ZoneType = ZoneType.NORMAL
    color: str | None = None
    max_drones: int = 1
    is_start: bool = False
    is_end: bool = False

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Zone name cannot be empty")
        if "-" in self.name:
            raise ValueError(
                f"Zone name '{self.name}' can not contain dashes (-)"
                )
        if " " in self.name:
            raise ValueError(
                f"Zone name '{self.name}' can not contain spaces"
                )
        if self.has_capacity_limit and self.max_drones < 1:
            raise ValueError(
                f"Max drones must be a positive int, got {self.max_drones}"
                )
        if self.zone_type is ZoneType.BLOCKED and not self.has_capacity_limit:
            raise ValueError(
                f"The start and end hubs cannot be blocked ('{self.name}')"
                )

    @property
    def is_blocked(self) -> bool:
        """Return True if drones may never enter this zone."""
        return self.zone_type is ZoneType.BLOCKED

    @property
    def has_capacity_limit(self) -> bool:
        """Return True if not end or start."""
        return not (self.is_start or self.is_end)


"""if self.max_drones < 1:
            raise ValueError(
                f"Max drones must be a positive int, got{self.max_drones}"
                )
what is max_drones is 0



The generated __init__ calls this automatically after all fields are set
how does this happen after the post_init, what is the generated init

what does a map need to be for this to happen
if not self.name:
            raise ValueError("Zone name cannot be empty")

what will be the default color if none is given
                """
