import json
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import re
import sys
import glob
import os
from collections import Counter, defaultdict

# ─────────────────────────── CLI argument ───────────────────────────
if len(sys.argv) < 2:
    print("Napaka: Prosim podaj ime eksperimenta.")
    print("Primer: python3 plot.py GP-R100-F2")
    sys.exit(1)

exp_name = sys.argv[1]
exp_dir  = f"results/{exp_name}"

if not os.path.exists(exp_dir):
    print(f"Napaka: Mapa {exp_dir} ne obstaja.")
    sys.exit(1)

json_files = glob.glob(os.path.join(exp_dir, "*.json"))
log_files  = glob.glob(os.path.join(exp_dir, "*.txt"))

if not json_files or not log_files:
    print(f"Napaka: V mapi {exp_dir} manjka .json ali .txt datoteka.")
    sys.exit(1)

json_path = json_files[0]
log_path  = log_files[0]

print(f"Analiziram JSON: {os.path.basename(json_path)}")
print(f"Analiziram LOG:  {os.path.basename(log_path)}")

# ─────────────────────────── JSON parsing ───────────────────────────
with open(json_path, "r") as f:
    data = json.load(f)

action_model    = data.get("actionModel", "N/A")
all_valid       = data.get("AllValid", "N/A")
team_size       = data.get("teamSize", 0)
num_tasks_done  = data.get("numTaskFinished", 0)
sum_of_cost     = data.get("sumOfCost", 0)
makespan        = data.get("makespan", 0)
planner_times   = data.get("plannerTimes", [])

# ─────────────────────────── LOG parsing ────────────────────────────
finish_pattern   = re.compile(r"\[timestep=(\d+)\] Agent (\d+) finishes task (\d+)")
assign_pattern   = re.compile(r"\[timestep=(\d+)\] Task \d+ is assigned to agent (\d+)")

finish_timesteps   = []          # timestep of each finish event
tasks_per_agent    = defaultdict(int)
assign_per_agent   = defaultdict(int)
tasks_per_timestep = Counter()

try:
    with open(log_path, "r") as f:
        for line in f:
            m = finish_pattern.search(line)
            if m:
                ts, agent, _ = int(m.group(1)), int(m.group(2)), int(m.group(3))
                finish_timesteps.append(ts)
                tasks_per_agent[agent] += 1
                tasks_per_timestep[ts] += 1
                continue
            m = assign_pattern.search(line)
            if m:
                assign_per_agent[int(m.group(2))] += 1
except Exception as e:
    print(f"Napaka pri branju log datoteke: {e}")
    sys.exit(1)

if not finish_timesteps:
    print("Opozorilo: V log datoteki nisem našel podatkov o končanih nalogah.")
    sys.exit(1)

# Cumulative task completion over timesteps
sorted_steps = sorted(tasks_per_timestep.keys())
cumulative   = []
total = 0
for s in sorted_steps:
    total += tasks_per_timestep[s]
    cumulative.append(total)

# Tasks per timestep (throughput)
throughput_steps  = sorted_steps
throughput_values = [tasks_per_timestep[s] for s in sorted_steps]

# Tasks per agent distribution
agent_task_counts = list(tasks_per_agent.values())

# Planner times
pt = np.array(planner_times) * 1000  # convert to ms

# Throughput rolling average (window = 20 timesteps)
window = 20
if len(throughput_values) >= window:
    rolling_avg = np.convolve(throughput_values, np.ones(window) / window, mode="valid")
    rolling_steps = throughput_steps[window - 1:]
else:
    rolling_avg   = np.array(throughput_values)
    rolling_steps = throughput_steps

# ─────────────────────────── Figure layout ──────────────────────────
fig = plt.figure(figsize=(18, 14))
fig.suptitle(
    f"MAPF analiza: {exp_name}  |  Model: {action_model}  |  "
    f"Agentov: {team_size}  |  Nalog: {num_tasks_done}  |  Makespan: {makespan}",
    fontsize=13, fontweight="bold", y=0.98
)

gs = gridspec.GridSpec(3, 3, figure=fig, hspace=0.45, wspace=0.35)

BLUE   = "#2563EB"
GREEN  = "#16A34A"
ORANGE = "#EA580C"
PURPLE = "#7C3AED"
RED    = "#DC2626"
GRAY   = "#6B7280"

# ── 1. Kumulativne opravljene naloge ─────────────────────────────────
ax1 = fig.add_subplot(gs[0, :2])
ax1.plot(sorted_steps, cumulative, color=BLUE, linewidth=2, label="Kumulativne naloge")
ax1.fill_between(sorted_steps, cumulative, color=BLUE, alpha=0.12)
# Ideal linear reference
ideal = np.linspace(0, num_tasks_done, len(sorted_steps))
ax1.plot(sorted_steps, ideal, "--", color=GRAY, linewidth=1.2, label="Idealna linearna rast")
ax1.set_title("Kumulativno opravljene naloge skozi čas", fontsize=11)
ax1.set_xlabel("Timestep")
ax1.set_ylabel("Število nalog")
ax1.legend(fontsize=9)
ax1.grid(True, linestyle="--", alpha=0.5)
ax1.annotate(
    f"Skupaj: {num_tasks_done}",
    xy=(sorted_steps[-1], cumulative[-1]),
    xytext=(-60, -18), textcoords="offset points",
    fontsize=9, color=BLUE,
    arrowprops=dict(arrowstyle="->", color=BLUE, lw=1.2),
)

# ── 2. Throughput po timestepih ──────────────────────────────────────
ax2 = fig.add_subplot(gs[0, 2])
ax2.bar(throughput_steps, throughput_values, color=GREEN, alpha=0.5, width=1.0, label="Naloge/timestep")
ax2.plot(rolling_steps, rolling_avg, color=GREEN, linewidth=2, label=f"Drseče povprečje (n={window})")
ax2.set_title("Throughput (naloge / timestep)", fontsize=11)
ax2.set_xlabel("Timestep")
ax2.set_ylabel("Naloge")
ax2.legend(fontsize=8)
ax2.grid(True, linestyle="--", alpha=0.5)

# ── 3. Porazdelitev nalog po agentih (histogram) ─────────────────────
ax3 = fig.add_subplot(gs[1, 0])
bins = range(min(agent_task_counts), max(agent_task_counts) + 2)
ax3.hist(agent_task_counts, bins=bins, color=PURPLE, edgecolor="white", alpha=0.85)
ax3.axvline(np.mean(agent_task_counts), color=RED, linestyle="--", linewidth=1.5,
            label=f"Povprečje: {np.mean(agent_task_counts):.1f}")
ax3.set_title("Porazdelitev nalog po agentih", fontsize=11)
ax3.set_xlabel("Število nalog na agenta")
ax3.set_ylabel("Število agentov")
ax3.legend(fontsize=8)
ax3.grid(True, linestyle="--", alpha=0.5)

# ── 4. Top 20 agentov po opravljenih nalogah ─────────────────────────
ax4 = fig.add_subplot(gs[1, 1])
top20 = sorted(tasks_per_agent.items(), key=lambda x: x[1], reverse=True)[:20]
top_agents, top_counts = zip(*top20)
colors_bar = [ORANGE if c == max(top_counts) else BLUE for c in top_counts]
bars = ax4.barh([f"A{a}" for a in top_agents], top_counts, color=colors_bar, edgecolor="white")
ax4.set_title("Top 20 agentov (naloge)", fontsize=11)
ax4.set_xlabel("Število opravljenih nalog")
ax4.invert_yaxis()
ax4.grid(True, axis="x", linestyle="--", alpha=0.5)
for bar, val in zip(bars, top_counts):
    ax4.text(val + 0.05, bar.get_y() + bar.get_height() / 2,
             str(val), va="center", fontsize=7)

# ── 5. Planner časi ──────────────────────────────────────────────────
ax5 = fig.add_subplot(gs[1, 2])
if len(pt) > 0:
    timestep_axis = list(range(len(pt)))
    ax5.plot(timestep_axis, pt, color=ORANGE, linewidth=1, alpha=0.7)
    ax5.axhline(np.mean(pt), color=RED, linestyle="--", linewidth=1.5,
                label=f"Povprečje: {np.mean(pt):.2f} ms")
    ax5.axhline(np.percentile(pt, 95), color=GRAY, linestyle=":", linewidth=1.2,
                label=f"P95: {np.percentile(pt, 95):.2f} ms")
    ax5.set_title("Čas načrtovalnika po timestepih", fontsize=11)
    ax5.set_xlabel("Timestep")
    ax5.set_ylabel("Čas [ms]")
    ax5.legend(fontsize=8)
    ax5.grid(True, linestyle="--", alpha=0.5)

# ── 6. Histogram planner časov ───────────────────────────────────────
ax6 = fig.add_subplot(gs[2, 0])
if len(pt) > 0:
    ax6.hist(pt, bins=40, color=ORANGE, edgecolor="white", alpha=0.85)
    ax6.axvline(np.mean(pt), color=RED, linestyle="--", linewidth=1.5,
                label=f"Povprečje: {np.mean(pt):.2f} ms")
    ax6.axvline(np.median(pt), color=BLUE, linestyle="--", linewidth=1.5,
                label=f"Mediana: {np.median(pt):.2f} ms")
    ax6.set_title("Porazdelitev časa načrtovalnika", fontsize=11)
    ax6.set_xlabel("Čas [ms]")
    ax6.set_ylabel("Frekvenca")
    ax6.legend(fontsize=8)
    ax6.grid(True, linestyle="--", alpha=0.5)

# ── 7. Čas nalog po intervalih (box plot simulacija z fill) ──────────
ax7 = fig.add_subplot(gs[2, 1])
interval = max(1, makespan // 10)
buckets  = defaultdict(list)
for ts in finish_timesteps:
    bucket = (ts // interval) * interval
    buckets[bucket].append(ts)
bucket_keys    = sorted(buckets.keys())
bucket_counts  = [len(buckets[k]) for k in bucket_keys]
bucket_labels  = [f"{k}–{k+interval}" for k in bucket_keys]
ax7.bar(range(len(bucket_keys)), bucket_counts, color=GREEN, alpha=0.8, edgecolor="white")
ax7.set_xticks(range(len(bucket_keys)))
ax7.set_xticklabels(bucket_labels, rotation=45, ha="right", fontsize=7)
ax7.set_title(f"Zaključene naloge po intervalih (Δ={interval})", fontsize=11)
ax7.set_xlabel("Interval timestepov")
ax7.set_ylabel("Število nalog")
ax7.grid(True, axis="y", linestyle="--", alpha=0.5)

# ── 8. Ključne statistike (text box) ─────────────────────────────────
ax8 = fig.add_subplot(gs[2, 2])
ax8.axis("off")
avg_tasks_per_agent = np.mean(agent_task_counts)
throughput_overall  = num_tasks_done / makespan if makespan else 0
pt_mean = np.mean(pt) if len(pt) > 0 else 0
pt_max  = np.max(pt)  if len(pt) > 0 else 0
pt_p95  = np.percentile(pt, 95) if len(pt) > 0 else 0

stats = [
    ("Eksperiment",          exp_name),
    ("Model",                action_model),
    ("Veljavnost",           all_valid),
    ("─────────────────",    "──────────"),
    ("Agentov (team size)",  f"{team_size}"),
    ("Nalog opravljenih",    f"{num_tasks_done}"),
    ("Makespan",             f"{makespan} ts"),
    ("Sum of cost",          f"{sum_of_cost}"),
    ("─────────────────",    "──────────"),
    ("Throughput (avg)",     f"{throughput_overall:.2f} nalog/ts"),
    ("Nalog / agent (avg)",  f"{avg_tasks_per_agent:.1f}"),
    ("─────────────────",    "──────────"),
    ("Planner čas (avg)",    f"{pt_mean:.3f} ms"),
    ("Planner čas (P95)",    f"{pt_p95:.3f} ms"),
    ("Planner čas (max)",    f"{pt_max:.3f} ms"),
]
y_pos = 0.97
for key, val in stats:
    ax8.text(0.02, y_pos, key, transform=ax8.transAxes,
             fontsize=9, fontweight="bold", va="top", color="#374151")
    ax8.text(0.55, y_pos, val, transform=ax8.transAxes,
             fontsize=9, va="top", color="#1D4ED8")
    y_pos -= 0.063

ax8.set_title("Povzetek", fontsize=11)
rect = plt.Rectangle((0, 0), 1, 1, transform=ax8.transAxes,
                     fill=True, facecolor="#F0F9FF", edgecolor="#BFDBFE", linewidth=1.5)
ax8.add_patch(rect)
# Re-render text above the patch
y_pos = 0.97
for key, val in stats:
    ax8.text(0.02, y_pos, key, transform=ax8.transAxes,
             fontsize=9, fontweight="bold", va="top", color="#374151", zorder=5)
    ax8.text(0.55, y_pos, val, transform=ax8.transAxes,
             fontsize=9, va="top", color="#1D4ED8", zorder=5)
    y_pos -= 0.063

# ─────────────────────────── Save ───────────────────────────────────
output_img = os.path.join(exp_dir, f"plot_{exp_name}.png")
plt.savefig(output_img, dpi=150, bbox_inches="tight")
print(f"\nGraf shranjen: {output_img}")
plt.show()