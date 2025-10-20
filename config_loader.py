def load_config(filename):
    with open(filename, "r") as f:
        lines = [line.strip() for line in f if line.strip()]

    header = lines[0].split(";")
    algorithm, quantum = header[0], int(header[1])

    tasks = []
    for line in lines[1:]:
        id_, color, arrival, duration, priority, events = line.split(";")
        task = {
            "id_": id_,
            "color": color,
            "arrival": int(arrival),
            "duration": int(duration),
            "priority": int(priority),
            "events": events.split(",") if events else []
        }
        tasks.append(task)

    return {
        "algorithm": algorithm,
        "quantum": quantum,
        "tasks": tasks
    }
