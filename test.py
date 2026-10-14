import unittest
import os
import tempfile

from source.parser import MapParser
from source.zone import Zone, ZoneType
from source.errors import ParseError
from source.graph import Graph, Connection
from source.reservations import ReservationTable, trip_turns


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


class TestMapParser(unittest.TestCase):

    def setUp(self) -> None:
        self.parser = MapParser()
        self.temp = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".map",
            delete=False
        )
        self.addCleanup(self._cleanup)

    def _cleanup(self) -> None:
        self.temp.close()
        if os.path.exists(self.temp.name):
            os.unlink(self.temp.name)

    def _parse_text(self, text: str) -> Graph:
        self.temp.write(text)
        self.temp.flush()
        return self.parser.parse(self.temp.name)

    def test_valid_map(self) -> None:
        graph = self._parse_text(
            "nb_drones: 3\n"
            "start_hub: start 0 0\n"
            "hub: middle 1 1\n"
            "end_hub: end 2 2\n"
            "connection: start-middle\n"
            "connection: middle-end\n"
        )

        self.assertIsNotNone(graph.start)
        self.assertIsNotNone(graph.end)
        self.assertEqual(len(graph.connections), 2)

    def test_connection_default_capacity(self) -> None:
        graph = self._parse_text(
            "nb_drones: 2\n"
            "start_hub: a 0 0\n"
            "end_hub: b 1 1\n"
            "connection: a-b\n"
        )

        self.assertEqual(graph.connections[0].max_link_capacity, 1)

    def test_connection_custom_capacity(self) -> None:
        graph = self._parse_text(
            "nb_drones: 2\n"
            "start_hub: a 0 0\n"
            "end_hub: b 1 1\n"
            "connection: a-b [max_link_capacity=5]\n"
            )

        self.assertEqual(graph.connections[0].max_link_capacity, 5)

    def test_connection_invalid_format(self) -> None:
        with self.assertRaises(ParseError):
            self._parse_text(
                "nb_drones: 2\n"
                "start_hub: a 0 0\n"
                "end_hub: b 1 1\n"
                "connection: a-b-c\n"
            )

    def test_connection_invalid_capacity(self) -> None:
        with self.assertRaises(ParseError):
            self._parse_text(
                "nb_drones: 2\n"
                "start_hub: a 0 0\n"
                "end_hub: b 1 1\n"
                "connection: a-b [max_link_capacity=abc]\n"
            )

    def test_connection_unknown_metadata(self) -> None:
        with self.assertRaises(ParseError):
            self._parse_text(
                "nb_drones: 2\n"
                "start_hub: a 0 0\n"
                "end_hub: b 1 1\n"
                "connection: a-b [unknown=5]\n"
            )

    def test_missing_start_hub(self) -> None:
        with self.assertRaises(ParseError):
            self._parse_text(
                "nb_drones: 2\n"
                "hub: a 0 0\n"
                "end_hub: b 1 1\n"
            )

    def test_missing_end_hub(self) -> None:
        with self.assertRaises(ParseError):
            self._parse_text(
                "nb_drones: 2\n"
                "start_hub: a 0 0\n"
                "hub: b 1 1\n"
            )

    def test_first_line_must_be_nb_drones(self) -> None:
        with self.assertRaises(ParseError):
            self._parse_text(
                "start_hub: a 0 0\n"
                "end_hub: b 1 1\n"
            )

    def test_invalid_drone_count(self) -> None:
        with self.assertRaises(ParseError):
            self._parse_text(
                "nb_drones: abc\n"
                "start_hub: a 0 0\n"
                "end_hub: b 1 1\n"
            )

    def test_empty_map(self) -> None:
        with self.assertRaises(ParseError):
            self._parse_text("")

    def test_comments_and_blank_lines(self) -> None:
        graph = self._parse_text(
            "# Example map\n"
            "\n"
            "nb_drones: 2\n"
            "start_hub: a 0 0 # starting point\n"
            "end_hub: b 1 1\n"
            "connection: a-b\n"
        )

        self.assertIsNotNone(graph.start)
        self.assertIsNotNone(graph.end)
        self.assertEqual(len(graph.connections), 1)


class TestReservationTable(unittest.TestCase):

    def setUp(self) -> None:
        self.table = ReservationTable()
        self.a = Zone("a", 0, 0)
        self.b = Zone("b", 1, 1)
        self.conn = Connection("a", "b", 1)

    def test_can_stay_with_available_capacity(self) -> None:
        self.assertTrue(self.table.can_stay(self.a, 0))

    def test_reserve_stay_increments_usage(self) -> None:
        self.table.reserve_stay(self.a, 1)
        self.table.reserve_stay(self.a, 1)

        self.assertEqual(self.table.zone_usage[("a", 1)], 2)

    def test_can_stay_respects_capacity(self) -> None:
        zone = Zone("limited", 0, 0, max_drones=1)

        self.table.reserve_stay(zone, 1)

        self.assertFalse(self.table.can_stay(zone, 1))
        self.assertTrue(self.table.can_stay(zone, 2))

    def test_unlimited_zone_can_stay(self) -> None:
        zone = Zone("start", 0, 0, is_start=True, max_drones=1)

        self.table.reserve_stay(zone, 1)
        self.table.reserve_stay(zone, 1)

        self.assertTrue(self.table.can_stay(zone, 1))

    def test_can_move_with_available_link(self) -> None:
        self.assertTrue(self.table.can_move(self.b, self.conn, 1))

    def test_blocked_destination_cannot_move(self) -> None:
        blocked = Zone("blocked", 1, 1, ZoneType.BLOCKED)
        conn = Connection("a", "blocked")

        self.assertFalse(self.table.can_move(blocked, conn, 1))

    def test_link_capacity_is_respected(self) -> None:
        self.table.reserve_move(self.b, self.conn, 1)

        self.assertFalse(self.table.can_move(self.b, self.conn, 1))
        self.assertTrue(self.table.can_move(self.b, self.conn, 2))

    def test_reserve_move_records_link_usage(self) -> None:
        self.table.reserve_move(self.b, self.conn, 3)

        self.assertEqual(
            self.table.link_usage[(self.conn.key, 3)], 1
        )

    def test_reserve_move_records_destination_usage(self) -> None:
        self.table.reserve_move(self.b, self.conn, 3)

        arrival_turn = 3 + trip_turns(self.b) - 1

        self.assertEqual(
            self.table.zone_usage[("b", arrival_turn)], 1
        )

    def test_destination_capacity_prevents_move(self) -> None:
        destination = Zone("limited", 1, 1, max_drones=1)
        conn = Connection("a", "limited")
        arrival_turn = trip_turns(destination) - 1

        self.table.reserve_stay(destination, arrival_turn)

        self.assertFalse(
            self.table.can_move(destination, conn, 0)
        )

    def test_link_capacity_checked_for_every_trip_turn(self) -> None:
        restricted = Zone("restricted", 1, 1, ZoneType.RESTRICTED)
        conn = Connection("a", "restricted", 1)

        duration = trip_turns(restricted)
        self.assertGreaterEqual(duration, 2)

        # Occupy the link on the second turn of the trip.
        self.table.link_usage[(conn.key, 1)] = 1

        self.assertFalse(self.table.can_move(restricted, conn, 0))

    def test_reserve_restricted_move_uses_multiple_turns(self) -> None:
        restricted = Zone("restricted", 1, 1, ZoneType.RESTRICTED)
        conn = Connection("a", "restricted", 2)

        duration = trip_turns(restricted)
        self.table.reserve_move(restricted, conn, 2)

        for turn in range(2, 2 + duration):
            self.assertEqual(
                self.table.link_usage[(conn.key, turn)], 1
            )

        arrival_turn = 2 + duration - 1
        self.assertEqual(
            self.table.zone_usage[("restricted", arrival_turn)], 1
        )

    def test_trip_turns_returns_destination_movement_cost(self) -> None:
        self.assertEqual(
            trip_turns(self.b), self.b.zone_type.movement_cost
        )

    def test_connection_capacity_allows_multiple_drones(self) -> None:
        # Use an unlimited-capacity destination so only link capacity matters.
        destination = Zone("b", 1, 1, is_end=True, max_drones=1)
        conn = Connection("a", "b", 2)

        self.table.reserve_move(destination, conn, 1)

        self.assertTrue(self.table.can_move(destination, conn, 1))

        self.table.reserve_move(destination, conn, 1)

        self.assertFalse(self.table.can_move(destination, conn, 1))


if __name__ == "__main__":
    unittest.main()
