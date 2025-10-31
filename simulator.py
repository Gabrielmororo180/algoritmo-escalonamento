"""simulator.py
=================
Contém a classe Simulator que executa o loop de escalonamento e coleta dados
para visualização (timeline de execução e períodos de espera) e métricas
básicas de chegada/conclusão.

Decisões de design:
-------------------
1. `ready_queue` mantém apenas tarefas aguardando CPU. Ao iniciar execução
    a tarefa é removida da fila; isso evita remoções duplicadas em término.
2. Preempção delegada aos algoritmos via atributo `should_preempt` – reduz
    complexidade aqui.
3. `wait_map` registra ticks em que cada tarefa está pronta mas não executa.
    Facilita visualização do tempo de espera e futura extração de métricas.
4. `timeline` armazena por tick o id da tarefa executada ou None (idle).
5. `arrivals_map` e `finish_map` guardam instante de chegada e término (exclusivo).
6. Quantum só é incrementado se o algoritmo não sinaliza `ignore_quantum`.
"""

from tcb import TaskControlBlock
from scheduler import get_scheduler
from gantt_renderer import render_gantt_terminal, render_gantt_image, render_gantt_live

class Simulator:
    def __init__(self, config):
        """Inicializa o simulador.

        Parâmetro `config` esperado:
        {
            'algorithm': <str>,
            'quantum': <int>,
            'tasks': [ {id_, color, arrival, duration, priority, events[]} ]
        }

        Justificativa: manter config como dict simples facilita carga de
        diferentes fontes (arquivo, CLI, GUI) sem acoplamento a tipos.
        """
        self.quantum = config["quantum"]
        self.scheduler = get_scheduler(config["algorithm"])
        self.time = 0
        self.tick_limit = 1000

        self.tasks = [
            TaskControlBlock(**task) for task in config["tasks"]
        ]
        self.ready_queue = []
        self.running_task = None
        self.timeline = []
        # Lista por tick da tarefa em execução (None ou 'IDLE')
        # E um dict acumulando ticks de espera por tarefa para o renderer avançado
        self.wait_map = {}
        self.arrivals_map = {}
        self.finish_map = {}
        # Flag interna para habilitar verbosidade adicional em modo debug
        self.debug_mode = False
        # Mapa de cores definidas por tarefa (id -> cor configurada)
        self.task_colors = {t.id: t.color for t in self.tasks}

    def run(self):
        """Executa a simulação completa até todas as tarefas finalizarem
        ou até alcançar `tick_limit` de segurança para evitar loops.
        """
        print(f"Iniciando simulação com algoritmo: {self.scheduler.__name__}")
        while not self.all_tasks_completed() and self.time < self.tick_limit:
            self._check_arrivals()  
            self._schedule()        
            self._tick()
            
            self.time += 1
        print("Simulação encerrada.")
        render_gantt_terminal(self.timeline)
        # Passa mapas completos + cores definidas pelo usuário
        render_gantt_image(self.timeline, arrivals=self.arrivals_map, finishes=self.finish_map, wait_map=self.wait_map, task_colors=self.task_colors)

    def run_debug(self):
        """Reinicia estado interno para modo passo-a-passo.
        Não avança ticks automaticamente; usar `step()`.
        """
        self.time = 0
        self.timeline = []
        self.ready_queue = []
        self.running_task = None
        self.wait_map = {}
        self.arrivals_map = {}
        self.finish_map = {}
        for task in self.tasks:
            task.remaining_time = task.duration
            task.completed = False
            task.executed_ticks = 0
        self.debug_mode = True

    def snapshot(self):
        """Retorna um dicionário imutável com o estado corrente do sistema.

        Campos principais:
        - time: tick atual
        - running: id da tarefa em execução ou None
        - ready_queue: lista de ids das tarefas prontas
        - tasks: lista de dicts por tarefa (id, arrival, duration, remaining, priority,
                 completed, waited_ticks, executed_ticks)
        - wait_map: mapa de ticks de espera (cópia superficial)
        - timeline: cópia da linha do tempo até agora
        - algorithm: nome do algoritmo ativo
        - quantum: valor configurado
        """
        task_states = []
        for t in self.tasks:
            task_states.append({
                "id": t.id,
                "arrival": t.arrival,
                "duration": t.duration,
                "remaining": t.remaining_time,
                "priority": t.priority,
                "completed": t.completed,
                "executed_ticks": t.executed_ticks,
                "waited_ticks": len(self.wait_map.get(t.id, [])),
                "waiting_now": (t in self.ready_queue and t is not self.running_task and not t.completed)
            })
        return {
            "time": self.time,
            "running": self.running_task.id if self.running_task else None,
            "ready_queue": [t.id for t in self.ready_queue],
            "tasks": task_states,
            "wait_map": {k: list(v) for k, v in self.wait_map.items()},
            "timeline": list(self.timeline),
            "algorithm": self.scheduler.__name__,
            "quantum": self.quantum
        }

    def step(self):
        """Executa um único tick da simulação em modo debug.
        Retorna False se terminou ou atingiu limite.
        """
        if self.all_tasks_completed() or self.time >= self.tick_limit:
            return False 

        self._check_arrivals()  
        self._schedule()        
        self._tick()
        if self.debug_mode:
            snap = self.snapshot()
            print(f"[Tick {self.time}] EXEC: {snap['running']} | READY: {snap['ready_queue']} | QUANTUM={self.quantum}")
            for ts in snap['tasks']:
                print(f"  - {ts['id']}: rem={ts['remaining']} dur={ts['duration']} prio={ts['priority']} waited={ts['waited_ticks']} completed={ts['completed']} waiting_now={ts['waiting_now']}")
            # Atualização incremental: evita gerar várias figuras
            render_gantt_live(self.timeline, arrivals=self.arrivals_map, finishes=self.finish_map, wait_map=self.wait_map, task_colors=self.task_colors)
        else:
            render_gantt_terminal(self.timeline)
        self.time += 1
        return True


    def _check_arrivals(self):
        """Move tarefas cujo tempo de chegada == tempo atual para a ready_queue.
        Armazena instante em `arrivals_map` se ainda não registrado.
        """
        for task in self.tasks:
            if task.arrival == self.time and task not in self.ready_queue and not task.completed:
                self.ready_queue.append(task)
                # registra chegada
                self.arrivals_map.setdefault(task.id, self.time)

    def _schedule(self):
        # Se não há tarefa rodando ou a atual terminou, escolher nova.
        if not self.running_task or self.running_task.remaining_time <= 0:
            self.running_task = self.scheduler(self.ready_queue)
            if self.running_task:
                self.running_task.executed_quantum = 0
                # Remove da fila pois agora está em execução
                if self.running_task in self.ready_queue:
                    self.ready_queue.remove(self.running_task)
            return

        # Preempção imediata delegada ao scheduler (should_preempt)
        if getattr(self.scheduler, 'preemptive', False):
            candidate = self.scheduler(self.ready_queue)
            if candidate and candidate is not self.running_task:
                should_switch = False
                if hasattr(self.scheduler, 'should_preempt'):
                    should_switch = self.scheduler.should_preempt(self.running_task, candidate)
                if should_switch:
                    if self.running_task not in self.ready_queue and not self.running_task.completed:
                        self.ready_queue.append(self.running_task)
                    self.running_task.executed_quantum = 0
                    # Remover candidata da fila e promover
                    if candidate in self.ready_queue:
                        self.ready_queue.remove(candidate)
                    self.running_task = candidate

    def apply_aging(self):
        #Exemplo simples de aging: incrementa prioridade de quem está esperando.
        for task in self.ready_queue:
            if task != self.running_task and not task.completed:
                task.priority += 1 


    def _tick(self):
        """Avança um tick de tempo:
        - Atualiza tempos da tarefa corrente
        - Registra espera das demais
        - Aplica lógica de término ou de expiração de quantum
        - Adiciona ID (ou None) à timeline para visualização
        """
        if self.running_task:
            self.running_task.remaining_time -= 1
            self.running_task.executed_ticks += 1
            # Incrementa quantum somente se algoritmo usa quantum e não ignora.
            if (not getattr(self.scheduler, 'non_preemptive', False) and
                not getattr(self.scheduler, 'ignore_quantum', False)):
                self.running_task.executed_quantum += 1
            self.timeline.append(self.running_task.id)
            # Marca espera das demais tarefas na fila
            for task in self.ready_queue:
                if task is not self.running_task and not task.completed:
                    self.wait_map.setdefault(task.id, []).append(self.time)

            if self.running_task.remaining_time <= 0:
                self.running_task.completed = True
                # Não precisa remover: já foi removida ao iniciar execução
                print(f"Tarefa {self.running_task.id} concluída em t={self.time}")
                self.finish_map[self.running_task.id] = self.time + 1  # fim exclusivo
                self.running_task = None

            elif (not getattr(self.scheduler, 'non_preemptive', False) and
                  not getattr(self.scheduler, 'ignore_quantum', False) and
                  self.running_task.executed_quantum >= self.quantum):
                # Quantum expirou: preempção por fatia de tempo (Round-Robin genérico)
                print(f"Tarefa {self.running_task.id} preemptada por quantum em t={self.time}")
                # Rotaciona tarefa
                self.ready_queue.append(self.running_task)
                self.running_task.executed_quantum = 0
                self.running_task = None
        else:
            # CPU ociosa
            self.timeline.append(None)
            # Todas na fila estão esperando
            for task in self.ready_queue:
                if not task.completed:
                    self.wait_map.setdefault(task.id, []).append(self.time)


    def all_tasks_completed(self):
        """Retorna True se todas as tarefas marcaram `completed=True`.
        Facilita leitura do loop principal.
        """
        return all(task.completed for task in self.tasks)
