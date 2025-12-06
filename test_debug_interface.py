#!/usr/bin/env python3
"""Teste simples da interface para debugar problema com toolbar"""

import tkinter as tk
from interface import TaskEditorApp
import sys

# Redireciona stdout para ver os prints
class TeeOutput:
    def __init__(self, original):
        self.original = original
        self.file = open('debug.log', 'w')
    
    def write(self, msg):
        self.original.write(msg)
        self.file.write(msg)
        self.file.flush()
    
    def flush(self):
        self.original.flush()
        self.file.flush()

sys.stdout = TeeOutput(sys.stdout)
sys.stderr = TeeOutput(sys.stderr)

print("=== Iniciando teste da interface ===")

root = tk.Tk()
app = TaskEditorApp(root)

# Carrega arquivo automaticamente
print("Carregando arquivo de config...")
app.load_from_file()
print(f"Tarefas carregadas: {len(app.tasks)}")

# Clica em Debug
print("\nClicando em Debug...")
app.start_debug()

print("\nTestando se toolbar está visível...")
print(f"Toolbar grid info: {app.debug_toolbar.grid_info()}")

root.quit()
print("\n=== Teste finalizado ===")
