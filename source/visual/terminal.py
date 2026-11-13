"""Colored terminal output for the simulation."""

import sys

from source.models.graph import Graph

RESET = "\033[0m"

# Color name (from the map file) -> ANSI code.
COLORS: dict[str, str] = {
    "black": "30", "red": "31", "green": "32", "yellow": "33",
    "blue": "34", "magenta": "35", "cyan": "36", "white": "37",
    "gray": "90", "grey": "90", "orange": "38;5;208",
    "purple": "38;5;129", "brown": "38;5;130", "pink": "38;5;213",
    "gold": "38;5;220", "maroon": "38;5;88",
}


class TerminalRenderer:
    """Prints the simulation lines with zone names in their map color."""

    def __init__(self, graph: Graph) -> None:
        """Store the graph; colors are used only on a real terminal."""
        self.graph = graph
        self.enabled: bool = sys.stdout.isatty()

    def paint(self, zone_name: str) -> str:
        """Return the zone name wrapped in its ANSI color, if it has one."""
        zone = self.graph.zones.get(zone_name)
        if not self.enabled or zone is None or zone.color is None:
            return zone_name
        code = COLORS.get(zone.color.lower())
        if code is None:
            return zone_name
        return f"\033[{code}m{zone_name}{RESET}"

    def paint_entry(self, entry: str) -> str:
        """Color one movement: D1-zone or D1-zoneA-zoneB (in flight)."""
        drone, _, target = entry.partition("-")
        names = [self.paint(name) for name in target.split("-")]
        return f"{drone}-{'-'.join(names)}"

    def show(self, lines: list[str]) -> None:
        """Print one colored line per turn."""
        for line in lines:
            print(" ".join(self.paint_entry(e) for e in line.split()))
