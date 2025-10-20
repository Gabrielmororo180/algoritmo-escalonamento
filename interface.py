import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from config_loader import load_config
from simulator import Simulator
import tempfile
from config_loader import load_config

class TaskEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Escalonador de Tarefas - Simulador SO")

        self.tasks = []
        self.task_counter = 1 

        # Cabeçalho: Algoritmo + Quantum
        tk.Label(root, text="Algoritmo").grid(row=0, column=0, sticky="e")
        self.algorithm_cb = ttk.Combobox(root, values=["FIFO", "SRTF", "PRIORIDADE"], state="readonly", width=18)
        self.algorithm_cb.grid(row=0, column=1, pady=2)
        self.algorithm_cb.set("FIFO")

        tk.Label(root, text="Quantum").grid(row=0, column=2, sticky="e")
        self.quantum_entry = tk.Entry(root, width=6)
        self.quantum_entry.grid(row=0, column=3)
        self.quantum_entry.insert(0, "3")

        # Campos de tarefa (com Combobox de Cor)
        self.fields = {}

        # Cor (como combobox)
        tk.Label(root, text="Cor").grid(row=1, column=0, sticky="e")
        self.fields["cor"] = ttk.Combobox(root, values=[
            "red", "blue", "green", "orange", "purple", "yellow", "cyan", "gray", "black"
        ], state="readonly", width=18)
        self.fields["cor"].grid(row=1, column=1, pady=2, columnspan=3, sticky="w")
        self.fields["cor"].set("red")

        # Ingresso, Duração, Prioridade
        for i, label in enumerate(["Ingresso", "Duração", "Prioridade"]):
            tk.Label(root, text=label).grid(row=i+2, column=0, sticky="e")
            entry = tk.Entry(root, width=20)
            entry.grid(row=i+2, column=1, pady=2, columnspan=3, sticky="w")
            self.fields[label.lower()] = entry

        # Botões
        tk.Button(root, text="Carregar Arquivo", command=self.load_from_file).grid(row=6, column=4, pady=5)
        tk.Button(root, text="Inserir", command=self.insert_task).grid(row=1, column=4, padx=10)
        tk.Button(root, text="Atualizar", command=self.update_task).grid(row=2, column=4)
        tk.Button(root, text="Excluir", command=self.delete_task).grid(row=3, column=4)
        tk.Button(root, text="Salvar em arquivo", command=self.save_to_file).grid(row=4, column=4, pady=10)
        tk.Button(root, text="Executar Simulação", command=self.run_simulation).grid(row=5, column=4, pady=5)

        tk.Button(root, text="Debug", command=self.start_debug).grid(row=8, column=0, pady=5)
        tk.Button(root, text="Próximo Tick", command=self.next_tick).grid(row=8, column=1)

        # Lista de tarefas com ID visível
        self.tree = ttk.Treeview(root, columns=["ID", "Cor", "Ingresso", "Duração", "Prioridade"], show="headings")
        for col in ["ID", "Cor", "Ingresso", "Duração", "Prioridade"]:
            self.tree.heading(col, text=col)
        self.tree.grid(row=7, column=0, columnspan=5, pady=10)
        self.tree.bind("<Double-1>", self.load_selected_task)

    def generate_task_id(self):
        return f"T{self.task_counter}"

    def load_from_file(self):
        filepath = "sample_config.txt"
        
        try:
            config = load_config(filepath)
            self.algorithm_cb.set(config["algorithm"])
            self.quantum_entry.delete(0, tk.END)
            self.quantum_entry.insert(0, str(config["quantum"]))

            self.tasks = []
            self.tree.delete(*self.tree.get_children())
            self.task_counter = 1

            for task_dict in config["tasks"]:
                task_id = f"T{self.task_counter}"
                task = (
                    task_id,
                    task_dict["color"],
                    task_dict["arrival"],
                    task_dict["duration"],
                    task_dict["priority"]
                )
                self.tasks.append(task)
                self.tree.insert("", "end", values=task)
                self.task_counter += 1

            messagebox.showinfo("Sucesso", f"Arquivo carregado: {filepath}")

        except Exception as e:
            messagebox.showerror("Erro ao carregar arquivo", str(e))

    def insert_task(self):
        try:
            task_id = self.generate_task_id()
            task = (
                task_id,
                self.fields["cor"].get(),
                int(self.fields["ingresso"].get()),
                int(self.fields["duração"].get()),
                int(self.fields["prioridade"].get())
            )
            self.tasks.append(task)
            self.tree.insert("", "end", values=task)
            self.task_counter += 1
            self.clear_fields()
        except ValueError:
            messagebox.showerror("Erro", "Campos numéricos inválidos.")

    def load_selected_task(self, event):
        selected = self.tree.focus()
        if not selected:
            return
        values = self.tree.item(selected, "values")
        keys = ["cor", "ingresso", "duração", "prioridade"]
        for k, v in zip(keys, values[1:]):
            self.fields[k].delete(0, tk.END)
            self.fields[k].insert(0, v)
        self.fields["cor"].set(values[1])

    def update_task(self):
        selected = self.tree.focus()
        if not selected:
            return
        try:
            old_id = self.tree.item(selected, "values")[0]
            updated_task = (
                old_id,
                self.fields["cor"].get(),
                int(self.fields["ingresso"].get()),
                int(self.fields["duração"].get()),
                int(self.fields["prioridade"].get())
            )
            self.tree.item(selected, values=updated_task)
            index = self.tree.index(selected)
            self.tasks[index] = updated_task
            self.clear_fields()
        except ValueError:
            messagebox.showerror("Erro", "Campos numéricos inválidos.")

    def run_simulation(self):
        if not self.tasks:
            messagebox.showwarning("Aviso", "Adicione pelo menos uma tarefa antes de simular.")
            return

        algorithm = self.algorithm_cb.get()
        try:
            quantum = int(self.quantum_entry.get())
        except ValueError:
            messagebox.showerror("Erro", "Quantum deve ser um número inteiro.")
            return

        try:
            self.save_to_file()
            with open("sample_config.txt", "w") as f:
                f.write(f"{algorithm};{quantum}\n")
                for task in self.tasks:
                    linha = f"{task[0]};{task[1]};{task[2]};{task[3]};{task[4]};\n"
                    f.write(linha)

            config = load_config("sample_config.txt")
            simulator = Simulator(config)
            simulator.run()
        except Exception as e:
            messagebox.showerror("Erro ao simular", str(e))



    def delete_task(self):
        selected = self.tree.focus()
        if not selected:
            return
        index = self.tree.index(selected)
        self.tree.delete(selected)
        del self.tasks[index]
        self.clear_fields()

    def save_to_file(self):
        if not self.tasks:
            messagebox.showwarning("Aviso", "Nenhuma tarefa para salvar.")
            return

        algorithm = self.algorithm_cb.get()
        try:
            quantum = int(self.quantum_entry.get())
        except ValueError:
            messagebox.showerror("Erro", "Quantum deve ser um número inteiro.")
            return

        filepath = "sample_config.txt"
      
        try:
            with open(filepath, "w") as f:
                f.write(f"{algorithm};{quantum}\n")
                for task in self.tasks:
                    linha = f"{task[0]};{task[1]};{task[2]};{task[3]};{task[4]};\n"
                    f.write(linha)
                    
            messagebox.showinfo("Sucesso", f"Arquivo salvo: {filepath}")
        except Exception as e:
            messagebox.showerror("Erro ao salvar", str(e))

    def clear_fields(self):
        for key in ["ingresso", "duração", "prioridade"]:
            self.fields[key].delete(0, tk.END)
        self.fields["cor"].set("red")

    def start_debug(self):
        if not self.tasks:
            messagebox.showwarning("Aviso", "Nenhuma tarefa para simular.")
            return

        algorithm = self.algorithm_cb.get()
        try:
            quantum = int(self.quantum_entry.get())
        except ValueError:
            messagebox.showerror("Erro", "Quantum inválido.")
            return

        # Salvar arquivo e carregar simulador
        try:
            with open("sample_config.txt", "w") as f:
                f.write(f"{algorithm};{quantum}\n")
                for task in self.tasks:
                    linha = f"{task[0]};{task[1]};{task[2]};{task[3]};{task[4]};\n"
                    f.write(linha)

            from config_loader import load_config
            config = load_config("sample_config.txt")
            self.simulator = Simulator(config)
            self.simulator.run_debug()

            messagebox.showinfo("Modo Debug", " Clique em 'Próximo Tick' para continuar.")
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def next_tick(self):
        if not hasattr(self, 'simulator'):
            messagebox.showwarning("Aviso", "Inicie a simulação com o botão 'Debug' antes.")
            return

        tick_result = self.simulator.step()

        if not tick_result:
            messagebox.showinfo("Fim", "Todas as tarefas foram finalizadas.")


if __name__ == "__main__":
    root = tk.Tk()
    app = TaskEditorApp(root)
    root.mainloop()
