"""Entry point for the Fly-in drone routing simulation."""

import sys

from source.errors import ParseError
from source.output import build_lines
from source.parser import MapParser
from source.scheduler import plan_all
from source.simulation import ScheduleChecker, SimulationError


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

    for line in lines:
        print(line)
    print(f"Total turns: {turns}", file=sys.stderr)

    try:
        from source.gui import PygameRenderer
        PygameRenderer(graph, lines).run()
    except KeyboardInterrupt:
        pass  # Ctrl+C: leave quietly
    except Exception as error:  # pygame missing, no display, ...
        print(f"Window unavailable: {error}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        sys.exit(130)
