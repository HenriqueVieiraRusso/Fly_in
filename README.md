*This project has been created as part of the 42 curriculum by hevieira.*

# Fly-in

**Drone fleet routing simulation: move every drone from the start hub to the end hub in the fewest turns.**

## Description

Given a map of connected zones, the program moves all drones from a start hub to an end hub in as few simulation turns as possible, while respecting zone capacities, connection capacities and the transit rules of restricted zones.

The pipeline:

```
map.txt -> MapParser -> Graph -> Pathfinder + Scheduler -> OutputFormatter -> ScheduleChecker -> turn log (stdout)
                                                                                     |
                                                                                     +-> pygame replay
```

- **Parser**: strict map validation, errors reported as `line N: cause`, never a traceback.
- **Pathfinding**: hand-written Dijkstra (`heapq`, no graph library) over `(zone, turn)` states.
- **Scheduler**: plans the drones one after another against a shared reservation table, so later drones route around or wait for earlier ones.
- **Checker**: an independent replay of the printed lines that verifies every rule before anything is shown.
- **Visual**: pygame window that animates the schedule on the map's own coordinates.

## Instructions

### Install

```bash
make install
```

Requires Python 3.10+. Creates a `.venv` and installs everything in `requirements.txt` (flake8, mypy, pytest, pygame).

### Run

```bash
make run MAP=maps/easy/01_linear_path.txt
```

Or directly:

```bash
.venv/bin/python main.py <map_file>
```

The program prints the simulation to stdout (one line per turn), prints the total number of turns to stderr, then opens the pygame window. There are no command-line options besides the map file.

### Development

```bash
make lint          # flake8 + mypy
make lint-strict   # flake8 + mypy --strict
make debug MAP=maps/easy/01_linear_path.txt
make clean
python -m unittest -v
```

### Output format

One line per turn, moves separated by spaces. Drones that do not move are omitted, and delivered drones are no longer listed. A drone travelling toward a restricted zone is shown on its connection.

```
D1-a
D1-end D2-a
D2-end
```

### Map format

```
nb_drones: 5

start_hub: hub 0 0 [color=green]
end_hub: goal 10 10 [color=yellow]
hub: roof1 3 4 [zone=restricted color=red]
hub: corridorA 4 3 [zone=priority color=green max_drones=2]
hub: obstacleX 5 5 [zone=blocked color=gray]

connection: hub-roof1
connection: corridorA-goal [max_link_capacity=2]
```

| Zone type | Cost | Notes |
|-----------|------|-------|
| `normal` | 1 turn | default |
| `priority` | 1 turn | preferred when paths tie |
| `restricted` | 2 turns | the drone must arrive on the next turn, it cannot wait on the link |
| `blocked` | n/a | cannot be entered |

Defaults: `zone=normal`, `max_drones=1` (ignored on start and end hubs), `max_link_capacity=1`. Comments start with `#`.

### Pygame controls

| Key | Action |
|-----|--------|
| Space | Pause / resume |
| Right / Left | Step one turn forward / back (pauses) |
| Up / Down | Faster / slower |
| Esc | Quit |

`Ctrl+C` in the terminal also closes the window cleanly.

## Results

<!-- Fill in with your real numbers. -->

| Map | Drones | Target | Achieved |
|-----|--------|--------|----------|
| Easy: linear path | 2 | <= 6 | |
| Easy: simple fork | 4 | <= 8 | |
| Easy: basic capacity | 4 | <= 6 | |
| Medium: dead end trap | 5 | <= 12 | |
| Medium: circular loop | 6 | <= 15 | 15 |
| Medium: priority puzzle | 5 | <= 12 | |
| Hard: maze nightmare | 8 | <= 30 | |
| Hard: capacity hell | 12 | <= 35 | |
| Hard: ultimate challenge | 15 | <= 45 | |
| Challenger: impossible dream | 25 | ref. 45 (optional) | |

## Project structure

```
.
├── main.py                 # entry point
├── Makefile
├── requirements.txt
├── source/
│   ├── zone.py             # Zone, ZoneType
│   ├── connection.py       # Connection
│   ├── graph.py            # Graph: map-level rules and lookups
│   ├── errors.py           # ParseError
│   ├── parser.py           # MapParser
│   ├── reservations.py     # ReservationTable
│   ├── pathfinder.py       # earliest-arrival search for one drone
│   ├── scheduler.py        # plans all drones
│   ├── output.py           # paths -> output lines
│   ├── simulation.py       # ScheduleChecker
│   ├── frames.py           # per-turn drone positions
│   └── gui.py              # pygame display
├── tests/
└── maps/                   # easy / medium / hard / challenger / invalid
```

## Algorithms

### Time model

Turns are numbered by output line. A state `(zone, T)` means "the drone is in `zone` after line `T`", so its next move happens on line `T + 1`.

### Pathfinding: Dijkstra over space and time

For one drone, Dijkstra runs on `(zone, turn)` states. From each state the drone can:

- **wait** in its zone (costs 1 turn), or
- **move** to a neighbouring zone (costs the destination's movement cost: 1 for normal and priority, 2 for restricted).

Blocked zones are never neighbours. A wait or move is only allowed when the reservation table shows room in the destination zone and on the link. The start and end hubs are unlimited.

Priority zones are preferred through a tie-break: among states reached at the same turn, the heap favours the path that crossed more priority zones.

### Reservation table and scheduling

`ReservationTable` stores how many drones occupy each zone and each link on each turn. Drones are planned one at a time: after a drone's path is found, every wait and move is written into the table, then the next drone is planned. Waiting at the start hub is free, so later drones are pushed back automatically when routes are full, and they spread over alternative routes when one exists.

A drone that leaves a zone frees its place on the same turn, because zone usage only counts drones that are in the zone after the line.

### Restricted zones and link capacity

A move into a restricted zone leaves on line `T`: the drone is on the connection after line `T` and must arrive on line `T + 1`. It is in no zone during the in-flight line, so it uses no zone capacity then.

**Interpretation chosen:** the connection is occupied on **both** lines of the trip. A schedule that is valid under this rule is also valid under the weaker reading (link used on the departure line only), so it is the safe choice. The rule lives in one place (`ReservationTable`), plus the checker.

### Independent checker

`ScheduleChecker` replays the printed lines from scratch. It verifies that moves follow real connections, blocked zones are never entered, restricted trips arrive on the next line, zone and link capacity are never exceeded, and every drone ends in the end hub. It shares no code with the planner or the table, so a bug in either is caught instead of silently printed. `main.py` runs it before printing.

### Complexity

With `Z` zones, `N` drones and a turn horizon `H` (bounded by `Z * N + 10`):

- One search visits at most `Z * H` states and scans each state's neighbours: about `O(Z * H * (deg + 1) * log(Z * H))`.
- The whole fleet needs `N` searches, so roughly `N` times that.
- Memory: `O(Z * H)` for one search, plus the reservation table, which grows with the number of reserved zone-turns and link-turns.
- Paths are not cached: each drone needs a fresh search because the table changes after every drone.

### Limits

Planning is greedy (one drone at a time), so the result is not guaranteed optimal on every map.

## Visual representation

The pygame window places every zone at its map coordinates.

- **Zone colour** comes from the `color=` value in the map file. Unknown colour names fall back to grey.
- **Rings**: red for restricted zones, gold for priority zones; blocked zones are crossed out.
- **Links** are lines whose thickness shows `max_link_capacity`.
- **Labels**: `start hub`, `end hub`, `hub 1`, `hub 2`, ... in the order the hubs appear in the file.
- **Drones** are numbered circles animated between zones, with a short pause at the end of each turn. A drone crossing a restricted link rests at the midpoint of the link for one turn.
- **Header** shows the current turn, the speed and the paused state.

This makes bottlenecks easy to see: queues at the start hub, drones splitting over routes, and capacity-limited links.

## Resources

### References

- [Dijkstra's algorithm](https://en.wikipedia.org/wiki/Dijkstra%27s_algorithm)
- [Multi-agent pathfinding and reservation tables (cooperative A*)](https://en.wikipedia.org/wiki/Multi-agent_pathfinding)
- [Python heapq](https://docs.python.org/3/library/heapq.html)
- [Python dataclasses](https://docs.python.org/3/library/dataclasses.html)
- [Python enum](https://docs.python.org/3/library/enum.html)
- [PEP 257, docstring conventions](https://peps.python.org/pep-0257/)
- [mypy documentation](https://mypy.readthedocs.io/)
- [pygame documentation](https://www.pygame.org/docs/)

### AI usage

<!-- Fill this in honestly: which tasks, which parts of the project. -->

AI (Claude) was used as a learning and review assistant for: <list the tasks, for example explaining concepts, reviewing code, suggesting test cases, drafting the README structure>.

Parts written by the authors: <list them>.

All AI-assisted code was reviewed, tested and understood before being kept.