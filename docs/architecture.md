# Contratti del primo MVP

Questo documento descrive le responsabilità architetturali. La [guida alla lettura](reading-guide.md) collega ogni componente al relativo file commentato e distingue i controlli dello schema da quelli della sessione.

## Separazione delle responsabilità

CAMEL gestisce assegnazione, esecuzione e collaborazione. Il CountermeasureAgent genera le strategie. Ranking e validazione sono funzioni dei backend, invocate dallo StrategicAgent. La proiezione delle stime in un grafo è un tool locale esplicito: non interpella il modello e non ordina le strategie.

Il risultato di dominio è il JSON pubblicato tramite tool, validato da Pydantic. Il normale envelope CAMEL `TaskResult` trasporta un riepilogo; non può sostituire un artefatto mancante. Prima di dichiarare completo il run, si controllano tutti gli otto artefatti e la loro corrispondenza con lo stato validato.

## DAG e convergenza degli artefatti

La pipeline CAMEL mantiene quattro task, con dipendenze dichiarate esplicitamente:

| Task | Prerequisiti diretti |
|---|---|
| `telemetry` | nessuno |
| `vulnerability` | `telemetry` |
| `countermeasure` | `telemetry`, `vulnerability` |
| `strategic` | `telemetry`, `vulnerability`, `countermeasure` |

Il collegamento telemetry → vulnerability serve a identificare software/versione per il lookup. Il rapporto pubblicato dal VulnerabilityAgent non incorpora né sostituisce `RuntimeEvidence`. Il CountermeasureAgent usa esplicitamente sia evidence sia report; lo StrategicAgent legge tre chiavi distinte da `get_context`: `artifacts.runtime_evidence`, `artifacts.vulnerability_report` e `artifacts.candidate_strategies`. `artifact_producers` ne espone rispettivamente i produttori TelemetryAgent, VulnerabilityAgent e CountermeasureAgent (con prefisso `fixture:` nella dimostrazione senza LLM).

`ArtifactSession` richiede i tre modelli Pydantic separatamente prima della costruzione del grafo e della decisione finale, e verifica che il ranking della decisione corrisponda alle candidate pubblicate. I controlli già esistenti impediscono riscritture degli artefatti e campi aggiuntivi nel rapporto. La provenienza locale della decisione conserva già i riferimenti ai tre artefatti, al ranking e alla validazione.

`pipeline` resta il default, con scheduling CAMEL e gli stessi quattro agenti.
L'ordine resta di fatto sequenziale per i prerequisiti del caso, ma le dipendenze
dirette rappresentano il flusso dati completo. Anche i prompt gestionali della
modalità `auto` descrivono questo DAG.

La gestione dei fallimenti della pipeline è adattata da `ArtifactWorkforce`:
dopo che un produttore esaurisce i tentativi CAMEL, i suoi task discendenti sono
marcati `FAILED` con un motivo di blocco, senza avviare i rispettivi LLM. CAMEL
0.2.90 normalmente avvia anche i join di task falliti per consentire recuperi;
qui un errore non può sostituire un artefatto richiesto. Il retry del produttore
rimane gestito dall'SDK e i task indipendenti restano disponibili allo scheduler.
Il risultato della CLI conserva la causa del produttore e i nomi dei task bloccati.

## Messaggi principali

| Contratto | Produttore | Consumatore | Vincoli essenziali |
|---|---|---|---|
| `RuntimeEvidence` | TelemetryAgent | VulnerabilityAgent, CountermeasureAgent, StrategicAgent | Identità e fatti uguali all'input; ID evidence univoci |
| `VulnerabilityReport` | VulnerabilityAgent + tool KG | CountermeasureAgent, StrategicAgent | Rapporto uguale al risultato del tool; `unsupported` distinto da `matched` |
| `CandidateStrategies` | CountermeasureAgent | StrategicAgent | ID univoci, CVE presenti nel rapporto, stime finite in `[0,1]` |
| `ArgumentationGraph` | Tool invocato dallo StrategicAgent | Ranking tool | Nodi univoci, relazioni con estremi esistenti |
| `RankingResult` | Ranking tool | StrategicAgent | Stesso grafo e insieme di candidati; ordine decrescente e tie-break per ID |
| `SemanticValidationReport` | Semantic tool | StrategicAgent | Registro dei tentativi in ordine di ranking; arresto al primo esito accettato |
| `FinalDecision` | StrategicAgent + validatore di pubblicazione | Output | Selezione uguale al primo candidato accettato; esito esplicito se non selezionabile |
| `ProvenanceRecord` | Provenance tool | Output | Input/output, hash, attività, ruoli e modalità di esecuzione |

`StaticTelemetry` è l'input; `DecisionContext` aggrega evidence, rapporto e capacità/policy per il tool semantico. I modelli rifiutano campi sconosciuti. Nel primo caso supportiamo una sola osservazione software; il mock KG ha una sola corrispondenza esatta. Questi limiti sono intenzionali e non devono essere interpretati come copertura di un inventario reale.

Gli attributi `observations`, `rationale`, `description` e le spiegazioni libere
dei tool restano testo dentro uno schema: il controllo strutturale non ne
dimostra la veridicità semantica. I fatti critici, le CVE, i punteggi del ranking
e la selezione vengono invece verificati anche fra gli artefatti.

### Spiegazione della decisione

`publish_final_decision(selected_strategy_id, explanation)` conserva la firma,
ma ora tratta l'argomento `explanation` come commento dell'agente: lo registra
in `agent_commentary.text`, con `verification="unverified"`. Non lo presenta
come spiegazione verificata e non cerca di correggerlo mediante espressioni
regolari o un secondo giudizio LLM.

La spiegazione autorevole `FinalDecision.explanation` è composta dal tool con
`orchestration/explanations.py`, usando i campi strutturati validati della
sessione. `explanation_method="artifact-derived-v1"` identifica il metodo;
`explanation_claims` distingue dati riportati (`reported_fact`), stime
(`estimate`), decisione (`decision`) e limiti (`limitation`). Ogni elemento
contiene riferimenti `artifact`, `pointer` (JSON Pointer) e `producer`.
Il punteggio di beneficio resta una stima del CountermeasureAgent; la presenza
di una CVE resta un risultato del lookup, senza diventare una verifica esterna.
`unsupported` indica copertura mancante del lookup, senza attestare lo stato
di supporto del vendor o l'assenza di vulnerabilità.

Pydantic verifica la struttura e la corrispondenza fra testo e claim.
`ArtifactSession.assert_complete` ricostruisce i claim dagli artefatti correnti
e ne verifica l'uguaglianza: riferimenti formalmente validi non bastano.
La provenienza dell'attività `decision` include anche `input`, perché la
spiegazione cita direttamente capacità e policy dello scenario.
I JSON storici restano leggibili con `explanation_method="legacy-unverified"`;
una nuova sessione completa deve invece pubblicare il formato derivato.

Questo controllo garantisce coerenza con gli artefatti del prototipo, non la
verità di dati esterni o di ogni campo narrativo. Non è un validatore semantico
generale e non sostituisce i backend finali. CAMEL, i quattro agenti, il DAG,
i criteri di selezione e il ciclo di chiamate tool mantengono la loro semantica.
Il tool compone la spiegazione soltanto quando lo Strategic ne invoca la
pubblicazione. Le [prove dedicate](artifact-explanations.md) documentano la verifica.

## Tool pubblici per ruolo

Ogni worker usa `ArtifactTaskHandler`, un adattamento del gestore di output
strutturato di CAMEL: chiarisce che la risposta finale JSON segue le chiamate ai
tool e verifica tramite `ArtifactSession.require` gli output del ruolo prima di
accettare `failed=false`. Non pubblica risultati al posto dell'agente. Un errore
o un output mancante produce un task fallito anche se il modello dichiara successo.
In modalità pipeline CAMEL può effettuare un solo tentativo aggiuntivo (due
tentativi totali). Il prompt viene aggiornato con i nomi degli artefatti già
validati e di quelli mancanti; il worker rilegge `get_context` e completa le
pubblicazioni senza sostituire i risultati precedenti. Il retry è coperto da un
test che interrompe lo Strategic dopo la validazione e verifica la conservazione
degli artefatti fino alla pubblicazione di decisione e provenienza.
Scheduling, assegnazione, DAG e ciclo di tool calling restano gestiti da CAMEL.
Prima di creare il prompt, il gestore verifica anche gli artefatti di ingresso
del ruolo tramite `ArtifactSession.require`. Questo controllo impedisce
l'inferenza del worker senza prerequisiti validi sia in pipeline sia in auto.
La propagazione del blocco nel DAG riguarda la pipeline; la modalità auto
mantiene lo scheduling e le politiche di recupero dell'SDK.
L'aggancio all'handler e l'adattamento di `_post_ready_tasks` usano l'API interna
della versione fissata 0.2.90 e sono coperti dai test di integrazione; vanno
ricontrollati in caso di aggiornamento SDK.

| Ruolo | Tool |
|---|---|
| TelemetryAgent | `get_context`, `publish_runtime_evidence` |
| VulnerabilityAgent | `get_context`, `lookup_vulnerabilities`, `publish_vulnerability_report` |
| CountermeasureAgent | `get_context`, `publish_candidate_strategies` |
| StrategicAgent | `get_context`, `build_argumentation_graph`, `rank_graph`, `validate_countermeasure`, `publish_final_decision`, `record_provenance` |

I tre tool di pubblicazione esposti a CAMEL usano un parametro `payload` di tipo
oggetto, descritto dai modelli Pydantic. `PublicationTools` adatta questi oggetti
ai metodi JSON della sessione: il modello non deve generare una stringa JSON
annidata in un'altra chiamata JSON. Lo schema del payload viene ricavato dai
modelli, senza duplicare manualmente i campi; `get_context` continua a fornire
gli schemi e gli artefatti separati.

L'API Python di `ArtifactSession` conserva il parametro stringa e la validazione
`model_validate_json`, così fixture e chiamanti esistenti restano compatibili.
L'adapter serializza soltanto oggetti validati: non estrae JSON da testo libero,
non corregge fatti e non pubblica al posto dell'agente. Dopo la prima
pubblicazione, una ripetizione identica è consentita; una riscrittura differente
viene rifiutata. La validazione semantica conserva i tentativi già registrati.

## Sostituzione incrementale dei backend

Le quattro interfacce in `tools/interfaces.py` non dipendono da CAMEL. `ArtifactSession` accetta implementazioni sostitutive nel costruttore:

```python
session = ArtifactSession(
    case,
    output_dir,
    vulnerability_tool=kg_adapter,
    ranking_tool=bwaf_adapter,
    semantic_tool=tinyme_adapter,
    provenance_tool=fabric_adapter,
)
```

Gli adapter reali non sono ancora implementati. In una fase successiva:

1. `lookup_vulnerabilities` userà matcher e KG esistenti.
2. `rank_graph` potrà incapsulare `store_graph`, `rank_graph`, `get_rank_result` e, se necessario, `get_annotated_graph` via MCP, restituendo lo stesso `RankingResult` normalizzato.
3. `validate_countermeasure` mapperà candidate e contesto ai concetti Tiny-ME, conservando l'esito strutturato.
4. `record_provenance` mapperà entità, attività, agenti e dipendenze a PROV-O e persistenza Fabric.

Prima del collegamento reale bisognerà concordare la semantica dei pesi, l'ontologia delle capacità/azioni, il formato BWAF e i riferimenti alle transazioni. Il mock non presume di conoscere tali dettagli dalle repository precedenti, non presenti in questa workspace.

La provenienza locale è una proiezione delle dipendenze dei sette stadi di dominio, registrata solo dopo la decisione. Include gli hash dei file e conserva tutti i tentativi semantici nel relativo artefatto. Non è un log completo dei prompt/token o degli errori della Workforce, non è firmata e non dichiara conformità PROV-O.

## Prove da completare con un modello effettivo

Il [runner della demo](demo-runner.md), in `thesis_agents/demo.py`, avvia processi
CLI indipendenti per confrontare i quattro scenari. È uno strumento di prova
esterno al DAG: non sostituisce la Workforce e non pubblica gli artefatti degli
agenti. `demo_audit.py` ricontrolla i risultati salvati e la consegna dei tool
nei log SDK, usando i contratti e i backend mock attuali.

La suite locale verifica contratti e integrazione SDK tramite inferenza programmata. Il run con un LLM richiede configurazione esplicita di modello e credenziali/endpoint. Vanno poi osservati: qualità delle strategie generate, capacità di correggere pubblicazioni rifiutate, rispetto dell'ordine di validazione, latenza e costo. Anche la decomposizione `--workflow auto` va valutata con il modello scelto; il percorso iniziale più controllabile è la pipeline a quattro task.
