import sys

from source.parsing.errors import ParseError
from source.parsing.parser import MapParser
from source.planning.scheduler import plan_all
from source.simulation.output import build_lines
from source.simulation.simulation import ScheduleChecker, SimulationError
from source.visual.terminal import TerminalRenderer


def main(argv: list[str]) -> int:
    """Run the simulation on the map file given in argv.

    Returns:
        0 on success, 1 on error.
    """
    if len(argv) != 1:
        print("Usage: ./main.py <map_file>", file=sys.stderr)
        return 1
    map_file = argv[0]

    try:
        graph = MapParser().parse(map_file)
        paths = plan_all(graph)
        lines = build_lines(graph, paths)
        checker = ScheduleChecker(graph)
        turns = checker.check(lines)
    except (ParseError, ValueError, SimulationError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    TerminalRenderer(graph).show(lines)
    print(f"Total turns: {turns}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        print("\nProgram interrupted by user", file=sys.stderr)
        sys.exit(130)
