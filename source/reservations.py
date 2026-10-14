"""Reservation table for the Fly-in simulation.

Convention: turn N is the Nth output line. A drone's position "at turn N"
is where it is after that line. Turn 0 is the initial state, before any
line is printed.
"""

from source.connection import Connection
from source.zone import Zone


def trip_turns(dst: Zone) -> int:
    """Return how many turns a move into `dst` takes.

    Raises:
        ValueError: If `dst` is blocked.
    """
    return dst.zone_type.movement_cost


class ReservationTable:
    """Tracks zone and link usage per turn.

    A move that starts on turn T and takes c turns:
      - uses its link on turns T .. T + c - 1 (both turns for a
        restricted zone), and
      - puts the drone in the destination at turn T + c - 1.

    Attributes:
        zone_usage: (zone name, turn) -> drones present after that turn.
        link_usage: (connection key, turn) -> drones using the link.
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

        for t in range(turn, turn + duration):
            used = self.link_usage.get((conn.key, t), 0)
            if used >= conn.max_link_capacity:
                return False

        return self.can_stay(dst, turn + duration - 1)

    def reserve_move(self, dst: Zone, conn: Connection, turn: int) -> None:
        """Record a move to `dst` that starts at `turn`."""
        duration = trip_turns(dst)

        for t in range(turn, turn + duration):
            key = (conn.key, t)
            self.link_usage[key] = self.link_usage.get(key, 0) + 1

        self.reserve_stay(dst, turn + duration - 1)
