def render_gantt_terminal(timeline):
    print("\nGráfico de Gantt (terminal):\n")
    header = ""
    values = ""
    for tick, task_id in enumerate(timeline):
        header += f"{task_id[:3]:^5}"
        values += f"{tick:^5}"
    print(header)
    print(values)


def render_gantt_image(timeline, filename="gantt.png"):
    import tkinter as tk

    cell_width = 40
    cell_height = 40
    width = len(timeline) * cell_width
    height = cell_height + 40

    root = tk.Tk()
    root.title("Gráfico de Gantt")
    canvas = tk.Canvas(root, width=width, height=height, bg="white")
    canvas.pack()

    # Paleta para cores diferentes se não quiser usar as reais
    palette = ["red", "blue", "green", "orange", "purple", "cyan", "yellow", "gray"]
    colors = {}

    for i, task_id in enumerate(timeline):
        color = "lightgray"
        if task_id != "IDLE":
            if task_id not in colors:
                colors[task_id] = palette[len(colors) % len(palette)]
            color = colors[task_id]

        x0 = i * cell_width
        y0 = 0
        x1 = x0 + cell_width
        y1 = y0 + cell_height
        canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline="black")
        canvas.create_text((x0 + x1) // 2, (y0 + y1) // 2, text=task_id[:2], font=("Arial", 10, "bold"))
        canvas.create_text(x0, y1 +20, text=str(i), font=("Arial", 8))


    # Atualiza a interface antes de salvar
    canvas.update()

    # Exporta como .ps
    ps_file = "gantt_output.eps"
    canvas.postscript(file=ps_file)

    # Converte EPS para PNG (se Pillow estiver disponível)
    try:
        from PIL import Image
        img = Image.open(ps_file)
        img.save(filename, "PNG")
        print(f"\nImagem salva como {filename}")
    except ImportError:
        print(f"\n[INFO] Pillow não instalado. EPS salvo como: {ps_file}")
        print("Para PNG, instale com: pip install Pillow")

    # Mantém a janela aberta até fechar manualmente
    root.mainloop()
