# Prima esecuzione completa con Ollama

L'11 settembre 2026 la pipeline CAMEL ha completato il caso statico Log4j con
inferenza locale reale. La CLI ha restituito codice 0 e `ArtifactSession.assert_complete`
ha verificato gli otto artefatti. I backend di dominio sono rimasti i mock originali.

## Configurazione e riproduzione

- Ollama: `tesi-qwen3:4b`, creato dal `Modelfile` del repository con
  `qwen3:4b-instruct`, contesto 16.384 token e temperatura HTTP esplicita 0.
- Endpoint: `http://localhost:11434/v1`, credenziale fittizia `local`.
- CAMEL 0.2.90, modalità `pipeline`, quattro agenti e DAG esistente.
- Due tentativi totali per task: al massimo un recupero gestito da CAMEL.
- Input: `thesis_agents/data/log4j_case.json`.

Con Ollama avviato e il modello installato:

```bash
ollama create tesi-qwen3:4b -f Modelfile
LLM_MODEL=tesi-qwen3:4b LLM_API_KEY=local \
LLM_BASE_URL=http://localhost:11434/v1 LLM_TEMPERATURE=0 \
LLM_TIMEOUT_SECONDS=300 .venv/bin/python main.py --mode camel --workflow pipeline
```

## Esito osservato

| Strategia | Score del mock |
|---|---:|
| S_UPGRADE | 0.9 |
| S_BLOCK | 0.8 |
| S_ISOLATE | 0.725 |
| S_MONITOR | 0.675 |

Il mock semantico ha accettato `S_UPGRADE`; `FinalDecision.status` è `selected`.
Non è stata eseguita alcuna modifica all'infrastruttura.

Il primo tentativo dello Strategic si è fermato dopo la validazione. Il gestore
del risultato ha respinto il falso successo perché mancavano `final_decision`
e `provenance`. CAMEL ha ripetuto il task; il modello ha riletto `get_context`,
richiamato la validazione idempotente e invocato realmente `publish_final_decision`
e `record_provenance`. Nessun output è stato scritto manualmente per completare
la prova.

Le richieste registrate allo Strategic contengono separatamente `RuntimeEvidence`,
`VulnerabilityReport` e `CandidateStrategies`, con i rispettivi produttori. I loro
contenuti coincidono con i file pubblicati. Sono stati ricontrollati gli otto
schemi Pydantic e tutti gli otto hash riportati nel registro di provenienza.

Sono state registrate 26 richieste LLM, incluse quelle gestionali. L'intervallo
tra prima richiesta e ultima risposta è di circa 128 secondi. Sono misure di
questa singola esecuzione, senza caricamento iniziale o download del modello.

Nella workspace, il run è conservato in `output/ollama-qwen3-retry-20260911/`:
input, otto artefatti, `run.log`, `run_summary.json` e conversazioni SDK in `llm/`.
La directory `output/` è esclusa da Git: i file della prova non vengono distribuiti
con il repository. I log di inferenza sono distinti dal mock di provenienza.

## Limiti e verifiche successive

Questa prova dimostra il funzionamento completo del percorso agenti–tool–artefatti
sul caso statico, con recupero di un fallimento. Non dimostra affidabilità generale
né correttezza semantica di ogni frase generata.

La spiegazione finale cita, ad esempio, una versione target `2.17.0+` che non
proviene dal lookup mock. Tale indicazione non è verificata e non va usata come
raccomandazione operativa. I campi narrativi restano da valutare e vincolare alle
fonti; Pydantic e i controlli attuali tutelano struttura, fatti critici e coerenza
fra artefatti, ma non provano la veridicità di tutto il testo. Gli score dipendono
dalle stime di beneficio e impatto generate dal modello e dalla formula del mock.

La suite automatica conta 51 test passati. Include il rifiuto del falso successo,
la consegna dei tre input allo Strategic e un recupero attraverso la Workforce
reale con inferenza programmata, verificando che i file precedenti restino identici.
I test automatici non sostituiscono la prova live qui descritta.

Prima di integrare altri backend, ripetere le prove su casi con prerequisiti
mancanti, lookup non supportato e contromisure vietate, misurando completamenti,
retry ed errori nei contenuti generati.
