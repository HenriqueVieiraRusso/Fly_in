"""Reservation table for the Fly-in simulation.

Convention: turn N is the Nth output line. A drone's position "at turn N"
is where it is after that line. Turn 0 is the initial state, before any
line is printed.
"""

from source.models.connection import Connection
from source.models.zone import Zone


def trip_turns(dst: Zone) -> int:
    """Return how many turns a move into `dst` takes.

    Raises:
        ValueError: If `dst` is blocked.
    """
    return dst.zone_type.movement_cost


class ReservationTable:
    """Tracks zone and link usage per turn.

    A move that departs on line T and takes c turns (c = 1 for normal
    and priority zones, 2 for restricted zones):
      - uses its link only on line T. The link is freed on the line
        the drone arrives, so another drone may start crossing then.
      - puts the drone in the destination zone at turn T + c - 1,
        which is the line it arrives on.

    A drone waiting in a zone is booked in that zone for every turn it
    stays. A drone that has left a zone is not counted in it, so the
    space is free for another drone on the same line.

    Attributes:
        zone_usage: (zone name, turn) -> number of drones in that zone
            after that turn.
        link_usage: (connection key, turn) -> number of drones that
            start crossing that connection on that line.
    """

    def __init__(self) -> None:
        """Create an empty table."""
        self.zone_usage: dict[tuple[str, int], int] = {}
        self.link_usage: dict[tuple[frozenset[str], int], int] = {}

    def can_stay(self, zone: Zone, turn: int) -> bool:
        """Return True if one more drone may be in `zone` at `turn`."""
        if not zone.has_capacity_limit:
            return True
        used = self.zone_usage.get((zone.name, turn), 0)
        return used < zone.max_drones

    def reserve_stay(self, zone: Zone, turn: int) -> None:
        """Record a drone being in `zone` at `turn`."""
        key = (zone.name, turn)
        self.zone_usage[key] = self.zone_usage.get(key, 0) + 1

    def can_move(self, dst: Zone, conn: Connection, turn: int) -> bool:
        """Return True if a drone may start a move to `dst` at `turn`."""
        if dst.is_blocked:
            return False
        duration = trip_turns(dst)

        used = self.link_usage.get((conn.key, turn), 0)
        if used >= conn.max_link_capacity:
            return False

        return self.can_stay(dst, turn + duration - 1)

    def reserve_move(self, dst: Zone, conn: Connection, turn: int) -> None:
        """Record a move to `dst` that starts at `turn`."""
        duration = trip_turns(dst)

        key = (conn.key, turn)
        self.link_usage[key] = self.link_usage.get(key, 0) + 1

        self.reserve_stay(dst, turn + duration - 1)
