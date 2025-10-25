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

    def run(self):
        print(f"Iniciando simulação com algoritmo: {self.scheduler.__name__}")
        while not self.all_tasks_completed() and self.time < self.tick_limit:
            self._check_arrivals()  
            self._schedule()        
            self._tick()
            
            self.time += 1
        print("Simulação encerrada.")
        render_gantt_terminal(self.timeline)
        render_gantt_image(self.timeline)

    def run_debug(self):
     
        self.time = 0
        self.timeline = []
        self.ready_queue = []
        self.running_task = None
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

    def _schedule(self):
        if not self.running_task or self.running_task.remaining_time <= 0:
            self.running_task = self.scheduler(self.ready_queue)
            if self.running_task:
                self.running_task.executed_quantum = 0

    def apply_aging(self):
        for task in self.ready_queue:
            if task != self.running_task and not task.completed:
                task.priority += 1 


    def _tick(self):
        if self.running_task:
            self.running_task.remaining_time -= 1
            self.running_task.executed_ticks += 1
            self.running_task.executed_quantum += 1
            self.timeline.append(self.running_task.id)

            if self.running_task.remaining_time <= 0:
                self.running_task.completed = True
                self.ready_queue.remove(self.running_task)
                print(f"Tarefa {self.running_task.id} concluída em t={self.time}")
                self.running_task = None

            elif self.running_task.executed_quantum >= self.quantum:
                # Quantum expirou: preempção
                print(f"Tarefa {self.running_task.id} preemptada em t={self.time}")
                self.ready_queue.append(self.running_task)
                self.ready_queue.remove(self.running_task)
                self.running_task.executed_quantum = 0
                self.running_task = None
        else:
            self.timeline.append("IDLE")


    def all_tasks_completed(self):
        return all(task.completed for task in self.tasks)
