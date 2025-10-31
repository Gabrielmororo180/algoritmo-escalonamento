"""scheduler.py
=================
Responsável por definir funções de seleção de tarefa (algoritmos de escalonamento)
e metadados que orientam o simulador sobre comportamento preemptivo, uso de quantum
e critério de preempção.

Design:
- Cada algoritmo é uma função que recebe a `ready_queue` e retorna a tarefa escolhida.
- Flags (atributos) são anexadas às funções para evitar condicional espalhada no simulador.
    * `non_preemptive`: não realizar troca antes do término da tarefa.
    * `preemptive`: algoritmo permite interrupção quando surge uma tarefa mais apropriada.
    * `ignore_quantum`: quantum do sistema não é utilizado para forçar troca.
    * `should_preempt(current, candidate)`: função de decisão isolada.

Justificativa:
Usar atributos nas funções ao invés de uma classe permite
que o simulador permaneça genérico, perguntando somente pelas capacidades do
algoritmo sem criar estruturas de herança. É simples extender: adicionar nova
função e setar flags.
"""

def fifo_scheduler(ready_queue):
    """Retorna a primeira tarefa da fila de prontos.

    Marcado como não preemptivo: uma vez escolhida a tarefa ela deve seguir
    executando até terminar (ignorando quantum) antes de trocar para outra.
    """
    return ready_queue[0] if ready_queue else None

# Flag para o simulador identificar comportamento não preemptivo
fifo_scheduler.non_preemptive = True

def srtf_scheduler(ready_queue):
    # Shortest Remaining Time First (versão preemptiva do SJF).
    # Seleciona a tarefa com menor tempo restante de execução.
    return min(ready_queue, key=lambda t: t.remaining_time, default=None)
srtf_scheduler.preemptive = True
srtf_scheduler.ignore_quantum = True  # SRTF decide por menor tempo restante, não por quantum
srtf_scheduler.should_preempt = lambda current, candidate: candidate and current and candidate.remaining_time < current.remaining_time

def priority_preemptive_scheduler(ready_queue):
    # Prioridade preemptiva: escolhe a tarefa de maior prioridade numérica.
    # Em caso de igualdade, mantém a atual (decisão feita em should_preempt < apenas >).
    return max(ready_queue, key=lambda t: t.priority, default=None)
priority_preemptive_scheduler.preemptive = True
priority_preemptive_scheduler.ignore_quantum = True
priority_preemptive_scheduler.priority_preemptive = True
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
