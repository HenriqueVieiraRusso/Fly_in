"""Graph model for the Fly-in drone network."""

from source.connection import Connection
from source.zone import Zone


class Graph:
    """The whole map: zones, connections and the number of drones.

    Attributes:
        nb_drones: Number of drones that start at the start hub.
        zones: Map from zone name to Zone.
        connections: Every connection in the map, in file order.
        start: The start hub (None until added).
        end: The end hub (None until added).
    """

    def __init__(self, nb_drones: int = 1) -> None:
        """Create an empty graph."""
        if nb_drones < 1:
            raise ValueError(
                f"nb_drones must be a positive integer, got {nb_drones}"
            )
        self.nb_drones: int = nb_drones
        self.zones: dict[str, Zone] = {}
        self.connections: list[Connection] = []
        self.start: Zone | None = None
        self.end: Zone | None = None
        self._adjacency: dict[str, list[Connection]] = {}
        self._seen_keys: set[frozenset[str]] = set()

    def add_zone(self, zone: Zone) -> None:
        """Add a zone to the graph.

        Raises:
            ValueError: If the name already exists, or if a second
                start or end hub is added.
        """
        if zone.name in self.zones:
            raise ValueError(f"Duplicate zone name '{zone.name}'")
        if zone.is_start:
            if self.start is not None:
                raise ValueError("There can only be one start_hub")
            self.start = zone
        if zone.is_end:
            if self.end is not None:
                raise ValueError("There can only be one end_hub")
            self.end = zone
        self.zones[zone.name] = zone
        self._adjacency[zone.name] = []

    def add_connection(self, connection: Connection) -> None:
        """Add a connection between two existing zones.

        Raises:
            ValueError: If a zone is undefined or the connection is a
                duplicate (a-b and b-a count as the same).
        """
        if connection.zone_a not in self.zones:
            raise ValueError(
                f"Unknown zone '{connection.zone_a}'")

        if connection.zone_b not in self.zones:
            raise ValueError(
                f"Unknown zone '{connection.zone_b}'")

        if connection.key in self._seen_keys:
            raise ValueError(
                f"fDuplicate connection "
                f"'{connection.zone_a}-{connection.zone_b}'"
                )

        self._seen_keys.add(connection.key)
        self.connections.append(connection)
        self._adjacency[connection.zone_a].append(connection)
        self._adjacency[connection.zone_b].append(connection)

        """_seen_keys.add(...): remembers this connection,
        so a later b-a gets caught as a duplicate.
        connections.append(...): keeps the full list in file order.
        and 4. Add it to the adjacency list of both ends. Links are
        bidirectional, so standing on zone_a you must see it, and standing on
        zone_b you must see it too. If you only add it to one,
        neighbors would work in one direction only."""

    def get_zone(self, name: str) -> Zone:
        """Return the zone with this name.

        Raises:
            ValueError: If no such zone exists.
        """
        try:
            return self.zones[name]
        except KeyError:
            raise ValueError(f"Unknown zone '{name}'") from None

    def connections_of(self, name: str) -> list[Connection]:
        """Return every connection touching this zone."""
        return list(self._adjacency[name])

    def neighbors(self, name: str) -> list[Zone]:
        """Return the zones reachable from `name`, skipping blocked ones."""

        result = []

        for connection in self._adjacency[name]:
            other_name = connection.other(name)
            zone = self.zones[other_name]
            if not zone.is_blocked:
                result.append(zone)

        return result
