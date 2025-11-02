"""gantt_renderer.py
=====================
Responsável por gerar representações do cronograma de execução:
- Terminal: tabela simplificada de tarefa por tick.
- Imagem: gráfico de Gantt com diferenciação de execução (colorido) e espera (branco com borda).

Decisões chave:
1. Usar lista `timeline` indexada por tick simplifica reconstrução de intervalos.
2. Calcular intervalos de execução por varredura linear evita armazenar estruturas extras.
3. Espera é derivada: todos os ticks entre arrival e finish que não pertencem a execução.
4. Atualização incremental usa `plt.pause(0.001)` para manter responsividade.
"""

import matplotlib.pyplot as plt

# Objetos globais para renderização incremental
_LIVE_FIG = None
_LIVE_AX = None
_LIVE_LAST_LEN = 0

def render_gantt_terminal(timeline, wait_map=None):
    """Renderização simples em texto da linha do tempo.

    Usa '---' para ticks ociosos (None) para evitar exceção ao fatiar.
    """
    print("\nGráfico de Gantt (terminal):\n")
    header = ""
    values = ""
    for tick, task_id in enumerate(timeline):
        label = (task_id[:3] if isinstance(task_id, str) else '---')
        header += f"{label:^5}"
        values += f"{tick:^5}"
    print(header)
    print(values)
    if wait_map:
        print("\nTempos de espera (ticks):")
        for tid, ticks in wait_map.items():
            print(f"{tid}: {len(ticks)} ticks -> {ticks}")


def render_gantt_image(timeline, arrivals=None, finishes=None, wait_map=None, task_colors=None, filename="gantt.png"):
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

    # Altura proporcional ao número de tarefas para leitura adequada.
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

    # Intervalos de execução: detecta blocos contíguos de mesma tarefa.
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
        if task_colors and task in task_colors:
            color = task_colors[task]
        else:
            color = colors[i % len(colors)]
        for st, dur in intervals:
            # recorta para que não ultrapasse [start_time, end_time)
            seg_start = max(st, start_time)
            seg_end = min(st + dur, end_time)
            seg_dur = seg_end - seg_start
            if seg_dur > 0:
                ax.broken_barh([(seg_start, seg_dur)], (y_pos, 0.8),
                               facecolors=color, edgecolors="black", linewidth=1.2)

    # Ticks de espera: inclui todos os ticks entre arrival e end não presentes em exec_ticks.
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

    # Agrupa ticks contíguos para reduzir objetos desenhados (melhor performance e clareza visual).
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

    plt.title("Gráfico de Gantt (execução vs espera)")
    plt.tight_layout()
    plt.savefig(filename, format="png", dpi=300)
    plt.show()

def render_gantt_live(timeline, arrivals=None, finishes=None, wait_map=None, task_colors=None):
    """Renderiza incrementalmente uma única figura de Gantt usando as cores originais das tarefas.

    Só redesenha quando o tamanho da timeline aumenta.
    """
    global _LIVE_FIG, _LIVE_AX, _LIVE_LAST_LEN
    total_time = len(timeline)
    if _LIVE_FIG is None:
        _LIVE_FIG, _LIVE_AX = plt.subplots(figsize=(10, 4))
    if total_time == _LIVE_LAST_LEN:
        plt.pause(0.001)
        return
    _LIVE_LAST_LEN = total_time
    _LIVE_AX.clear()

    tasks = sorted({t for t in timeline if t is not None and t != 'IDLE'})
    if arrivals is None:
        arrivals = {}
        for task in tasks:
            for i, cur in enumerate(timeline):
                if cur == task:
                    arrivals[task] = i
                    break
    if finishes is None:
        finishes = {}
        for task in tasks:
            last = None
            for i in range(total_time - 1, -1, -1):
                if timeline[i] == task:
                    last = i
                    break
            finishes[task] = (last + 1) if last is not None else arrivals.get(task, 0)

    colors = plt.cm.tab10.colors
    for i, task in enumerate(tasks):
        y_pos = i - 0.4
        start_time = arrivals.get(task, 0)
        end_time = finishes.get(task, total_time)
        life_duration = max(0, end_time - start_time)
        _LIVE_AX.broken_barh([(start_time, life_duration)], (y_pos, 0.8), facecolors='none', edgecolors='black', linewidth=1.0)
        intervals = []
        s = None
        for t_idx, cur in enumerate(timeline):
            if cur == task:
                if s is None:
                    s = t_idx
            else:
                if s is not None:
                    intervals.append((s, t_idx - s))
                    s = None
        if s is not None:
            intervals.append((s, total_time - s))
        exec_ticks = set()
        for st, dur in intervals:
            for tt in range(st, st + dur):
                exec_ticks.add(tt)
        if task_colors and task in task_colors:
            color = task_colors[task]
        else:
            color = colors[i % len(colors)]
        for st, dur in intervals:
            seg_start = max(st, start_time)
            seg_end = min(st + dur, end_time)
            seg_dur = seg_end - seg_start
            if seg_dur > 0:
                _LIVE_AX.broken_barh([(seg_start, seg_dur)], (y_pos, 0.8), facecolors=color, edgecolors='black', linewidth=1.0)
        waiting_ticks = set()
        if wait_map and task in wait_map:
            waiting_ticks.update(wait_map[task])
        for tt in range(start_time, end_time):
            if tt not in exec_ticks:
                waiting_ticks.add(tt)
        wait_intervals = []
        ws = None
        for tt in range(start_time, end_time):
            if tt in waiting_ticks and tt not in exec_ticks:
                if ws is None:
                    ws = tt
            else:
                if ws is not None:
                    wait_intervals.append((ws, tt - ws))
                    ws = None
        if ws is not None:
            wait_intervals.append((ws, end_time - ws))
        for st, dur in wait_intervals:
            if dur > 0:
                _LIVE_AX.broken_barh([(st, dur)], (y_pos, 0.8), facecolors='white', edgecolors='black', linewidth=0.8)

    _LIVE_AX.set_xlabel('Tempo (t)')
    _LIVE_AX.set_ylabel('Tarefas')
    _LIVE_AX.set_yticks(range(len(tasks)))
    _LIVE_AX.set_yticklabels(tasks)
    _LIVE_AX.set_xticks(range(total_time + 1))
    _LIVE_AX.grid(True, axis='x', linestyle=':', alpha=0.4)
    _LIVE_AX.set_title('Debug Gantt (incremental)')
    _LIVE_FIG.tight_layout()
    plt.pause(0.001)