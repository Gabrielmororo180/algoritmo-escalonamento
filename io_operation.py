"""io_operation.py
==================
Implementa operações de E/S (Input/Output) para tarefas.

Uma operação de E/S bloqueia a tarefa por um tempo específico, simulando
operações de disco, rede, etc.

Formato: IO:xx-yy
  xx = tempo relativo ao início da tarefa quando IO inicia
  yy = duração da operação de E/S (em ticks)

Exemplo: IO:2-5 significa:
  - No tick 2 da tarefa, inicia uma operação de E/S
  - A operação leva 5 ticks para completar
  - A tarefa fica bloqueada durante esses 5 ticks
"""


class IOOperation:
    """Representa uma operação de E/S.
    
    Attributes:
        time: Tempo relativo ao início da tarefa quando IO inicia
        duration: Quantos ticks a operação leva
        remaining: Tempo restante até a operação completar
    """
    
    def __init__(self, time, duration):
        """Inicializa operação de E/S.
        
        Args:
            time (int): Tempo relativo ao início da tarefa
            duration (int): Duração da operação em ticks
        """
        self.time = time
        self.duration = duration
        self.remaining = duration
    
    def tick(self):
        """Avança um tick na operação de E/S.
        
        Returns:
            bool: True se operação completou, False caso contrário
        """
        if self.remaining > 0:
            self.remaining -= 1
        return self.remaining == 0
    
    def is_active(self):
        """Verifica se operação ainda está em andamento."""
        return self.remaining > 0
    
    def reset(self):
        """Reseta operação para o estado inicial."""
        self.remaining = self.duration
    
    def __repr__(self):
        return f"IO(time={self.time}, duration={self.duration}, remaining={self.remaining})"
