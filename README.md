# Simulador de Algoritmos de Escalonamento

## Finalidade
Este projeto simula o comportamento de diferentes algoritmos de escalonamento de tarefas de um sistema operacional (FIFO, SRTF, PRIORIDADE preemptivo - PRIOP). Ele gera um gráfico de Gantt que mostra intervalos de execução e espera de cada tarefa, permitindo estudar impacto de prioridades, tempo restante e quantum.

## Formato do Arquivo de Configuração
Arquivo texto simples (UTF-8), mínimo 2 linhas.

Linha 1 (parâmetros globais):
```
algoritmo;quantum
```
Linhas seguintes (uma por tarefa):
```
id;cor;ingresso;duracao;prioridade;lista_eventos
```
Observações:
* `algoritmo` pode ser: `FIFO`, `SRTF`, `PRIOP`.
* `quantum` é usado apenas em algoritmos que respeitam quantum (atualmente não usado por SRTF/PRIOP que ignoram quantum).
* `lista_eventos` é uma lista separada por vírgulas (ex: `io:disk,mutex_lock:M1`). Se vazia, deixe o campo final em branco terminando com `;`.
* Campos faltantes recebem valores default (cor=gray, prioridade=1, quantum=3, algoritmo=FIFO).

Exemplo:
```
SRTF;4
T1;red;0;8;2;
T2;blue;1;3;1;io:disk
T3;green;2;2;3;mutex_lock:M1,mutex_unlock:M1
```

## Valores Padrão
Definidos em `config_loader.py` (dicionário `DEFAULTS`):
```
algorithm = FIFO
quantum   = 3
color     = gray
priority  = 1
events    = []
```
Se o arquivo não existir, um template é gerado automaticamente.

## Modos de Execução
### Linha de Comando
`main.py` aceita parâmetros posicionais e flags:
```
python main.py [ALGORITMO] [ARQUIVO_CONFIG] [QUANTUM]
```
Flags:
```
--gen-template      Gera arquivo de configuração padrão (se não existir) e sai
--tasks N           Número de tarefas ao gerar template (default 5)
```
Sobrescrevendo apenas algoritmo:
```
python main.py SRTF
```
Sobrescrevendo algoritmo + quantum + arquivo:
```
python main.py PRIOP meu_config.txt 5
```
Gerando template:
```
python main.py --gen-template --tasks 7
```

### Modo Debug / Inspeção de Estado
O modo debug permite avançar a simulação tick a tick e inspecionar o estado completo de cada tarefa.

Atualmente há duas formas de usar o debug:

1. Pela interface gráfica (recomendado):
	 - Execute `python interface.py`.
	 - Configure algoritmo e quantum.
	 - Insira tarefas ou carregue `sample_config.txt`.
	 - Clique em `Debug` para iniciar o modo passo-a-passo.
	 - Use `Próximo Tick` para avançar. A janela inferior mostra:
		 * Tick atual
		 * Tarefa em execução
		 * Fila de prontos
		 * Tabela por tarefa (arrival, duração, restante, prioridade, ticks executados, total de espera, se está esperando agora, se completou)
		 * Recorte dos últimos ticks da timeline

2. Via código (programaticamente):
	 ```python
	 from config_loader import load_config
	 from simulator import Simulator

	 cfg = load_config('sample_config.txt')
	 sim = Simulator(cfg)
	 sim.run_debug()  # prepara estado para debug
	 while sim.step():
			 snap = sim.snapshot()  # dicionário com todo o estado
			 # opcional: imprimir ou analisar snap
	 ```

Em modo debug, cada chamada a `step()`:
* Processa chegadas, escalonamento e um tick de execução.
* Permite coletar métricas incrementais.

Campos do snapshot retornado:
```json
{
	"time": <int>,
	"running": <id ou null>,
	"ready_queue": [<ids>],
	"tasks": [
		{"id": "T1", "arrival": 0, "duration": 5, "remaining": 2,
		 "priority": 3, "completed": false, "executed_ticks": 3,
		 "waited_ticks": 1, "waiting_now": false}
	],
	"wait_map": {"T1": [1,4]},
	"timeline": ["T1","T1","T2",null,...],
	"algorithm": "fifo_scheduler",
	"quantum": 3
}
```

Planejado (futuro): flag `--debug` na CLI para execução interativa sem GUI.

### Interface Gráfica (Tkinter)
Execute:
```
python interface.py
```
Na janela você pode:
1. Selecionar algoritmo e quantum.
2. Inserir tarefas (cores pré-definidas, ingresso, duração, prioridade).
3. Carregar arquivo existente (`sample_config.txt`).
4. Salvar em arquivo.
5. Executar simulação (gera gráfico de Gantt).
6. Usar modo Debug: avançar tick a tick.

## Alteração de Parâmetros
* Alterando diretamente o arquivo de configuração antes da execução.
* Via CLI passando novos valores (sobrepõe os do arquivo).
* Via interface gráfica ajustando campos e salvando.
* Para adicionar eventos: editar coluna `lista_eventos` com eventos separados por vírgula (a lógica interna ainda não bloqueia tarefas, mas já registra para futura expansão).

## Saída
* Terminal: mostra progresso e ticks, algoritmo usado e tarefas concluídas.
* Arquivo de imagem `gantt.png`: execução (blocos coloridos) e espera (blocos brancos contornados).

## Estrutura Principal
| Arquivo | Função |
|---------|--------|
| `main.py` | Entrada CLI / overrides |
| `config_loader.py` | Parser + defaults + geração de template |
| `scheduler.py` | Funções dos algoritmos + regras de preempção |
| `simulator.py` | Loop de simulação, registro de espera e execução |
| `gantt_renderer.py` | Renderização terminal e imagem do Gantt |
| `interface.py` | Interface Tk para criação/execução de tarefas |

## Extensões Futuras
* Suporte a eventos que bloqueiam tarefas (IO, mutex) e cálculo de métricas (turnaround, waiting, response).
* Round-Robin real (RR) usando quantum.
* Exportação de métricas para CSV.

## Licença
Definir conforme necessidade (ex: MIT). Adicionar texto de licença aqui.

## Contribuição
Pull requests e sugestões de novos algoritmos são bem-vindos.
