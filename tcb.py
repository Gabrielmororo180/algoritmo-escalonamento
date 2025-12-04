"""tcb.py
=========
Representa a estrutura mínima de uma tarefa (Process Control Block simplificado).

Justificativa de atributos:
- `id`: identificação única, usada para exibição e mapa de chegada/conclusão.
- `color`: cor no gráfico de Gantt para facilitar distinção visual.
- `arrival`: tick de criação/ingresso no sistema (usado para liberar a tarefa).
- `duration`: tempo total necessário de CPU (base para SRTF e cálculo de restante).
- `priority`: valor numérico, maior significa maior prioridade na política atual.
- `events`: lista de dicionários com eventos de mutex {type, mutex_id, time}
    - type: "lock" ou "unlock"
    - mutex_id: número do mutex
    - time: tempo relativo ao início da tarefa quando ação ocorre
- `remaining_time`: decrementado a cada tick de execução.
- `completed`: marca finalização para evitar re-escalonamento.
- `executed_ticks`: acumula total efetivo de execução.
- `blocked`: bool - se tarefa está bloqueada esperando mutex
- `elapsed_time`: tempo de execução relativo ao início da tarefa (para rastrear eventos)
"""

class TaskControlBlock:
    def __init__(self, id_, color, arrival, duration, priority, events):
        self.id = id_
        self.color = color
        self.arrival = arrival
        self.duration = duration
        self.priority = priority
        
        # Eventos de mutex: lista de {type, mutex_id, time}
        self.events = events if events else []
        
        # Estado de execução
        self.remaining_time = duration
        self.completed = False
        self.executed_ticks = 0
        self.executed_count = 0
        
        # Estado de bloqueio por mutex
        self.blocked = False
        self.blocking_mutex_id = None  # qual mutex está bloqueando
        
        # Tempo relativo desde que começou a executar (para rastrear eventos)
        self.elapsed_time = 0
    
    def get_pending_events(self, current_time):
        """Retorna eventos que devem acontecer no tempo atual (relativo ao início).
        
        Args:
            current_time (int): tempo decorrido desde o início da execução
            
        Returns:
            list: eventos que acontecem neste tick
        """
        return [e for e in self.events if e.get("time") == current_time]
    
    def __repr__(self):
        status = "BLOCKED" if self.blocked else "RUNNING" if not self.completed else "DONE"
        return f"TCB({self.id}, {status}, remaining={self.remaining_time})"
