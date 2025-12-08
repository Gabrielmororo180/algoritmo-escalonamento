"""mutex.py
===========
Sistema de mutex (mutual exclusion) para sincronização entre tarefas.

Um mutex protege uma seção crítica permitindo que apenas uma tarefa
execute por vez. Outras tarefas ficam bloqueadas na fila de espera.
"""


class Mutex:
    """Representa um mutex com lock e fila de espera.
    
    Atributos:
    - id: número do mutex (ex: 1, 2, 3...)
    - locked: bool - se está ocupado
    - owner_id: str - ID da tarefa que tem o lock (ex: 'T1')
    - waiting_queue: list - fila de tarefas esperando [T2, T3, ...]
    """
    
    def __init__(self, mutex_id):
        """Cria um novo mutex.
        
        Args:
            mutex_id (int): número único do mutex
        """
        self.id = mutex_id
        self.locked = False
        self.owner_id = None
        self.waiting_queue = []
    
    def try_lock(self, task_id):
        """Tenta adquirir o lock do mutex.
        
        Args:
            task_id (str): ID da tarefa (ex: 'T1')
            
        Returns:
            bool: True se conseguiu lock, False se ficou na fila de espera
        """
        if not self.locked:
            # Mutex livre - acquire immediately
            self.locked = True
            self.owner_id = task_id
            return True
        else:
            if task_id not in self.waiting_queue:
                self.waiting_queue.append(task_id)
            return False
    
    def unlock(self, task_id):
        """Libera o lock do mutex.
        
        Args:
            task_id (str): ID da tarefa liberando o lock
            
        Returns:
            str or None: ID da próxima tarefa que consegue o lock, ou None
        """
        if self.owner_id == task_id:
            self.owner_id = None
            self.locked = False
            
            # Promove primeira tarefa da fila
            if self.waiting_queue:
                next_task = self.waiting_queue.pop(0)
                self.locked = True
                self.owner_id = next_task
                return next_task
        
        return None
    
    def is_owner(self, task_id):
        """Verifica se uma tarefa é a dona do lock."""
        return self.owner_id == task_id
    
    def is_locked(self):
        """Verifica se o mutex está atualmente bloqueado."""
        return self.locked
    
    def is_waiting(self, task_id):
        """Verifica se uma tarefa está na fila de espera."""
        return task_id in self.waiting_queue
    
    def get_status(self):
        """Retorna um dicionário com o estado do mutex."""
        return {
            "id": self.id,
            "locked": self.locked,
            "owner": self.owner_id,
            "waiting": self.waiting_queue.copy()
        }
    
    def __repr__(self):
        status = "LIVRE" if not self.locked else f"LOCKED by {self.owner_id}"
        waiting_str = f", waiting: {self.waiting_queue}" if self.waiting_queue else ""
        return f"Mutex({self.id}): {status}{waiting_str}"
