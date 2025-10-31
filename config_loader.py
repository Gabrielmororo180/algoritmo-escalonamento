DEFAULTS = {
    "algorithm": "FIFO",
    "quantum": 3,
    "color": "gray",
    "priority": 1,
    "events": []
}

def generate_default_config(path="sample_config.txt", tasks=5):
    """Gera um arquivo de configuração padrão caso não exista.
    Formato:
    algoritmo;quantum
    id;cor;ingresso;duracao;prioridade;lista_eventos
    """
    import os
    if os.path.exists(path):
        return path
    with open(path, "w") as f:
        f.write(f"{DEFAULTS['algorithm']};{DEFAULTS['quantum']}\n")
        for i in range(1, tasks + 1):
            # Eventos vazio
            f.write(f"T{i};{DEFAULTS['color']};{i-1};{2 + (i % 3)};{DEFAULTS['priority']};\n")
    return path

def parse_task_line(line):
    parts = line.split(";")
    # Garante 6 campos (último eventos pode faltar)
    while len(parts) < 6:
        parts.append("")
    id_, color, arrival, duration, priority, events = parts[:6]
    # Aplicar defaults e conversões seguras
    def to_int(val, default):
        try:
            return int(val)
        except (ValueError, TypeError):
            return default
    arrival_i = to_int(arrival, 0)
    duration_i = to_int(duration, 1)
    priority_i = to_int(priority, DEFAULTS['priority'])
    color_v = color if color else DEFAULTS['color']
    events_list = [e.strip() for e in events.split(',') if e.strip()] if events else []
    return {
        "id_": id_,
        "color": color_v,
        "arrival": arrival_i,
        "duration": duration_i,
        "priority": priority_i,
        "events": events_list
    }

def load_config(filename):
    # Gera config padrão se arquivo não existir
    import os
    if not os.path.exists(filename):
        generate_default_config(filename)

    with open(filename, "r") as f:
        lines = [line.strip() for line in f if line.strip()]
    if not lines:
        raise ValueError("Arquivo de configuração vazio.")

    header = lines[0].split(";")
    algorithm = header[0] if header and header[0] else DEFAULTS['algorithm']
    try:
        quantum = int(header[1]) if len(header) > 1 and header[1] else DEFAULTS['quantum']
    except ValueError:
        quantum = DEFAULTS['quantum']

    tasks = [parse_task_line(line) for line in lines[1:]]

    return {
        "algorithm": algorithm,
        "quantum": quantum,
        "tasks": tasks
    }
