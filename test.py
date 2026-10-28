import unittest
import os
import tempfile

from source.parsing.parser import MapParser
from source.models.zone import Zone, ZoneType
from source.parsing.errors import ParseError
from source.models.graph import Graph, Connection
from source.planning.reservations import ReservationTable, trip_turns
from source.planning.pathfinder import find_path
from source.planning.scheduler import plan_all, reserve_path
from source.simulation.output import build_lines
from source.simulation.simulation import ScheduleChecker, SimulationError


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


class TestPathfinder(unittest.TestCase):
    def test_linear_map(self) -> None:
        """A drone should follow a simple path to the end."""
        graph = Graph(1)
        a = Zone("a", 0, 0, is_start=True)
        b = Zone("b", 1, 0)
        c = Zone("c", 2, 0, is_end=True)

        for zone in (a, b, c):
            graph.add_zone(zone)

        graph.add_connection(Connection("a", "b"))
        graph.add_connection(Connection("b", "c"))

        path = find_path(graph, ReservationTable())

        self.assertIsNotNone(path)
        assert path is not None
        self.assertEqual(path[0], ("a", 0))
        self.assertEqual(path[-1][0], "c")
        self.assertEqual(path[-1][1], 2)

    def test_waits_when_connection_is_at_capacity(self) -> None:
        """The drone should wait, then use the connection when available."""
        graph = Graph(1)
        a = Zone("a", 0, 0, is_start=True)
        b = Zone("b", 1, 0, is_end=True)

        graph.add_zone(a)
        graph.add_zone(b)

        connection = Connection("a", "b")
        graph.add_connection(connection)

        table = ReservationTable()
        table.link_usage[(connection.key, 1)] = 1

        path = find_path(graph, table)

        self.assertIsNotNone(path)
        assert path is not None
        self.assertEqual(
            path,
            [("a", 0), ("a", 1), ("b", 2)],
        )

    def test_fork_chooses_available_route(self) -> None:
        """If one branch is blocked, the drone should take the other."""
        graph = Graph(1)
        a = Zone("a", 0, 0, is_start=True)
        b = Zone("b", 1, 0)
        c = Zone("c", 1, 1)
        d = Zone("d", 2, 0, is_end=True)

        for zone in (a, b, c, d):
            graph.add_zone(zone)

        ab = Connection("a", "b")
        ac = Connection("a", "c")
        bd = Connection("b", "d")
        cd = Connection("c", "d")

        for connection in (ab, ac, bd, cd):
            graph.add_connection(connection)

        table = ReservationTable()
        table.link_usage[(ab.key, 1)] = ab.max_link_capacity

        path = find_path(graph, table)

        self.assertIsNotNone(path)
        assert path is not None
        self.assertEqual(path[0], ("a", 0))
        self.assertEqual(path[-1][0], "d")
        self.assertIn(("c", 1), path)
        self.assertNotIn(("b", 1), path)

    def test_restricted_zone_takes_extra_turn(self) -> None:
        """Entering a zone with movement cost 2 should take two turns."""
        graph = Graph(1)
        a = Zone("a", 0, 0, is_start=True)
        restricted = Zone("r", 1, 0, zone_type=ZoneType.RESTRICTED)
        end = Zone("end", 2, 0, is_end=True)

        for zone in (a, restricted, end):
            graph.add_zone(zone)

        graph.add_connection(Connection("a", "r"))
        graph.add_connection(Connection("r", "end"))

        path = find_path(graph, ReservationTable())

        self.assertIsNotNone(path)
        assert path is not None
        self.assertIn(("r", 2), path)
        self.assertEqual(path[-1], ("end", 3))

    def test_prefers_priority_zone_when_arrival_time_ties(self) -> None:
        """Among equally fast routes,
            prefer the route through a priority zone."""
        graph = Graph(1)
        a = Zone("a", 0, 0, is_start=True)
        regular = Zone("regular", 1, 0)
        priority = Zone(
            "priority",
            1,
            1,
            zone_type=ZoneType.PRIORITY,
        )
        end = Zone("end", 2, 0, is_end=True)

        for zone in (a, regular, priority, end):
            graph.add_zone(zone)

        graph.add_connection(Connection("a", "regular"))
        graph.add_connection(Connection("regular", "end"))
        graph.add_connection(Connection("a", "priority"))
        graph.add_connection(Connection("priority", "end"))

        path = find_path(graph, ReservationTable())

        self.assertIsNotNone(path)
        assert path is not None
        self.assertIn(("priority", 1), path)
        self.assertEqual(path[-1], ("end", 2))

    def test_returns_none_when_no_path_exists(self) -> None:
        """An isolated end zone should be unreachable."""
        graph = Graph(1)
        a = Zone("a", 0, 0, is_start=True)
        end = Zone("end", 1, 0, is_end=True)

        graph.add_zone(a)
        graph.add_zone(end)

        path = find_path(graph, ReservationTable())

        self.assertIsNone(path)


class TestScheduler(unittest.TestCase):
    """Tests for reserve_path and plan_all."""

    def test_reserve_path_records_wait(self) -> None:
        graph = Graph(1)
        graph.add_zone(Zone("start", 0, 0, is_start=True))
        graph.add_zone(Zone("end", 1, 0, is_end=True))
        conn = Connection("start", "end")
        graph.add_connection(conn)

        table = ReservationTable()
        path = [("start", 0), ("start", 1), ("end", 2)]
        reserve_path(graph, table, path)

        self.assertEqual(table.zone_usage.get(("start", 1), 0), 1)
        self.assertEqual(table.link_usage.get((conn.key, 2), 0), 1)
        self.assertEqual(table.zone_usage.get(("end", 2), 0), 1)

    def test_reserve_restricted_move_uses_both_turns(self) -> None:
        graph = Graph(1)
        graph.add_zone(Zone("start", 0, 0, is_start=True))
        graph.add_zone(Zone("r", 1, 0, ZoneType.RESTRICTED))
        graph.add_zone(Zone("end", 2, 0, is_end=True))
        conn = Connection("start", "r")
        graph.add_connection(conn)
        graph.add_connection(Connection("r", "end"))

        table = ReservationTable()
        path = [("start", 0), ("r", 2), ("end", 3)]
        reserve_path(graph, table, path)

        self.assertEqual(table.link_usage[(conn.key, 1)], 1)
        self.assertEqual(table.link_usage[(conn.key, 2)], 1)
        self.assertEqual(table.zone_usage[("r", 2)], 1)
        self.assertNotIn(("r", 1), table.zone_usage)

    def test_plan_all_returns_one_path_per_drone(self) -> None:
        graph = Graph(2)
        graph.add_zone(Zone("start", 0, 0, is_start=True))
        graph.add_zone(Zone("end", 1, 0, is_end=True))
        graph.add_connection(
            Connection("start", "end", max_link_capacity=2)
        )

        paths = plan_all(graph)

        self.assertEqual(len(paths), 2)
        self.assertTrue(all(p[0] == ("start", 0) for p in paths))
        self.assertTrue(all(p[-1] == ("end", 1) for p in paths))

    def test_capacity_one_link_delays_second_drone(self) -> None:
        graph = Graph(2)
        graph.add_zone(Zone("start", 0, 0, is_start=True))
        graph.add_zone(Zone("end", 1, 0, is_end=True))
        graph.add_connection(Connection("start", "end"))

        paths = plan_all(graph)

        self.assertEqual(paths[0][-1], ("end", 1))
        self.assertEqual(paths[1][-1], ("end", 2))

    def test_fork_splits_two_drones(self) -> None:
        graph = Graph(2)
        graph.add_zone(Zone("start", 0, 0, is_start=True))
        graph.add_zone(Zone("b", 1, 0))
        graph.add_zone(Zone("c", 1, 1))
        graph.add_zone(Zone("end", 2, 0, is_end=True))
        for a, b in (("start", "b"), ("start", "c"),
                     ("b", "end"), ("c", "end")):
            graph.add_connection(Connection(a, b))

        paths = plan_all(graph)

        self.assertEqual(paths[0][-1], ("end", 2))
        self.assertEqual(paths[1][-1], ("end", 2))
        self.assertNotEqual(paths[0][1], paths[1][1])

    def test_plan_all_raises_when_a_drone_cannot_arrive(self) -> None:
        graph = Graph(1)
        graph.add_zone(Zone("start", 0, 0, is_start=True))
        graph.add_zone(Zone("end", 1, 0, is_end=True))

        with self.assertRaises(ValueError):
            plan_all(graph)


class TestOutput(unittest.TestCase):
    """Tests for build_lines."""

    def _graph(self, middle: Zone) -> Graph:
        graph = Graph(1)
        graph.add_zone(Zone("start", 0, 0, is_start=True))
        graph.add_zone(middle)
        graph.add_zone(Zone("end", 2, 0, is_end=True))
        graph.add_connection(Connection("start", middle.name))
        graph.add_connection(Connection(middle.name, "end"))
        return graph

    def test_linear(self) -> None:
        graph = self._graph(Zone("a", 1, 0))
        path = [("start", 0), ("a", 1), ("end", 2)]
        self.assertEqual(build_lines(graph, [path]), ["D1-a", "D1-end"])

    def test_restricted(self) -> None:
        graph = self._graph(Zone("r", 1, 0, ZoneType.RESTRICTED))
        path = [("start", 0), ("r", 2), ("end", 3)]
        self.assertEqual(
            build_lines(graph, [path]),
            ["D1-start-r", "D1-r", "D1-end"],
        )

    def test_wait_and_two_drones(self) -> None:
        graph = self._graph(Zone("a", 1, 0))
        p1 = [("start", 0), ("a", 1), ("end", 2)]
        p2 = [("start", 0), ("start", 1), ("a", 2), ("end", 3)]
        self.assertEqual(
            build_lines(graph, [p1, p2]),
            ["D1-a", "D1-end D2-a", "D2-end"],
        )

    def test_empty(self) -> None:
        graph = self._graph(Zone("a", 1, 0))
        self.assertEqual(build_lines(graph, []), [])


class TestChecker(unittest.TestCase):
    def _graph(self, cap: int = 1) -> Graph:
        g = Graph(2)
        g.add_zone(Zone("start", 0, 0, is_start=True))
        g.add_zone(Zone("a", 1, 0))
        g.add_zone(Zone("end", 2, 0, is_end=True))
        g.add_connection(Connection("start", "a", cap))
        g.add_connection(Connection("a", "end", cap))
        return g

    def test_valid(self) -> None:
        lines = ["D1-a", "D1-end D2-a", "D2-end"]
        checker = ScheduleChecker(self._graph())
        self.assertEqual(checker.check(lines), 3)

    def test_teleport(self) -> None:
        with self.assertRaises(SimulationError):
            ScheduleChecker(self._graph()).check(["D1-end"])

    def test_zone_over_capacity(self) -> None:
        with self.assertRaises(SimulationError):
            ScheduleChecker(self._graph()).check(["D1-a D2-a"])

    def test_link_over_capacity(self) -> None:
        g = Graph(2)
        g.add_zone(Zone("start", 0, 0, is_start=True))
        g.add_zone(Zone("a", 1, 0, max_drones=2))
        g.add_zone(Zone("end", 2, 0, is_end=True))
        g.add_connection(Connection("start", "a", 1))
        g.add_connection(Connection("a", "end"))
        with self.assertRaisesRegex(SimulationError, "link"):
            ScheduleChecker(g).check(["D1-a D2-a"])

    def test_not_all_delivered(self) -> None:
        with self.assertRaises(SimulationError):
            ScheduleChecker(self._graph()).check(["D1-a", "D1-end"])


if __name__ == "__main__":
    unittest.main()
