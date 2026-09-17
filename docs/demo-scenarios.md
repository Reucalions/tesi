# Quattro scenari per la demo

Gli input `thesis_agents/data/demo_*.json` usano il contratto `StaticTelemetry`
esistente. Non cambiano agenti, DAG, tool o backend. Il caso predefinito
`log4j_case.json` resta disponibile; il primo scenario ne riprende i dati.

## Casi e risultati attesi

| Input | Variazione rispetto al nominale | Esito con `--mode fixtures` |
|---|---|---|
| `demo_01_nominal.json` | Nessuna: tutte le capacità disponibili, nessun divieto | `selected`, `S_UPGRADE` |
| `demo_02_no_maintenance.json` | Manca soltanto `maintenance_window` | Upgrade primo nel ranking ma rifiutato; `selected`, `S_ISOLATE` |
| `demo_03_all_actions_prohibited.json` | Capacità presenti, tutte le quattro categorie di azione vietate | Quattro rifiuti per policy; `no_valid_strategy` |
| `demo_04_unsupported_lookup.json` | Pacchetto sintetico `demo-unsupported-package`, versione `0.0.0` | Lookup `unsupported`, candidate e ranking vuoti; `insufficient_evidence` |

Il terzo caso isola il vincolo di policy: i rifiuti non dipendono da capacità
mancanti. Il quarto usa un nome sintetico per mostrare la mancata copertura del
mock, senza suggerire che una versione reale sia sicura o vulnerabile.

## Verifica senza LLM

Il 14 settembre 2026 tutti e quattro i casi sono stati eseguiti in modalità
`fixtures`, ottenendo gli esiti della tabella. I risultati sono disponibili nella
workspace in `output/demo-fixtures/<nome-scenario>/`. La suite completa ha
superato 55 test e i controlli Ruff sono passati. Non sono state eseguite nuove
inferenze Ollama in questa fase.

Dalla radice del repository:

```bash
for scenario in thesis_agents/data/demo_*.json; do
  case_name=${scenario##*/}
  case_name=${case_name%.json}
  .venv/bin/python main.py --mode fixtures --input "$scenario" \
    --output "output/demo-fixtures/$case_name" || break
done
```

Ogni cartella contiene la copia dell'input e gli otto artefatti validati. Le
directory di destinazione devono essere assenti o vuote. Per ripetere la prova,
scegli un nuovo prefisso, per esempio `output/demo-fixtures-02`, preservando i
risultati precedenti. Questa esecuzione non avvia agenti CAMEL né inferenza LLM;
la provenienza dichiara `fixtures`.

I test sui quattro file distribuiti si eseguono con:

```bash
.venv/bin/pytest -q tests/test_demo_scenarios.py
```

Verificano gli otto schemi, l'input conservato, le selezioni, l'ordine dei tentativi
e le cause dei rifiuti. La suite completa resta `.venv/bin/pytest -q`.

## Prova successiva con CAMEL e Ollama

Il [runner nel repository](demo-runner.md) esegue la matrice e verifica gli esiti:

```bash
.venv/bin/python -m thesis_agents.demo --mode camel --repetitions 2
```

Le esecuzioni LLM del 14 settembre, inclusi i fallimenti e la correzione del
percorso vuoto, sono documentate nel [resoconto delle prove](ollama-demo-runs.md).
Le successive correzioni dei tool e le esecuzioni complete disponibili per i
quattro scenari sono nel [resoconto dei tool strutturati](structured-tools-runs.md),
con gli ultimi esiti ricontrollati il 16 settembre e i limiti dei testi generati.

Con Ollama avviato e il profilo del modello già creato secondo il README:

```bash
LLM_MODEL=tesi-qwen3:4b LLM_API_KEY=local \
LLM_BASE_URL=http://localhost:11434/v1 LLM_TEMPERATURE=0 \
LLM_TIMEOUT_SECONDS=300 LLM_MAX_TOKENS=2048 .venv/bin/python main.py \
  --mode camel --workflow pipeline \
  --input thesis_agents/data/demo_01_nominal.json
```

Ripetere sostituendo il file di input; la CLI crea una nuova directory per ogni
run. Le variabili esplicite selezionano Ollama locale. Per conservare anche le
conversazioni SDK, usare `CAMEL_MODEL_LOG_ENABLED=true` e un `CAMEL_LOG_DIR`
distinto per ciascuna prova, come descritto nel README.

Con l'LLM, ID, punteggi, prerequisiti e insieme delle candidate possono variare.
Le aspettative esatte della tabella valgono per le fixture; per CAMEL si valuta:

- **Nominale:** selezione della prima candidata accettata secondo il ranking.
  Una mancata selezione nonostante le capacità disponibili richiede l'esame
  delle proposte e dei loro eventuali prerequisiti aggiuntivi.
- **Senza manutenzione:** nessun upgrade può essere accettato. Se il modello
  non lo propone o una candidata precedente è accettata, il run può essere
  coerente senza mostrare un tentativo di upgrade rifiutato. Il fallback è
  dimostrato in modo deterministico dalle fixture.
- **Azioni vietate:** tutte le candidate devono essere rifiutate per policy,
  con decisione `no_valid_strategy`. Un task interrotto è un fallimento di
  esecuzione, non equivale a questa decisione di dominio.
- **Lookup non supportato:** nessuna CVE inventata, candidate e ranking vuoti,
  decisione `insufficient_evidence`. Non significa assenza di vulnerabilità.

Per ciascun run annotare directory, modello, durata, completamento, retry,
decisione e affermazioni non sostenute dalle fonti. Ripetere almeno due volte
ogni caso prima di trarre conclusioni sulla variabilità. La preparazione degli
input e la verifica in modalità fixtures non dimostrano questi esiti con LLM.

## Percorso da mostrare al professore

1. Input, capacità e policy del caso.
2. `runtime_evidence.json` e `vulnerability_report.json`, distinti.
3. `candidate_strategies.json`, quindi grafo e ranking.
4. `semantic_validation.json`: motivi dei rifiuti e primo eventuale successo.
5. `final_decision.json` e collegamenti in `provenance.json`.

Le stime non sono misure empiriche; ranking, validazione e provenienza restano
mock locali. Nessuna contromisura viene eseguita. Dal 16 settembre la spiegazione
autorevole della decisione è [derivata dagli artefatti](artifact-explanations.md),
mentre il commento LLM è conservato separatamente come non verificato.
Le descrizioni e i rationale delle candidate possono ancora contenere
affermazioni non sostenute dalle fonti e richiedono esame critico.

## Pulizia degli output del 14 settembre 2026

Sono state eliminate 17 directory di prove precedenti, probe di telemetria e
schemi rigenerabili: 155 file, circa 1,65 MiB di spazio allocato. È stata
conservata integralmente `output/ollama-qwen3-retry-20260911/`, citata nel
resoconto della prima esecuzione completa; i digest SHA-256 dei suoi 37 file
sono rimasti identici dopo la pulizia. Gli output non sono versionati in Git.
La pulizia riguarda spazio su disco, non la RAM usata dal modello.
