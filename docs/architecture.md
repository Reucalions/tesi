# Contratti del primo MVP

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

Non cambia la semantica di esecuzione della Workforce: `pipeline` resta il default, con scheduling CAMEL e gli stessi agenti/tool. L'ordine resta di fatto sequenziale per i prerequisiti del caso, ma le dipendenze dirette rappresentano il flusso dati completo, anziché affidarsi al solo task precedente. Anche i prompt gestionali della modalità `auto` descrivono questo DAG.

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

Gli attributi `observations`, `rationale`, `description` ed `explanation` restano testo dentro uno schema: il controllo strutturale non ne dimostra la veridicità semantica. I fatti critici, le CVE, i punteggi del ranking e la selezione vengono invece verificati anche fra gli artefatti.

## Tool pubblici per ruolo

| Ruolo | Tool |
|---|---|
| TelemetryAgent | `get_context`, `publish_runtime_evidence` |
| VulnerabilityAgent | `get_context`, `lookup_vulnerabilities`, `publish_vulnerability_report` |
| CountermeasureAgent | `get_context`, `publish_candidate_strategies` |
| StrategicAgent | `get_context`, `build_argumentation_graph`, `rank_graph`, `validate_countermeasure`, `publish_final_decision`, `record_provenance` |

Le pubblicazioni JSON usano un parametro `payload` di tipo stringa per mantenere il tool calling semplice su provider diversi; lo schema completo è disponibile in `get_context` e la validazione usa `model_validate_json`, senza estrazione permissiva da testo libero. Dopo la prima pubblicazione, una ripetizione identica è consentita; una riscrittura differente viene rifiutata. La validazione semantica accumula gli esiti senza ricalcolare quelli già registrati.

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

La suite locale verifica contratti e integrazione SDK tramite inferenza programmata. Il run con un LLM richiede configurazione esplicita di modello e credenziali/endpoint. Vanno poi osservati: qualità delle strategie generate, capacità di correggere pubblicazioni rifiutate, rispetto dell'ordine di validazione, latenza e costo. Anche la decomposizione `--workflow auto` va valutata con il modello scelto; il percorso iniziale più controllabile è la pipeline a quattro task.
