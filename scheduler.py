def fifo_scheduler(ready_queue):
    """Retorna a primeira tarefa da fila de prontos.

    Marcado como não preemptivo: uma vez escolhida a tarefa ela deve seguir
    executando até terminar (ignorando quantum) antes de trocar para outra.
    """
    return ready_queue[0] if ready_queue else None

# Flag para o simulador identificar comportamento não preemptivo
fifo_scheduler.non_preemptive = True

def srtf_scheduler(ready_queue):
    return min(ready_queue, key=lambda t: t.remaining_time, default=None)
srtf_scheduler.preemptive = True
srtf_scheduler.ignore_quantum = True  # SRTF decide por menor tempo restante, não por quantum
srtf_scheduler.should_preempt = lambda current, candidate: candidate and current and candidate.remaining_time < current.remaining_time

def priority_preemptive_scheduler(ready_queue):
    return max(ready_queue, key=lambda t: t.priority, default=None)
priority_preemptive_scheduler.preemptive = True
priority_preemptive_scheduler.ignore_quantum = True
priority_preemptive_scheduler.priority_preemptive = True
priority_preemptive_scheduler.should_preempt = lambda current, candidate: candidate and current and candidate.priority > current.priority

def get_scheduler(algorithm):
    if algorithm.upper() == "FIFO":
        return fifo_scheduler
    elif algorithm.upper() == "SRTF":
        return srtf_scheduler
    elif algorithm.upper() == "PRIOP":
        return priority_preemptive_scheduler
    else:
        raise ValueError(f"Algoritmo desconhecido: {algorithm}")
