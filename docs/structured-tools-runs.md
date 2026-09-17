# Pubblicazioni strutturate e prerequisiti — 15 settembre 2026

Il problema osservato il 14 settembre riguardava anche la serializzazione:
il TelemetryAgent doveva generare una stringa JSON all'interno degli argomenti
JSON della chiamata tool. Payload incompleti o con escape errati impedivano
la pubblicazione. Il limite di token conteneva la generazione ma non risolveva
la validità degli argomenti.

## Modifiche

`PublicationTools` espone a CAMEL tre parametri Pydantic:
`payload: RuntimeEvidence`, `payload: VulnerabilityReport` e
`payload: CandidateStrategies`. Gli argomenti della chiamata contengono ora
un oggetto JSON. L'adapter valida e serializza l'oggetto per i metodi esistenti
di `ArtifactSession`; i controlli su fatti, CVE, produttori e immutabilità restano
quelli della sessione. Le fixture conservano la loro API e gli stessi risultati.

`ArtifactWorkforce` estende lo scheduler CAMEL limitatamente al comportamento
dopo un fallimento definitivo in pipeline. I discendenti del produttore fallito
vengono bloccati prima di essere inviati ai worker. Il primo fallimento lascia
disponibile il retry CAMEL; un ramo indipendente non viene bloccato. I task
bloccati hanno stato SDK `FAILED` e un motivo esplicito nei log e nel riepilogo.

Il gestore del worker verifica inoltre i modelli di ingresso prima della
chiamata LLM, anche in modalità auto. Questo controllo non pubblica risultati,
non sostituisce il produttore e non modifica la decomposizione automatica CAMEL.
La modalità predefinita resta pipeline con lo stesso DAG e quattro ChatAgent.
Gli hook interni sono verificati sulla versione CAMEL fissata, 0.2.90.

## Verifiche automatiche

Sono passati 74 test, insieme a `ruff check`, `ruff format --check` e
`git diff --check`. Le nuove verifiche includono:

- chiamate FunctionTool sincrone e asincrone con oggetti strutturati;
- rifiuto di stringhe JSON, booleani convertiti in stringhe, campi sconosciuti,
  fatti modificati e report alterati rispetto al lookup;
- conservazione delle pubblicazioni precedenti;
- due tentativi del produttore e nessuna inferenza dei suoi discendenti dopo
  il fallimento, per Telemetry, Vulnerability e Countermeasure;
- conservazione dei task indipendenti e controllo degli input prima del modello
  sia in pipeline sia in auto.

I test di integrazione usano la Workforce reale con risposte del modello
programmate: non misurano la qualità della generazione LLM.

## TelemetryAgent con Ollama reale

Il caso `demo_03_all_actions_prohibited.json` è stato eseguito tre volte sul solo
worker Telemetry, costruito dalla stessa `build_workforce` della CLI. Ogni prova
usa una nuova sessione e attraversa `_process_task` del worker CAMEL. Non sono
state pubblicate evidenze manualmente né utilizzati i dati generati dalle fixture.

Configurazione: `tesi-qwen3:4b`, endpoint locale `http://localhost:11434/v1`,
temperatura 0, limite di risposta 2048 token, timeout del backend 120 secondi,
limite esterno di 180 secondi per prova. I tempi includono il processo Python.

| Prova | Esito | Secondi | Richieste LLM |
|---|---|---:|---:|
| 1 | `DONE`, RuntimeEvidence valido | 24,63 | 3 |
| 2 | `DONE`, RuntimeEvidence valido | 10,24 | 3 |
| 3 | `DONE`, RuntimeEvidence valido | 10,67 | 3 |

Ogni prova ha richiesto `get_context`, poi `publish_runtime_evidence` con
`payload` effettivamente di tipo oggetto, quindi ha concluso il task. Nessun
secondo tentativo di task è stato necessario. Questo è un miglioramento
osservato sul caso problematico, non una misura di affidabilità generale.

I risultati sono in `output/structured-telemetry-20260915T151710Z/`, con
`summary.json`, il riproduttore `probe_script.py` e una directory per prova
contenente artefatti, log e conversazioni SDK. Sono prove isolate: non producono
gli otto artefatti di una pipeline completa.

## Pipeline completa

Una nuova prova per ciascuno dei quattro scenari usa la CLI `--mode camel
--workflow pipeline`, lo stesso modello locale, temperatura 0, massimo 2048
token per risposta e timeout del backend 300 secondi. Un limite esterno di
300 secondi interrompe ciascun processo che non termina. I risultati sono
conservati separatamente in `output/structured-pipeline-20260915T151927Z/`.

Il batch conserva il riproduttore `batch_script.py`, gli input, gli artefatti
pubblicati e le conversazioni LLM. Nessun backend di dominio è stato sostituito:
KG, ranking, validazione e provenienza restano mock locali.

Questa prima matrice ha evidenziato un errore distinto dalla serializzazione:
il VulnerabilityAgent tentava di passare pacchetto/versione a un tool che accetta
soltanto `{}` e legge già `RuntimeEvidence` dalla sessione. I quattro run sono
terminati senza decisione; tutti hanno pubblicato l'evidenza runtime, e l'ultimo
anche il report prima di fallire nel task Vulnerability. I task Countermeasure
e Strategic sono stati bloccati senza inferenze di dominio, come previsto.

| Prima matrice strutturata | Secondi | Richieste LLM | Output validi su 8 |
|---|---:|---:|---:|
| Nominale | 52,25 | 15 | 1 |
| Senza manutenzione | 44,13 | 15 | 1 |
| Azioni vietate | 43,37 | 15 | 1 |
| Lookup non supportato | 56,41 | 13 | 2 |

Il prompt del VulnerabilityAgent e la descrizione di `lookup_vulnerabilities`
sono stati chiariti: chiamata senza argomenti, software/versione ricavati dal
tool attraverso l'evidenza pubblicata. Non si ignorano argomenti errati e non
si accettano identificativi alternativi generati dall'LLM. La matrice successiva
è conservata in `output/structured-pipeline-lookup-20260915T152323Z/`, insieme
agli hash dei sorgenti usati per la prova.

| Dopo il chiarimento del lookup | Esito | Secondi | Richieste LLM |
|---|---|---:|---:|
| Nominale | `selected`, `S_UPGRADE` | 127,25 | 25 |
| Senza manutenzione | `selected`, `S_BLOCK` dopo rifiuto dell'upgrade | 110,40 | 23 |
| Azioni vietate | `no_valid_strategy`, quattro rifiuti per policy | 108,75 | 25 |
| Lookup non supportato | Task Countermeasure fallito, Strategic bloccato | 73,57 | 19 |

Nei tre run completi sono validi tutti gli otto artefatti. Hash di provenienza,
sequenza semantica e consegna dei tre input distinti allo Strategic sono stati
ricontrollati dai file e dai messaggi effettivamente inviati all'LLM. Nel caso
nominale lo Strategic ha richiesto un retry di task; negli altri due non sono
stati necessari retry di task. Le correzioni di singole chiamate tool sono un
conteggio distinto.

L'ultimo scenario ha mostrato un falso successo del CountermeasureAgent: dopo
`get_context` il modello dichiarava pubblicata la lista vuota senza effettuare
la chiamata. Il gestore ha respinto entrambi i tentativi e la Workforce ha
bloccato lo Strategic. Sono rimasti soltanto runtime evidence e report, oltre
all'input. Il prompt del CountermeasureAgent ora indica esplicitamente la
chiamata `publish_candidate_strategies` con `{"payload": {"strategies": []}}`
anche quando il lookup è non supportato; precisa inoltre che assenza di dati
non significa assenza di vulnerabilità.

Due verifiche mirate successive del solo scenario non supportato sono conservate
in `output/structured-empty-publication-20260915T153119Z/`.

## Esito delle ultime prove, verificato il 16 settembre

Le due esecuzioni avviate il 15 settembre si sono entrambe concluse con successo.
Il 16 settembre sono stati ricontrollati gli otto schemi Pydantic, la copia
dell'input, gli hash delle entità di provenienza e i messaggi dei tool consegnati
allo Strategic.

| Prova del lookup non supportato | Esito | Secondi | Richieste LLM |
|---|---|---:|---:|
| 1 | `insufficient_evidence`, 8 artefatti validi | 133,27 | 32 |
| 2 | `insufficient_evidence`, 8 artefatti validi | 119,84 | 30 |

In entrambe, le candidate, il ranking e le validazioni sono vuoti, e la
selezione finale è `null`. Le pubblicazioni dei tre produttori usano realmente
oggetti JSON come `payload`. Lo Strategic riceve runtime evidence, report e
candidate separati, con contenuti uguali ai file pubblicati e produttori corretti.
Non risultano tentativi di task falliti; alcune pubblicazioni sono state
ripetute, per cui questo non significa assenza di chiamate ridondanti.

`audit.json` e `summary.json` del batch riportano ora i controlli completati.
La suite ricontrollata il 16 settembre passa con 74 test, insieme ai controlli
Ruff. Non sono state avviate nuove inferenze per questa verifica dei risultati.

## Stato della demo e limite ancora aperto

Sono disponibili esecuzioni LLM complete per tutti e quattro gli scenari,
ottenute nelle fasi di correzione documentate sopra. Non si tratta di due
matrici complete ripetute con un'unica revisione finale: le tre prove nominale,
senza manutenzione e con azioni vietate precedono l'ultimo chiarimento del
prompt Countermeasure per le candidate vuote. I fallimenti precedenti restano
conservati e distinguibili dai run riusciti.

Le spiegazioni libere restano da migliorare. In particolare, la prima delle
ultime due decisioni descrive il pacchetto come non supportato e ne deduce che
ogni contromisura sia invalida; la seconda parla di assenza di vulnerabilità
perché il pacchetto sarebbe non supportato. Il dato autorevole è invece che
**il lookup mock non copre quella coppia pacchetto/versione**. Non è stato
verificato il supporto del vendor, né dimostrata l'assenza di vulnerabilità o
l'invalidità di ogni contromisura. Il risultato strutturato `insufficient_evidence`
è coerente, ma non rende vere queste deduzioni narrative.

Il successivo intervento del 16 settembre collega le affermazioni della
spiegazione alle fonti effettivamente presenti, distinguendo dati riportati,
stime e informazioni mancanti. Implementazione e nuove prove sono documentate
in [Spiegazioni derivate dagli artefatti](artifact-explanations.md).
I JSON storici descritti qui non sono stati corretti a posteriori.
