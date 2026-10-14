# Contratti del primo MVP

Il [grafo dell'architettura implementata](architettura-implementata.md) mostra
agenti, sessione validata e server MCP mock, distinguendo i profili disponibili
dai componenti dell'architettura finale ancora da collegare.

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
| `RuntimeEvidence` | TelemetryAgent | VulnerabilityAgent, CountermeasureAgent, StrategicAgent | Fatti uguali all'input statico o allo snapshot OTel; ID evidence univoci e fonte preservata |
| `VulnerabilityReport` | VulnerabilityAgent + tool KG | CountermeasureAgent, StrategicAgent | Rapporto uguale al risultato del tool; `unsupported` distinto da `matched` |
| `CandidateStrategies` | CountermeasureAgent | StrategicAgent | ID univoci, CVE presenti nel rapporto, stime finite in `[0,1]` |
| `ArgumentationGraph` | Tool invocato dallo StrategicAgent | Ranking tool | Nodi univoci, relazioni con estremi esistenti |
| `RankingResult` | Ranking tool | StrategicAgent | Stesso grafo e insieme di candidati; ordine decrescente e tie-break per ID |
| `SemanticValidationReport` | Semantic tool | StrategicAgent | Registro dei tentativi in ordine di ranking; arresto al primo esito accettato |
| `FinalDecision` | StrategicAgent + validatore di pubblicazione | Output | Selezione uguale al primo candidato accettato; esito esplicito se non selezionabile |
| `ProvenanceRecord` | Provenance tool | Output | Input/output, hash, attività, ruoli e modalità di esecuzione |

`StaticTelemetry` è l'input predefinito. Con il profilo HTTP, `TelemetryInput`
contiene invece il selettore della sorgente e le policy; i fatti runtime vengono
dal tool di acquisizione. `DecisionContext` aggrega evidence, rapporto e
capacità/policy per il tool semantico. I modelli rifiutano campi sconosciuti.
Supportiamo una sola identità software per run; il mock KG ha una sola
corrispondenza esatta. Questi limiti non costituiscono copertura di un inventario reale.

L'[ingresso OpenTelemetry](opentelemetry-integration.md) salva uno snapshot
strutturato fuori dal contesto LLM, mantenendone riferimenti e digest in
`RuntimeEvidence`. I flag non osservati sono `null`. L'agente deve prima chiamare
`collect_runtime_evidence` e poi pubblicare esattamente il risultato; la sessione
verifica lo snapshot anche prima del lookup e della decisione. Il gateway HTTP
legge export registrati della baseline oppure log SDK della
[nuova applicazione locale](observed-app-integration.md), con origine `sdk-file`.
La seconda prova usa osservazioni raccolte nella nuova esecuzione e una SBOM
della stessa build. Il gateway non avvia la raccolta; DAG e scheduling restano
invariati.

L'[ingresso SBOM/OSV](sbom-osv-integration.md) è un'altra fonte opzionale:
`external_inputs.countermeasure.context` contiene la proiezione validata di
inventario, advisory e range, conservata in `countermeasure_context.json`.
Il Countermeasure deve acquisirla con `collect_countermeasure_context` quando
configurata, prima di pubblicare strategie. Lo snapshot completo resta fuori
dal contesto LLM. Il report CTI non viene esteso o sostituito dagli advisory OSV;
gli ID non correlati rimangono informazioni aggiuntive. La decisione e l'audit
citano anche questa fonte, mantenendo i tre artefatti dei produttori distinti.

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
| TelemetryAgent | `get_context`, `collect_runtime_evidence` (ingresso OTel), `publish_runtime_evidence` |
| VulnerabilityAgent | `get_context`, `lookup_vulnerabilities`, `publish_vulnerability_report` |
| CountermeasureAgent | `get_context`, `collect_countermeasure_context` (se configurato), `publish_candidate_strategies` |
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

Il [piano MCP sul branch full](mcp-integration-plan.md) descrive il trasporto
remoto, la selezione dei backend e le verifiche prima del collegamento alla
Workforce. Sono implementati il [lookup MCP](mcp-lookup.md) e i tre
[adapter strategici](mcp-strategic.md) per ranking, validazione e provenienza,
con server mock HTTP separati. La CLI accetta `--backends` con una scelta per
ciascun backend; senza profilo il comportamento resta locale. Il profilo
`backends.mcp-strategic-mock.json` porta su MCP solo i tool dello Strategic.
La provenienza conserva una ricevuta remota verificata in un file separato;
il server mock la associa a un record persistito in SQLite. Il documento e
la ricevuta non sono ancora PROV-O o una transazione Fabric. Il
[profilo CTI reale](cti-workforce.md) collega il servizio cve2owl al lookup,
con artefatti estesi e tool strategici locali. Il profilo `backends.otel-cti.json`
aggiunge l'ingresso HTTP di telemetria registrata. `backends.cti-sbom-osv.json`
abbina CTI e OSV reali a una SBOM dimostrativa Maven e telemetria statica.
Il profilo prodotto da `examples/observed-app/prepare.py` combina invece log SDK
della nuova esecuzione, SBOM della build, CTI e OSV reali. È collaudato con CAMEL
programmato e con [Ollama effettivo](observed-app-ollama.md) sul caso negativo;
raccolta continua e servizi strategici reali restano da collegare.
I profili CTI/OTel richiedono
la validazione semantica locale: i contratti MCP v1 congelati non rappresentano
questi metadati estesi.

Le interfacce in `tools/interfaces.py` non dipendono da CAMEL. `ArtifactSession` accetta implementazioni sostitutive nel costruttore:

```python
session = ArtifactSession(
    case,
    output_dir,
    telemetry_tool=otel_adapter,  # con input TelemetryInput
    supply_chain_tool=sbom_osv_adapter,  # fonte opzionale per Countermeasure
    vulnerability_tool=kg_adapter,
    ranking_tool=bwaf_adapter,
    semantic_tool=tinyme_adapter,
    provenance_tool=fabric_adapter,
)
```

Il primo adapter reale è `CTIVulnerabilityTool`. Lo stato dei collegamenti è:

1. `lookup_vulnerabilities` usa il servizio MCP `assess_software` e il matcher
   esistente sullo snapshot cve2owl; nessuna inferenza OWL nel client.
2. `rank_graph` potrà incapsulare `store_graph`, `rank_graph`, `get_rank_result` e, se necessario, `get_annotated_graph` via MCP, restituendo lo stesso `RankingResult` normalizzato.
3. `validate_countermeasure` mapperà candidate e contesto ai concetti Tiny-ME, conservando l'esito strutturato.
4. `record_provenance` mapperà entità, attività, agenti e dipendenze a PROV-O e persistenza Fabric.

Prima del collegamento reale bisognerà concordare la semantica dei pesi, l'ontologia delle capacità/azioni, il formato BWAF e i riferimenti alle transazioni. Le copie delle baseline sulla Scrivania sono state esaminate in sola lettura durante la revisione bibliografica del 17 settembre; non sono integrate nel mock. Il ranking locale resta un'euristica distinta dal backend. Fonti, commit e limiti della verifica sono in [fonti e scelte](fonti-e-scelte.md).

La provenienza locale è una proiezione delle dipendenze di dominio, registrata solo dopo la decisione. Nei profili CTI e OTel include anche gli snapshot remoti e le attività che li usano. Include gli hash dei file e conserva tutti i tentativi semantici nel relativo artefatto. Non è un log completo dei prompt/token o degli errori della Workforce, non è firmata e non dichiara conformità PROV-O.

## Prove con un modello effettivo

`ArtifactChatAgent` è una sottoclasse CAMEL che mantiene disabilitata la sintesi
automatica anche nei cloni del pool. Conserva i messaggi integrali; il budget
opzionale di `BoundedCompatibleModel` rifiuta richieste troppo grandi prima
del provider, contando anche tool e riserva per la risposta. È un controllo
stimato con margine, non il tokenizer esatto di Qwen. Il giudizio qualitativo
gestionale resta CAMEL, con task che distinguono dati sconosciuti da lavoro
mancante. Implementazione, limiti e prove sono nelle
[verifiche dei contratti e del contesto](ollama-contract-tests.md).
La Workforce espone i tool di acquisizione solo quando il relativo ingresso
è configurato: il caso statico mantiene la normalizzazione nell'agente,
mentre OTel richiede sia `TelemetryInput` sia un backend. La disponibilità
di un tool non equivale alla riuscita della chiamata, che resta verificata
dalla sessione. I test LLM hanno ancora rilevato pubblicazioni finali omesse,
respinte dal contratto anche quando il testo generato dichiarava successo.
Per questi errori è stato introdotto il
[controllo per fonte e per fase](agent-tool-phases.md): i tool di pubblicazione
Telemetry espongono schemi statici/OTel coerenti con la sessione, mentre
`StrategicToolPolicy` limita ogni richiesta al tool della fase raggiunta.
Il modello deve ancora fornire gli argomenti ed eseguire la chiamata effettiva;
la policy non pubblica artefatti. Le risposte testuali premature hanno un
recupero limitato, poi sono respinte se il contratto resta incompleto.

Il [runner della demo](demo-runner.md), in `thesis_agents/demo.py`, avvia processi
CLI indipendenti per confrontare i quattro scenari. È uno strumento di prova
esterno al DAG: non sostituisce la Workforce e non pubblica gli artefatti degli
agenti. `demo_audit.py` ricontrolla i risultati salvati e la consegna dei tool
nei log SDK, usando i contratti e i backend mock attuali.

La suite locale verifica contratti e integrazione SDK tramite inferenza programmata.
La [prova Ollama sui tre ingressi](observed-app-ollama.md) ha verificato anche
inferenza dei quattro ruoli e consegna dei contesti: 475,59 secondi, 46 richieste,
esito `no_findings`. I retry qualitativi mostrano però che il valutatore gestionale
può penalizzare dati sconosciuti o insiemi vuoti corretti; la chiusura di un task
SDK non equivale a una certificazione della qualità. L'audit e la sessione restano
il controllo della validità degli artefatti. Il commento libero è non verificato.

Restano da valutare generazione su finding reali, affidabilità su più ripetizioni,
limite di contesto e decomposizione `--workflow auto`. Il runner della matrice
storica e il relativo audit restano specifici dei backend mock; non vanno usati
per attestare direttamente il nuovo profilo remoto.
