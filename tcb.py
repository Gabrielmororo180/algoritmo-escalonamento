class TaskControlBlock:
    def __init__(self, id_, color, arrival, duration, priority, events):
        self.id = id_
        self.color = color
        self.arrival = arrival
        self.duration = duration
        self.priority = priority
        self.events = events

        self.remaining_time = duration
        self.completed = False
        self.executed_ticks = 0
