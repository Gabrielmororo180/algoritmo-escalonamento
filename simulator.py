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
6. Algoritmos:
   - FIFO: 
   - SRTF: 
   - PRIOP: 
"""

from tcb import TaskControlBlock
from scheduler import get_scheduler
from mutex import Mutex
from io_operation import IOOperation


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
        self.algorithm_name = config["algorithm"]
        self.scheduler = get_scheduler(config["algorithm"])
        self.time = 0
        self.tick_limit = 1000

        self.tasks = [
            TaskControlBlock(**task) for task in config["tasks"]
        ]
        self.ready_queue = []
        self.running_task = None
        self.timeline = []
       

        self.wait_map = {}
        self.arrivals_map = {}
        self.finish_map = {}
        self.debug_mode = False

        # Pool de mutexes: mapeamento de mutex_id -> objeto Mutex
        self.mutexes = {}
        self._initialize_mutexes()

        # Mapa de cores definidas por tarefa (id -> cor configurada)
        self.task_colors = {t.id: t.color for t in self.tasks}

    def _initialize_mutexes(self):
        """Identifica todos os mutexes referenciados nos eventos das tarefas
        e cria objetos Mutex para cada um."""
        mutex_ids = set()
        for task in self.tasks:
            for event in task.events:
                if event.get("type") in ("lock", "unlock"):
                    mutex_ids.add(event.get("mutex_id"))
        
        for mutex_id in mutex_ids:
            self.mutexes[mutex_id] = Mutex(mutex_id)

    def render_gantt_terminal(self, timeline, wait_map=None):
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

    def run(self):
        """Executa a simulação completa até todas as tarefas finalizarem
        ou até alcançar `tick_limit` de segurança para evitar loops.
        """
        print(f"Iniciando simulação com algoritmo: {self.algorithm_name}")
        while not self.all_tasks_completed() and self.time < self.tick_limit:
            self._check_arrivals()  
            self._schedule()        
            self._tick()
            
            self.time += 1
        print("Simulação encerrada.")
        self.render_gantt_terminal(self.timeline, self.wait_map)

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
        
        # Reinicializa estado das tarefas
        for task in self.tasks:
            task.remaining_time = task.duration
            task.completed = False
            task.executed_ticks = 0
            task.blocked = False
            task.blocking_mutex_id = None
            task.elapsed_time = 0
            task.io_blocked = False
            task.io_remaining = 0
        
        # Reinicializa mutexes
        self._initialize_mutexes()
        
        self.debug_mode = True

    def snapshot(self):
        """Retorna um dicionário imutável com o estado corrente do sistema.

        Campos principais:
        - time: tick atual
        - running: id da tarefa em execução ou None
        - ready_queue: lista de ids das tarefas prontas
        - tasks: lista de dicts por tarefa (id, arrival, duration, remaining, priority,
                 completed, waited_ticks, executed_ticks, blocked, blocking_mutex_id,
                 io_blocked, io_remaining)
        - wait_map: mapa de ticks de espera (cópia superficial)
        - timeline: cópia da linha do tempo até agora
        - algorithm: nome do algoritmo ativo
        - quantum: valor configurado
        - mutexes: estado de cada mutex {id, locked, owner, waiting}
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
                "waiting_now": (t in self.ready_queue and t is not self.running_task and not t.completed),
                "blocked": t.blocked,
                "blocking_mutex_id": t.blocking_mutex_id,
                "io_blocked": t.io_blocked,
                "io_remaining": t.io_remaining
            })
        
        mutex_states = [self.mutexes[m_id].get_status() for m_id in sorted(self.mutexes.keys())]
        
        return {
            "time": self.time,
            "running": self.running_task.id if self.running_task else None,
            "ready_queue": [t.id for t in self.ready_queue],
            "tasks": task_states,
            "wait_map": {k: list(v) for k, v in self.wait_map.items()},
            "timeline": list(self.timeline),
            "algorithm": self.scheduler.__name__,
            "quantum": self.quantum,
            "mutexes": mutex_states
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
            #render_gantt_live(self.timeline, arrivals=self.arrivals_map, finishes=self.finish_map, wait_map=self.wait_map, task_colors=self.task_colors)
        else:
            self.render_gantt_terminal(self.timeline)
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
        """Realiza escalonamento: escolhe próxima tarefa ou verifica preempção.
        SRTF/PRIOP: preemptivos, verificam a cada tick se deve trocar.
        
        Nota: Tarefas bloqueadas (mutex ou IO) não são consideradas para escalonamento.
        """
        # Se não há tarefa rodando ou a atual terminou, escolher nova.
        if not self.running_task or self.running_task.remaining_time <= 0:
            # Filtra tarefas não bloqueadas (nem mutex nem IO)
            available = [t for t in self.ready_queue if not t.blocked and not t.io_blocked]
            self.running_task = self.scheduler(available)
            if self.running_task:
                self.running_task.executed_count = 0
                # Remove da fila pois agora está em execução
                if self.running_task in self.ready_queue:
                    self.ready_queue.remove(self.running_task)
            return

        # Preempção para SRTF e PRIOP (têm should_preempt)
        if hasattr(self.scheduler, 'should_preempt'):
            available = [t for t in self.ready_queue if not t.blocked and not t.io_blocked]
            candidate = self.scheduler(available)
            if candidate and candidate is not self.running_task:
                if self.scheduler.should_preempt(self.running_task, candidate):
                    # Preempção confirmada: volta tarefa atual à fila
                    if self.running_task not in self.ready_queue and not self.running_task.completed:
                        self.ready_queue.append(self.running_task)
                    self.running_task.executed_count = 0
                    # Remove candidata da fila e promove
                    if candidate in self.ready_queue:
                        self.ready_queue.remove(candidate)
                    self.running_task = candidate



    def _tick(self):
        """Avança um tick de tempo:
        - Processa eventos de IO (bloqueio e desbloqueio)
        - Processa eventos de mutex (lock/unlock)
        - Atualiza tempos da tarefa corrente
        - Registra espera das demais
        - Aplica lógica de término ou de expiração de quantum (SRTF/PRIOP)
        - Adiciona ID (ou None) à timeline para visualização
        """
        # Processa IO para tarefas bloqueadas que ainda estão na ready_queue
        # Também incrementa elapsed_time para contabilizar tempo de bloqueio
        for task in list(self.ready_queue):
            if task.io_blocked or task.blocked:
                task.elapsed_time += 1
                if task.io_blocked:
                    self._process_io_events(task)
        
        if self.running_task:
            # Incrementa tempo de execução relativo ANTES de processar eventos
            self.running_task.elapsed_time += 1
            
            # Processa eventos de IO para a tarefa em execução
            self._process_io_events(self.running_task)
            
            # Se tarefa ficou bloqueada por IO, não executa CPU este tick
            if self.running_task.io_blocked:
                self.timeline.append(None)  # CPU ociosa por bloqueio de IO
                # Readiciona tarefa à fila de prontos
                if self.running_task not in self.ready_queue and not self.running_task.completed:
                    self.ready_queue.append(self.running_task)
                # Tarefa bloqueada também registra espera
                for task in self.ready_queue:
                    if not task.completed:
                        self.wait_map.setdefault(task.id, []).append(self.time)
                self.running_task = None
                return
            
            # Processa eventos de mutex para a tarefa em execução
            self._process_mutex_events(self.running_task)
            
            # Se tarefa ficou bloqueada por mutex, não executa CPU este tick
            if self.running_task.blocked:
                self.timeline.append(None)  # CPU ociosa por bloqueio de mutex
                # Readiciona tarefa à fila de prontos
                if self.running_task not in self.ready_queue and not self.running_task.completed:
                    self.ready_queue.append(self.running_task)
                # Tarefa bloqueada também registra espera
                for task in self.ready_queue:
                    if not task.completed:
                        self.wait_map.setdefault(task.id, []).append(self.time)
                self.running_task = None
                return
            
            self.running_task.remaining_time -= 1
            self.running_task.executed_ticks += 1
            self.running_task.executed_count += 1
            
            self.timeline.append(self.running_task.id)
            # Marca espera das demais tarefas na fila
            for task in self.ready_queue:
                if task is not self.running_task and not task.completed:
                    self.wait_map.setdefault(task.id, []).append(self.time)

            if self.running_task.remaining_time <= 0:
                self.running_task.completed = True
               
                print(f"Tarefa {self.running_task.id} concluída em t={self.time}")
                self.finish_map[self.running_task.id] = self.time + 1  # fim exclusivo
                self.running_task = None

            elif self.running_task.executed_count >= self.quantum:
              
                print(f"Tarefa {self.running_task.id} preemptada por quantum em t={self.time}")
                # Rotaciona tarefa e deixa a "CPU" livre
                self.ready_queue.append(self.running_task)
                self.running_task.executed_count = 0
                self.running_task = None
        else:
            # CPU ociosa
            self.timeline.append(None)
            for task in self.ready_queue:
                if not task.completed:
                    self.wait_map.setdefault(task.id, []).append(self.time)

    def _process_io_events(self, task):
        """Processa eventos de IO para uma tarefa em execução.
        
        Tempo relativo (elapsed_time) determina qual evento disparar.
        Quando IO é iniciado:
        - Marca tarefa como io_blocked=True
        - Inicia contador io_remaining com duração da operação
        
        Cada tick enquanto io_bloqueada:
        - Decrementa io_remaining
        - Quando io_remaining==0, desbloqueia tarefa
        """
        # Se tarefa já está bloqueada por IO, decrementa contador
        if task.io_blocked:
            task.io_remaining -= 1
            if task.io_remaining <= 0:
                task.io_blocked = False
                task.io_remaining = 0
                print(f"Tarefa {task.id} desbloqueada de IO em t={self.time}")
                # Readiciona à fila se não estiver lá
                if task not in self.ready_queue and not task.completed:
                    self.ready_queue.append(task)
            return
        
        # Procura por IO events que começam neste tempo relativo
        pending_io = task.get_pending_io(task.elapsed_time)
        if pending_io:
            # Inicia novo IO
            task.io_blocked = True
            task.io_remaining = pending_io["duration"]
            print(f"Tarefa {task.id} iniciando IO com duração {pending_io['duration']} em t={self.time}")

    def _process_mutex_events(self, task):
        """Processa eventos de lock/unlock para uma tarefa em execução.
        
        Tempo relativo (elapsed_time) determina qual evento disparar.
        Lock: tenta adquirir; se falhar, marca tarefa como bloqueada.
        Unlock: libera o mutex e promove próxima tarefa em espera.
        """
        events = task.get_pending_events(task.elapsed_time)
        
        for event in events:
            event_type = event.get("type")
            mutex_id = event.get("mutex_id")
            
            if event_type == "lock":
                mutex = self.mutexes.get(mutex_id)
                if mutex:
                    if not mutex.try_lock(task.id):
                        # Lock falhou: tarefa fica bloqueada
                        task.blocked = True
                        task.blocking_mutex_id = mutex_id
                        print(f"Tarefa {task.id} bloqueada aguardando M{mutex_id}")
            
            elif event_type == "unlock":
                mutex = self.mutexes.get(mutex_id)
                if mutex:
                    next_task_id = mutex.unlock(task.id)
                    print(f"Tarefa {task.id} liberou M{mutex_id}")
                    
                    # Se há tarefa esperando, desbloqueia
                    if next_task_id:
                        for t in self.tasks:
                            if t.id == next_task_id:
                                t.blocked = False
                                t.blocking_mutex_id = None
                                # Readiciona à fila se não estiver lá
                                if t not in self.ready_queue and not t.completed:
                                    self.ready_queue.append(t)
                                print(f"Tarefa {next_task_id} desbloqueada em M{mutex_id}")


    def all_tasks_completed(self):
        """Retorna True se todas as tarefas marcaram `completed=True`.
        Facilita leitura do loop principal.
        """
        return all(task.completed for task in self.tasks)
