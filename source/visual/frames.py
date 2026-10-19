"""Compute drone positions after every turn."""

from source.models.graph import Graph

Point = tuple[float, float]
Frame = dict[str, Point]


class FrameBuilder:
    """Replays output lines into per-turn drone positions.

    A drone on a restricted connection is drawn halfway along it.
    """

    def __init__(self, graph: Graph) -> None:
        """Store the graph."""
        self.graph = graph

    def _point(self, zone: str) -> Point:
        z = self.graph.zones[zone]
        return (float(z.x), float(z.y))

    def build(self, lines: list[str]) -> list[Frame]:
        """Return frame 0 (initial state) plus one frame per line."""
        if self.graph.start is None:
            raise ValueError("The graph has no start hub")
        zone_of = {
            f"D{i}": self.graph.start.name
            for i in range(1, self.graph.nb_drones + 1)
        }
        coords: Frame = {d: self._point(z) for d, z in zone_of.items()}
        frames: list[Frame] = [dict(coords)]

        for line in lines:
            for entry in line.split():
                drone, _, target = entry.partition("-")
                if "-" in target:
                    a, _, b = target.partition("-")
                    dest = b if zone_of[drone] == a else a
                    (x1, y1) = self._point(zone_of[drone])
                    (x2, y2) = self._point(dest)
                    coords[drone] = ((x1 + x2) / 2, (y1 + y2) / 2)
                    zone_of[drone] = dest
                else:
                    zone_of[drone] = target
                    coords[drone] = self._point(target)
            frames.append(dict(coords))
        return frames
