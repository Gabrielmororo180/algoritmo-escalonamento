"""interface.py
================
Interface gráfica (Tkinter) para criação, edição e execução de tarefas.

Decisões:
- Simples tabela (Treeview) para refletir estado das tarefas em memória.
- IDs gerados sequencialmente (T1, T2, ...) para evitar colisões rápidas.
- Salvamento explícito no arquivo padrão `sample_config.txt` antes de rodar
    simulação (mantém compatibilidade com CLI).
- Modo Debug expõe ticking manual, útil para fins didáticos.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from config_loader import load_config
from simulator import Simulator
from config_loader import load_config
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

class TaskEditorApp:
    """Aplicação principal da GUI de edição de tarefas.

    Fluxo de uso:
    1. Selecionar algoritmo/quantum.
    2. Inserir tarefas (Ingresso, Duração, Prioridade, Cor).
    3. Salvar ou executar diretamente.
    4. Opcional: entrar em modo Debug para avançar tick a tick.
    """
    def __init__(self, root):
        self.root = root
        self.root.title("Escalonador de Tarefas - Simulador SO")
        self.tasks = []          
        self.task_counter = 1    

        tk.Label(root, text="Algoritmo").grid(row=0, column=0, sticky="e")
        self.algorithm_cb = ttk.Combobox(root, values=["FIFO", "SRTF", "PRIOP"], state="readonly", width=18)
        self.algorithm_cb.grid(row=0, column=1, pady=2)
        self.algorithm_cb.set("FIFO")

        tk.Label(root, text="Quantum").grid(row=0, column=2, sticky="e")
        self.quantum_entry = tk.Entry(root, width=6)
        self.quantum_entry.grid(row=0, column=3)
        self.quantum_entry.insert(0, "3")
        self.fields = {}

        
        tk.Label(root, text="Cor").grid(row=1, column=0, sticky="e")
        self.fields["cor"] = ttk.Combobox(root, values=[
            "red", "blue", "green", "orange", "purple", "yellow", "cyan", "gray", "black"
        ], state="readonly", width=18)
        self.fields["cor"].grid(row=1, column=1, pady=2, columnspan=3, sticky="w")
        self.fields["cor"].set("red")

        for i, label in enumerate(["Ingresso", "Duração", "Prioridade"]):
            tk.Label(root, text=label).grid(row=i+2, column=0, sticky="e")
            entry = tk.Entry(root, width=20)
            entry.grid(row=i+2, column=1, pady=2, columnspan=3, sticky="w")
            self.fields[label.lower()] = entry

        # Frame único para todos os botões em uma linha
        buttons_frame = tk.Frame(root)
        buttons_frame.grid(row=6, column=0, columnspan=5, sticky='w', pady=8)

        btn_specs = [
            ("Carregar Arquivo", self.load_from_file),
            ("Inserir", self.insert_task),
            ("Atualizar", self.update_task),
            ("Excluir", self.delete_task),
            ("Salvar em arquivo", self.save_to_file),
            ("Executar Simulação", self.run_simulation),
            ("Debug", self.start_debug),
            ("Próximo Tick", self.next_tick)
        ]
        for i, (label, cmd) in enumerate(btn_specs):
            tk.Button(buttons_frame, text=label, command=cmd).grid(row=0, column=i, padx=4)

        # Lista de tarefas com ID visível
        self.tree = ttk.Treeview(root, columns=["ID", "Cor", "Ingresso", "Duração", "Prioridade"], show="headings")
        for col in ["ID", "Cor", "Ingresso", "Duração", "Prioridade"]:
            self.tree.heading(col, text=col)
        self.tree.grid(row=7, column=0, columnspan=5, pady=10, sticky='we')
        self.tree.bind("<Double-1>", self.load_selected_task)
        
        # Frame para o gráfico Gantt
        self.gantt_frame = tk.Frame(root, bd=2, relief='groove', height=400)
        self.gantt_frame.grid(row=10, column=0, columnspan=5, sticky='nsew', pady=10)
        self.gantt_frame.grid_propagate(False)
        self.root.grid_rowconfigure(10, weight=1)

    def generate_task_id(self):
        """Gera ID sequencial (T1, T2...). Evita necessidade de entrada manual."""
        return f"T{self.task_counter}"

    def load_from_file(self):
        """Carrega tarefas de arquivo de configuração padrão e atualiza a tabela.
        Ignora eventos (não exibidos na GUI). Reinicia contador de IDs.
        """
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
        """Insere nova tarefa com valores dos campos.
        Valida campos numéricos básicos.
        """
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
        """Ao dar duplo clique na tabela, carrega valores nos campos para edição."""
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
        """Atualiza tarefa existente mantendo o mesmo ID."""
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
        """Salva tarefas em arquivo e executa simulação completa.
        Reusa o arquivo para manter consistência com o fluxo CLI.
        """
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
            
            # Renderiza gráfico Gantt no frame
            self.render_gantt_in_frame(simulator)
            
        except Exception as e:
            messagebox.showerror("Erro ao simular", str(e))



    def delete_task(self):
        """Remove tarefa selecionada da lista e da tabela."""
        selected = self.tree.focus()
        if not selected:
            return
        index = self.tree.index(selected)
        self.tree.delete(selected)
        del self.tasks[index]
        self.clear_fields()

    def save_to_file(self):
        """Persiste conjunto atual de tarefas em `sample_config.txt`."""
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
        """Limpa campos de edição (exceto cor que volta ao default)."""
        for key in ["ingresso", "duração", "prioridade"]:
            self.fields[key].delete(0, tk.END)
        self.fields["cor"].set("red")

    def start_debug(self):
        """Inicia modo debug preparando simulador para stepping manual."""
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
            # Cria/limpa painel de estado se ainda não existir
            if not hasattr(self, 'debug_frame'):
                self.debug_frame = tk.Frame(self.root, bd=2, relief='groove')
                self.debug_frame.grid(row=9, column=0, columnspan=5, sticky='we', pady=5)
                tk.Label(self.debug_frame, text='Estado Debug (snapshot)').grid(row=0, column=0, sticky='w')
                self.debug_text = tk.Text(self.debug_frame, height=12, width=80, font=('Consolas', 9))
                self.debug_text.grid(row=1, column=0, sticky='we')
            else:
                self.debug_text.delete('1.0', tk.END)
            
            self.update_debug_snapshot()
            # Renderiza gráfico Gantt inicial no modo debug
            self.update_debug_gantt()

            messagebox.showinfo("Modo Debug", " Clique em 'Próximo Tick' para continuar.")
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def next_tick(self):
        """Avança um tick no modo debug e mostra mensagem ao concluir todas as tarefas."""
        if not hasattr(self, 'simulator'):
            messagebox.showwarning("Aviso", "Inicie a simulação com o botão 'Debug' antes.")
            return

        tick_result = self.simulator.step()
        self.update_debug_snapshot()
        self.update_debug_gantt()

        if not tick_result:
            messagebox.showinfo("Fim", "Todas as tarefas foram finalizadas.")

    def update_debug_snapshot(self):
        """Renderiza snapshot detalhado do simulador no painel de debug."""
        if not hasattr(self, 'simulator') or not hasattr(self, 'debug_text'):
            return
        snap = self.simulator.snapshot()
        lines = []
        lines.append(f"Tick atual: {snap['time']}")
        lines.append(f"Algoritmo: {snap['algorithm']} | Quantum: {snap['quantum']}")
        lines.append(f"Rodando: {snap['running']}")
        lines.append(f"Fila de Prontos: {', '.join(snap['ready_queue']) if snap['ready_queue'] else '(vazia)'}")
        lines.append("\nTarefas:")
        header = f"{'ID':<4} {'Arr':>3} {'Dur':>3} {'Rem':>3} {'Prio':>4} {'Exec':>4} {'Waits':>5} {'W?':>3} {'Done':>4}"
        lines.append(header)
        lines.append('-' * len(header))
        for t in snap['tasks']:
            lines.append(f"{t['id']:<4} {t['arrival']:>3} {t['duration']:>3} {t['remaining']:>3} {t['priority']:>4} {t['executed_ticks']:>4} {t['waited_ticks']:>5} {'Y' if t['waiting_now'] else 'N':>3} {'Y' if t['completed'] else 'N':>4}")
        lines.append("\nTimeline (últimos 30 ticks):")
        last30 = snap['timeline'][-30:]
        lines.append(' '.join([str(x) if x is not None else '-' for x in last30]))
        self.debug_text.delete('1.0', tk.END)
        self.debug_text.insert(tk.END, '\n'.join(lines))

    def update_debug_gantt(self):
        """Atualiza o gráfico Gantt em tempo real no modo debug."""
        if not hasattr(self, 'simulator'):
            return
        
        # Renderiza no frame gantt_frame
        self.render_gantt_in_frame(self.simulator)

    def render_gantt_in_frame(self, simulator):
        """Renderiza gráfico Gantt direto no frame da interface."""
        # Limpar frame anterior
        for widget in self.gantt_frame.winfo_children():
            widget.destroy()
        
        # Criar figura Matplotlib
        fig = Figure(figsize=(10, 3), dpi=100)
        ax = fig.add_subplot(111)
        
        # Dados da simulação
        timeline = simulator.timeline
        arrivals = simulator.arrivals_map
        finishes = simulator.finish_map
        wait_map = simulator.wait_map
        task_colors = simulator.task_colors
        
        # Renderizar gráfico
        total_time = len(timeline)
        tasks = sorted({t for t in timeline if t is not None and t != 'IDLE'})
        
        if not tasks:
            ax.text(0.5, 0.5, 'Nenhuma tarefa executada', ha='center', va='center')
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
        else:
            colors = plt.cm.tab10.colors
            
            for i, task in enumerate(tasks):
                y_pos = i - 0.4
                start_time = arrivals.get(task, 0)
                end_time = finishes.get(task, total_time)
                life_duration = max(0, end_time - start_time)
                
                # Contorno da vida
                ax.broken_barh([(start_time, life_duration)], (y_pos, 0.8),
                              facecolors="none", edgecolors="black", linewidth=1.2)
                
                # Intervalos de execução
                intervals = []
                s = None
                for t, cur in enumerate(timeline):
                    if cur == task:
                        if s is None:
                            s = t
                    else:
                        if s is not None:
                            intervals.append((s, t - s))
                            s = None
                if s is not None:
                    intervals.append((s, total_time - s))
                
                # Cor
                if task_colors and task in task_colors:
                    color = task_colors[task]
                else:
                    color = colors[i % len(colors)]
                
                # Pintar execução
                for st, dur in intervals:
                    seg_start = max(st, start_time)
                    seg_end = min(st + dur, end_time)
                    seg_dur = seg_end - seg_start
                    if seg_dur > 0:
                        ax.broken_barh([(seg_start, seg_dur)], (y_pos, 0.8),
                                      facecolors=color, edgecolors="black", linewidth=1.2)
                
                # Calcular esperas
                exec_ticks = set()
                for st, dur in intervals:
                    for tt in range(st, st + dur):
                        exec_ticks.add(tt)
                
                waiting_ticks = set()
                if wait_map and task in wait_map:
                    waiting_ticks.update(wait_map[task])
                
                for tt in range(start_time, end_time):
                    if tt not in exec_ticks:
                        waiting_ticks.add(tt)
                
                # Agrupar intervalos de espera
                wait_intervals = []
                ws = None
                for t in range(start_time, end_time):
                    if t in waiting_ticks and t not in exec_ticks:
                        if ws is None:
                            ws = t
                    else:
                        if ws is not None:
                            wait_intervals.append((ws, t - ws))
                            ws = None
                if ws is not None:
                    wait_intervals.append((ws, end_time - ws))
                
                for st, dur in wait_intervals:
                    if dur > 0:
                        ax.broken_barh([(st, dur)], (y_pos, 0.8),
                                      facecolors="white", edgecolors="black", linewidth=0.8)
            
            ax.set_xlabel("Tempo (t)")
            ax.set_ylabel("Tarefas")
            ax.set_yticks(range(len(tasks)))
            ax.set_yticklabels(tasks)
            ax.set_xticks(range(total_time + 1))
            ax.grid(True, axis='x', linestyle=':', alpha=0.5)
        
        ax.set_title("Gráfico de Gantt")
        fig.tight_layout()
        
        # Embutir no frame
        canvas = FigureCanvasTkAgg(fig, master=self.gantt_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)


if __name__ == "__main__":
    root = tk.Tk()
    app = TaskEditorApp(root)
    root.mainloop()
