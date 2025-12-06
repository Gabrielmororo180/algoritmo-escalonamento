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
- `io_events`: lista de operações de E/S {type: "io", time, duration}
    - time: quando a operação inicia (relativo ao início da tarefa)
    - duration: quantos ticks a operação leva
- `remaining_time`: decrementado a cada tick de execução.
- `completed`: marca finalização para evitar re-escalonamento.
- `executed_ticks`: acumula total efetivo de execução.
- `blocked`: bool - se tarefa está bloqueada esperando mutex
- `io_blocked`: bool - se tarefa está bloqueada em operação de E/S
- `io_remaining`: tempo restante da operação de E/S atual
- `elapsed_time`: tempo de execução relativo ao início da tarefa (para rastrear eventos)
"""

class TaskControlBlock:
    def __init__(self, id_, color, arrival, duration, priority, events, io_events=None):
        self.id = id_
        self.color = color
        self.arrival = arrival
        self.duration = duration
        # Prioridade estática (pe) e dinâmica (pd)
        self.priority = priority  # manter compatibilidade: pe
        self.static_priority = priority
        self.dynamic_priority = priority
        
        # Eventos de mutex: lista de {type, mutex_id, time}
        self.events = events if events else []
        
        # Eventos de IO: lista de {type: "io", time, duration}
        self.io_events = io_events if io_events else []
        
        # Estado de execução
        self.remaining_time = duration
        self.completed = False
        self.executed_ticks = 0
        self.executed_count = 0
        
        # Estado de bloqueio por mutex
        self.blocked = False
        self.blocking_mutex_id = None  # qual mutex está bloqueando
        
        # Estado de bloqueio por IO
        self.io_blocked = False
        self.io_remaining = 0  # tempo restante na operação de IO
        
        # Tempo relativo desde que começou a executar (para rastrear eventos)
        self.elapsed_time = 0
        
        # Marcar se foi escolhida por sorteio (para Gantt)
        self.chosen_by_lottery = False
    
    def get_pending_events(self, current_time):
        """Retorna eventos de mutex que devem acontecer no tempo atual.
        
        Args:
            current_time (int): tempo decorrido desde o início da execução
            
        Returns:
            list: eventos que acontecem neste tick
        """
        return [e for e in self.events if e.get("time") == current_time]
    
    def get_pending_io(self, current_time):
        """Retorna PRIMEIRO evento de IO que deve iniciar no tempo atual.
        
        DEPRECATED: use get_pending_ios() em vez disso para suportar múltiplos IOs.
        
        Args:
            current_time (int): tempo decorrido desde o início da execução
            
        Returns:
            dict or None: evento de IO que inicia neste tick, ou None
        """
        for io_event in self.io_events:
            if io_event.get("time") == current_time:
                return io_event
        return None
    
    def get_pending_ios(self, current_time):
        """Retorna TODOS os eventos de IO que devem iniciar no tempo atual.
        
        Mantém ordem de aparição no arquivo de configuração (critério 3.5).
        
        Args:
            current_time (int): tempo decorrido desde o início da execução
            
        Returns:
            list: eventos de IO que iniciam neste tick, em ordem
        """
        return [io_event for io_event in self.io_events if io_event.get("time") == current_time]
    
    def __repr__(self):
        status = "BLOCKED" if self.blocked else "IO_BLOCKED" if self.io_blocked else "RUNNING" if not self.completed else "DONE"
        return f"TCB({self.id}, {status}, remaining={self.remaining_time}, pe={self.static_priority}, pd={self.dynamic_priority})"
