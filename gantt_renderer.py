import matplotlib.pyplot as plt

def render_gantt_terminal(timeline, wait_map=None):
    print("\nGráfico de Gantt (terminal):\n")
    header = ""
    values = ""
    for tick, task_id in enumerate(timeline):
        header += f"{task_id[:3]:^5}"
        values += f"{tick:^5}"
    print(header)
    print(values)
    if wait_map:
        print("\nTempos de espera (ticks):")
        for tid, ticks in wait_map.items():
            print(f"{tid}: {len(ticks)} ticks -> {ticks}")


def render_gantt_image(timeline, arrivals=None, finishes=None, wait_map=None, filename="gantt.png"):
    """
    timeline: lista com a tarefa executada em cada unidade de tempo
              Ex: ["T1","T1","T2", None, "T3", ...]  (pode usar None se CPU ociosa)
    arrivals: opcional dict {"T1": t_arrival, ...}
    finishes: opcional dict {"T1": t_finish, ...} (t_finish é exclusivo: intervalo [arrival, finish))
    """

    total_time = len(timeline)
    # tarefas únicas ignorando None
    tasks = sorted({t for t in timeline if t is not None and t != 'IDLE'})

    # calcula arrivals/finishes se não fornecidos (se chegarem do simulador, usa direto)
    if arrivals is None or finishes is None:
        arrivals = {} if arrivals is None else dict(arrivals)
        finishes = {} if finishes is None else dict(finishes)
        for task in tasks:
            # primeiro índice onde aparece
            if task not in arrivals:
                for i, cur in enumerate(timeline):
                    if cur == task:
                        arrivals[task] = i
                        break
            # último índice onde aparece -> finish = last_index + 1
            if task not in finishes:
                last = None
                for i in range(total_time - 1, -1, -1):
                    if timeline[i] == task:
                        last = i
                        break
                finishes[task] = (last + 1) if last is not None else arrivals.get(task, 0)

    fig, ax = plt.subplots(figsize=(10, 0.8 * max(3, len(tasks))))
    colors = plt.cm.tab10.colors
    for i, task in enumerate(tasks):
        y_pos = i - 0.4
        start_time = arrivals.get(task, 0)
        end_time = finishes.get(task, total_time)
        life_duration = max(0, end_time - start_time)

        # Vida total como contorno apenas (sem preenchimento) para referência
        ax.broken_barh([(start_time, life_duration)], (y_pos, 0.8),
                       facecolors="none", edgecolors="black", linewidth=1.2)

        # Intervalos de execução
        intervals = []
        s = None
        for t, cur in enumerate(timeline):
            if cur == task:
                if s is None:
                    s = t
            else:
                if s is not None:
                    intervals.append((s, t - s))
                    s = None
        if s is not None:
            intervals.append((s, total_time - s))

        # 3) pintar intervalos de execução (somente se estiverem dentro da vida)
        color = colors[i % len(colors)]
        for st, dur in intervals:
            # recorta para que não ultrapasse [start_time, end_time)
            seg_start = max(st, start_time)
            seg_end = min(st + dur, end_time)
            seg_dur = seg_end - seg_start
            if seg_dur > 0:
                ax.broken_barh([(seg_start, seg_dur)], (y_pos, 0.8),
                               facecolors=color, edgecolors="black", linewidth=1.2)

        # Ticks de espera: inclui todos os ticks entre arrival e end que não estão em execução
        waiting_ticks = set()
        if wait_map and task in wait_map:
            waiting_ticks.update(wait_map[task])
        # Inclui também ticks antes da primeira execução se a tarefa chegou e não executou ainda
        # Constrói conjunto execução para rapidez
        exec_ticks = set()
        for st, dur in intervals:
            for tt in range(st, st + dur):
                exec_ticks.add(tt)
        for tt in range(start_time, end_time):
            if tt not in exec_ticks:
                waiting_ticks.add(tt)

        # Agrupa ticks contíguos
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

        for st, dur in wait_intervals:
            if dur > 0:
                ax.broken_barh([(st, dur)], (y_pos, 0.8),
                               facecolors="white", edgecolors="black", linewidth=0.8, hatch=None)

    # ajustes visuais
    ax.set_xlabel("Tempo (t)")
    ax.set_ylabel("Tarefas")
    ax.set_yticks(range(len(tasks)))
    ax.set_yticklabels(tasks)
    ax.set_xticks(range(total_time + 1))
    ax.grid(True, axis='x', linestyle=':', alpha=0.5)
    ax.invert_yaxis()
    plt.title("Gráfico de Gantt (execução vs espera)")
    plt.tight_layout()
    plt.savefig(filename, format="png", dpi=300)
    plt.show()