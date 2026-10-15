"""Colored terminal rendering of a simulation."""

from source.graph import Graph

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

# The subject allows any single-word color, so unknown names are
# simply printed without color.
ANSI_COLORS: dict[str, str] = {
    "black": "\033[30m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "purple": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
    "gray": "\033[90m",
    "grey": "\033[90m",
    "orange": "\033[38;5;208m",
    "brown": "\033[38;5;94m",
    "pink": "\033[38;5;213m",
}


class Renderer:
    """Prints a simulation with colors and a per-turn summary.

    Attributes:
        graph: The map, used to look up zone colors.
    """

    def __init__(self, graph: Graph) -> None:
        """Store the graph."""
        self.graph = graph

    @staticmethod
    def paint(text: str, color: str | None, bold: bool = False) -> str:
        """Wrap `text` in the ANSI code for `color`, if it is known."""
        code = ANSI_COLORS.get(color.lower()) if color else None
        if code is None:
            return text
        return f"{BOLD if bold else ''}{code}{text}{RESET}"

    def zone_label(self, name: str) -> str:
        """Return a zone name painted in its own color."""
        zone = self.graph.zones.get(name)
        return self.paint(name, zone.color if zone else None)

    def render_entry(self, entry: str) -> str:
        """Color one entry such as D1-roof1 or D1-roof1-roof2."""
        drone, _, target = entry.partition("-")
        if "-" in target:
            # In flight: show the connection dimmed, ends colored.
            first, _, second = target.partition("-")
            link = (
                f"{self.zone_label(first)}{DIM}-{RESET}"
                f"{self.zone_label(second)}"
            )
            return f"{BOLD}{drone}{RESET}{DIM}~{RESET}{link}"
        return f"{BOLD}{drone}{RESET}-{self.zone_label(target)}"

    def legend(self) -> list[str]:
        """Return a short legend listing every zone."""
        rows = [f"{BOLD}Zones{RESET}"]
        for zone in self.graph.zones.values():
            role = (
                "start" if zone.is_start
                else "end" if zone.is_end
                else zone.zone_type.value
            )
            rows.append(f"  {self.zone_label(zone.name)} ({role})")
        return rows

    def render(self, lines: list[str]) -> list[str]:
        """Return the colored report, one block per turn."""
        if self.graph.end is None:
            raise ValueError("The graph has no end hub")
        end = self.graph.end.name
        out = self.legend()
        delivered = 0
        for number, line in enumerate(lines, start=1):
            entries = line.split()
            in_flight = sum(1 for e in entries if e.count("-") > 1)
            delivered += sum(
                1 for e in entries if e.partition("-")[2] == end
            )
            moves = " ".join(self.render_entry(e) for e in entries)
            summary = (
                f"{DIM}[in flight: {in_flight}, "
                f"delivered: {delivered}/{self.graph.nb_drones}]{RESET}"
            )
            out.append(f"{BOLD}Turn {number:>2}{RESET} | {moves}")
            out.append(f"        {summary}")
        out.append(
            f"{BOLD}Done in {len(lines)} turns{RESET} "
            f"({delivered}/{self.graph.nb_drones} delivered)"
        )
        return out

    def color_line(self, line: str) -> str:
        """Color the zone names of one output line, keeping its format."""
        parts: list[str] = []
        for entry in line.split():
            drone, _, target = entry.partition("-")
            names = target.split("-")  # one zone, or a connection's two
            painted = "-".join(self.zone_label(n) for n in names)
            parts.append(f"{drone}-{painted}")
        return " ".join(parts)
