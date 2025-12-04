#!/usr/bin/env python3
"""
test_mutex.py
=============
Script para testar a implementação de mutex.

Carrega configuração com eventos de mutex e executa simulação,
validando bloqueio e desbloqueio corretos.
"""

from config_loader import load_config
from simulator import Simulator

def test_mutex_simulation():
    """Testa simulação com mutexes usando sample_config.txt"""
    print("=" * 60)
    print("TESTANDO IMPLEMENTAÇÃO DE MUTEX")
    print("=" * 60)
    
    # Carrega configuração
    config = load_config("sample_config.txt")
    print(f"\nConfigração Carregada:")
    print(f"  Algoritmo: {config['algorithm']}")
    print(f"  Quantum: {config['quantum']}")
    print(f"  Tarefas: {len(config['tasks'])}")
    
    for task in config['tasks']:
        print(f"    {task['id_']}: chegada={task['arrival']}, duração={task['duration']}, eventos={task['events']}")
    
    # Cria e executa simulador
    simulator = Simulator(config)
    print(f"\nMutexes inicializados: {list(simulator.mutexes.keys())}")
    
    print("\n" + "=" * 60)
    print("EXECUTANDO SIMULAÇÃO")
    print("=" * 60)
    simulator.run()
    
    print("\n" + "=" * 60)
    print("RESULTADO FINAL")
    print("=" * 60)
    
    snapshot = simulator.snapshot()
    
    print(f"\nTempo Final: {snapshot['time']}")
    print("\nEstado das Tarefas:")
    for task in snapshot['tasks']:
        status = "CONCLUÍDA" if task['completed'] else "NÃO CONCLUÍDA"
        blocked = f" (BLOQUEADA EM M{task['blocking_mutex_id']})" if task['blocked'] else ""
        print(f"  {task['id']}: {status}{blocked}")
        print(f"    - Duração total: {task['duration']}, Tempo de execução: {task['executed_ticks']}")
        print(f"    - Tempo de espera: {task['waited_ticks']} ticks")
    
    print("\nEstado dos Mutexes:")
    for mutex in snapshot['mutexes']:
        owner_str = f"Proprietário: {mutex['owner']}" if mutex['owner'] else "Proprietário: Nenhum"
        waiting_str = f"Aguardando: {', '.join(mutex['waiting'])}" if mutex['waiting'] else "Aguardando: Nenhum"
        status = "BLOQUEADO" if mutex['locked'] else "LIVRE"
        print(f"  M{mutex['id']}: {status}")
        print(f"    - {owner_str}")
        print(f"    - {waiting_str}")
    
    print("\nTimeline de execução (primeiros 40 ticks):")
    timeline_str = ' '.join([str(x) if x is not None else '-' for x in snapshot['timeline'][:40]])
    print(f"  {timeline_str}")
    
    print("\n" + "=" * 60)
    print("TESTE CONCLUÍDO")
    print("=" * 60)

if __name__ == "__main__":
    test_mutex_simulation()
