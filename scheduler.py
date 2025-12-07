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
    """Prioridade Preemptiva: escolhe a tarefa de maior prioridade estática (sem envelhecimento)."""
    return max(ready_queue, key=lambda t: getattr(t, 'priority', getattr(t, 'static_priority', 0)), default=None)

priority_preemptive_scheduler.should_preempt = lambda current, candidate: candidate and current and (
    getattr(candidate, 'priority', getattr(candidate, 'static_priority', 0)) > getattr(current, 'priority', getattr(current, 'static_priority', 0))
)

def priority_preemptive_aging_scheduler(ready_queue, current=None):
    """Prioridade preemptiva com envelhecimento (PRIOPEnv).

    Seleciona tarefa com maior prioridade dinâmica (pd). Critérios de desempate:
      1) maior prioridade estática (pe)
      2) preferir tarefa que já está executando (evita troca desnecessária)
      3) menor instante de ingresso (chegou antes)
      4) menor duração total
      5) sorteio (último recurso)
    """
    if not ready_queue:
        return None

    # Ordenação multi-critério; para critério 2, se 'current' presente, favorece
    import random
    # Preparar chave de ordenação; como max, usamos tupla
    def sort_key(t):
        pd = getattr(t, 'dynamic_priority', getattr(t, 'priority', 0))
        pe = getattr(t, 'static_priority', getattr(t, 'priority', 0))
        is_current = 1 if (current is not None and t is current) else 0
        arrival = -getattr(t, 'arrival', 0)  # negativo para max favorecer menor arrival
        duration = -getattr(t, 'duration', 0)  # negativo para max favorecer menor duração
        return (pd, pe, is_current, arrival, duration)  # ORDEM: pd > pe > is_current > arrival > duration

    # Em caso de empate completo, sorteia entre empatados e indica via atributo
    best = max(ready_queue, key=sort_key, default=None)
    # Verifica se há empate com outras tarefas pelo sort_key
    top_key = sort_key(best)
    tied = [t for t in ready_queue if sort_key(t) == top_key]
    if len(tied) > 1:
        # sorteio
        best = random.choice(tied)
        # marca atributo para o simulador poder indicar no gantt se desejar
        setattr(best, '_tie_break_random', True)
    else:
        # limpa flag se existir
        if hasattr(best, '_tie_break_random'):
            delattr(best, '_tie_break_random')
    return best
# should_preempt para PRIOPEnv: preempção se candidato tem pd maior, aplicando desempates
def _priopenv_should_preempt(current, candidate):
    if not current or not candidate:
        return False
    c_pd = getattr(candidate, 'dynamic_priority', getattr(candidate, 'priority', 0))
    cur_pd = getattr(current, 'dynamic_priority', getattr(current, 'priority', 0))
    if c_pd != cur_pd:
        return c_pd > cur_pd
    # desempates
    c_pe = getattr(candidate, 'static_priority', getattr(candidate, 'priority', 0))
    cur_pe = getattr(current, 'static_priority', getattr(current, 'priority', 0))
    if c_pe != cur_pe:
        return c_pe > cur_pe
    # preferir manter a atual
    return False

priority_preemptive_aging_scheduler.should_preempt = _priopenv_should_preempt

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
    elif algorithm.upper() == "PRIOPENV":
        # Para PRIOPEnv, retornamos uma função wrapper que aceita (ready_queue, current)
        # O simulador chamará passando a tarefa atual quando disponível.
        return priority_preemptive_aging_scheduler
    else:
        raise ValueError(f"Algoritmo desconhecido: {algorithm}")
