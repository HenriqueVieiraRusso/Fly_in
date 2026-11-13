"""Parser for Fly-in map files."""

from source.models.connection import Connection
from source.parsing.errors import ParseError
from source.models.graph import Graph
from source.models.zone import Zone, ZoneType


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
        if graph.start is None:
            raise ParseError(0, "Missing start_hub")
        if graph.end is None:
            raise ParseError(0, "Missing end_hub")
        return graph

    def _parse_line(self, line: str, graph: Graph | None) -> Graph | None:
        """Handle one non-empty line; return the (possibly new) graph."""
        if ":" not in line:
            raise ValueError("Expected 'key: value' format")
        prefix, _, rest = line.partition(":")
        prefix = prefix.strip()
        rest = rest.strip()

        if graph is None:
            if prefix != "nb_drones":
                raise ValueError("The first line must define nb_drones")
            try:
                nb_drones = int(rest)
            except ValueError:
                raise ValueError(
                    f"nb_drones must be an integer, got '{rest}'"
                ) from None
            return Graph(nb_drones)

        if prefix == "nb_drones":
            raise ValueError("nb_drones is defined more than once")
        if prefix in ("start_hub", "hub", "end_hub"):
            self._parse_zone(prefix, rest, graph)
        elif prefix == "connection":
            self._parse_connection(rest, graph)
        else:
            raise ValueError(
                f"Unknown prefix '{prefix}' (expected start_hub, hub, "
                "end_hub or connection)"
            )
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
                raise ValueError(f"Metadata key '{key}' has no value")
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
                f"Coordinates of '{name}' must be int, "
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
            max_drones=max_drones,
            is_start=(prefix == "start_hub"),
            is_end=(prefix == "end_hub")
        )

        graph.add_zone(zone)

    def _parse_connection(self, rest: str, graph: Graph) -> None:
        """Parse a connection line and add it to the graph."""
        main, bracket, tail = rest.partition("[")
        names = main.strip().split("-")

        if len(names) != 2:
            raise ValueError(
                "Connection must contain exactly "
                "two zone names separated by '-'"
            )

        zone_a, zone_b = (name.strip() for name in names)

        capacity = 1
        if bracket:
            metadata = self._parse_metadata(
                bracket + tail.strip(), {"max_link_capacity"}
            )

            if "max_link_capacity" in metadata:
                try:
                    capacity = int(metadata["max_link_capacity"])
                except ValueError:
                    raise ValueError(
                        "max_link_capacity must be an int, got "
                        f"'{metadata['max_link_capacity']}'"
                    ) from None

        graph.add_connection(Connection(zone_a, zone_b, capacity))
