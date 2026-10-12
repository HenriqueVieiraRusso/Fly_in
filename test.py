import unittest

from source.zone import Zone, ZoneType
from source.errors import ParseError
from source.graph import Graph, Connection


class TestZone(unittest.TestCase):
    def test_valid_zone(self) -> None:
        zone = Zone("roof1", 3, 4, ZoneType.RESTRICTED, "red", 2)
        self.assertEqual(zone.name, "roof1")
        self.assertEqual(zone.zone_type.movement_cost, 2)

    def test_name_with_dash(self) -> None:
        with self.assertRaises(ValueError):
            Zone("bad-name", 0, 0)

    def test_max_drones_zero(self) -> None:
        with self.assertRaises(ValueError):
            Zone("a", 0, 0, max_drones=0)

    def test_capacity_limit(self) -> None:
        self.assertTrue(Zone("a", 0, 0).has_capacity_limit)
        self.assertFalse(Zone("a", 0, 0, is_start=True).has_capacity_limit)
        self.assertFalse(Zone("a", 0, 0, is_end=True).has_capacity_limit)


class TestGraph(unittest.TestCase):

    def setUp(self) -> None:
        self.g = Graph(2)
        self.g.add_zone(Zone("a", 0, 0))
        self.g.add_zone(Zone("b", 1, 1))

    def test_add_connection(self) -> None:
        self.g.add_connection(Connection("a", "b"))
        self.assertEqual(len(self.g.connections), 1)

    def test_duplicate_connection(self) -> None:
        self.g.add_connection(Connection("a", "b"))

        with self.assertRaises(ValueError):
            self.g.add_connection(Connection("b", "a"))

    def test_unknown_zone(self) -> None:
        with self.assertRaises(ValueError):
            self.g.add_connection(Connection("a", "zzz"))

    def test_neighbors_with_blocked_zone(self) -> None:
        g = Graph(1)
        g.add_zone(Zone("a", 0, 0))
        g.add_zone(Zone("b", 1, 0))
        g.add_zone(Zone("c", 2, 0, ZoneType.BLOCKED))
        g.add_connection(Connection("a", "b"))
        g.add_connection(Connection("a", "c"))

        self.assertEqual([z.name for z in g.neighbors("a")], ["b"])
        self.assertEqual([z.name for z in g.neighbors("b")], ["a"])


class TestParseError(unittest.TestCase):
    def test_error_args(self) -> None:
        error = ParseError(7, "bad")
        self.assertEqual(error.args, ("line 7: bad",))

    def test_error_string(self) -> None:
        error = ParseError(7, "bad")
        self.assertEqual(str(error), "line 7: bad")


if __name__ == "__main__":
    unittest.main()
