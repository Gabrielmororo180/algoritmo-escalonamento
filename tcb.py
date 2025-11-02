"""tcb.py
=========
Representa a estrutura mínima de uma tarefa (Process Control Block simplificado).

Justificativa de atributos:
- `id`: identificação única, usada para exibição e mapa de chegada/conclusão.
- `color`: cor no gráfico de Gantt para facilitar distinção visual.
- `arrival`: tick de criação/ingresso no sistema (usado para liberar a tarefa).
- `duration`: tempo total necessário de CPU (base para SRTF e cálculo de restante).
- `priority`: valor numérico, maior significa maior prioridade na política atual.
- `events`: lista de strings representando eventos (IO, mutex, etc.) – ainda não
    afetam bloqueio, futura extensão.
- `remaining_time`: decrementado a cada tick de execução.
- `completed`: marca finalização para evitar re-escalonamento.
- `executed_ticks`: acumula total efetivo de execução (pode divergir de duration
    em cenários futuros com preempções e pausas).
"""

class TaskControlBlock:
    def __init__(self, id_, color, arrival, duration, priority, events):
        self.id = id_
        self.color = color
        self.arrival = arrival
        self.duration = duration

        self.priority = priority

        self.events = events

        self.remaining_time = duration
        self.completed = False
        self.executed_ticks = 0
        self.executed_count = 0
