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
        self.alpha = config.get("alpha", 0)
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
        self.suspended_map = {}  # Rastreia ticks em que tarefas estão suspensas (IO/mutex)
        self.arrivals_map = {}
        self.finish_map = {}
        self.debug_mode = False
        
        # Flag para envelhecimento: marca se houve nova tarefa ou preempção
        self.queue_changed = False
        
        # Flag para rescalonamento: marca se precisa recalcular tarefa após suspensão
        self.needs_reschedule = False

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
        Mostra apenas os primeiros 40 ticks para evitar saída muito grande.
        """
        print("\nGráfico de Gantt (terminal):\n")
        
        # Limita a exibição aos primeiros ticks ativos (últimas tarefas completadas)
        display_limit = min(len(timeline), 40)
        timeline_display = timeline[:display_limit]
        
        header = ""
        values = ""
        for tick, task_id in enumerate(timeline_display):
            label = (task_id[:3] if isinstance(task_id, str) else '---')
            header += f"{label:^4}"
            values += f"{tick:^4}"
        print(header)
        print(values)
        
        if len(timeline) > display_limit:
            print(f"\n... ({len(timeline) - display_limit} ticks omitidos)")
        
        if wait_map:
            print("\nTempos de espera (ticks):")
            for tid, ticks in wait_map.items():
                # Mostra só o total, não a lista completa
                print(f"{tid}: {len(ticks)} ticks")

    def run(self):
        """Executa a simulação completa até todas as tarefas finalizarem
        ou até alcançar `tick_limit` de segurança para evitar loops.
        """
        print(f"Iniciando simulação com algoritmo: {self.algorithm_name}")
        
          
        while not self.all_tasks_completed() and self.time < self.tick_limit:
            self._check_arrivals()
            self._check_suspension_exits()  # Processa desbloqueios ANTES de rescalonar
            if self.queue_changed or not self.running_task or self.needs_reschedule:
                self._schedule()
                
            self._tick()
               # Processa desbloqueios ANTES de rescalonar
            # Envelhecimento: APÓS execução do tick, apenas se houve mudança na fila
            # (nova tarefa chegou ou preempção ocorreu)
            # Obs: tarefas bloqueadas (IO ou mutex) NÃO recebem envelhecimento
            if (self.needs_reschedule  or self.queue_changed) and self.algorithm_name.upper() == "PRIOPENV" and self.alpha > 0:
                for task in self.ready_queue:
                    if task is not self.running_task and not task.completed and not task.blocked and not task.io_blocked:
                        task.dynamic_priority += self.alpha
            
            # Reseta flag APÓS processar tudo (para não perder mudanças feitas em _tick)
            self.queue_changed = False
            self.needs_reschedule = False 
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
        self.suspended_map = {}
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
            # Reinicia prioridades dinâmicas
            if hasattr(task, 'static_priority'):
                task.dynamic_priority = task.static_priority
        
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
                "dynamic_priority": getattr(t, 'dynamic_priority', t.priority),  # Para PRIOPENV
                "completed": t.completed,
                "executed_ticks": t.executed_ticks,
                "elapsed_time": t.elapsed_time,
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

        self.queue_changed = False  # Reseta flag a cada iteração
        self._check_arrivals()
        self._check_suspension_exits()  # Processa desbloqueios ANTES de rescalonar
        if self.queue_changed or not self.running_task or self.needs_reschedule:
            self._schedule()
            
        self._tick()
            
            # Envelhecimento: APÓS execução do tick, apenas se houve mudança na fila
            # (nova tarefa chegou ou preempção ocorreu)
            # Obs: tarefas bloqueadas (IO ou mutex) NÃO recebem envelhecimento
        if (self.needs_reschedule or self.queue_changed) and self.algorithm_name.upper() == "PRIOPENV" and self.alpha > 0:
                for task in self.ready_queue:
                    if task is not self.running_task and not task.completed and not task.blocked and not task.io_blocked:
                        task.dynamic_priority += self.alpha
        
        # Reseta flag APÓS processar tudo
        self.queue_changed = False
        self.needs_reschedule = False
            
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
        
        Define flag `queue_changed` se nova tarefa chegou.
        """
        for task in self.tasks:
            if task.arrival == self.time and task not in self.ready_queue and not task.completed:
                self.ready_queue.append(task)
                # registra chegada
                self.arrivals_map.setdefault(task.id, self.time)
                # Para PRIOPEnv, pdnova <- penova
                if hasattr(task, 'static_priority'):
                    task.dynamic_priority = task.static_priority
                # Marca que fila mudou (nova tarefa chegou)
                self.queue_changed = True
                task.dynamic_priority = task.static_priority

    def _check_suspension_exits(self):
        """Processa desbloqueios de IO e mutex ANTES de rescalonar.
        
        Decrementa contadores de suspensão para tarefas bloqueadas,
        incrementa elapsed_time, processa eventos e marca needs_reschedule.
        TUDO acontece FORA do _tick().
        """
        for task in list(self.ready_queue):
            # Se está bloqueada por IO
            if task.io_blocked:
                # Incrementa elapsed_time para rastrear tempo desde chegada
                task.elapsed_time += 1
                task.io_remaining -= 1
                if task.io_remaining > 0:
                    # Ainda está em IO, registra como suspenso
                    self.suspended_map.setdefault(task.id, []).append(self.time)
                if task.io_remaining <= 0:
                    task.io_blocked = False
                    task.io_remaining = 0
                    self.needs_reschedule = True
                    print(f"[PRE-TICK] Tarefa {task.id} desbloqueada de IO em t={self.time}")
            
            # Se está bloqueada por mutex
            elif task.blocked:
                # Tarefas bloqueadas TAMBÉM incrementam elapsed_time para rastrear tempo esperando
                task.elapsed_time += 1
                self.suspended_map.setdefault(task.id, []).append(self.time)



    def _schedule(self):
        """Realiza escalonamento: escolhe próxima tarefa ou verifica preempção.
        SRTF/PRIOP: preemptivos, verificam a cada tick se deve trocar.
        
        Nota: Tarefas bloqueadas (mutex ou IO) não são consideradas para escalonamento.
        """
        # Se não há tarefa rodando ou a atual terminou, escolher nova.
        if not self.running_task or self.running_task.remaining_time <= 0:
            # Filtra tarefas não bloqueadas (nem mutex nem IO)
            available = [t for t in self.ready_queue if not t.blocked and not t.io_blocked]
            # PRIOPEnv aceita (ready_queue, current)
            if self.algorithm_name.upper() == "PRIOPENV":
                self.running_task = self.scheduler(available, current=self.running_task)
            else:
                self.running_task = self.scheduler(available)
            if self.running_task:
                self.running_task.executed_count = 0
                # CORREÇÃO: Só reseta elapsed_time se for a PRIMEIRA execução da tarefa
                if self.running_task.elapsed_time == 0:
                    pass  # elapsed_time já está em 0 na primeira vez
                # Se elapsed_time != 0, mantém o valor (tarefa voltando do IO/mutex)
                # Remove da fila pois agora está em execução
                if self.running_task in self.ready_queue:
                    self.ready_queue.remove(self.running_task)
                # Rejuvenação: reseta prioridade dinâmica ao começar execução
                if self.algorithm_name.upper() == "PRIOPENV":
                    self.running_task.dynamic_priority = self.running_task.static_priority
            self.queue_changed = True        
            return

        # Preempção para SRTF e PRIOP (têm should_preempt)
        if hasattr(self.scheduler, 'should_preempt'):
            available = [t for t in self.ready_queue if not t.blocked and not t.io_blocked]
            # PRIOPEnv precisa considerar tarefa atual para desempate
            if self.algorithm_name.upper() == "PRIOPENV":
                candidate = self.scheduler(available, current=self.running_task)
            else:
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
                    candidate.executed_count = 0    
                    self.running_task = candidate
                    # Rejuvenação: reseta prioridade dinâmica ao começar execução
                    if self.algorithm_name.upper() == "PRIOPENV":
                        self.running_task.dynamic_priority = self.running_task.static_priority
                    



    def _tick(self):
        """Avança um tick de tempo:
        - Processa eventos de IO (bloqueio e desbloqueio)
        - Processa eventos de mutex (lock/unlock)
        - Atualiza tempos da tarefa corrente
        - Registra espera das demais
        - Aplica lógica de término ou de expiração de quantum (SRTF/PRIOP)
        - Adiciona ID (ou None) à timeline para visualização
        """
        if self.running_task:
            # CRITÉRIO 3.6: Se tarefa está iniciando execução (elapsed_time==0),
            # processa eventos de t=0 ANTES de incrementar
            if self.running_task.elapsed_time == 0:
                # Processa eventos de IO para t=0
                self._process_io_events(self.running_task)
                
                # Se tarefa ficou bloqueada por IO em t=0, não executa CPU este tick
                if self.running_task.io_blocked:
                    self.timeline.append(None)
                    if self.running_task not in self.ready_queue and not self.running_task.completed:
                        self.ready_queue.append(self.running_task)
                    for task in self.ready_queue:
                        if not task.completed:
                            self.wait_map.setdefault(task.id, []).append(self.time)
                    self.running_task = None
                    return
                
                # Processa eventos de mutex para t=0
                self._process_mutex_events(self.running_task)
                
                # Se tarefa ficou bloqueada por mutex em t=0, não executa CPU este tick
                if self.running_task.blocked:
                    self.timeline.append(None)
                    if self.running_task not in self.ready_queue and not self.running_task.completed:
                        self.ready_queue.append(self.running_task)
                    for task in self.ready_queue:
                        if not task.completed:
                            self.wait_map.setdefault(task.id, []).append(self.time)
                    self.running_task = None
                    return
                
                # AGORA incrementa elapsed_time para 1 e executa CPU
                self.running_task.elapsed_time += 1
                self.running_task.remaining_time -= 1
                self.running_task.executed_ticks += 1
                self.running_task.executed_count += 1
            else:
                # Para execuções subsequentes, processa eventos ANTES de incrementar
                # (eventos são relativos ao tempo atual de execução)
                # IMPORTANTE: Processa MUTEX PRIMEIRO para liberar recursos antes de IO
                self._process_mutex_events(self.running_task)
                
                # Se tarefa ficou bloqueada por mutex, não executa CPU este tick
                if self.running_task.blocked:
                    # Readiciona tarefa à fila de prontos
                    if self.running_task not in self.ready_queue and not self.running_task.completed:
                        self.ready_queue.append(self.running_task)
                    # Tarefa bloqueada também registra espera
                    for task in self.ready_queue:
                        if not task.completed:
                            self.wait_map.setdefault(task.id, []).append(self.time)
                    self.running_task = None
                    # Reschedule: escolher próxima tarefa disponível
                    self._schedule()
                    if not self.running_task:
                        # Nenhuma tarefa - CPU ociosa
                        self.timeline.append(None)
                    # Se conseguiu, deixa continuar para executar
                    return
                
                # Depois processa IO
                self._process_io_events(self.running_task)
                
                # Se tarefa ficou bloqueada por IO, não executa CPU este tick
                if self.running_task.io_blocked:
                    # Readiciona tarefa à fila de prontos
                    if self.running_task not in self.ready_queue and not self.running_task.completed:
                        self.ready_queue.append(self.running_task)
                    # Tarefa bloqueada também registra espera
                    for task in self.ready_queue:
                        if not task.completed:
                            self.wait_map.setdefault(task.id, []).append(self.time)
                    self.running_task = None
                    # Reschedule: escolher próxima tarefa disponível
                    self._schedule()
                    if not self.running_task:
                        # Nenhuma tarefa - CPU ociosa
                        self.timeline.append(None)
                    else:
                        # Nova tarefa foi alocada, processa como se fosse t=0
                        self._process_io_events(self.running_task)
                        if self.running_task.io_blocked:
                            self.timeline.append(None)
                            if self.running_task not in self.ready_queue and not self.running_task.completed:
                                self.ready_queue.append(self.running_task)
                            for task in self.ready_queue:
                                if not task.completed:
                                    self.wait_map.setdefault(task.id, []).append(self.time)
                            self.running_task = None
                            return
                        
                        self._process_mutex_events(self.running_task)
                        if self.running_task.blocked:
                            self.timeline.append(None)
                            if self.running_task not in self.ready_queue and not self.running_task.completed:
                                self.ready_queue.append(self.running_task)
                            for task in self.ready_queue:
                                if not task.completed:
                                    self.wait_map.setdefault(task.id, []).append(self.time)
                            self.running_task = None
                            return
                        
                        # Executa CPU
                        self.running_task.remaining_time -= 1
                        self.running_task.executed_ticks += 1
                        self.running_task.executed_count += 1
                        
                        # Incrementa elapsed_time APÓS processar t=0 e executar
                        self.running_task.elapsed_time += 1
                        
                        # Adiciona à timeline
                        task_id = self.running_task.id
                        self.timeline.append(task_id)
                        for task in self.ready_queue:
                            if task is not self.running_task and not task.completed:
                                self.wait_map.setdefault(task.id, []).append(self.time)
                    # Se conseguiu, deixa continuar para executar
                    return
                
                # Executa a tarefa (decrementa remaining_time)
                self.running_task.remaining_time -= 1
                self.running_task.executed_ticks += 1
                self.running_task.executed_count += 1
                
                # Incrementa elapsed_time APÓS processar eventos e executar CPU
                self.running_task.elapsed_time += 1
            
            # Adiciona ID à timeline, com marcação se foi sorteio
            task_id = self.running_task.id
            if hasattr(self.running_task, '_tie_break_random') and self.running_task._tie_break_random:
                task_id = task_id + "L"  # "L" indica escolha por sorteio (Lottery)
                self.running_task.chosen_by_lottery = True
            
            self.timeline.append(task_id)
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
        
        Critério 3.3: Tempo relativo (elapsed_time) ao início determina qual evento disparar.
        Inicia novo IO bloqueando a tarefa.
        
        Nota: Desbloqueio é processado em _check_suspension_exits() antes de rescalonar.
        """
        # Procura por IO events que começam neste tempo relativo
        # CRITÉRIO 3.3: Tempo relativo ao início da tarefa
        pending_io = task.get_pending_io(task.elapsed_time)
        if pending_io:
            # Inicia novo IO
            task.io_blocked = True
            task.io_remaining = pending_io["duration"]
            # Registra suspensão
            self.suspended_map.setdefault(task.id, []).append(self.time)
            # CRITÉRIO 3.2: Formato IO:xx-yy onde yy é duração
            print(f"[IO START] Tarefa {task.id} iniciando E/S (duração={pending_io['duration']} ticks) em t={self.time}")



    def _process_mutex_events(self, task):
        """Processa eventos de lock/unlock para uma tarefa em execução ou bloqueada.
        
        Tempo relativo (elapsed_time) determina qual evento disparar.
        Lock: tenta adquirir; se falhar, marca tarefa como bloqueada.
        Unlock: libera o mutex e promove próxima tarefa bloqueada.
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
                        # Registra suspensão
                        self.suspended_map.setdefault(task.id, []).append(self.time)
                        print(f"Tarefa {task.id} bloqueada aguardando M{mutex_id}")
            
            elif event_type == "unlock":
                mutex = self.mutexes.get(mutex_id)
                if mutex:
                    next_task_id = mutex.unlock(task.id)
                    print(f"Tarefa {task.id} liberou M{mutex_id}")
                    # Se há tarefa esperando, desbloqueia AGORA
                    if next_task_id:
                        # Encontra a tarefa promovida e desbloqueia
                        for t in self.tasks:
                            if t.id == next_task_id and t.blocked and t.blocking_mutex_id == mutex_id:
                                t.blocked = False
                                t.blocking_mutex_id = None
                                self.needs_reschedule = True
                                print(f"[UNLOCK] Tarefa {next_task_id} desbloqueada - adquiriu M{mutex_id}")
                                break


    def all_tasks_completed(self):
        """Retorna True se todas as tarefas marcaram `completed=True`.
        Facilita leitura do loop principal.
        """
        return all(task.completed for task in self.tasks)
