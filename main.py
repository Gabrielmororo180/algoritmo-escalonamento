"""main.py
==========
Ponto de entrada em modo linha de comando para o simulador.

Responsabilidades:
1. Interpretar argumentos (algoritmo, arquivo de config, quantum, geração de template).
2. Carregar configuração (gerando defaults se não existir).
3. Aplicar overrides sem modificar o arquivo original.
4. Instanciar e rodar o `Simulator`.

Justificativa das escolhas:
- Uso de argparse para documentação automática de parâmetros.
- Overrides posicionais simples mantêm comando curto (ex: `python main.py SRTF config.txt 5`).
- Flag `--gen-template` melhora onboarding gerando arquivo base.
"""

from config_loader import load_config, generate_default_config, DEFAULTS
from simulator import Simulator
import argparse
import sys
import os

def build_parser():
    #Constrói e retorna parser de argumentos.
    p = argparse.ArgumentParser(description="Simulador de escalonamento de tarefas")
    p.add_argument("algorithm", nargs="?", help="Algoritmo (FIFO, SRTF PRIOP)")
    p.add_argument("config", nargs="?", help="Caminho do arquivo de configuração", default="sample_config.txt")
    p.add_argument("quantum", nargs="?", help="Quantum override (int)")
    p.add_argument("--gen-template", dest="gen_template", action="store_true", help="Gerar arquivo de configuração padrão e sair")
    p.add_argument("--tasks", type=int, default=5, help="Número de tarefas ao gerar template padrão")
    return p

def apply_overrides(cfg, args):
    """Aplica parâmetros passados na CLI por cima da configuração carregada.
    Não persiste alterações no arquivo, apenas na instância em memória.
    """
    if args.algorithm:
        cfg["algorithm"] = args.algorithm.upper()
    if args.quantum:
        try:
            cfg["quantum"] = int(args.quantum)
        except ValueError:
            print("Quantum inválido, usando valor do arquivo.")
    return cfg

def main(argv=None):
    #Executa fluxo completo da CLI.
    argv = argv or sys.argv[1:]
    parser = build_parser()
    args = parser.parse_args(argv)

    # Geração de template
    if args.gen_template:
        path = args.config or "sample_config.txt"
        generate_default_config(path, tasks=args.tasks)
        print(f"Template gerado em {path}")
        return

    config_path = args.config or "sample_config.txt"
    cfg = load_config(config_path)
    cfg = apply_overrides(cfg, args)

    simulator = Simulator(cfg)
    simulator.run()  # Encapsula toda a simulação e geração de saída

if __name__ == "__main__":
    main()
