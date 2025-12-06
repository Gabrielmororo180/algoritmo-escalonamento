"""config_loader.py
====================
Responsável por carregar e validar o arquivo de configuração simples da simulação.

Formato esperado:
Primeira linha (algoritmos atuais):
    FIFO;quantum
    SRTF;quantum
    PRIOP;quantum
    PRIOPEnv;quantum;alpha
Linhas seguintes:
    id;cor;ingresso;duracao;prioridade;lista_eventos

Decisões de design:
- Parsing tolerante: campos faltantes recebem defaults evitando falha dura.
- Defaults centralizados em `DEFAULTS` para reutilização por CLI e geração de template.
- Separação `parse_task_line` mantém `load_config` enxuto e testável.
"""

DEFAULTS = {
    "algorithm": "FIFO",
    "quantum": 3,
    "color": "#808080",  # gray em hexadecimal
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
    
    def validate_hex_color(color_str):
        """Valida se é uma cor hexadecimal válida, senão usa default."""
        if not color_str:
            return DEFAULTS['color']
        
        # Se não começa com #, adiciona
        if not color_str.startswith("#"):
            color_str = "#" + color_str
        
        # Valida formato #RRGGBB (6 caracteres hex)
        if len(color_str) == 7 and all(c in "0123456789ABCDEFabcdef" for c in color_str[1:]):
            return color_str.upper()
        else:
            return DEFAULTS['color']
    
    arrival_i = to_int(arrival, 0)
    duration_i = to_int(duration, 1)
    priority_i = to_int(priority, DEFAULTS['priority'])
    color_v = validate_hex_color(color)
    
    # Parsear eventos de mutex e IO
    mutex_events = []
    io_events = []
    if events:
        for event_str in events.split(','):
            event_str = event_str.strip()
            if event_str:
                # Tenta parsear como mutex primeiro
                parsed_event = parse_mutex_event(event_str)
                if parsed_event:
                    mutex_events.append(parsed_event)
                else:
                    # Tenta parsear como IO
                    parsed_io = parse_io_event(event_str)
                    if parsed_io:
                        io_events.append(parsed_io)
    
    return {
        "id_": id_,
        "color": color_v,
        "arrival": arrival_i,
        "duration": duration_i,
        "priority": priority_i,
        "events": mutex_events,
        "io_events": io_events
    }

def parse_mutex_event(event_str):
    """Parseia evento de mutex no formato MLxx:tt ou MUxx:tt.
    
    MLxx:tt - Lock do mutex xx no tempo relativo tt
    MUxx:tt - Unlock do mutex xx no tempo relativo tt
    
    Args:
        event_str (str): ex: "ML01:5", "MU02:10"
        
    Returns:
        dict or None: {"type": "lock"|"unlock", "mutex_id": int, "time": int}
                      ou None se formato inválido
    """
    event_str = event_str.strip().upper()
    
    if not (event_str.startswith("ML") or event_str.startswith("MU")):
        return None
    
    try:
        action = event_str[:2]  # "ML" ou "MU"
        rest = event_str[2:]    # "01:5" ou "02:10"
        
        if ":" not in rest:
            return None
        
        mutex_str, time_str = rest.split(":", 1)
        mutex_id = int(mutex_str)
        time_val = int(time_str)
        
        action_type = "lock" if action == "ML" else "unlock"
        
        return {
            "type": action_type,
            "mutex_id": mutex_id,
            "time": time_val  # tempo relativo ao início da tarefa
        }
    except (ValueError, IndexError):
        return None

def parse_io_event(event_str):
    """Parseia evento de E/S no formato IOxx-yy.
    
    IOxx-yy - Operação de E/S que inicia no tempo xx e dura yy ticks
    
    Args:
        event_str (str): ex: "IO2-5", "IO10-3"
        
    Returns:
        dict or None: {"type": "io", "time": int, "duration": int}
                      ou None se formato inválido
    """
    event_str = event_str.strip().upper()
    
    if not event_str.startswith("IO"):
        return None
    
    try:
        rest = event_str[2:]  # "2-5" ou "10-3"
        
        if "-" not in rest:
            return None
        
        time_str, duration_str = rest.split("-", 1)
        time_val = int(time_str)
        duration_val = int(duration_str)
        
        return {
            "type": "io",
            "time": time_val,        # tempo relativo ao início da tarefa
            "duration": duration_val # duração da operação em ticks
        }
    except (ValueError, IndexError):
        return None

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

    # Alpha para PRIOPEnv (preemptivo com envelhecimento)
    alpha = 0
    if algorithm.upper() == "PRIOPENV":
        try:
            alpha = int(header[2]) if len(header) > 2 and header[2] else 0
        except ValueError:
            alpha = 0

    tasks = [parse_task_line(line) for line in lines[1:]]

    return {
        "algorithm": algorithm,
        "quantum": quantum,
        "alpha": alpha,
        "tasks": tasks
    }
