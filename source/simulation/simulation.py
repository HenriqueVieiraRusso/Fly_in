"""Turn counter for the Fly-in output."""

from source.models.graph import Graph


class SimulationError(Exception):
    """Raised when a schedule breaks a rule."""


class ScheduleChecker:
    """Reports how many turns the schedule takes."""

    def __init__(self, graph: Graph) -> None:
        """Store the graph."""
        self.graph = graph

    def check(self, lines: list[str]) -> int:
        """Return the number of turns (one per output line)."""
        return len(lines)
