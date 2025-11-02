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

# 📐 ARQUITETURA DO PROJETO - Simulador de Escalonamento

## 🏗️ DIAGRAMA DE COMPONENTES

```
┌─────────────────────────────────────────────────────────────────────┐
│                         APLICAÇÃO                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────────┐         ┌──────────────────────┐          │
│  │   main.py            │         │   interface.py       │          │
│  │                      │         │  (GUI Tkinter)       │          │
│  │ • Entrada principal  │◄────────┤ • Criar tarefas      │          │
│  │ • Modo CLI/GUI       │         │ • Selecionar algo    │          │
│  │ • Carrega config     │         │ • Visualizar Gantt   │          │
│  └──────────┬───────────┘         └──────────┬───────────┘          │
│             │                                │                       │
│             └────────────┬───────────────────┘                       │
│                          │                                           │
│                          ▼                                           │
│             ┌────────────────────────┐                              │
│             │  config_loader.py      │                              │
│             │                        │                              │
│             │ • parse_task_line()    │                              │
│             │ • load_config()        │                              │
│             │ • generate_default_    │                              │
│             │   config()             │                              │
│             └────────┬───────────────┘                              │
│                      │                                              │
│                      ▼                                              │
│        ┌─────────────────────────┐                                 │
│        │  Config (dict)          │                                 │
│        │ {                       │                                 │
│        │  'algorithm': 'FIFO',   │                                 │
│        │  'quantum': 2,          │                                 │
│        │  'tasks': [...]         │                                 │
│        │ }                       │                                 │
│        └────────────┬────────────┘                                 │
│                     │                                              │
└─────────────────────┼──────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    NÚCLEO DA SIMULAÇÃO                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│            ┌─────────────────────────────────┐                      │
│            │   simulator.py (Simulator)      │                      │
│            │                                  │                      │
│            │  MÉTODOS PRINCIPAIS:            │                      │
│            │  ┌────────────────────────┐     │                      │
│            │  │ run()                  │     │                      │
│            │  │ • Loop principal       │     │                      │
│            │  │ • Chama os 3 passos    │     │                      │
│            │  │ • Gera visualização    │     │                      │
│            │  └────────────────────────┘     │                      │
│            │                                  │                      │
│            │  ┌────────────────────────┐     │                      │
│            │  │ _check_arrivals()      │     │                      │
│            │  │ • Verifica chegadas    │     │                      │
│            │  │ • Adiciona à fila      │     │                      │
│            │  └────────────────────────┘     │                      │
│            │                                  │                      │
│            │  ┌────────────────────────┐     │                      │
│            │  │ _schedule()            │     │                      │
│            │  │ • Escolhe algoritmo    │     │                      │
│            │  │ • Verifica preempção   │     │                      │
│            │  │ • Promove tarefa       │     │                      │
│            │  └────────────────────────┘     │                      │
│            │                                  │                      │
│            │  ┌────────────────────────┐     │                      │
│            │  │ _tick()                │     │                      │
│            │  │ • Executa 1 unidade    │     │                      │
│            │  │ • Registra tempo       │     │                      │
│            │  │ • Verifica término     │     │                      │
│            │  │ • Verifica quantum     │     │                      │
│            │  └────────────────────────┘     │                      │
│            │                                  │                      │
│            └──┬───────────────────────────┬──┘                      │
│               │                           │                         │
│               ▼                           ▼                         │
│        ┌──────────────┐          ┌──────────────────┐              │
│        │ scheduler.py │          │ tcb.py           │              │
│        │              │          │                  │              │
│        │ Algoritmos:  │          │ TaskControlBlock │              │
│        │ ┌──────────┐ │          │                  │              │
│        │ │ FIFO     │ │          │ Atributos:       │              │
│        │ │ (não-pre)│ │          │ • id             │              │
│        │ └──────────┘ │          │ • arrival        │              │
│        │ ┌──────────┐ │          │ • duration       │              │
│        │ │ SRTF     │ │          │ • remaining_time │              │
│        │ │ (pre)    │ │          │ • priority       │              │
│        │ └──────────┘ │          │ • completed      │              │
│        │ ┌──────────┐ │          │ • executed_ticks │              │
│        │ │ PRIOP    │ │          │ • executed_count │              │
│        │ │ (pre)    │ │          │ • color          │              │
│        │ └──────────┘ │          │                  │              │
│        └──────────────┘          └──────────────────┘              │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                      │
                      │ Dados coletados:
                      │ • timeline
                      │ • wait_map
                      │ • arrivals_map
                      │ • finish_map
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  VISUALIZAÇÃO & SAÍDA                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────────┐       ┌──────────────────────┐            │
│  │ gantt_renderer.py    │       │ interface.py         │            │
│  │                      │       │ (Matplotlib)         │            │
│  │ • Terminal output    │       │ • PNG file           │            │
│  │ • PNG Gantt chart    │       │ • Live visualization │            │
│  │ • Live matplotlib    │       │ • Interativo         │            │
│  └──────────────────────┘       └──────────────────────┘            │
│           │                              │                          │
│           └──────────────┬───────────────┘                          │
│                          │                                          │
│                          ▼                                          │
│         ┌─────────────────────────────┐                            │
│         │  Gráfico de Gantt (PNG)     │                            │
│         │  Com tempo x tarefas        │                            │
│         │  • Execução (colored)       │                            │
│         │  • Espera (white)           │                            │
│         └─────────────────────────────┘                            │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 FLUXO DE EXECUÇÃO (Loop Principal)

```
┌─────────────────────────────────┐
│   main.py / interface.py        │
│   Inicializa Simulator          │
└────────────────┬────────────────┘
                 │
                 ▼
    ┌────────────────────────┐
    │  simulator.run()       │
    │                        │
    │  time = 0              │
    └────────────┬───────────┘
                 │
                 ▼
    ┌────────────────────────────────────┐
    │  while NOT all_tasks_completed:    │
    │                                    │
    │  ┌──────────────────────────────┐  │
    │  │ 1. _check_arrivals()         │  │
    │  │    Tarefas chegam?           │  │
    │  │    → Adiciona à ready_queue  │  │
    │  └──────────────────────────────┘  │
    │                 │                  │
    │                 ▼                  │
    │  ┌──────────────────────────────┐  │
    │  │ 2. _schedule()               │  │
    │  │    Qual tarefa executa?      │  │
    │  │    → Escolhe/Verifica preempt│  │
    │  │    → Define running_task     │  │
    │  └──────────────────────────────┘  │
    │                 │                  │
    │                 ▼                  │
    │  ┌──────────────────────────────┐  │
    │  │ 3. _tick()                   │  │
    │  │    Executa 1 unidade         │  │
    │  │    → Reduz remaining_time    │  │
    │  │    → Incrementa executed_count	 |	
    │  │    → Registra timeline       │  │
    │  │    → Verifica término        │  │
    │  │    → Verifica quantum        │  │
    │  └──────────────────────────────┘  │
    │                 │                  │
    │                 ▼                  │
    │           time += 1                │
    │                 │                  │
    │                 └──────────────┐   │
    │                                │   │
    └────────────────────────────────┼───┘
                                     │
                    ┌────────────────┘
                    │
                    ▼
        ┌─────────────────────────────────┐
        │  Gera visualização              │
        │  • render_gantt_terminal()      │
        │  • render_gantt_image()         │
        └─────────────────────────────────┘
```

---

## 📋 ESTRUTURA DE DADOS - Timeline & Maps

```
TIMELINE (lista simples):
┌───────────────────────────────────────────────┐
│ ['T1', 'T1', 'T2', 'T2', 'T3', 'T3', 'T1']    │
│  t=0   t=1   t=2   t=3   t=4   t=5   t=6      │
│                                               │
│ Cada índice = 1 tick                          │
│ Cada valor = qual tarefa executou neste tick  │
└───────────────────────────────────────────────┘

WAIT_MAP (dict de listas):
┌────────────────────────────────────────┐
│ {                                      │
│   'T1': [1, 2, 5, 6],                  │
│          ↓  ↓  ↓  ↓                    │
│   Esperou nos ticks: 1, 2, 5, 6        │
│                                        │
│   'T2': [0, 1, 4, 5, 6],               │
│   'T3': [0, 1, 2, 3],                  │
│ }                                      │
└────────────────────────────────────────┘

ARRIVALS_MAP (dict):
┌──────────────────────────┐
│ {                        │
│   'T1': 0  (chegou t=0)  │
│   'T2': 0  (chegou t=0)  │
│   'T3': 1  (chegou t=1)  │
│   'T4': 3  (chegou t=3)  │
│   'T5': 5  (chegou t=5)  │
│ }                        │
└──────────────────────────┘

FINISH_MAP (dict):
┌──────────────────────────┐
│ {                        │
│   'T1': 14 (terminou t=14)
│   'T2': 4  (terminou t=4) │
│   'T3': 6  (terminou t=6) │
│   'T4': 8  (terminou t=8) │
│   'T5': 17 (terminou t=17)
│ }                        │
└──────────────────────────┘
```

---

## 🎯 DECISÕES DE ALGORITMO

```
┌─────────────────────────────────────────────────────────────┐
│ scheduler.py - Decisão por Algoritmo                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  FIFO (First In First Out)                                 │
│  ├─ Non-preemptive                                         │
│  ├─ Sem should_preempt                                    │
│  └─ Tarefa executa até terminar                           │
│                                                              │
│  SRTF (Shortest Remaining Time First)                     │
│  ├─ Preemptive                                             │
│  ├─ should_preempt: candidate.remaining < current.remaining
│  ├─ Com quantum (executa max 2 ticks)                    │
│  └─ Se nova tarefa é mais curta → preempta              │
│                                                              │
│  PRIOP (Priority Preemptive)                              │
│  ├─ Preemptive                                             │
│  ├─ should_preempt: candidate.priority > current.priority │
│  ├─ Com quantum (executa max 2 ticks)                    │
│  └─ Se nova tarefa tem prioridade maior → preempta       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 💾 ARQUIVOS DO PROJETO

```
algoritmo-escalonamento/
│
├── 📄 main.py                    ← Entrada CLI
├── 📄 interface.py               ← GUI Tkinter
├── 📄 simulator.py               ← Motor de simulação
├── 📄 scheduler.py               ← 3 algoritmos
├── 📄 tcb.py                     ← TaskControlBlock
├── 📄 config_loader.py           ← Parser de config
├── 📄 gantt_renderer.py          ← Visualização
│
├── 📝 sample_config.txt          ← Config exemplo
├── 📝 README.md
├── 📝 requirements.txt            ← matplotlib

```

---

## 🔗 DEPENDÊNCIAS ENTRE MÓDULOS

```
main.py
  ├─→ config_loader.py
  │     └─→ Retorna dict config
  │
  ├─→ simulator.py
  │     ├─→ tcb.py (importa TaskControlBlock)
  │     ├─→ scheduler.py (importa get_scheduler)
  │     └─→ gantt_renderer.py
  │           └─→ matplotlib
  │
  └─→ interface.py (Tkinter)
        ├─→ simulator.py
        ├─→ config_loader.py
        └─→ gantt_renderer.py
```

---

## 🎬 EXEMPLO DE EXECUÇÃO COMPLETA

```
ENTRADA (sample_config.txt):
┌──────────────────────┐
│ FIFO;2               │
│ T1;red;0;5;2;       │
│ T2;blue;0;2;3;      │
│ T3;green;1;4;1;     │
│ T4;orange;3;1;4;    │
│ T5;purple;5;2;5;    │
└──────────────────────┘
       │
       ▼
┌──────────────────────┐
│ config_loader.py    │
│ parse + load_config │
└──────────────────────┘
       │
       ▼
┌──────────────────────────────────┐
│ config = {                       │
│   'algorithm': 'FIFO',           │
│   'quantum': 2,                  │
│   'tasks': [                     │
│     {id_:'T1', arrival:0, ...}, │
│     ...                          │
│   ]                              │
│ }                                │
└──────────────────────────────────┘
       │
       ▼
┌──────────────────────┐
│ Simulator(config)    │
│ .run()               │
└──────────────────────┘
       │
       ├─→ _check_arrivals()
       ├─→ _schedule()
       ├─→ _tick()
       └─→ (repeats 14+ ticks)
       │
       ▼
┌──────────────────────────────────────┐
│ SAÍDA (Terminal + PNG):              │
│                                      │
│ Gráfico de Gantt (execução vs espera)│
│                                      │
│ T5 ├─────┤  ██  ├───┤  ██  ├─────┤  │
│ T4 ├────┤  █   ├─────────────────┤  │
│ T3 ├─┤ ██ ├────┤  ██  ├─────────┤  │
│ T2 ├┤ ██ ├────────────────────────┤  │
│ T1 ├██   ├──┤ ██ ├───┤ ██ ├─────┤  │
│    0 1 2 3 4 5 6 7 8 9 10 11 12 13  │
│                                      │
│ ██ = Execução (colored)             │
│ ├──┤ = Espera (white)               │
└──────────────────────────────────────┘
```

---

## 📊 SNAPSHOT (Estado em um Tick)

```python
snapshot = {
    'time': 5,
    'running': 'T3',
    'ready_queue': ['T1', 'T4'],
    'tasks': [
        {
            'id': 'T1',
            'arrival': 0,
            'duration': 5,
            'remaining': 2,        # Faltam 2 ticks
            'priority': 2,
            'completed': False,
            'executed_ticks': 3,   # Já executou 3
            'waited_ticks': 2,     # Esperou em 2 ticks
            'waiting_now': True    # Esperando AGORA
        },
        ...
    ],
    'timeline': ['T1', 'T1', 'T2', 'T2', 'T3', 'T3'],
    'algorithm': 'fifo_scheduler',
    'quantum': 2
}
```

---

## 🎓 RESUMO VISUAL: DESDE ENTRADA ATÉ SAÍDA

```
┌─────────────────────────────────────────────────────────────────┐
│                        ENTRADA                                  │
│              (sample_config.txt ou Interface)                   │
└───────────────────┬────────────────────────────────────────────┘
                    │
                    ▼
        ┌───────────────────────────┐
        │   config_loader.py        │
        │   Parse configuração      │
        │   Cria TaskControlBlocks  │
        └───────────┬───────────────┘
                    │
                    ▼
        ┌───────────────────────────┐
        │   Simulator.__init__      │
        │   • ready_queue = []      │
        │   • running_task = None   │
        │   • timeline = []         │
        │   • wait_map = {}         │
        └───────────┬───────────────┘
                    │
                    ▼
        ┌───────────────────────────┐
        │   simulator.run()         │
        │   Loop de ticks           │
        │   (vários ciclos)         │
        └───────────┬───────────────┘
                    │
                    ▼
        ┌───────────────────────────┐
        │   Coleta dados:           │
        │   • timeline              │
        │   • wait_map              │
        │   • arrivals_map          │
        │   • finish_map            │
        └───────────┬───────────────┘
                    │
                    ▼
        ┌───────────────────────────┐
        │   gantt_renderer.py       │
        │   Cria PNG + Terminal     │
        └───────────┬───────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                        SAÍDA                                    │
│         • Gráfico Gantt (PNG)                                  │
│         • Terminal output (texto)                              │
│         • Métricas (console)                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## ✨ CARACTERÍSTICAS DO PROJETO

| Característica | Descrição |
|---|---|
| **Algoritmos** | FIFO, SRTF, PRIOP |
| **Quantum** | Configurável (ex: 2 ticks) |
| **Preempção** | SRTF e PRIOP usam |
| **Visualização** | Gantt chart (PNG + terminal) |
| **Interface** | CLI (main.py) + GUI (interface.py) |
| **Arquitetura** | Modular, fácil extensão |
| **Entrada** | Arquivo de config ou GUI |
| **Saída** | Gráfico PNG + prints |



## Extensões Futuras
* Suporte a eventos que bloqueiam tarefas (IO, mutex) e cálculo de métricas (turnaround, waiting, response)..
* Exportação de métricas para CSV.

## Licença
Definir conforme necessidade (ex: MIT). Adicionar texto de licença aqui.

## Contribuição
Pull requests e sugestões de novos algoritmos são bem-vindos.
