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
        
        
        self.debug_history = []  
        self.debug_current_index = -1  

        tk.Label(root, text="Algoritmo").grid(row=0, column=0, sticky="e")
        self.algorithm_cb = ttk.Combobox(root, values=["FIFO", "SRTF", "PRIOP", "PRIOPEnv"], state="readonly", width=18)
        self.algorithm_cb.grid(row=0, column=1, pady=2)
        self.algorithm_cb.set("FIFO")

        tk.Label(root, text="Quantum").grid(row=0, column=2, sticky="e")
        self.quantum_entry = tk.Entry(root, width=6)
        self.quantum_entry.grid(row=0, column=3)
        self.quantum_entry.insert(0, "3")
        
        tk.Label(root, text="Alpha").grid(row=0, column=4, sticky="e")
        self.alpha_entry = tk.Entry(root, width=6)
        self.alpha_entry.grid(row=0, column=5)
        self.alpha_entry.insert(0, "0")
        
        self.fields = {}

        
        tk.Label(root, text="Cor (Hex)").grid(row=1, column=0, sticky="e")
        
       
        cor_frame = tk.Frame(root)
        cor_frame.grid(row=1, column=1, pady=2, columnspan=3, sticky="w")
        
       
        self.color_options = {
            "Vermelho": "#FF0000",
            "Verde": "#00FF00",
            "Azul": "#0000FF",
            "Amarelo": "#FFFF00",
            "Magenta": "#FF00FF",
            "Ciano": "#00FFFF",
            "Laranja": "#FFA500",
            "Roxo": "#800080",
            "Cinza": "#808080",
            "Preto": "#000000",
            "Branco": "#FFFFFF",
            "Rosa": "#FFC0CB"
        }
        
        # Combobox com cores
        self.fields["cor"] = ttk.Combobox(
            cor_frame, 
            values=list(self.color_options.keys()),
            state="readonly",
            width=15
        )
        self.fields["cor"].pack(side=tk.LEFT, padx=5)
        self.fields["cor"].set("Vermelho")
        self.fields["cor"].bind("<<ComboboxSelected>>", self.update_color_preview)
        
        # Preview da cor
        self.color_preview = tk.Canvas(cor_frame, width=30, height=30, bg="#FF0000", relief="solid", borderwidth=1)
        self.color_preview.pack(side=tk.LEFT, padx=5)

        for i, label in enumerate(["Ingresso", "Duração", "Prioridade"]):
            tk.Label(root, text=label).grid(row=i+2, column=0, sticky="e")
            entry = tk.Entry(root, width=20)
            entry.grid(row=i+2, column=1, pady=2, columnspan=3, sticky="w")
            self.fields[label.lower()] = entry

        # Campo de eventos (mutex)
        tk.Label(root, text="Eventos").grid(row=5, column=0, sticky="ne")
        eventos_entry = tk.Entry(root, width=20)
        eventos_entry.grid(row=5, column=1, pady=2, columnspan=3, sticky="w")
        self.fields["eventos"] = eventos_entry
        tk.Label(root, text="(ex: ML1:2,MU1:5)", font=('Arial', 8), fg='gray').grid(row=5, column=4, sticky="w")

        # Campo de eventos de IO
        tk.Label(root, text="IO Eventos").grid(row=6, column=0, sticky="ne")
        io_eventos_entry = tk.Entry(root, width=20)
        io_eventos_entry.grid(row=6, column=1, pady=2, columnspan=3, sticky="w")
        self.fields["io_eventos"] = io_eventos_entry
        tk.Label(root, text="(ex: IO2-5,IO10-3)", font=('Arial', 8), fg='gray').grid(row=6, column=4, sticky="w")

        # Frame único para todos os botões em uma linha
        buttons_frame = tk.Frame(root)
        buttons_frame.grid(row=7, column=0, columnspan=5, sticky='w', pady=8)

        btn_specs = [
            ("Carregar Arquivo", self.load_from_file),
            ("Inserir", self.insert_task),
            ("Atualizar", self.update_task),
            ("Excluir", self.delete_task),
            ("Salvar em arquivo", self.save_to_file),
            ("Executar Simulação", self.run_simulation),
            ("Debug", self.start_debug),
        ]
        for i, (label, cmd) in enumerate(btn_specs):
            tk.Button(buttons_frame, text=label, command=cmd).grid(row=0, column=i, padx=4)
        
        
        self.debug_toolbar = tk.Frame(root, bd=2, relief='sunken', bg='#f0f0f0')
        self.debug_toolbar.grid(row=8, column=0, columnspan=5, sticky='ew', pady=5)
        self.debug_toolbar.grid_remove()  
        
        
        self.debug_progress_label = tk.Label(self.debug_toolbar, text='', bg='#f0f0f0', font=('Arial', 10, 'bold'))
        self.debug_progress_label.pack(side=tk.LEFT, padx=10, pady=5)
        
       
        ttk.Separator(self.debug_toolbar, orient='vertical').pack(side=tk.LEFT, fill='y', padx=5)
        
        # Botão Voltar Tick
        self.prev_tick_btn = tk.Button(
            self.debug_toolbar,
            text='⏮ Tick Anterior',
            command=self.prev_tick,
            bg='#2196F3',
            fg='white',
            font=('Arial', 10),
            padx=10,
            pady=8,
            state=tk.DISABLED
        )
        self.prev_tick_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Botão Próximo Tick (grande e destacado)
        self.next_tick_btn = tk.Button(
            self.debug_toolbar, 
            text='⏭ Próximo Tick', 
            command=self.next_tick,
            bg='#4CAF50',
            fg='white',
            font=('Arial', 11, 'bold'),
            padx=15,
            pady=8
        )
        self.next_tick_btn.pack(side=tk.LEFT, padx=10, pady=5)
        
        # Separador
        ttk.Separator(self.debug_toolbar, orient='vertical').pack(side=tk.LEFT, fill='y', padx=5)
        
        # Botão Pausar/Retomar
        self.pause_debug_btn = tk.Button(
            self.debug_toolbar,
            text=' Pausar',
            command=self.pause_debug,
            bg='#FF9800',
            fg='white',
            font=('Arial', 10),
            padx=10,
            pady=8
        )
        self.pause_debug_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Botão Reiniciar
        self.restart_debug_btn = tk.Button(
            self.debug_toolbar,
            text=' Reiniciar',
            command=self.restart_debug,
            bg='#2196F3',
            fg='white',
            font=('Arial', 10),
            padx=10,
            pady=8
        )
        self.restart_debug_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Botão Sair do Debug
        self.exit_debug_btn = tk.Button(
            self.debug_toolbar,
            text='Sair do Debug',
            command=self.exit_debug,
            bg='#f44336',
            fg='white',
            font=('Arial', 10),
            padx=10,
            pady=8
        )
        self.exit_debug_btn.pack(side=tk.LEFT, padx=5, pady=5)

        
        self.tree = ttk.Treeview(root, columns=["ID", "Cor", "Ingresso", "Duração", "Prioridade", "Eventos", "IO Eventos"], show="headings", height=8)
        
        
        col_widths = {
            "ID": 40,
            "Cor": 70,
            "Ingresso": 70,
            "Duração": 70,
            "Prioridade": 70,
            "Eventos": 150,
            "IO Eventos": 150
        }
        
        for col in ["ID", "Cor", "Ingresso", "Duração", "Prioridade", "Eventos", "IO Eventos"]:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=col_widths[col])
        
        self.tree.grid(row=9, column=0, columnspan=5, pady=10, sticky='we')
        self.tree.bind("<Double-1>", self.load_selected_task)
        
        # Frame para o gráfico Gantt
        self.gantt_frame = tk.Frame(root, bd=2, relief='groove', height=400)
        self.gantt_frame.grid(row=11, column=0, columnspan=5, sticky='nsew', pady=10)
        self.gantt_frame.grid_propagate(False)
        self.root.grid_rowconfigure(11, weight=1)

    def generate_task_id(self):
        """Gera ID sequencial (T1, T2...). Evita necessidade de entrada manual."""
        return f"T{self.task_counter}"

    def update_color_preview(self, event=None):
        """Atualiza o preview da cor quando o usuário seleciona uma cor."""
        try:
            color_name = self.fields["cor"].get()
            hex_color = self.color_options.get(color_name, "#808080")
            self.color_preview.config(bg=hex_color)
        except:
            self.color_preview.config(bg="#808080")

    def load_from_file(self):
        """Carrega tarefas de arquivo de configuração padrão e atualiza a tabela.
        Inclui eventos (mutex) e io_eventos na tabela. Reinicia contador de IDs.
        """
        filepath = "sample_config.txt"
        
        try:
            config = load_config(filepath)
            self.algorithm_cb.set(config["algorithm"])
            self.quantum_entry.delete(0, tk.END)
            self.quantum_entry.insert(0, str(config["quantum"]))
            self.alpha_entry.delete(0, tk.END)
            self.alpha_entry.insert(0, str(config.get("alpha", 0)))

          
            if not self.tasks:
                self.task_counter = 1
            else:
               
                self.task_counter = len(self.tasks) + 1

            for task_dict in config["tasks"]:
                task_id = f"T{self.task_counter}"
                
                
                eventos_list = task_dict.get("events", [])
                if isinstance(eventos_list, list) and eventos_list:
                   
                    eventos_strs = []
                    for e in eventos_list:
                        event_type = "ML" if e.get("type") == "lock" else "MU"
                        mutex_id = e.get("mutex_id", "")
                        time_val = e.get("time", "")
                        eventos_strs.append(f"{event_type}{mutex_id}:{time_val}")
                    eventos_str = ",".join(eventos_strs)
                else:
                    eventos_str = ""
                
                # Processa eventos de IO
                io_eventos_list = task_dict.get("io_events", [])
                if isinstance(io_eventos_list, list) and io_eventos_list:
                    # Reconstrói string a partir dos dicts
                    io_eventos_strs = []
                    for e in io_eventos_list:
                        time_val = e.get("time", "")
                        duration_val = e.get("duration", "")
                        io_eventos_strs.append(f"IO{time_val}-{duration_val}")
                    io_eventos_str = ",".join(io_eventos_strs)
                else:
                    io_eventos_str = ""
                
                task = (
                    task_id,
                    task_dict["color"],
                    task_dict["arrival"],
                    task_dict["duration"],
                    task_dict["priority"],
                    eventos_str,
                    io_eventos_str
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
            color_name = self.fields["cor"].get()
            hex_color = self.color_options.get(color_name, "#FF0000")
            
            # Obtém eventos (campos opcionais)
            eventos_str = self.fields.get("eventos", tk.Entry()).get() if "eventos" in self.fields else ""
            io_eventos_str = self.fields.get("io_eventos", tk.Entry()).get() if "io_eventos" in self.fields else ""
            
            task = (
                task_id,
                hex_color,
                int(self.fields["ingresso"].get()),
                int(self.fields["duração"].get()),
                int(self.fields["prioridade"].get()),
                eventos_str,
                io_eventos_str
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
        keys = ["cor", "ingresso", "duração", "prioridade", "eventos", "io_eventos"]
        for k, v in zip(keys, values[1:]):
            if k == "cor":
                # Tenta encontrar o nome da cor pelo hex
                hex_value = str(v).upper()
                color_name = "Vermelho"  # padrão
                for name, hex_code in self.color_options.items():
                    if hex_code.upper() == hex_value:
                        color_name = name
                        break
                self.fields[k].set(color_name)
                self.update_color_preview()
            else:
                self.fields[k].delete(0, tk.END)
                self.fields[k].insert(0, str(v))

    def update_task(self):
        """Atualiza tarefa existente mantendo o mesmo ID."""
        selected = self.tree.focus()
        if not selected:
            return
        try:
            old_id = self.tree.item(selected, "values")[0]
            color_name = self.fields["cor"].get()
            hex_color = self.color_options.get(color_name, "#FF0000")
            eventos_str = self.fields.get("eventos", tk.Entry()).get() if "eventos" in self.fields else ""
            io_eventos_str = self.fields.get("io_eventos", tk.Entry()).get() if "io_eventos" in self.fields else ""
            
            updated_task = (
                old_id,
                hex_color,
                int(self.fields["ingresso"].get()),
                int(self.fields["duração"].get()),
                int(self.fields["prioridade"].get()),
                eventos_str,
                io_eventos_str
            )
            self.tree.item(selected, values=updated_task)
            index = self.tree.index(selected)
            self.tasks[index] = updated_task
            self.clear_fields()
        except ValueError:
            messagebox.showerror("Erro", "Campos numéricos inválidos.")

    def run_simulation(self):
        """Salva tarefas em arquivo e executa simulação completa.
        Se não houver tarefas, carrega do arquivo automaticamente.
        Depois exibe o snapshot final com a mesma formatação do debug.
        """
        # Se não há tarefas, tenta carregar do arquivo
        if not self.tasks:
            self.load_from_file()
            if not self.tasks:
                messagebox.showwarning("Aviso", "Nenhuma tarefa para simular.")
                return

        algorithm = self.algorithm_cb.get()
        try:
            quantum = int(self.quantum_entry.get())
            alpha = int(self.alpha_entry.get())
        except ValueError:
            messagebox.showerror("Erro", "Quantum e Alpha devem ser números inteiros.")
            return

        try:
            self.save_to_file()
            with open("sample_config.txt", "w") as f:
                f.write(f"{algorithm};{quantum};{alpha}\n")
                for task in self.tasks:
                    eventos = task[5] if len(task) > 5 else ""
                    io_eventos = task[6] if len(task) > 6 else ""
                    
                    
                    all_events = eventos
                    if io_eventos:
                        all_events = f"{eventos},{io_eventos}" if eventos else io_eventos
                    
                    linha = f"{task[0]};{task[1]};{task[2]};{task[3]};{task[4]};{all_events}\n"
                    f.write(linha)

            config = load_config("sample_config.txt")
            self.simulator = Simulator(config)
            self.simulator.run()
            
           
            self.render_gantt_in_frame(self.simulator)
            
          
            self._show_final_snapshot()
            
        except Exception as e:
            messagebox.showerror("Erro ao simular", str(e))

    def _show_final_snapshot(self):
        """Exibe o snapshot final da simulação com formatação de debug."""
        if not hasattr(self, 'simulator'):
            return
        
        
        if not hasattr(self, 'debug_frame'):
            self.debug_frame = tk.Frame(self.root, bd=2, relief='groove')
            self.debug_frame.grid(row=10, column=0, columnspan=5, sticky='we', pady=5)
            tk.Label(self.debug_frame, text='Estado Debug (snapshot)').grid(row=0, column=0, sticky='w')
            self.debug_text = tk.Text(self.debug_frame, height=12, width=80, font=('Consolas', 9))
            self.debug_text.grid(row=1, column=0, sticky='we')
        else:
            self.debug_text.delete('1.0', tk.END)
        
        
        snap = self.simulator.snapshot()
        
       
        self.update_debug_snapshot_from_data(snap)



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
            alpha = int(self.alpha_entry.get())
        except ValueError:
            messagebox.showerror("Erro", "Quantum e Alpha devem ser números inteiros.")
            return

        filepath = "sample_config.txt"
      
        try:
            with open(filepath, "w") as f:
                f.write(f"{algorithm};{quantum};{alpha}\n")
                for task in self.tasks:
                    eventos = task[5] if len(task) > 5 else ""
                    io_eventos = task[6] if len(task) > 6 else ""
                    
                   
                    all_events = eventos
                    if io_eventos:
                        all_events = f"{eventos},{io_eventos}" if eventos else io_eventos
                    
                    linha = f"{task[0]};{task[1]};{task[2]};{task[3]};{task[4]};{all_events}\n"
                    f.write(linha)
                    
            messagebox.showinfo("Sucesso", f"Arquivo salvo: {filepath}")
        except Exception as e:
            messagebox.showerror("Erro ao salvar", str(e))

    def clear_fields(self):
        """Limpa campos de edição (exceto cor que volta ao default)."""
        for key in ["ingresso", "duração", "prioridade", "eventos", "io_eventos"]:
            if key in self.fields:
                self.fields[key].delete(0, tk.END)
        self.fields["cor"].set("Vermelho")
        self.update_color_preview()

    def start_debug(self):
        """Inicia modo debug preparando simulador para stepping manual."""
        if not self.tasks:
            messagebox.showwarning("Aviso", "Nenhuma tarefa para simular.")
            return

        algorithm = self.algorithm_cb.get()
        try:
            quantum = int(self.quantum_entry.get())
            alpha = int(self.alpha_entry.get())
        except ValueError:
            messagebox.showerror("Erro", "Quantum e Alpha devem ser números inteiros.")
            return

        # Salvar arquivo e carregar simulador
        try:
            with open("sample_config.txt", "w") as f:
                f.write(f"{algorithm};{quantum};{alpha}\n")
                for task in self.tasks:
                    # Incluir eventos (6º elemento) e io_eventos (7º elemento) se existirem
                    eventos = task[5] if len(task) > 5 else ""
                    io_eventos = task[6] if len(task) > 6 else ""
                    
                    # Combina eventos e io_eventos
                    all_events = eventos
                    if io_eventos:
                        all_events = f"{eventos},{io_eventos}" if eventos else io_eventos
                    
                    linha = f"{task[0]};{task[1]};{task[2]};{task[3]};{task[4]};{all_events}\n"
                    f.write(linha)

            from config_loader import load_config
            config = load_config("sample_config.txt")
            self.simulator = Simulator(config)
            self.simulator.run_debug()
            self.debug_active = True
            self.debug_paused = False
            
            # Inicializa histórico de eventos
            self.debug_history = []
            self.debug_current_index = -1
            
            # Captura o estado inicial (tick 0)
            initial_snap = self.simulator.snapshot()
            self.debug_history.append(initial_snap)
            self.debug_current_index = 0
            
            # Cria/limpa painel de estado se ainda não existir
            if not hasattr(self, 'debug_frame'):
                self.debug_frame = tk.Frame(self.root, bd=2, relief='groove')
                self.debug_frame.grid(row=10, column=0, columnspan=5, sticky='we', pady=5)
                tk.Label(self.debug_frame, text='Estado Debug (snapshot)').grid(row=0, column=0, sticky='w')
                self.debug_text = tk.Text(self.debug_frame, height=12, width=80, font=('Consolas', 9))
                self.debug_text.grid(row=1, column=0, sticky='we')
            else:
                self.debug_text.delete('1.0', tk.END)
            
            # Mostra barra de ferramentas
            self.debug_toolbar.grid()
            self.update_debug_display()

        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def next_tick(self):
        """Avança um tick no modo debug e mostra mensagem ao concluir todas as tarefas."""
        if not hasattr(self, 'simulator'):
            messagebox.showwarning("Aviso", "Inicie a simulação com o botão 'Debug' antes.")
            return
        
        if self.debug_paused:
            messagebox.showinfo("Pausado", "Debug está pausado. Clique em 'Pausar' novamente para retomar.")
            return

      
        if self.debug_current_index < len(self.debug_history) - 1:
          
            self.debug_current_index += 1
            self.update_debug_display()
        else:
           
            if self.debug_current_index < len(self.debug_history) - 1:
                self._rebuild_simulator_to_tick(self.debug_current_index)
            
       
            tick_result = self.simulator.step()
            
           
            new_snap = self.simulator.snapshot()
            self.debug_history.append(new_snap)
            self.debug_current_index += 1
            
            self.update_debug_display()

            if not tick_result:
                messagebox.showinfo("Fim", "Todas as tarefas foram finalizadas.")
                self.exit_debug()
    
    def _rebuild_simulator_to_tick(self, target_tick):
        """Reconstrói o simulador até um tick específico."""
        from config_loader import load_config
        
        config = load_config("sample_config.txt")
        self.simulator = Simulator(config)
        self.simulator.run_debug()
        
       
        for _ in range(target_tick):
            self.simulator.step()

    def prev_tick(self):
        """Volta um tick no modo debug usando o histórico."""
        if not hasattr(self, 'simulator'):
            return
        
        if self.debug_current_index > 0:
            self.debug_current_index -= 1
            self.update_debug_display()

    def update_debug_display(self):
        """Atualiza a exibição com o snapshot atual do histórico."""
        if self.debug_current_index < 0 or self.debug_current_index >= len(self.debug_history):
            return
        
        snap = self.debug_history[self.debug_current_index]
  
       
        self.update_debug_snapshot_from_data(snap)
        
        self.update_debug_gantt_from_data(snap)
     
        self.update_debug_progress_from_data(snap)
        
       
        self.prev_tick_btn.config(state=tk.NORMAL if self.debug_current_index > 0 else tk.DISABLED)
        self.next_tick_btn.config(state=tk.NORMAL if self.debug_current_index < len(self.debug_history) - 1 else tk.NORMAL)

    def pause_debug(self):
        """Pausa ou retoma o modo debug."""
        if not hasattr(self, 'simulator'):
            return
        
        self.debug_paused = not self.debug_paused
        if self.debug_paused:
            self.pause_debug_btn.config(text='▶ Retomar', bg='#4CAF50')
        else:
            self.pause_debug_btn.config(text='⏸ Pausar', bg='#FF9800')

    def restart_debug(self):
        """Reinicia o debug do zero."""
        if not hasattr(self, 'simulator'):
            return
        
        if messagebox.askyesno("Confirmar", "Deseja reiniciar o debug? Perderá o progresso atual."):
            self.debug_active = False
            self.debug_paused = False
            self.debug_toolbar.grid_remove()
            self.start_debug()

    def exit_debug(self):
        """Sai do modo debug e oculta a barra de ferramentas."""
        self.debug_active = False
        self.debug_paused = False
        self.debug_toolbar.grid_remove()
        self.pause_debug_btn.config(text='⏸ Pausar', bg='#FF9800')
        if hasattr(self, 'debug_frame'):
            self.debug_text.delete('1.0', tk.END)
            self.debug_text.insert(tk.END, 'Debug finalizado.')
    
    def update_debug_snapshot_from_data(self, snap):
        """Renderiza snapshot usando dados do histórico."""
        if not hasattr(self, 'debug_text'):
            return
        
        lines = []
        lines.append(f"Tick atual: {snap['time']}")
        lines.append(f"Algoritmo: {snap['algorithm']} | Quantum: {snap['quantum']}")
        lines.append(f"Rodando: {snap['running'] or 'IDLE'}")
        lines.append(f"Fila de Prontos: {', '.join(snap['ready_queue']) if snap['ready_queue'] else '(vazia)'}")
        lines.append("\nTarefas:")
        header = f"{'ID':<4} {'Arr':>3} {'Dur':>3} {'Rem':>3} {'Prio':>4} {'Dyn':>4} {'Exec':>4} {'Waits':>5} {'W?':>3} {'Done':>4} {'Bloq':>4} {'IO':>5}"
        lines.append(header)
        lines.append('-' * len(header))
        for t in snap['tasks']:
            blocked_str = f"M{t['blocking_mutex_id']}" if t['blocked'] else 'N'
            io_str = f"{t['io_remaining']}t" if t['io_blocked'] else 'N'
            dyn_prio = t.get('dynamic_priority', t['priority'])
            lines.append(f"{t['id']:<4} {t['arrival']:>3} {t['duration']:>3} {t['remaining']:>3} {t['priority']:>4} {dyn_prio:>4} {t['executed_ticks']:>4} {t['waited_ticks']:>5} {'Y' if t['waiting_now'] else 'N':>3} {'Y' if t['completed'] else 'N':>4} {blocked_str:>4} {io_str:>5}")
        
        # Adiciona eventos de cada tarefa
        lines.append("\nEventos de Tarefas:")
        has_events = False
        if hasattr(self, 'simulator') and hasattr(self.simulator, 'tasks'):
            for sim_task in self.simulator.tasks:
                events_parts = []
                
                # Mutex events
                if sim_task.events:
                    has_events = True
                    eventos_str = ", ".join([f"{e['type'][:1].upper()}{e['mutex_id']}:{e['time']}" for e in sim_task.events])
                    events_parts.append(eventos_str)
                
                # IO events
                if sim_task.io_events:
                    has_events = True
                    io_str = ", ".join([f"IO{e['time']}-{e['duration']}" for e in sim_task.io_events])
                    events_parts.append(io_str)
                
                if events_parts:
                    lines.append(f"  {sim_task.id}: {' | '.join(events_parts)}")
        
        if not has_events:
            lines.append("  (nenhum evento)")
        
        # Adiciona estado dos mutexes se disponível
        if snap.get('mutexes'):
            lines.append("\nMutexes:")
            for mutex_state in snap['mutexes']:
                mutex_id = mutex_state['id']
                locked = "Bloqueado" if mutex_state['locked'] else "Livre"
                owner = f"Proprietário: {mutex_state['owner']}" if mutex_state['owner'] else "Proprietário: Nenhum"
                waiting = f"Aguardando: {', '.join(mutex_state['waiting'])}" if mutex_state['waiting'] else "Aguardando: Nenhum"
                lines.append(f"  M{mutex_id}: {locked} | {owner} | {waiting}")
        
        lines.append("\nTimeline (últimos 30 ticks):")
        last30 = snap['timeline'][-30:]
        lines.append(' '.join([str(x) if x is not None else '-' for x in last30]))
        self.debug_text.delete('1.0', tk.END)
        self.debug_text.insert(tk.END, '\n'.join(lines))

    def update_debug_gantt_from_data(self, snap):
        """Atualiza Gantt usando snapshot do histórico."""
        if not hasattr(self, 'simulator'):
            return
        
        # Cria um objeto temporário com os dados do snapshot
        class TempSimulator:
            pass
        
        temp = TempSimulator()
        temp.timeline = snap['timeline']
        # Pega arrivals_map e finish_map do simulador real, não do snapshot
        temp.arrivals_map = self.simulator.arrivals_map
        temp.finish_map = self.simulator.finish_map
        temp.wait_map = self.simulator.wait_map
        temp.suspended_map = self.simulator.suspended_map
        temp.task_colors = getattr(self.simulator, 'task_colors', {})
        
        self.render_gantt_in_frame(temp)

    def update_debug_progress_from_data(self, snap):
        """Atualiza progresso usando dados do snapshot."""
        if not hasattr(self, 'debug_progress_label'):
            return
        
        time = snap['time']
        running = snap['running'] or 'IDLE'
        completed = sum(1 for t in snap['tasks'] if t['completed'])
        total = len(snap['tasks'])
        
        status = "PAUSADO" if self.debug_paused else "EXECUTANDO"
        progress_text = f"Tick: {time} | Rodando: {running} | Tarefas: {completed}/{total} | {status}"
        self.debug_progress_label.config(text=progress_text)

    def update_debug_snapshot(self):
        """Renderiza snapshot detalhado do simulador no painel de debug."""
        if not hasattr(self, 'simulator') or not hasattr(self, 'debug_text'):
            return
        snap = self.simulator.snapshot()
        self.update_debug_snapshot_from_data(snap)

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
        
        
        fig = Figure(figsize=(10, 3), dpi=100)
        ax = fig.add_subplot(111)
      
        timeline = simulator.timeline
        arrivals = simulator.arrivals_map
        finishes = simulator.finish_map
        wait_map = simulator.wait_map
        suspended_map = simulator.suspended_map 
        task_colors = simulator.task_colors
        
       
        total_time = len(timeline)
     
        task_ids = set()
        for t in timeline:
            if t is not None and t != 'IDLE':
                # Remove qualquer sufixo depois do ID (como "L" de sorteio)
                base_id = ''.join(c for c in str(t) if c.isalnum() or c == 'T')
                # Limpa para pegar só a parte T#
                import re
                match = re.match(r'(T\d+)', str(t))
                if match:
                    task_ids.add(match.group(1))
        tasks = sorted(task_ids)
        
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
                    # Remove o sufixo "L" (sorteio) para comparar IDs base
                    cur_base = str(cur).rstrip('L') if cur else None
                    if cur_base == task:
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
                
                # Desenhar blocos de espera (branco)
                for st, dur in wait_intervals:
                    if dur > 0:
                        ax.broken_barh([(st, dur)], (y_pos, 0.8),
                                      facecolors="white", edgecolors="black", linewidth=0.8)
                
                # Desenhar blocos de suspensão (cinza claro) - IO/mutex
                suspended_ticks = set()
                if suspended_map and task in suspended_map:
                    suspended_ticks.update(suspended_map[task])
                
                suspend_intervals = []
                ss = None
                for t in range(start_time, end_time):
                    if t in suspended_ticks and t not in exec_ticks:
                        if ss is None:
                            ss = t
                    else:
                        if ss is not None:
                            suspend_intervals.append((ss, t - ss))
                            ss = None
                if ss is not None:
                    suspend_intervals.append((ss, end_time - ss))
                
                for st, dur in suspend_intervals:
                    if dur > 0:
                        ax.broken_barh([(st, dur)], (y_pos, 0.8),
                                      facecolors="#D3D3D3", edgecolors="black", linewidth=0.8)  # cinza claro
                        # Add duration label
                        mid_x = st + dur / 2
                        ax.text(mid_x, y_pos + 0.4, f"{dur}", ha='center', va='center',
                               fontsize=8, weight='bold', color='black')
            
            ax.set_xlabel("Tempo (t)")
            ax.set_ylabel("Tarefas")
            ax.set_yticks(range(len(tasks)))
            ax.set_yticklabels(tasks)
            ax.set_xticks(range(total_time + 1))
            ax.grid(True, axis='x', linestyle=':', alpha=0.5)
        
        ax.set_title("Gráfico de Gantt")
        fig.tight_layout()
        
        # Salvar como PNG
        png_filename = "gantt.png"
        fig.savefig(png_filename, format="png", dpi=300, bbox_inches='tight')
        print(f"Gráfico salvo em: {png_filename}")
        
        # Embutir no frame
        canvas = FigureCanvasTkAgg(fig, master=self.gantt_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)


if __name__ == "__main__":
    root = tk.Tk()
    app = TaskEditorApp(root)
    root.mainloop()
