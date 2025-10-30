from tcb import TaskControlBlock
from scheduler import get_scheduler
from gantt_renderer import render_gantt_terminal, render_gantt_image

class Simulator:
    def __init__(self, config):
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

    def run(self):
        print(f"Iniciando simulação com algoritmo: {self.scheduler.__name__}")
        while not self.all_tasks_completed() and self.time < self.tick_limit:
            self._check_arrivals()  
            self._schedule()        
            self._tick()
            
            self.time += 1
        print("Simulação encerrada.")
        render_gantt_terminal(self.timeline)
        # Passa mapas completos para renderer (espera, chegada, fim)
        render_gantt_image(self.timeline, arrivals=self.arrivals_map, finishes=self.finish_map, wait_map=self.wait_map)

    def run_debug(self):
     
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

    def step(self):
        if self.all_tasks_completed() or self.time >= self.tick_limit:
            return False 

        self._check_arrivals()  
        self._schedule()        
        self._tick()


        print(f"[Tick {self.time}] Executando: {self.running_task.id if self.running_task else 'IDLE'}")
        self.time += 1  
        render_gantt_terminal(self.timeline)
        render_gantt_image(self.timeline)         
        return True              


    def _check_arrivals(self):
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
        for task in self.ready_queue:
            if task != self.running_task and not task.completed:
                task.priority += 1 


    def _tick(self):
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
        return all(task.completed for task in self.tasks)
