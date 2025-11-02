"""scheduler.py
=================
Responsável por definir funções de seleção de tarefa (algoritmos de escalonamento)
e metadados que orientam o simulador sobre comportamento preemptivo, uso de quantum
e critério de preempção.

Design:
- Cada algoritmo é uma função que recebe a `ready_queue` e retorna a tarefa escolhida.
- Flags (atributos) são anexadas às funções para evitar condicional espalhada no simulador.
    * `should_preempt(current, candidate)`: função de decisão isolada.
"""

def fifo_scheduler(ready_queue):
    """FIFO: Retorna a primeira tarefa da fila de prontos.
    
    Não preemptivo: a tarefa executa até o final sem interrupção.
    """
    return ready_queue[0] if ready_queue else None

def srtf_scheduler(ready_queue):
    """SRTF: Shortest Remaining Time First (versão preemptiva do SJF).
    
    Seleciona a tarefa com menor tempo restante de execução.
    Usa quantum: após executar `quantum` ticks, a tarefa retorna à fila.
    """
    return min(ready_queue, key=lambda t: t.remaining_time, default=None)

srtf_scheduler.should_preempt = lambda current, candidate: candidate and current and candidate.remaining_time < current.remaining_time

def priority_preemptive_scheduler(ready_queue):
    """Prioridade Preemptiva: escolhe a tarefa de maior prioridade numérica.
    
    Em caso de igualdade, mantém a atual. Usa quantum: após executar `quantum` ticks,
    a tarefa retorna à fila.
    """
    return max(ready_queue, key=lambda t: t.priority, default=None)

priority_preemptive_scheduler.should_preempt = lambda current, candidate: candidate and current and candidate.priority > current.priority

def get_scheduler(algorithm):
    """Mapeia string de algoritmo para função correspondente.

    Permite fácil extensão: adicionar nova função e inserir condição aqui.
    Levanta erro claro para facilitar feedback ao usuário/CLI.
    """
    if algorithm.upper() == "FIFO":
        return fifo_scheduler
    elif algorithm.upper() == "SRTF":
        return srtf_scheduler
    elif algorithm.upper() == "PRIOP":
        return priority_preemptive_scheduler
    else:
        raise ValueError(f"Algoritmo desconhecido: {algorithm}")
