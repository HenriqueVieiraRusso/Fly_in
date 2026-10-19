"""Plan a schedule for every drone."""

from source.models.graph import Graph
from source.planning.pathfinder import State, find_path
from source.planning.reservations import ReservationTable


def reserve_path(
    graph: Graph, table: ReservationTable, path: list[State]
) -> None:
    """Record every wait and move of `path` in the table.

    Raises:
        ValueError: If two consecutive zones are not connected.
    """
    for (zone_a, turn_a), (zone_b, turn_b) in zip(path, path[1:]):
        dst = graph.zones[zone_b]
        if zone_a == zone_b:
            # A wait: the drone is in the same zone after line turn_b.
            table.reserve_stay(dst, turn_b)
        else:
            # A move: it leaves on line turn_a + 1.
            conn = graph.connection_between(zone_a, zone_b)
            if conn is None:
                raise ValueError(
                    f"No connection between '{zone_a}' and '{zone_b}'"
                )
            table.reserve_move(dst, conn, turn_a + 1)


def plan_all(graph: Graph) -> list[list[State]]:
    """Return one path per drone, in drone order (D1 first).

    Drones are planned one at a time. Each path is reserved in the
    table before the next drone is planned, so later drones route
    around the earlier ones.

    Raises:
        ValueError: If some drone cannot reach the end hub.
    """
    table = ReservationTable()
    paths: list[list[State]] = []
    for drone in range(1, graph.nb_drones + 1):
        path = find_path(graph, table)
        if path is None:
            raise ValueError(f"No path to the end hub for drone D{drone}")
        reserve_path(graph, table, path)
        paths.append(path)
    return paths
