from source.models.graph import Graph
from source.planning.pathfinder import State


def _connection_name(graph: Graph, zone_a: str, zone_b: str) -> str:
    """Return the connection name used for a drone in flight.

    Raises:
        ValueError: If the two zones are not connected.
    """
    conn = graph.connection_between(zone_a, zone_b)
    if conn is None:
        raise ValueError(
            f"No connection between '{zone_a}' and '{zone_b}'"
        )
    return f"{conn.zone_a}-{conn.zone_b}"


def build_lines(graph: Graph, paths: list[list[State]]) -> list[str]:
    """Return one output line per turn.

    Args:
        graph: The map, used to name connections.
        paths: One path per drone, in drone order (D1 first).

    Returns:
        The output lines, from turn 1 to the last turn.
    """
    turns: dict[int, list[str]] = {}

    for drone_index, path in enumerate(paths, start=1):
        drone_name = f"D{drone_index}"

        for (zone_a, turn_a), (zone_b, turn_b) in zip(path, path[1:]):
            if zone_a == zone_b:
                continue

            if turn_b - turn_a > 1:
                name = _connection_name(graph, zone_a, zone_b)
                turns.setdefault(turn_a + 1, []).append(
                    f"{drone_name}-{name}"
                )

            turns.setdefault(turn_b, []).append(f"{drone_name}-{zone_b}")

    total = max(turns.keys(), default=0)
    return [
        " ".join(turns.get(turn, []))
        for turn in range(1, total + 1)
    ]
