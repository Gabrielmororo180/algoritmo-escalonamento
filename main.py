from config_loader import load_config, generate_default_config, DEFAULTS
from simulator import Simulator
import argparse
import sys
import os

def build_parser():
    p = argparse.ArgumentParser(description="Simulador de escalonamento de tarefas")
    p.add_argument("algorithm", nargs="?", help="Algoritmo (FIFO, SRTF, PRIOP)")
    p.add_argument("config", nargs="?", help="Caminho do arquivo de configuração", default="sample_config.txt")
    p.add_argument("quantum", nargs="?", help="Quantum override (int)")
    p.add_argument("--gen-template", dest="gen_template", action="store_true", help="Gerar arquivo de configuração padrão e sair")
    p.add_argument("--tasks", type=int, default=5, help="Número de tarefas ao gerar template padrão")
    return p

def apply_overrides(cfg, args):
    if args.algorithm:
        cfg["algorithm"] = args.algorithm.upper()
    if args.quantum:
        try:
            cfg["quantum"] = int(args.quantum)
        except ValueError:
            print("Quantum inválido, usando valor do arquivo.")
    return cfg

def main(argv=None):
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
    simulator.run()

if __name__ == "__main__":
    main()
