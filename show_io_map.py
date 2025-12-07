"""
Script para visualizar o mapa de IO events das tarefas
"""
from config_loader import load_config

cfg = load_config('sample_config.txt')

print("=" * 60)
print("MAPA DE IO EVENTS")
print("=" * 60)

for task in cfg['tasks']:
    task_id = task['id_']
    print(f"\n{task_id}:")
    print(f"  Duração total: {task['duration']} ticks")
    print(f"  Prioridade estática: {task['priority']}")
    
    if task['io_events']:
        print(f"  IO Events:")
        for event in task['io_events']:
            print(f"    - Tempo relativo: {event['time']} | Duração IO: {event['duration']} ticks")
            print(f"      (Executa {event['time']} ticks, depois IO por {event['duration']} ticks, depois {task['duration'] - event['time']} ticks mais)")
    else:
        print(f"  IO Events: Nenhum")
    
    if task.get('mutex_events'):
        print(f"  Mutex Events:")
        for event in task['mutex_events']:
            print(f"    - {event}")
    else:
        print(f"  Mutex Events: Nenhum")

print("\n" + "=" * 60)
print("RESUMO")
print("=" * 60)

for task in cfg['tasks']:
    task_id = task['id_']
    io_str = ""
    if task['io_events']:
        for event in task['io_events']:
            io_str += f"IO(t={event['time']}, dur={event['duration']}) "
    else:
        io_str = "Sem IO"
    
    print(f"{task_id:3} | duration={task['duration']:2} | {io_str}")
