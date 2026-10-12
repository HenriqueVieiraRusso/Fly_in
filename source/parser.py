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
        # TODO: raise if graph is None, or has no start / no end
        return graph

    def _parse_line(self, line: str, graph: Graph | None) -> Graph | None:
        """Handle one non-empty line; return the (possibly new) graph."""
        # TODO: split on the first ':' into prefix and rest
        # TODO: if graph is None, prefix MUST be nb_drones -> create Graph
        # TODO: otherwise dispatch on prefix to _parse_zone / _parse_connection
        raise NotImplementedError

    def _parse_metadata(self, text: str, allowed: set[str]) -> dict[str, str]:
        """Parse '[a=b c=d]' into a dict."""
        # TODO: must start with '[' and end with ']'
        # TODO: each token must contain exactly one '='
        # TODO: key must be in `allowed`, else ValueError
        raise NotImplementedError
