from config_loader import load_config
from simulator import Simulator

def main():
    config_file = "sample_config.txt"
    config = load_config(config_file)

    simulator = Simulator(config)
    simulator.run()

if __name__ == "__main__":
    main()
