*This project has been created as part of the 42 curriculum by hevieira.*
 
# Fly-in
 
**Drone fleet routing: move every drone from the start hub to the end hub in as few simulation turns as possible.**
 
## Description
 
Fly-in reads a map of connected zones and routes a fleet of drones from a single start hub to a single end hub. Every turn each drone may move to a connected zone, wait, or (for restricted zones) travel along a connection that takes two turns. The program has to respect:
 
- zone capacity (`max_drones`),
- connection capacity (`max_link_capacity`),
- movement costs by zone type (`normal`, `priority`, `restricted`, `blocked`),
and print the schedule turn by turn while keeping the total number of turns as low as possible.
 
Overview of the pipeline:
 
```
map file -> MapParser -> Graph -> plan_all (find_path + ReservationTable) -> build_lines -> TerminalRenderer
```
 
| Stage | Class / function | Job |
|-------|------------------|-----|
| Parsing | `MapParser` | Reads the map file and validates every rule of the format. Errors are reported as `line N: cause`. |
| Model | `Graph`, `Zone`, `Connection` | Stores zones, connections and capacities. |
| Planning | `find_path`, `ReservationTable`, `plan_all` | Plans one drone at a time against a shared reservation table. |
| Output | `build_lines` | Turns the planned paths into the output lines. |
| Display | `TerminalRenderer` | Prints the lines with zone names in the colour given by the map. |
 
Project constraints that were respected: Python 3.10+, no graph library (`networkx`, `graphlib`, ...), fully object-oriented, type hints everywhere, `flake8` and `mypy` clean (including `--strict`).
 
## Instructions
 
### Install
 
```bash
make install
```
 
Requires Python 3.10 or later. It creates a `.venv` and installs `requirements.txt` (`flake8`, `mypy`, `pytest`). The program itself only uses the standard library.
 
### Run
 
```bash
make run MAP=maps/easy/01_linear_path.txt
```
 
or directly:
 
```bash
python3 main.py maps/easy/01_linear_path.txt
```
 
Pass the map as a variable (`MAP=...`) when using `make`. Without `MAP`, the default map is used.
 
- The simulation is printed to **stdout**, one line per turn.
- `Total turns: N` is printed to **stderr**, so stdout contains only the schedule.
- On any error the program prints `Error: <message>` to stderr and exits with code `1`. It never prints a traceback for a bad map.
### Other Makefile rules
 
| Rule | What it does |
|------|--------------|
| `make debug MAP=...` | Runs the program under `pdb`. |
| `make clean` | Removes `__pycache__`, `.mypy_cache` and `.pytest_cache`. |
| `make lint` | `flake8` and `mypy` with `--warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs`. |
| `make lint-strict` | `flake8` and `mypy --strict`. |
 
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
 
| Zone type | Cost to enter | Notes |
|-----------|---------------|-------|
| `normal` | 1 turn | default |
| `priority` | 1 turn | preferred when two routes arrive at the same time |
| `restricted` | 2 turns | the drone must arrive on the next turn, it cannot wait on the connection |
| `blocked` | not allowed | can never be entered |
 
Defaults: `zone=normal`, `max_drones=1`, `max_link_capacity=1`. Comments start with `#`. Zone names cannot contain dashes or spaces.
 
What the parser rejects, always with a line number:
 
- a missing, non-integer or non-positive `nb_drones`;
- more than one, or no, `start_hub` / `end_hub`;
- a start or end hub with `zone=blocked`;
- duplicate zone names, non-integer coordinates, dashes or spaces in a name;
- a connection to an undefined zone, to itself, or a duplicate (`a-b` and `b-a` are the same connection);
- an invalid zone type, an unknown metadata key, a malformed `[...]` block;
- a `max_drones` or `max_link_capacity` that is not a positive integer (`max_drones` on the start and end hubs is ignored).
A syntactically valid map with no path from start to end is also reported as an error (`No path to the end hub ...`) instead of looping or crashing.
 
### Output format
 
One line per turn. Each entry is `D<ID>-<zone>`, or `D<ID>-<zoneA>-<zoneB>` while a drone is on a connection toward a restricted zone. Drones that do not move are omitted, and a drone that reaches the end hub is no longer listed.
 
## Algorithm
 
### Time model
 
Turns are numbered like the output lines. A state `(zone, T)` means "the drone is in `zone` after line `T`", so its next move happens on line `T + 1`. Turn 0 is the initial state.
 
### Pathfinding: Dijkstra over (zone, turn)
 
`find_path` is a hand-written Dijkstra (`heapq`) where a node is a `(zone, turn)` pair, not just a zone. From each state the drone can:
 
- **wait**: go to `(same zone, T + 1)`, if the reservation table shows room in that zone;
- **move** to a neighbouring zone: go to `(neighbour, T + cost)`, where the cost is 1 for normal and priority zones and 2 for restricted ones, if both the connection and the destination zone have room.
Blocked zones are never neighbours. Because the turn is part of the state, waiting, capacity limits and zones that are full at some turns but free at others are all handled by the same search.
 
The heap is ordered by `(turn, -priority count, insertion counter)`. The earliest arrival always wins, and among arrivals at the same turn the route through more `priority` zones is preferred. The goal is checked when a state is popped, so the first goal state popped is the earliest possible arrival. A `visited` set avoids expanding the same state twice, and `parent` links rebuild the path at the end.
 
To guarantee termination on an unreachable goal, the search is capped at `zones x drones + 10` turns. If the heap empties without reaching the goal, there is no path.
 
### Reservation table and scheduling
 
`ReservationTable` keeps two dictionaries:
 
- `zone_usage[(zone, turn)]`: how many drones are in that zone after that turn;
- `link_usage[(connection, turn)]`: how many drones start crossing that connection on that line.
The table has two kinds of methods, kept separate on purpose:
 
- `can_stay` / `can_move` only **read** the table. The search uses them to ask what is allowed.
- `reserve_stay` / `reserve_move` only **write** it. `plan_all` calls them after a path is chosen.
`plan_all` plans the drones **one at a time**, D1 first. After each path is found, every wait and move is booked in the table, so the next drone routes around the bookings or waits for them. The start and end hubs have no capacity limit. A drone that leaves a zone does not count in it for that turn, so a vacated place can be used by another drone on the same line (a single-file column advances one step per turn).
 
### Restricted zones
 
A move into a restricted zone takes two turns. The drone leaves on line `T` (it is on the connection, in no zone) and must arrive on line `T + 1`. The connection capacity is counted on the departure line only, which matches the subject: the connection is freed on the turn the drone arrives, so another drone can start crossing on that same turn. The destination zone is booked on the arrival turn.
 
### Complexity, caching and memory
 
With `Z` zones, `N` drones and a turn horizon `H` (bounded by `Z * N + 10`):
 
- One search visits at most `Z * H` states and looks at each state's neighbours, about `O(Z * H * deg * log(Z * H))` with the heap.
- The fleet needs `N` searches, so about `N` times that.
- Memory: `O(Z * H)` for one search, plus the reservation table, which only stores entries that were actually booked.
- Paths are **not cached**: the table changes after every drone, so each drone needs a fresh search.
- On the provided maps every run takes about 0.1 s or less.
### Limitations
 
The planning is greedy: each drone gets its own earliest path given the earlier drones. This is not proven optimal for every possible map. It reaches the optimum on all the maps shipped with the subject.
 
## Visual representation
 
The visual feedback is coloured terminal output (`TerminalRenderer`):
 
- Every zone name in the output is printed in the colour given by its `color=` value in the map. Drone ids and dashes stay in the normal colour, so the zone names stand out.
- Twenty colour names are mapped to terminal colours (`black`, `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white`, `gray`/`grey`, `orange`, `purple`, `brown`, `pink`, `gold`, `maroon`, `crimson`, `darkred`, `lime`, `violet`). Any other single-word colour is shown in **bold**, so unknown colours never crash the program.
- A drone in flight toward a restricted zone (`D3-start-slow_path1`) shows both zone names, each in its own colour.
- Colours are used only when stdout is a real terminal. When the output is redirected to a file or piped to another program, plain text is printed, so the schedule always matches the required format exactly.
How it helps: colours let you follow a drone through the network at a glance, see which zones are busy, and tell in-flight entries from normal moves. It is a terminal display only; there is no graphical window.
 
## Example
 
Input (`maps/easy/02_simple_fork.txt`):
 
```
nb_drones: 4
 
start_hub: start 0 0 [color=green]
hub: junction 1 0 [color=yellow max_drones=2]
hub: path_a 2 1 [color=blue]
hub: path_b 2 -1 [color=blue]
end_hub: goal 3 0 [color=red]
 
connection: start-junction [max_link_capacity=2]
connection: junction-path_a
connection: junction-path_b
connection: path_a-goal
connection: path_b-goal
```
 
Output (4 turns, the optimum):
 
```
D1-junction D2-junction
D1-path_a D2-path_b D3-junction D4-junction
D1-goal D2-goal D3-path_a D4-path_b
D3-goal D4-goal
```
 
Example with a restricted zone (`maps/medium/03_priority_puzzle.txt`, 5 drones, 6 turns, the optimum):
 
```
D1-fast_junction D3-start-slow_path1
D1-fast_path D2-fast_junction D3-slow_path1 D5-start-slow_path1
D1-merge_point D2-fast_path D3-slow_path2 D4-fast_junction D5-slow_path1
D1-goal D2-merge_point D3-merge_point D4-fast_path D5-slow_path2
D2-goal D3-goal D4-merge_point D5-merge_point
D4-goal D5-goal
```
 
Reading line 1: `D3-start-slow_path1` means D3 has entered the connection toward the restricted zone `slow_path1`. On line 2, `D3-slow_path1` shows that it has arrived, exactly one turn later, as required.
 
## Results
 
Turns achieved on the maps shipped with the subject, compared with the optimum.
 
| Map | Drones | Optimum | Achieved |
|-----|--------|---------|----------|
| Easy: linear path | 2 | 4 | 4 |
| Easy: simple fork | 4 | 4 | 4 |
| Easy: basic capacity | 4 | 4 | 4 |
| Medium: dead end trap | 5 | 8 | 8 |
| Medium: circular loop | 6 | 10 | 10 |
| Medium: priority puzzle | 5 | 6 | 6 |
| Hard: maze nightmare | 8 | 13 | 13 |
| Hard: capacity hell | 12 | 16 | 16 |
| Hard: ultimate challenge | 15 | 26 | 26 |
| Challenger: the impossible dream | 25 | 43 | 43 |
 
## Project structure
 
```
.
├── main.py                    # entry point
├── Makefile
├── requirements.txt
├── maps/                      # easy / medium / hard / challenger
└── source/
    ├── models/
    │   ├── zone.py            # Zone, ZoneType
    │   ├── connection.py      # Connection
    │   └── graph.py           # Graph
    ├── parsing/
    │   ├── errors.py          # ParseError
    │   └── parser.py          # MapParser
    ├── planning/
    │   ├── reservations.py    # ReservationTable, trip_turns
    │   ├── pathfinder.py      # find_path (Dijkstra over (zone, turn))
    │   └── scheduler.py       # plan_all, reserve_path
    ├── simulation/
    │   ├── output.py          # build_lines
    │   └── simulation.py      # ScheduleChecker (turn count)
    └── visual/
        └── terminal.py        # TerminalRenderer
```
 
## Resources
 
### References
 
- [Dijkstra's algorithm](https://en.wikipedia.org/wiki/Dijkstra%27s_algorithm)
- [Multi-agent pathfinding](https://en.wikipedia.org/wiki/Multi-agent_pathfinding) (the idea behind planning drones one at a time with a reservation table)
- [Python `heapq`](https://docs.python.org/3/library/heapq.html)
### How AI was used

- Overall better understanding of the project, and the creation of the README.me file
- Testing parser edge cases (invalid maps, unsolvable maps) and suggesting the rule that start and end hubs cannot be blocked.
