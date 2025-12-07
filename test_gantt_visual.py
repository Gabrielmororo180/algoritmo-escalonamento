"""
Test script to generate gantt.png with suspension visualization
"""
from config_loader import load_config
from simulator import Simulator
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import re

def test_gantt():
    cfg = load_config('sample_config.txt')
    sim = Simulator(cfg)
    
    # Run simulation
    while not sim.all_tasks_completed():
        sim.queue_changed = False
        sim._check_arrivals()
        if sim.queue_changed or not sim.running_task:
            sim._schedule()
        sim._tick()
        sim.time += 1
    
    # Print suspended_map
    print("Suspended map (IO/Mutex bloqueios):")
    for task_id, ticks in sorted(sim.suspended_map.items()):
        print(f"  {task_id}: {ticks}")
    
    # Create figure similar to render_gantt_in_frame
    fig, ax = plt.subplots(figsize=(14, 6))
    
    timeline = sim.timeline
    arrivals = sim.arrivals_map
    finishes = sim.finish_map
    wait_map = sim.wait_map
    suspended_map = sim.suspended_map
    task_colors = sim.task_colors
    
    # Extract tasks
    task_ids = set()
    for t in timeline:
        if t is not None and t != 'IDLE':
            match = re.match(r'(T\d+)', str(t))
            if match:
                task_ids.add(match.group(1))
    
    tasks = sorted(task_ids)
    total_time = len(timeline)
    colors = plt.cm.tab10.colors
    
    print(f"\nTasks: {tasks}")
    print(f"Total time: {total_time}")
    
    for i, task in enumerate(tasks):
        y_pos = i - 0.4
        start_time = arrivals.get(task, 0)
        end_time = finishes.get(task, total_time)
        life_duration = max(0, end_time - start_time)
        
        # Background (life)
        ax.broken_barh([(start_time, life_duration)], (y_pos, 0.8),
                      facecolors="none", edgecolors="black", linewidth=1.2)
        
        # Execution intervals
        intervals = []
        s = None
        for t, cur in enumerate(timeline):
            cur_base = str(cur).rstrip('L') if cur else None
            if cur_base == task:
                if s is None:
                    s = t
            else:
                if s is not None:
                    intervals.append((s, t - s))
                    s = None
        if s is not None:
            intervals.append((s, total_time - s))
        
        # Color
        if task_colors and task in task_colors:
            color = task_colors[task]
        else:
            color = colors[i % len(colors)]
        
        # Paint execution
        for st, dur in intervals:
            seg_start = max(st, start_time)
            seg_end = min(st + dur, end_time)
            seg_dur = seg_end - seg_start
            if seg_dur > 0:
                ax.broken_barh([(seg_start, seg_dur)], (y_pos, 0.8),
                              facecolors=color, edgecolors="black", linewidth=1.2)
        
        # Execution ticks set
        exec_ticks = set()
        for st, dur in intervals:
            for tt in range(st, st + dur):
                exec_ticks.add(tt)
        
        # Waiting intervals
        waiting_ticks = set()
        if wait_map and task in wait_map:
            waiting_ticks.update(wait_map[task])
        
        for tt in range(start_time, end_time):
            if tt not in exec_ticks:
                waiting_ticks.add(tt)
        
        wait_intervals = []
        ws = None
        for t in range(start_time, end_time):
            if t in waiting_ticks and t not in exec_ticks:
                if ws is None:
                    ws = t
            else:
                if ws is not None:
                    wait_intervals.append((ws, t - ws))
                    ws = None
        if ws is not None:
            wait_intervals.append((ws, end_time - ws))
        
        # Paint waiting (white)
        for st, dur in wait_intervals:
            if dur > 0:
                ax.broken_barh([(st, dur)], (y_pos, 0.8),
                              facecolors="white", edgecolors="black", linewidth=0.8)
        
        # Paint suspension (light gray)
        suspended_ticks = set()
        if suspended_map and task in suspended_map:
            suspended_ticks.update(suspended_map[task])
        
        suspend_intervals = []
        ss = None
        for t in range(start_time, end_time):
            if t in suspended_ticks and t not in exec_ticks:
                if ss is None:
                    ss = t
            else:
                if ss is not None:
                    suspend_intervals.append((ss, t - ss))
                    ss = None
        if ss is not None:
            suspend_intervals.append((ss, end_time - ss))
        
        print(f"\n{task}:")
        print(f"  Execution intervals: {intervals}")
        print(f"  Suspended ticks: {sorted(suspended_ticks)}")
        print(f"  Suspension intervals: {suspend_intervals}")
        
        # Paint suspension intervals (light gray) with duration label
        for st, dur in suspend_intervals:
            if dur > 0:
                ax.broken_barh([(st, dur)], (y_pos, 0.8),
                              facecolors="#D3D3D3", edgecolors="black", linewidth=0.8)
                # Add duration label in the middle of the gray block
                mid_x = st + dur / 2
                ax.text(mid_x, y_pos + 0.4, f"{dur}", ha='center', va='center',
                       fontsize=8, weight='bold', color='black')
    
    ax.set_ylim(-1, len(tasks))
    ax.set_xlim(-1, total_time + 1)
    ax.set_yticks(range(len(tasks)))
    ax.set_yticklabels(tasks)
    ax.set_xlabel("Tempo (t)")
    ax.set_ylabel("Tarefas")
    ax.set_title(f"Gráfico de Gantt - {sim.algorithm_name}")
    ax.grid(True, alpha=0.3, axis='x')
    
    fig.savefig("gantt_test.png", format="png", dpi=300, bbox_inches='tight')
    print(f"\n✓ Saved to gantt_test.png")
    plt.close(fig)

if __name__ == "__main__":
    test_gantt()
