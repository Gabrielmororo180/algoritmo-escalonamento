def fifo_scheduler(ready_queue):
    return ready_queue[0] if ready_queue else None

def srtf_scheduler(ready_queue):
    return min(ready_queue, key=lambda t: t.remaining_time, default=None)

def priority_scheduler(ready_queue):
    return max(ready_queue, key=lambda t: t.priority, default=None)

def get_scheduler(algorithm):
    if algorithm.upper() == "FIFO":
        return fifo_scheduler
    elif algorithm.upper() == "SRTF":
        return srtf_scheduler
    elif algorithm.upper() == "PRIORIDADE":
        return priority_scheduler
    else:
        raise ValueError(f"Algoritmo desconhecido: {algorithm}")
