"""Parser for Fly-in map files."""

from source.connection import Connection
from source.errors import ParseError
from source.graph import Graph
from source.zone import Zone, ZoneType


class MapParser:
    """Reads a map file and builds a Graph."""

    def parse(self, path: str) -> Graph:
        """Parse the file and return the graph."""
        graph: Graph | None = None
        try:
            with open(path, "r", encoding="utf-8") as file:
                for number, raw in enumerate(file, start=1):
                    line = raw.split("#", 1)[0].strip()
                    if not line:
                        continue
                    try:
                        graph = self._parse_line(line, graph)
                    except ValueError as error:
                        raise ParseError(number, str(error)) from None
        except OSError as error:
            raise ParseError(0, f"Cannot read '{path}': {error}") from None
        if graph is None:
            raise ParseError(0, "The map file is empty.")
        return graph

    def _parse_line(self, line: str, graph: Graph | None) -> Graph | None:
        """Handle one non-empty line; return the (possibly new) graph."""
        if ":" not in line:
            raise ValueError("Expected 'key: value' format")

        prefix, rest = line.split(":", 1)
        prefix = prefix.strip()
        rest = rest.strip()

        try:
            nb_drones = int(rest)
        except ValueError:
            raise ValueError(
                f"nb_drones must be an int, got '{rest}'"
            ) from None
        graph = Graph(nb_drones)

        if graph is None:
            if prefix != "nb_drones":
                raise ValueError("The first line must define nb_drones")
            return Graph(self._parse_int(rest, "nb_drones"))

        if prefix == "nb_drones":
            raise ValueError("nb_drones is defined more than once")
        if prefix in ("start_hub", "hub", "end_hub"):
            self._parse_zone(prefix, rest, graph)
        elif prefix == "connection":
            self._parse_connection(rest, graph)
        else:
            raise ValueError(f"Unknown prefix: {prefix}")

        return graph

    def _parse_metadata(self, text: str, allowed: set[str]) -> dict[str, str]:
        """Parse '[a=b c=d]' into a dict."""
        if not (text.startswith("[") and text.endswith("]")):
            raise ValueError(f"Metadata must be inside [...], got {text}")

        result: dict[str, str] = {}
        for token in text[1:-1].split():
            if token.count("=") != 1:
                raise ValueError(
                    f"Invalid metadata '{token}' (expected key=value)")
            key, value = token.split("=")
            if key not in allowed:
                raise ValueError(f"Unknown metadata key '{key}'")
            if not value:
                raise ValueError(f"Metadata key '{key} has no value'")
            result[key] = value
        return result

    def _parse_zone(self, prefix: str, rest: str, graph: Graph) -> None:
        """Parse a zone line and add it to the graph."""
        main, bracket, tail = rest.partition("[")
        words = main.split()

        if len(words) != 3:
            raise ValueError("A zone needs: name, x, y")

        name, x_test, y_test = words
        metadata: dict[str, str] = {}

        if bracket:
            metadata = self._parse_metadata(
                bracket + tail.strip(), {"zone", "color", "max_drones"}
            )

        try:
            x = int(x_test)
            y = int(y_test)
        except ValueError:
            raise ValueError(
                f"Coordinates of '{name}' must be int,"
                f"got '{x_test}' and '{y_test}'"
            ) from None

        max_drones = 1
        if "max_drones" in metadata:
            try:
                max_drones = int(metadata["max_drones"])
            except ValueError:
                raise ValueError(
                    f"max_drones of '{name}' must be an int, "
                    f"got '{metadata['max_drones']}'"
                ) from None

        zone_type = ZoneType.from_string(metadata.get("zone", "normal"))
        color = metadata.get("color")

        zone = Zone(
            name=name,
            x=x,
            y=y,
            zone_type=zone_type,
            color=color,
            is_start=(prefix == "start_hub"),
            is_end=(prefix == "end_hub")
        )

        graph.add_zone(zone)
