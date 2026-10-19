"""Find the earliest-arriving schedule for one drone.

Convention (same as reservations.py): turn N is the Nth output line.
A state (zone, T) means "the drone is in `zone` after line T", so its
next move is made on line T + 1.
"""

import heapq
from itertools import count

from source.models.graph import Graph
from source.planning.reservations import ReservationTable, trip_turns
from source.models.zone import ZoneType

State = tuple[str, int]


def find_path(
    graph: Graph,
    table: ReservationTable,
    start_turn: int = 0,
) -> list[State] | None:
    """Return the earliest-arriving schedule, or None if no path exists.

    Each state is (zone name, turn). Waiting adds one turn; moving adds
    the destination zone's movement cost. A drone in transit toward a
    restricted zone has no state: it jumps from (a, T) to (r, T + 2).
    Among equally early arrivals, paths through more priority zones win.
    """
    if graph.start is None or graph.end is None:
        return None

    start = graph.start
    end = graph.end

    # Bound the search so an unreachable destination cannot loop forever.
    max_turn = start_turn + len(graph.zones) * max(1, graph.nb_drones) + 10

    start_state: State = (start.name, start_turn)
    counter = count()
    queue: list[tuple[int, int, int, State]] = []
    heapq.heappush(queue, (start_turn, 0, next(counter), start_state))

    visited: set[State] = set()
    parent: dict[State, State | None] = {start_state: None}
    priority_count: dict[State, int] = {start_state: 0}

    def offer(nxt: State, prev: State, priority: int) -> None:
        """Queue `nxt` unless it is done or already reached as well."""
        if nxt in visited:
            return
        if nxt in parent and priority_count[nxt] >= priority:
            return
        parent[nxt] = prev
        priority_count[nxt] = priority
        heapq.heappush(queue, (nxt[1], -priority, next(counter), nxt))

    while queue:
        _, _, _, state = heapq.heappop(queue)
        if state in visited:
            continue
        visited.add(state)

        zone_name, current_turn = state
        if zone_name == end.name:
            return _reconstruct_path(parent, state)
        if current_turn >= max_turn:
            continue

        zone = graph.zones[zone_name]
        base = priority_count[state]
        next_turn = current_turn + 1

        # Option 1: wait here for one more turn.
        if table.can_stay(zone, next_turn):
            offer((zone_name, next_turn), state, base)

        # Option 2: move to a neighbour, leaving on line `next_turn`.
        for dst in graph.neighbors(zone_name):
            conn = graph.connection_between(zone_name, dst.name)
            if conn is None:
                continue
            if not table.can_move(dst, conn, next_turn):
                continue
            # Leaves on line T + 1, occupies dst after line
            # T + 1 + duration - 1 = T + duration.
            arrival = current_turn + trip_turns(dst)
            if arrival > max_turn:
                continue
            bonus = int(dst.zone_type is ZoneType.PRIORITY)
            offer((dst.name, arrival), state, base + bonus)

    return None


def _reconstruct_path(
    parent: dict[State, State | None], state: State
) -> list[State]:
    """Rebuild the schedule from the parent links."""
    path: list[State] = []
    current: State | None = state
    while current is not None:
        path.append(current)
        current = parent[current]
    path.reverse()
    return path
