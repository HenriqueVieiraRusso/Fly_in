"""Entry point for the Fly-in drone routing simulation."""

import sys

from source.parsing.errors import ParseError
from source.simulation.output import build_lines
from source.parsing.parser import MapParser
from source.planning.scheduler import plan_all
from source.simulation.simulation import ScheduleChecker, SimulationError
from source.visual.terminal import TerminalRenderer


def main(argv: list[str]) -> int:
    """Run the simulation, print the turns, then show the window.

    Args:
        argv: Command-line arguments, excluding the program name.

    Returns:
        Process exit code (0 on success, 1 on error).
    """
    if len(argv) != 1:
        print("Usage: python3 main.py <map_file>", file=sys.stderr)
        return 1
    try:
        graph = MapParser().parse(argv[0])
        paths = plan_all(graph)
        lines = build_lines(graph, paths)
        turns = ScheduleChecker(graph).check(lines)
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
