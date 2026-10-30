## 11. Evoluzione del prototipo e integrazione dei servizi

Le sezioni precedenti descrivono la configurazione del mockup e la relativa matrice sperimentale. Il lavoro è proseguito con la sostituzione progressiva di alcune fonti simulate e con l'introduzione di un livello di comunicazione con servizi esterni. I risultati del mockup rimangono riferiti alla configurazione in cui sono stati ottenuti; le verifiche delle integrazioni costituiscono una valutazione distinta.

Lo sviluppo procede sul branch `full`, mentre `mockup` conserva la baseline dimostrativa. Sono mantenuti i quattro ruoli CAMEL, la modalità `pipeline`, il DAG e i contratti Pydantic. Il collegamento di un servizio non modifica il produttore degli artefatti: Telemetry pubblica `RuntimeEvidence`, Vulnerability pubblica `VulnerabilityReport`, Countermeasure genera `CandidateStrategies` e Strategic riceve separatamente i tre risultati attraverso `get_context`.

### 11.1 Confine tra agenti e backend

Il principio adottato è rendere i servizi accessibili attraverso contratti pubblici. Il processo degli agenti conosce gli argomenti ammessi, il formato della risposta e l'endpoint; non importa il motore del backend, non apre i suoi dataset e non avvia la pipeline esterna. Un adapter traduce le risposte nel modello di dominio e ne verifica la coerenza prima della pubblicazione.

I servizi possono essere processi distinti sulla stessa macchina durante il collaudo. Questo verifica il confine di comunicazione, ma non equivale a una distribuzione su host remoti. L'eventuale esecuzione di smart contract rimane interna al servizio esterno: gli agenti dovranno riceverne risultati e ricevute mediante tool black box.

La selezione avviene con `--backends`, che carica un profilo validato da `BackendConfig`. La scelta è per servizio e permette configurazioni miste: ad esempio CTI reale e strumenti strategici mock. Il default locale resta disponibile. La modalità `fixtures` continua a usare backend locali e risultati prefissati; la modalità `camel` esegue gli agenti anche quando alcuni backend sono simulati. Non è stata introdotta una seconda implementazione dei quattro agenti né uno switch deciso liberamente dall'LLM.

### 11.2 Client e server MCP

Il Model Context Protocol è utilizzato per individuare e invocare tool remoti tramite interfacce descritte da schemi. Il trasporto adottato è Streamable HTTP, con server eseguito separatamente dal client [MCP-HTTP, MCP-TOOLS]. Nel progetto sono effettivi l'inizializzazione della sessione, la discovery con `tools/list` e l'invocazione con `tools/call`.

`MCPClient` gestisce connessione e ciclo di vita attraverso l'SDK MCP. Un loop dedicato consente di utilizzare il client dai tool sincroni mentre CAMEL esegue il proprio ciclo asincrono. La discovery confronta gli schemi con i contratti previsti; agli agenti vengono resi disponibili soltanto i tool assegnati al ruolo, non tutte le operazioni dichiarate dal server.

Sono presenti un server mock per il lookup e un server mock strategico per ranking, validazione e provenienza. Il primo conserva il caso dimostrativo; il secondo riusa gli algoritmi locali dietro una vera comunicazione MCP. Un server mock verifica quindi il trasporto e i contratti senza rendere reale l'algoritmo simulato. Analogamente, configurare `expected_kind=real` richiede una risposta compatibile che si dichiari reale, ma non certifica da solo l'autenticità del servizio.

| Operazione remota | Contratto | Risultato utilizzato dal prototipo |
|---|---|---|
| Lookup mock | `vulnerability-lookup-v1` | Vulnerabilità della fixture |
| Ranking | `argumentation-ranking-v1` | Ordine e score delle candidate |
| Validazione | `semantic-validation-v1` | Ammissibilità della candidata nel contesto |
| Provenienza | `provenance-record-v1` | Ricevuta legata al record e al run |

I controlli verificano versione del contratto, identificativi, tipo dichiarato del backend e, nei contratti che lo prevedono, digest della richiesta. Errori di rete, risposte malformate o riferimenti incoerenti non diventano risultati di dominio e non attivano un fallback silenzioso ai mock. I file `backends.json` e `mcp_events.jsonl` conservano configurazione effettiva ed eventi tecnici; eventuali credenziali vengono lette dall'ambiente senza inserirne il valore negli artefatti.

### 11.3 Provenienza remota e limiti del collegamento

Il server strategico mock conserva i record di provenienza in SQLite. Un reinvio con lo stesso `run_id` e lo stesso contenuto restituisce la stessa ricevuta; un contenuto diverso per quel run viene rifiutato. La ricevuta contiene identificativo del run, digest del record, esito della registrazione e identificativo del backend. È distinta dal documento inviato e non costituisce una transazione Hyperledger Fabric.

Il digest della ricevuta riguarda una serializzazione JSON canonica; gli hash delle entità del record riguardano invece i byte degli artefatti salvati. Questi controlli rilevano incoerenze tra dati dichiarati e file, ma non attestano l'autenticità della fonte o la correttezza del calcolo remoto. La memoria operativa rimane in `ArtifactSession`; il ledger conserva il ruolo previsto di audit e registrazione degli eventi.

## 12. Collegamento del backend CTI reale

### 12.1 Servizio di correlazione cve2owl

La prima integrazione reale riguarda il lookup delle vulnerabilità. Nel repository `agent-based-cti-argumentation-pipeline`, sul branch `costa-thesis`, è stato aggiunto un servizio MCP dedicato, con test e dipendenze separate. Il servizio riusa il matcher e il valutatore delle versioni già presenti nella baseline; non modifica gli algoritmi preesistenti e non avvia la pipeline completa. La seconda baseline, `semantic-cti-ledger-argumentation`, non è stata modificata per questo collegamento [BASE-CTI].

Il tool `assess_software` espone il contratto `cve2owl-assessment-v1` e consulta un indice SQLite reale derivato da cve2owl. Il dataset è stato recuperato attraverso Git LFS e viene utilizzato in sola lettura, con controlli sullo schema e sull'integrità. Il processo `tesi` invia soltanto la richiesta MCP. La disponibilità del file OWL non implica che gli agenti eseguano ragionamento OWL: il percorso collegato usa matching dell'identità e valutazione delle regole di versione sull'indice derivato.

La sessione ricava pacchetto, versione ed evidence ID da `RuntimeEvidence`. L'LLM non può sostituirli attraverso gli argomenti del lookup. `CTIVulnerabilityTool` conserva la risposta in `cti_assessment.json` e prepara il report che Vulnerability deve pubblicare senza alterare i dati restituiti. Rimangono distinti matching, valutazione delle regole, riferimenti al dataset e metadati mancanti.

### 12.2 Esiti e rappresentazione dell'incertezza

L'adapter introduce una policy conservativa per interpretare le risposte, senza attribuirle valore di nuovo algoritmo scientifico. Un solo candidato con confidenza categoriale alta consente di trattare l'identità come risolta nel risultato ricevuto. Più candidati o confidenza insufficiente mantengono l'ambiguità. Lo score del matcher non viene trasformato in probabilità.

| Esito del lookup | Significato nel contratto |
|---|---|
| `matched` | Identità risolta e almeno un finding confermato dalle regole valutate |
| `ambiguous` | Identità non risolta univocamente |
| `no_match` | Nessuna identità restituita dalla ricerca |
| `not_evaluable` | Regole insufficienti per concludere, senza finding positivo confermato |
| `no_findings` | Nessun finding nelle voci restituite, con regole presenti e tutte valutate |
| `unsupported` | Caso non coperto dal lookup mock storico |

Con evidenze insufficienti la decisione resta `insufficient_evidence`; `no_findings` non dimostra l'assenza globale di vulnerabilità. Se alcune regole non sono valutabili, un finding positivo può essere conservato insieme alla copertura parziale, mentre un risultato negativo non viene promosso a conclusione completa. CVSS e confidenza numerica mancanti rimangono `null`; l'assenza di CWE e degli altri metadati è esplicitata nel report.

Le prove hanno mostrato che nomi apparentemente simili possono produrre identità ambigue o regole non valutabili. Non sono stati inseriti alias automatici per forzare il risultato. Il nome canonico utilizzato nei casi positivi è un input dichiarato della prova, non una correzione implicita operata dal modello.

I contratti MCP v1 preesistenti rimangono congelati. Il profilo CTI richiede per ora validazione semantica locale, perché `semantic-validation-v1` non rappresenta il report esteso. La configurazione rifiuta la combinazione incompatibile anziché eliminare informazioni per adattare la risposta.

## 13. Acquisizione OpenTelemetry

### 13.1 Dall'input statico al selettore di osservazioni

Il TelemetryAgent dispone di un ingresso HTTP separato. `TelemetryInput` descrive servizio, istanza e finestra di osservazione, insieme a capacità e policy; non impone al modello una versione software da inventare o confermare. Il tool `collect_runtime_evidence()` usa il selettore validato per consultare il gateway e ottenere uno snapshot delle osservazioni.

Il primo collaudo ha utilizzato export OpenTelemetry conservati nella baseline. La normalizzazione considera i soli attributi previsti dal contratto; dati assenti o discordanti non vengono ricostruiti dal testo libero. In particolare, esposizione dell'endpoint e deserializzazione osservata possono restare `null`, distinto da `false`.

Il riferimento alla fonte separa il tempo di osservazione dal momento in cui il gateway acquisisce il file. Questa distinzione è coerente con il modello dei log OpenTelemetry [OTEL-LOG]. Leggere nuovamente un export non rende attuali le osservazioni registrate. File incompleti, selezioni ambigue, risposte incoerenti o limiti superati producono errori espliciti, senza fallback statico o troncamenti silenziosi.

Lo snapshot viene salvato in `telemetry_snapshot.json`; `RuntimeEvidence` conserva riferimenti alla fonte e agli hash. La sessione accetta la pubblicazione solo dopo l'acquisizione e confronta l'intera evidenza con quella derivata dallo snapshot. Questi controlli vengono mantenuti fino alla decisione e alla registrazione della provenienza.

### 13.2 Applicazione osservata e coerenza delle fonti

Per disporre di telemetria e inventario della stessa applicazione è stato aggiunto il progetto Java `examples/observed-app`. Il workload esegue cinque elaborazioni dimostrative, utilizza Log4j Core 2.26.1 ed emette cinque record attraverso l'SDK OpenTelemetry Java 1.66.0. La versione osservata viene letta dal package della classe caricata; viene inoltre calcolato lo SHA-256 del JAR che la contiene.

Gli attributi `thesis.software.*` sono convenzioni del prototipo, non attributi standard OpenTelemetry. La strumentazione è manuale e usa l'exporter dell'SDK. Il percorso `sdk-file` produce log su file e li rende consultabili tramite gateway HTTP: non introduce un Collector, un receiver OTLP o una raccolta continua di tracce e metriche.

Lo script di preparazione confronta identità, versione e hash del JAR con l'inventario generato dalla build Maven e verifica che le osservazioni appartengano all'esecuzione appena effettuata. È un controllo locale della demo, non un'attestazione remota degli agenti. Le successive inferenze possono riusare quelle fonti, conservandone i riferimenti. Le capacità operative della demo restano vuote perché non sono presenti attuatori di mitigazione.

## 14. Contesto SBOM/OSV per Countermeasure

### 14.1 Inventario e interrogazione del servizio

Il CountermeasureAgent riceve un contesto aggiuntivo mediante un secondo gateway HTTP. Il servizio legge una SBOM CycloneDX e interroga OSV per il componente associato all'asset osservato. Nelle copie delle baseline non era emersa una SBOM applicativa utilizzabile: è stato quindi predisposto un inventario dimostrativo dichiarato e, successivamente, un inventario prodotto dalla build dell'applicazione Java.

La SBOM dimostrativa non deriva da una scansione o da un'applicazione in esecuzione. Quella generata con `cyclonedx-maven-plugin` 2.9.3 e `makeAggregateBom` contiene invece tredici componenti della build, comprese le dipendenze OpenTelemetry [CDX-MAVEN]. I due casi restano identificati rispettivamente come `demo` e `provided`; nessuna delle etichette costituisce un'attestazione del deployment.

L'associazione configurata collega servizio e nome del pacchetto a un componente della SBOM. Versione osservata, coordinate Maven e PURL devono essere coerenti. Il gateway usa `POST /v1/query` per pacchetto e versione e gestisce la paginazione prevista dall'API OSV [OSV-QUERY]. Il client conserva lo snapshot completo e verifica richieste e risposte prima di produrre il contesto utilizzabile dall'agente.

Il sottoinsieme implementato comprende CycloneDX JSON 1.5/1.6 e componenti Maven al primo livello, con PURL senza qualificatori oppure con il solo `type=jar`. Viene interrogato un componente associato, non l'intero insieme delle dipendenze. Formati non supportati, versioni discordanti, paginazione incompleta ed errori del servizio non diventano assenza di vulnerabilità.

### 14.2 Rapporto con il report delle vulnerabilità

`collect_countermeasure_context()` ricava la query da `RuntimeEvidence` dopo la pubblicazione del report. La risposta viene conservata in `supply_chain_snapshot.json`; la proiezione validata è salvata in `countermeasure_context.json` ed esposta anche in `external_inputs.countermeasure` tramite `get_context`.

Gli advisory OSV attivi vengono correlati soltanto alle CVE già presenti in `VulnerabilityReport`. Gli altri identificativi rimangono visibili come informazioni aggiuntive, senza diventare finding CTI confermati. L'assenza di riscontro OSV non annulla il report; i record ritirati o non correlabili non fondano le proposte. Gli eventi dei range, compreso `fixed`, conservano il significato della fonte [OSV-SCHEMA] e non equivalgono a una versione globalmente sicura o compatibile.

Countermeasure continua a generare le candidate usando evidence e report come input autorevoli distinti. L'acquisizione SBOM/OSV configurata è obbligatoria anche quando il report è vuoto. In questo caso l'agente deve pubblicare un insieme vuoto, senza inventare strategie per completare il task. I retry interni riusano lo snapshot della sessione; una nuova sessione effettua una nuova consultazione.

## 15. Adeguamento dei contratti e del ciclo degli agenti

### 15.1 Pubblicazione della telemetria secondo la fonte

Le prove combinate hanno evidenziato una difficoltà nel presentare allo stesso modello istruzioni e campi riferiti sia all'input statico sia all'acquisizione OTel. In un caso statico Telemetry ha tentato prima una raccolta non configurata e poi pubblicazioni con metadati OTel inventati. I controlli hanno respinto i dati e il DAG ha bloccato i task dipendenti: il problema riguardava le chiamate dell'agente, non l'indisponibilità del gateway.

La Workforce espone ora i tool di acquisizione soltanto quando il relativo ingresso è configurato. Il contratto di pubblicazione distingue `StaticRuntimeEvidence`, con riferimento `telemetry` nullo e flag booleani, da `OTelRuntimeEvidence`, con riferimento alla fonte obbligatorio e possibilità di mantenere flag sconosciuti. Il nome pubblico del tool resta `publish_runtime_evidence`; l'artefatto salvato rimane `RuntimeEvidence`.

Anche i prompt vengono selezionati in funzione della fonte. Per OTel è richiesta la copia esatta dell'evidenza acquisita; per l'input statico il confronto resta con i fatti dello scenario. Non vengono rimossi o corretti automaticamente metadati errati per accettare una pubblicazione.

### 15.2 Memoria e budget del contesto

L'integrazione delle fonti esterne aumenta la dimensione di schemi, messaggi e risposte. È stato introdotto `LLM_CONTEXT_TOKENS`, con un controllo preventivo del budget:

```text
stima della richiesta + LLM_MAX_TOKENS + 1024 <= LLM_CONTEXT_TOKENS
```

La stima comprende messaggi e schemi, ma usa il contatore del backend compatibile OpenAI, non il tokenizer esatto Qwen. Il margine di 1024 token è una scelta implementativa prudenziale, non una garanzia matematica. Le richieste troppo grandi vengono respinte; il controllo non elimina evidenze per rientrare nel limite e non modifica il parametro `num_ctx` del server Ollama.

Con un limite esplicito è emerso anche un ciclo di sintesi automatica della memoria. In CAMEL 0.2.90 i cloni dei worker ripristinavano la soglia predefinita di riassunto anche quando l'agente originale era configurato diversamente. `ArtifactChatAgent` conserva ora la memoria integrale e le opzioni necessarie anche nei cloni. Le memorie dei worker rimangono separate; lo stato condiviso autorevole resta nella sessione degli artefatti. L'adattamento riguarda l'SDK verificato e richiede regressioni prima di cambiarne versione [CAMEL-SDK].

### 15.3 Pubblicazioni strategiche per fase

Un secondo problema riguardava lo Strategic: il modello poteva scrivere nel testo una chiamata o dichiarare conclusa la decisione senza invocare i tool. Il chiarimento dei soli prompt non ha impedito tutte le omissioni. `ArtifactTaskHandler` ha continuato a respingere i tentativi con pubblicazioni mancanti.

`StrategicToolPolicy` determina ora il tool disponibile dalla fase raggiunta nello stato validato. Ogni clone deve prima leggere `get_context`; seguono costruzione del grafo, ranking, eventuali validazioni in ordine, pubblicazione della decisione e registrazione della provenienza. Solo dopo queste operazioni viene richiesta la risposta conclusiva del task.

Il modello produce ancora argomenti e chiamate effettive. La policy non esegue strumenti, non genera score e non sceglie una strategia al posto dell'agente. Un errore non fa avanzare la fase; una chiamata fuori fase viene respinta prima dell'esecuzione. Una risposta testuale prematura consente un solo recupero nel ciclo CAMEL; se l'omissione persiste, i controlli di completezza impediscono il falso successo.

Con candidate vuote vengono comunque pubblicati grafo e ranking vuoti. Non si valida una strategia inesistente: la decisione seleziona `null`, il report semantico resta vuoto e la provenienza deve essere registrata. Il DAG tra gli agenti non cambia; cambia il vincolo sulle operazioni disponibili all'interno del task strategico.

## 16. Verifica delle integrazioni e risultati

### 16.1 Test automatici e controlli sugli artefatti

La suite del prototipo comprende ora **270 test superati**, con controlli Ruff e formattazione verificati. Questo risultato estende la copertura dei 95 test della baseline senza sostituire la relativa matrice LLM. Sono verificati trasporto MCP, discovery e contratti incompatibili, errori HTTP, integrità delle fonti, metadati mancanti, pubblicazioni respinte, fasi strategiche, recuperi e isolamento dei cloni.

I test degli agenti utilizzano inferenza programmata; le prove HTTP avviano servizi separati. Servono a verificare il codice e i contratti, non a misurare la qualità del modello. Le prove sul servizio CTI sono state svolte prima su dati sintetici e poi sul dataset reale, distinguendo il collaudo del backend dall'esecuzione degli agenti.

Gli audit delle inferenze rileggono i modelli Pydantic, confrontano acquisizioni e pubblicazioni, controllano hash e produttori e verificano i messaggi effettivamente consegnati allo Strategic. Un controllo separato ricostruisce le fasi dalle conversazioni, senza utilizzare la policy di produzione. Non crea gli artefatti mancanti e non corregge quelli generati.

### 16.2 Difficoltà nelle prove preliminari

La prima inferenza con i tre ingressi collegati è terminata con `no_findings` in 475,59 secondi e 46 richieste LLM. L'audit è passato, ma sono stati necessari quattro retry qualitativi ed è stata respinta una chiamata di validazione su ranking vuoto. Il giudizio gestionale non distingueva sempre la mancanza di dati nella fonte dalla mancata esecuzione del task.

Nelle prove successive sono emersi il ciclo di riassunti, le pubblicazioni OTel inventate per dati statici e le chiamate finali omesse dallo Strategic. Due ripetizioni comparabili sul percorso senza finding hanno prodotto un successo e un fallimento. Questi esiti sono conservati nella documentazione tecnica e hanno motivato gli interventi sui contratti e sul ciclo degli agenti. Non sono conteggiati come esecuzioni riuscite della configurazione finale.

### 16.3 Ripetizioni della configurazione aggiornata

Il collaudo aggiornato comprende due percorsi, ciascuno ripetuto due volte. Il caso positivo usa telemetria statica dichiarata su Log4j Core 2.14.1 e una SBOM dimostrativa; CTI e OSV sono reali. Il secondo usa i log SDK registrati e la SBOM della build dell'applicazione con Log4j Core 2.26.1. In entrambi ranking, validazione e provenienza rimangono mock locali.

Le quattro prove usano `tesi-qwen3:4b`, quantizzazione Q4_K_M, temperatura zero, contesto di 16.384 token e massimo di risposta pari a 2048. I manifest confermano stessa revisione del codice, digest del modello, versioni delle librerie e parametri. Il server Ollama è 0.40.2; rispetto alle prove preliminari, eseguite con 0.34.4, questa differenza impedisce di attribuire l'intero miglioramento alla sola policy.

| Percorso | Ripetizione | Durata | Richieste LLM | Esito |
|---|---|---|---|---|
| Statico con finding | 1 | 398,01 s | 23 | `selected`, `S_UPGRADE` |
| Statico con finding | 2 | 389,44 s | 23 | `selected`, `S_ISOLATE` |
| OTel senza finding | 1 | 316,20 s | 23 | `no_findings`, strategia `null` |
| OTel senza finding | 2 | 324,01 s | 23 | `no_findings`, strategia `null` |

Tutte e quattro le inferenze hanno completato i task al primo tentativo e superato gli audit degli artefatti e delle fasi. Non compaiono retry qualitativi, errori dei tool, risposte strategiche premature, riassunti automatici o superamenti del budget. Decisione e provenienza sono presenti in ogni run. Il risultato riguarda questo campione e non stima un tasso generale di affidabilità.

Ogni ripetizione avvia un processo e una sessione CAMEL nuovi, senza importare conversazioni o artefatti delle precedenti. Le fonti registrate vengono invece riutilizzate: non sono nuove build o nuove osservazioni a ogni inferenza. OSV viene consultato nella nuova sessione; i retry interni possono riusare gli snapshot. Il modello risultava già residente soltanto prima della seconda prova positiva. Le durate includono caricamento, inferenza, tool e gestione CAMEL e non sono un benchmark controllato delle prestazioni.

### 16.4 Variabilità e limiti del risultato

Le due prove positive conservano gli stessi tre finding CTI, ma Countermeasure genera alternative e stime differenti. Nella prima propone upgrade, isolamento e blocco; nella seconda sostituisce il blocco con il monitoraggio e riduce l'impatto stimato dell'isolamento da 0.2 a 0.1, mantenendo il beneficio a 0.7.

La formula mock rimane invariata: lo score dell'isolamento passa da 0.75 a 0.8. Nella seconda prova anche l'upgrade ha score 0.8; lo spareggio deterministico per identificativo pone `S_ISOLATE` per primo. Lo Strategic seleziona quindi la prima candidata accettata secondo il ranking. Il flusso è coerente con i contratti, ma non produce una raccomandazione identica nelle due ripetizioni. Temperatura zero e medesimo modello non rendono identiche le conversazioni, che comprendono anche identificativi e metadati variabili.

Rimangono limiti nella prosa generata. Il commento libero dello Strategic contiene affermazioni non dimostrate e, in una prova, un conteggio delle CVE diverso dal report. Una candidata qualifica inoltre come supportata dal fornitore una versione presente nei limiti `fixed` degli advisory: quei dati non attestano supporto, compatibilità o sicurezza complessiva. Pydantic verifica la struttura, non il significato di ogni frase. `agent_commentary` resta marcato come non verificato e separato dalla spiegazione autorevole derivata dagli artefatti.

Countermeasure ha ricevuto il contesto aggiuntivo direttamente dalla risposta del tool di raccolta, omettendo la seconda lettura di `get_context` richiesta dal prompt. L'audit ha verificato la consegna esatta dei dati, ma conserva questa deviazione dall'istruzione. Per lo Strategic sono state invece verificate la lettura separata dei tre artefatti e la disponibilità del contesto SBOM/OSV tramite `get_context`.

## 17. Comandi e tracciabilità dell'esecuzione

### 17.1 Verifica del livello MCP

I server vengono avviati separatamente dalla Workforce. Per il collaudo degli strumenti strategici mock, dalla radice del repository:

```bash
.venv/bin/python -m thesis_agents.mcp.strategic_mock_server \
  --port 8002 --data-dir output/mcp-mock-store
```

In un altro terminale, la discovery verifica la configurazione senza inferenza né registrazioni di dominio:

```bash
.venv/bin/python -m thesis_agents.mcp.probe \
  --backends config/backends.mcp-strategic-mock.json --check-config
```

Per il servizio CTI reale è disponibile il profilo `config/backends.cti-real.json`. Il servizio deve essere già avviato nel repository esterno con il dataset configurato; il client non lo avvia automaticamente.

### 17.2 Preparazione delle fonti e inferenza locale

La preparazione dell'applicazione osservata richiede JDK, Maven e le dipendenze del progetto:

```bash
.venv/bin/python examples/observed-app/prepare.py \
  --output output/relazione-sources
```

Il comando esegue build, workload e controlli di coerenza, quindi produce selettore, manifest e profilo dei backend. La directory deve essere nuova. Dopo l'avvio separato dei gateway OTel e SBOM e del servizio CTI, secondo `docs/observed-app-integration.md`, l'inferenza si esegue con:

```bash
LLM_MODEL=tesi-qwen3:4b LLM_API_KEY=local \
LLM_BASE_URL=http://localhost:11434/v1 LLM_TEMPERATURE=0 \
LLM_TIMEOUT_SECONDS=300 LLM_CONTEXT_TOKENS=16384 \
LLM_MAX_TOKENS=2048 CAMEL_MODEL_LOG_ENABLED=true \
CAMEL_LOG_DIR="$PWD/output/relazione-run/llm" \
.venv/bin/python main.py --mode camel --workflow pipeline \
  --backends output/relazione-sources/backends.json \
  --input output/relazione-sources/input.json \
  --output output/relazione-run/artifacts
```

I valori valgono per il processo e non richiedono di riscrivere `.env`. Ollama deve avere il modello locale configurato con lo stesso contesto. Ogni run usa una destinazione distinta. Questi comandi descrivono una nuova esecuzione; i risultati della tabella precedente derivano dalle prove già conservate e non vengono rigenerati dalla stesura della relazione.

La documentazione `docs/agent-tool-phases.md` identifica i run, i manifest, i comandi effettivi e gli audit ripetibili offline. Gli output includono input, artefatti di dominio, snapshot delle fonti, conversazioni e riepiloghi. Le directory `output/` sono evidenze locali escluse da Git e vanno incluse esplicitamente quando occorre consegnare i dati sperimentali.

## 18. Stato raggiunto e sviluppi successivi

Il prototipo dispone ora di un percorso completo da fonti acquisite a decisione e provenienza, verificato con CAMEL e Ollama. Le dipendenze tra agenti rimangono esplicite e le evidenze non vengono sostituite dai risultati successivi. L'architettura supporta la migrazione progressiva dei backend attraverso contratti e adapter, mantenendo disponibile la configurazione dimostrativa.

| Componente | Stato verificato |
|---|---|
| CAMEL e LLM | Quattro agenti effettivi, inferenza locale e pubblicazioni controllate |
| Telemetry | Gateway HTTP, snapshot di log registrati e strumentazione SDK dell'applicazione dimostrativa |
| Vulnerability | Lookup MCP reale su indice cve2owl, con incertezza e copertura esplicite |
| Countermeasure | Ingresso HTTP SBOM/OSV e generazione delle candidate |
| MCP strategico | Client, adapter e server mock collaudati; algoritmi reali non collegati |
| Ranking e semantica nelle inferenze combinate | Mock locali; nessuna esecuzione BWAF reale o Tiny-ME |
| Provenienza | Record applicativi e hash; ricevute mock nel profilo MCP dedicato |
| PROV-O, Fabric e attuazione | Non ancora implementati nel flusso collaudato |

Il prossimo incremento richiede il mapping dei contratti dei backend strategici e della provenienza, seguito da test isolati e dal collegamento di un servizio alla volta. La rappresentazione PROV-O dovrà esplicitare entità, attività, agenti e relazioni di derivazione; l'esportazione dovrà essere verificata come RDF, senza equiparare gli attuali campi JSON a un'implementazione già conforme [PROVO]. La registrazione sul ledger dovrà conservare ricevute effettive e distinguere l'invio della richiesta dalla conferma della transazione.

Restano inoltre la valutazione indipendente delle stime e della qualità delle candidate, l'estensione dell'inventario analizzato e la raccolta continuativa da un deployment d'interesse. L'eventuale applicazione di una mitigazione richiederà un servizio dedicato e un esito osservabile, distinto dalla sola selezione. Il contributo verificato in questa fase riguarda l'integrazione e la coerenza del flusso, non l'efficacia operativa delle azioni proposte.

### 18.1 Riferimenti tecnici dell'integrazione

Le specifiche seguenti definiscono i protocolli e i formati utilizzati. Le policy di mapping, i controlli aggiunti alla sessione, la disponibilità dei tool per fase e i limiti di recupero sono scelte del prototipo, non algoritmi attribuiti a tali fonti.

**[MCP-HTTP]** Model Context Protocol contributors. *Transports*, specifica del protocollo adottata. https://modelcontextprotocol.io/specification/2025-06-18/basic/transports

**[MCP-TOOLS]** Model Context Protocol contributors. *Tools*, discovery, invocazione e schemi dei risultati. https://modelcontextprotocol.io/specification/2025-06-18/server/tools

**[OTEL-LOG]** OpenTelemetry. *Logs Data Model*, struttura e significato dei tempi del record. https://opentelemetry.io/docs/specs/otel/logs/data-model/

**[CDX-MAVEN]** CycloneDX. *Maven plugin: makeAggregateBom*. La versione verificata nel progetto è 2.9.3. https://cyclonedx.github.io/cyclonedx-maven-plugin/makeAggregateBom-mojo.html

**[OSV-QUERY]** OSV. *POST /v1/query*, ricerca per pacchetto/versione e paginazione. https://google.github.io/osv.dev/post-v1-query/

**[OSV-SCHEMA]** OpenSSF. *Open Source Vulnerability format*, alias, record ritirati e range delle versioni. https://ossf.github.io/osv-schema/

**[CAMEL-SDK]** CAMEL-AI. *CAMEL repository*, versione 0.2.90; codice dell'SDK utilizzato per agenti, cloni e ciclo dei tool. https://github.com/camel-ai/camel/tree/v0.2.90

**[BASE-CTI]** sisinflab-swot. *agent-based-cti-argumentation-pipeline*, repository privato e copia locale sul branch `costa-thesis`. Baseline esaminata: commit `3b483624286262f2e0ac94b4b950b904a5dc2ad4`. Collegamento e aggiunte del servizio sono documentati in `docs/owl-cti-integration.md` e `docs/cti-workforce.md`.

**[PROVO]** W3C. *PROV-O: The PROV Ontology*. Riferimento per il mapping previsto della provenienza. https://www.w3.org/TR/prov-o/

### 18.2 Riferimenti implementativi e sperimentali

| Ambito | Documentazione e sorgenti del progetto |
|---|---|
| Configurazione e MCP | `thesis_agents/backends.py`, `thesis_agents/mcp/`, `docs/mcp-strategic.md` |
| Correlazione CTI | `thesis_agents/tools/cti_mcp.py`, `docs/cti-workforce.md` |
| Acquisizione OTel | `thesis_agents/tools/telemetry_http.py`, `services/otel_gateway/`, `docs/opentelemetry-integration.md` |
| SBOM e OSV | `thesis_agents/tools/sbom_http.py`, `services/sbom_gateway/`, `docs/sbom-osv-integration.md` |
| Applicazione osservata | `examples/observed-app/`, `docs/observed-app-integration.md` |
| Artefatti e ciclo CAMEL | `thesis_agents/orchestration/artifacts.py`, `chat_agent.py`, `strategic_policy.py`, `publication_tools.py` nella stessa directory |
| Prove preliminari | `docs/observed-app-ollama.md`, `docs/ollama-contract-tests.md` |
| Ripetizioni e audit aggiornati | `docs/agent-tool-phases.md`, con riferimenti ai manifest e alle evidenze locali |
