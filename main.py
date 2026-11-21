import sys

from source.parsing.errors import ParseError
from source.parsing.parser import MapParser
from source.planning.scheduler import plan_all
from source.simulation.output import build_lines
from source.visual.terminal import TerminalRenderer


def zone_counts(
    paths: list[list[tuple[str, int]]], turns: int
) -> list[dict[str, int]]:
    """Drones per zone after each turn (a drone in flight is in no zone)."""
    counts: list[dict[str, int]] = [{} for _ in range(turns)]
    for path in paths:
        at = {turn: zone for zone, turn in path}
        for t in range(1, turns + 1):
            zone = at.get(t, path[-1][0] if t > path[-1][1] else None)
            if zone:
                counts[t - 1][zone] = counts[t - 1].get(zone, 0) + 1
    return counts


def main(argv: list[str]) -> int:
    """Run the simulation on the map file given in argv.

    Returns:
        0 on success, 1 on error.
    """
    zones = "--zones" in argv
    argv = [arg for arg in argv if arg != "--zones"]
    if len(argv) != 1:
        print("Usage: ./main.py <map_file>", file=sys.stderr)
        return 1
    map_file = argv[0]

    try:
        graph = MapParser().parse(map_file)
        paths = plan_all(graph)
        lines = build_lines(graph, paths)
        turns = len(lines)
    except (ParseError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    states = zone_counts(paths, turns) if zones else None
    TerminalRenderer(graph).show(lines, states)
    print(f"Total turns: {turns}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        print("\nProgram interrupted by user", file=sys.stderr)
        sys.exit(130)
