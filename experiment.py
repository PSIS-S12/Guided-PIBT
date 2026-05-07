import json
import random
import subprocess
import statistics
from pathlib import Path

ROOT = Path.cwd()
BENCH = ROOT / "guided-pibt" / "benchmark-lifelong"

MAP_NAME = "mapa2"
TEAM_SIZE = 1000
TASK_COUNT = 1000
PLAN_TIME_LIMIT = 10
RUNS = 20
TIMESTEPS = 256
MAP_TEXT = """
.@.......@........................................
.@.@.@@@.@.@.@@@.@@@.@.................@.@@@@@@@..
.@...@.......@.......@.................@..........
.@.@@@...@@@@@@@@@@@.@.......@.........@..........
.@.@.................@.......@.........@..........
.@.@.................@.......@.@@@@@@@.@..........
...@.........................@...@................
.@.@.@.......................@...@.@.@............
.@.@.@.......................@.....@.@............
.@.@.@.....@@@@@@@@@.........@.....@.@.......@....
.@...@...........@...................@.......@....
.@...@...........@...................@.......@....
.....@...........@...........................@....
.....@.@@@.......@...@@@@@@@.......@@@.......@....
.......@...........................@.........@....
.......@.@@@...@...@@@.@@@.........@.@@@@@...@....
.......@...@...@.......@...........@..............
.@@@@@@@...@...@...@...@...........@.@@@@@@@.....@
...........@...@...@...@.............@...........@
.@@@@@.....@...@...@@@.@.....@@@.....@...........@
...............@.............@...................@
...@@@@@@@.....@.....@@@@@@@.@.......@.......@...@
.............................@.......@.......@...@
.@@@.........................@.@@@@@@@.......@...@
...@.................................@.......@....
@@.@.@@@@@@@.........................@.....@@@....
...@.................................@............
...@.......@@@@@.@.........@...@@@@@.@............
.................@.........@...@..................
.................@.........@...@.@@@@@@@.@@@.@@@@@
.................@...............@................
.@@@@@...........@.....@@@.@.....@...........@@@.@
.................@.......@.@.....@...............@
.....@@@@@@@.@@@.@.......@.@.....@...............@
...........................@.....@...............@
.@.........@.@.....@@@@@.@.@.....@...............@
.@.........@.@.....@.....@.@......................
.@.@@@.@@@.@.@.....@...@.@.@.................@....
...........@.@.........@.@...................@....
@@@@.....@.@.@.........@.@...@@@@@@@.......@@@....
.........@.@.@.........@.....................@....
@@@@.....@.@.@...@@@...@.........@@@.@.......@.@..
.........@...@.....@...@...........@.@.......@.@..
.@.......@...@...@@@@@.@.........@.@.@.......@.@..
.@...........@...@.................@.@.........@..
.@...........@...@.........@@@@@@@.@.@.......@@@..
.....................................@............
@@@@.@@@@@@@...@...................@.@............
...@...........@...................@..............
.@@@...........@@@@@.@@@@@@@.......@..............
""".strip().splitlines()

# Pretvori koordinate (x, y) v zaporedno številko celice v mreži.
def cell_id(x, y, width):
    return y * width + x

# Poišče največjo skupino povezanih prostih celic na mapi.
def largest_connected_component(grid):
    h = len(grid)
    w = len(grid[0])
    visited = set()
    components = []

    for y in range(h):
        for x in range(w):
            if grid[y][x] != "." or (x, y) in visited: # preskoči zidove in že obiskane celice
                continue
            # začni novo komponento iz te celice
            stack = [(x, y)]
            visited.add((x, y))
            comp = []
            # BFS/DFS: obišči vse sosede dokler ne zmanjka celic
            while stack:
                cx, cy = stack.pop()
                comp.append(cell_id(cx, cy, w))
                # preveri vse 4 smeri (gor, dol, levo, desno)
                for dx, dy in [(1,0), (-1,0), (0,1), (0,-1)]:
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < w and 0 <= ny < h:
                        if grid[ny][nx] == "." and (nx, ny) not in visited:
                            visited.add((nx, ny))
                            stack.append((nx, ny))

            components.append(comp)
     # vrni največjo skupino povezanih celic
    largest = max(components, key=len)
    return largest

# Ustvari vhodne datoteke (mapa, agenti, taski, config) za en zagon simulacije.
def write_inputs(seed):
    random.seed(seed)

    h = len(MAP_TEXT)
    w = len(MAP_TEXT[0])

    assert h == 50 and w == 50, f"Mapa ni 50x50, ampak {w}x{h}"
    assert all(len(r) == 50 for r in MAP_TEXT), "Vse vrstice niso dolge 50"

    (BENCH / "maps").mkdir(parents=True, exist_ok=True)
    (BENCH / "agents").mkdir(parents=True, exist_ok=True)
    (BENCH / "tasks").mkdir(parents=True, exist_ok=True)

    map_path = BENCH / "maps" / f"{MAP_NAME}.map"
    agents_path = BENCH / "agents" / f"{MAP_NAME}_{seed}_{TEAM_SIZE}.agents"
    tasks_path = BENCH / "tasks" / f"{MAP_NAME}_{seed}.task"
    json_path = BENCH / f"{MAP_NAME}_{seed}_{TEAM_SIZE}.json"

    # Guided-PIBT format: first line is height,width
    with open(map_path, "w") as f:
        f.write(f"{h},{w}\n")
        for row in MAP_TEXT:
            f.write(row.replace("#", "@") + "\n")

    cells = largest_connected_component(MAP_TEXT)
    starts = random.sample(cells, TEAM_SIZE)

    tasks = []
    while len(tasks) < TASK_COUNT:
        t = random.choice(cells)
        if t not in starts:
            tasks.append(t)

    # Guided-PIBT format: first line count, then one cell id per line
    with open(agents_path, "w") as f:
        f.write(str(TEAM_SIZE) + "\n")
        for s in starts:
            f.write(str(s) + "\n")

    with open(tasks_path, "w") as f:
        f.write(str(TASK_COUNT) + "\n")
        for t in tasks:
            f.write(str(t) + "\n")

    config = {
        "mapFile": f"maps/{MAP_NAME}.map",
        "agentFile": f"agents/{MAP_NAME}_{seed}_{TEAM_SIZE}.agents",
        "teamSize": TEAM_SIZE,
        "taskFile": f"tasks/{MAP_NAME}_{seed}.task",
        "numTasksReveal": 1,
        "taskAssignmentStrategy": "roundrobin"
    }

    with open(json_path, "w") as f:
        json.dump(config, f, indent=2)

    return json_path

# Zažene simulator, prebere rezultate in vrne statistike tega zagona.

def run(seed, json_path):
    out = ROOT / f"output_{MAP_NAME}_{TEAM_SIZE}_seed_{seed}.json"
    log = ROOT / f"event_log_{MAP_NAME}_{TEAM_SIZE}_seed_{seed}.txt"

    cmd = [
        "./guided-pibt-build/lifelong",
        "--inputFile", str(json_path),
        "--simulationTime", str(TIMESTEPS),
        "--planTimeLimit", str(PLAN_TIME_LIMIT),
        "--output", str(out),
        "-l", str(log)
    ]

    proc = subprocess.run(cmd, check=True, text=True, capture_output=True)
    terminal_text = proc.stdout + proc.stderr

    with open(out) as f:
        data = json.load(f)

    with open(log) as f:
        log_text = f.read()

    full_text = terminal_text + "\n" + log_text

    makespan = data.get("makespan", 0)
    finished = data.get("numTaskFinished", 0)
    planner_times = data.get("plannerTimes", [])
    all_valid = data.get("AllValid") == "Yes"

    collision_count = (
        full_text.count("vertex conflict") +
        full_text.count("edge conflict") +
        full_text.count("collision")
    )

    throughput = finished / makespan if makespan else 0
    task_completion_ratio = finished / TASK_COUNT if TASK_COUNT else 0

    result = {
        "seed": seed,
        "map": MAP_NAME,
        "agents": TEAM_SIZE,
        "tasks_generated": TASK_COUNT,
        "tasks_finished": finished,
        "throughput": throughput,
        "task_completion_ratio": task_completion_ratio,
        "finished": finished,
        "collision_count": collision_count,
        "makespan": makespan,
        "avg_planner_time": statistics.mean(planner_times) if planner_times else 0,
        "max_planner_time": max(planner_times) if planner_times else 0,
        "valid_run": 1.0 if all_valid else 0.0,
        "all_valid": data.get("AllValid"),
        "output_file": str(out),
        "log_file": str(log)
    }

    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    results = []

    for seed in range(RUNS):
        print(f"\n=== RUN {seed + 1}/{RUNS}, seed={seed} ===")
        config = write_inputs(seed)
        result = run(seed, config)
        results.append(result)

    summary = {
        "runs": RUNS,
        "valid_runs": sum(r["valid_run"] for r in results),
        "avg_throughput": statistics.mean(r["throughput"] for r in results),
        "avg_task_completion_ratio": statistics.mean(r["task_completion_ratio"] for r in results),
        "avg_collision_count": statistics.mean(r["collision_count"] for r in results),
        "avg_makespan": statistics.mean(r["makespan"] for r in results),
        "avg_planner_time": statistics.mean(r["avg_planner_time"] for r in results),
        "max_planner_time_overall": max(r["max_planner_time"] for r in results),
        "min_throughput": min(r["throughput"] for r in results),
        "max_throughput": max(r["throughput"] for r in results),
    }

    with open("summary_20_runs.json", "w") as f:
        json.dump(
            {
                "runs": results,
                "summary": summary
            },
            f,
            indent=2
        )

    print("\n=== SUMMARY 20 RUNS ===")
    print(json.dumps(summary, indent=2))
