# Runner della demo

`python -m thesis_agents.demo` esegue gli scenari distribuiti con il progetto
attraverso la CLI esistente, in processi separati. In modalità `camel` i quattro
agenti mantengono l'orchestrazione CAMEL. Il runner non genera candidate e non
pubblica o completa artefatti di dominio al posto degli agenti.

## Comandi dalla radice del repository

Due prove per ciascuno dei quattro scenari, con Ollama attivo e il modello già installato:

```bash
.venv/bin/python -m thesis_agents.demo --mode camel --repetitions 2
```

Controlli senza LLM né collegamento a Ollama:

```bash
.venv/bin/python -m thesis_agents.demo --mode fixtures --repetitions 1
```

Una prova dei soli scenari selezionati:

```bash
.venv/bin/python -m thesis_agents.demo --mode camel --repetitions 1 \
  --scenarios demo_02_no_maintenance demo_03_all_actions_prohibited
```

| Opzione | Default | Scopo |
|---|---|---|
| `--mode` | `camel` | CAMEL/Ollama oppure `fixtures`, senza LLM |
| `--scenarios` | Tutti e quattro | Uno o più nomi dei casi distribuiti |
| `--repetitions` | `2` | Numero di prove per ogni caso |
| `--model` | `tesi-qwen3:4b` | Nome esatto del modello installato in Ollama locale |
| `--timeout` | `300` | Limite esterno in secondi per ciascun processo |
| `--output` | Cartella con timestamp e ID | Destinazione che non deve già esistere |

Il runner verifica il modello su `http://localhost:11434`, senza scaricarlo o
avviare il servizio. Imposta endpoint locale, chiave convenzionale `local`,
temperatura 0, massimo 2048 token per risposta e timeout del backend di
300 secondi. Queste variabili prevalgono sulla configurazione LLM in `.env`;
le credenziali del file non vengono copiate nel manifest. Il runner è dedicato
alla demo locale e non espone opzioni per provider remoti.

Il timeout esterno è distinto da quello di una singola chiamata al backend.
Le prove sono sequenziali per non far competere i processi sul modello locale.
Il codice di uscita complessivo è 0 soltanto quando tutte le prove previste
sono verificate; altrimenti è 1. Non viene ritentato automaticamente un intero
run fallito; restano i retry dei task già previsti dalla Workforce.

Gli esiti delle esecuzioni del 16 settembre sono nel
[resoconto della matrice](demo-matrix-runs.md).

## Risultati

```text
output/demo-matrix-<timestamp>-<id>/
  manifest.json                 # Configurazione, modello, versioni, hash sorgenti/input
  inputs/                       # Copie degli input usati
  summary.json                  # Stato complessivo e controlli di tutti i run
  summary.md                    # Tabella aggiornata dopo ogni run
  demo_01_nominal-r1/
    command.json                # Argomenti esatti della CLI figlia
    command.txt                 # Stessi argomenti, formattati per lettura
    run.log                     # stdout e stderr del processo
    run_summary.json            # Esito processo, audit e aspettativa scenario
    llm/                        # Richieste/risposte SDK, in modalità CAMEL
    artifacts/                  # Input e otto artefatti, oppure output parziali
  ...
```

Per riprodurre la configurazione usare il comando del runner nel manifest.
`command.txt` registra solo gli argomenti del processo figlio: le variabili
d'ambiente sono impostate dal runner e descritte sopra e nel manifest.

`execution_status` distingue `completed`, `failed`, `timeout`, `interrupted`.
`completed` significa exit code 0 della CLI; `verified` richiede anche audit
ed esito atteso dello scenario. `no_valid_strategy` è una decisione di dominio
e può appartenere a un run riuscito. Un timeout non diventa quella decisione.

Errori ordinari e timeout conservano i file e permettono di provare gli altri
casi; Ctrl-C interrompe la matrice conservando il run parziale. Un arresto
forzato del sistema può lasciare il batch nello stato `running`: i riepiloghi
già salvati restano disponibili e la cartella non viene riutilizzata.

Gli hash dei sorgenti e dei file di configurazione delle dipendenze sono
confrontati durante la matrice: un cambiamento impedisce di proseguire
mescolando revisioni differenti. Il digest del modello Ollama è conservato e
ricontrollato a fine batch. Gli hash identificano i file usati, ma non sostituiscono
una copia del codice o un commit conservato nel repository.

## Controlli

`thesis_agents/demo_audit.py` legge i file senza modificarli e verifica:

- nove schemi Pydantic: input e otto output, segnalando file mancanti o invalidi;
- input conservato, fatti runtime, risultato del lookup mock e CVE delle candidate;
- grafo derivato dalle candidate e ranking ricalcolato dal mock;
- tentativi semantici in ordine, primo accettato e decisione coerente;
- spiegazione ricostruita, fonti risolvibili e commento separato non verificato;
- modalità, produttori, dipendenze della decisione e hash della provenienza locale;
- richieste dei quattro ruoli nei log SDK, consegna dei tre input distinti
  allo Strategic e risposta del tool con la decisione finale.

I messaggi di contesto ricompaiono nella cronologia: il loro conteggio non è
quello delle chiamate. Il riepilogo distingue richieste LLM, tool call e tentativi
di task falliti, deduplicati dai log CAMEL. Non conta ogni errore di singole tool call.

In particolare, `failed_task_attempts` conta le righe SDK `failed (attempt ... )`.
I retry richiesti dal quality check CAMEL sono un percorso distinto e non sono
inclusi in quel campo: vanno letti in `run.log`. Un elenco vuoto non significa
quindi assenza di ogni retry. Nel resoconto della matrice sono riportati anche
questi eventi, separatamente dai controlli deterministici sugli artefatti.

Il caso senza manutenzione deve selezionare un'azione diversa dall'upgrade,
senza imporre l'ordine delle fixture. `fallback_observed` indica se è avvenuto
un rifiuto prima della selezione; il modello può proporre direttamente un'altra
azione. Le aspettative sono nella [guida degli scenari](demo-scenarios.md).

L'audit è specifico dei mock attuali: non certifica la qualità delle strategie,
la verità di ogni frase LLM o l'efficacia delle mitigazioni. Con i backend reali
andrà adattato ai relativi contratti.

## Test

```bash
.venv/bin/python -m pytest -q tests/test_demo_runner.py
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
git diff --check
```

Le regressioni coprono fixture senza rete, protezione delle cartelle,
configurazione locale, timeout reale di un subprocess, interruzione,
prosecuzione dopo un fallimento, sorgenti cambiati, artefatti alterati ma
formalmente validi e confronto di messaggi SDK in formato JSON/repr Python.
