"""Independent checker: replay output lines and verify every rule.

Convention: line N is the Nth output line. Entries are D<ID>-<zone>, or
D<ID>-<connection> for a drone entering a connection toward a
restricted zone. Zone names cannot contain dashes, so any target with a
dash is a connection.
"""

from source.models.graph import Graph
from source.models.zone import ZoneType


class SimulationError(Exception):
    """Raised when a schedule breaks a rule."""


class ScheduleChecker:
    """Replays output lines and verifies every rule."""

    def __init__(self, graph: Graph) -> None:
        """Store the graph and prepare empty per-turn usage history."""
        self.graph = graph
        self.zone_history: list[dict[str, int]] = []
        self.link_history: list[dict[frozenset[str], int]] = []

    @staticmethod
    def _parse_output_line(number: int, line: str) -> dict[str, str]:
        """Split one output line into {drone id: target}."""
        moves: dict[str, str] = {}
        for entry in line.split():
            drone, sep, target = entry.partition("-")
            if not sep or not target or not drone.startswith("D"):
                raise SimulationError(f"line {number}: bad entry '{entry}'")
            if drone in moves:
                raise SimulationError(
                    f"line {number}: {drone} moves twice"
                )
            moves[drone] = target
        if not moves:
            raise SimulationError(f"line {number}: no drone moves")
        return moves

    def check(self, lines: list[str]) -> int:
        """Replay `lines` from scratch and verify all the rules.

        Args:
            graph: The map.
            lines: The output lines, one per turn.

        Returns:
            The number of turns.

        Raises:
            SimulationError: On the first rule that is broken.
        """
        if self.graph.start is None or self.graph.end is None:
            raise SimulationError("map has no start or end hub")
        end = self.graph.end.name

        position = {
            f"D{i}": self.graph.start.name
            for i in range(1, self.graph.nb_drones + 1)
        }
        # drone -> (connection key, destination zone)
        in_flight: dict[str, tuple[frozenset[str], str]] = {}

        self.zone_history.clear()
        self.link_history.clear()

        for number, line in enumerate(lines, start=1):
            moves = self._parse_output_line(number, line)
            link_use: dict[frozenset[str], int] = {}

            for drone in in_flight:
                if drone not in moves:
                    raise SimulationError(
                        f"line {number}: {drone} must arrive this turn"
                    )

            for drone, target in moves.items():
                if drone not in position:
                    raise SimulationError(
                        f"line {number}: unknown drone {drone}"
                    )

                if drone in in_flight:
                    key, dest = in_flight.pop(drone)
                    if target != dest:
                        raise SimulationError(
                            f"line {number}: {drone} must arrive at "
                            f"'{dest}', not '{target}'"
                        )
                    link_use[key] = link_use.get(key, 0) + 1
                    position[drone] = dest
                    continue

                current = position[drone]
                if current == end:
                    raise SimulationError(
                        f"line {number}: {drone} is already delivered"
                    )

                if "-" in target:
                    a, _, b = target.partition("-")
                    conn = self.graph.connection_between(a, b)
                    if conn is None or current not in (a, b):
                        raise SimulationError(
                            f"line {number}: {drone} cannot use "
                            f"connection '{target}' from '{current}'"
                        )
                    dest = conn.other(current)
                    if (
                            self.graph.zones[dest].zone_type
                            is not ZoneType.RESTRICTED
                    ):
                        raise SimulationError(
                            f"line {number}: '{target}' leads to a "
                            "non-restricted zone"
                        )
                    in_flight[drone] = (conn.key, dest)
                    link_use[conn.key] = link_use.get(conn.key, 0) + 1
                else:
                    conn = self.graph.connection_between(current, target)
                    if conn is None:
                        raise SimulationError(
                            f"line {number}: {drone} cannot go from "
                            f"'{current}' to '{target}'"
                        )
                    zone = self.graph.zones[target]
                    if zone.is_blocked:
                        raise SimulationError(
                            f"line {number}: '{target}' is blocked"
                        )
                    if zone.zone_type is ZoneType.RESTRICTED:
                        raise SimulationError(
                            f"line {number}: '{target}' is restricted, "
                            "enter it through its connection"
                        )
                    position[drone] = target
                    link_use[conn.key] = link_use.get(conn.key, 0) + 1

            # Link capacity (a restricted trip counts on both lines).
            for key, used in link_use.items():
                a, b = tuple(key)
                conn = self.graph.connection_between(a, b)
                if conn is not None and used > conn.max_link_capacity:
                    raise SimulationError(
                        f"line {number}: link '{a}-{b}' over capacity "
                        f"({used} > {conn.max_link_capacity})"
                    )

            # Zone capacity, counted AFTER all moves of the line, so drones
            # leaving free their space on the same turn.
            counts: dict[str, int] = {}
            for drone, zone_name in position.items():
                if drone not in in_flight:
                    counts[zone_name] = counts.get(zone_name, 0) + 1
            for zone_name, used in counts.items():
                zone = self.graph.zones[zone_name]
                if zone.has_capacity_limit and used > zone.max_drones:
                    raise SimulationError(
                        f"line {number}: zone '{zone_name}' over capacity "
                        f"({used} > {zone.max_drones})"
                    )

            self.zone_history.append(counts)
            self.link_history.append(link_use)

        if in_flight:
            raise SimulationError("a drone is still in flight at the end")
        for drone, zone_name in position.items():
            if zone_name != end:
                raise SimulationError(
                    f"{drone} ends in '{zone_name}', not in '{end}'"
                )
        return len(lines)
