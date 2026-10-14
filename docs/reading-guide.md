# Guida alla lettura del codice commentato

I file Python contengono commenti in italiano su responsabilità, input/output, controlli e scelte implementative. I commenti sono esterni alle stringhe `PROMPT` e alle docstring operative dei tool: queste ultime vengono usate da CAMEL per descrivere le funzioni al modello. Anche le docstring dei modelli possono influenzare i JSON Schema, quindi sono state preservate.

## Ordine di lettura suggerito

1. `thesis_agents/main.py`: come nasce un run e come vengono scelte le modalità.
2. `schemas/`: quali dati possono attraversare i confini fra componenti.
3. `orchestration/artifacts.py`: chi può pubblicare cosa e quali invarianti vengono controllati.
4. `orchestration/workforce.py` e `agents/`: come CAMEL assegna i task e i tre produttori convergono nello StrategicAgent.
5. `backends.py` e `tools/`: selezione dei servizi, adapter remoti e backend mock.
6. `tests/`: esempi eseguibili di casi ammessi, errori e controlli del DAG.

## Avvio, configurazione e dimostrazione

| File | Cosa osservare nei commenti |
|---|---|
| [main.py](../main.py) | Wrapper dello script locale e conversione del risultato in codice di uscita. |
| [thesis_agents/main.py](../thesis_agents/main.py) | Parsing degli argomenti, export degli schemi, `.env`, risorsa JSON, directory del run, scelta CAMEL/fixtures ed errori gestiti. |
| [config.py](../thesis_agents/config.py) | Configurazione immutabile del modello, precedenza delle chiavi, URL opzionale e budget di contesto esplicito prima della costruzione del backend. |
| [fixtures.py](../thesis_agents/fixtures.py) | Proposte statiche, pubblicazioni attraverso gli stessi contratti, ranking e fallback senza inferenza. |
| [demo.py](../thesis_agents/demo.py) | Runner della matrice: processi CLI isolati, configurazione locale, input, timeout e riepiloghi. |
| [demo_audit.py](../thesis_agents/demo_audit.py) | Audit in sola lettura degli artefatti e dei messaggi consegnati allo Strategic. |
| [backends.py](../thesis_agents/backends.py) | Profilo dei backend, connessioni HTTP/MCP e audit delle chiamate. |
| [prepare.py](../examples/observed-app/prepare.py) | Build e osservazione dell'applicazione locale, verifica delle fonti e generazione del profilo; esterno alla Workforce. |
| [log4j_case.json](../thesis_agents/data/log4j_case.json) | Input dimostrativo: la [guida dei dati](../thesis_agents/data/README.md) descrive ogni campo e variazioni del caso. |

`mode` e `workflow` hanno scopi diversi. `mode=camel` usa inferenza tramite CAMEL; `mode=fixtures` esercita i contratti con dati prefissati. Solo nella prima modalità `workflow` decide se usare task dichiarati nella pipeline o decomposizione gestita dal modello.

## Stato e orchestrazione

| File | Cosa osservare nei commenti |
|---|---|
| [artifacts.py](../thesis_agents/orchestration/artifacts.py) | Copie profonde, scritture idempotenti, cache del lookup, contesto separato per produttore, validazioni in ordine e controlli della decisione. |
| [explanations.py](../thesis_agents/orchestration/explanations.py) | Spiegazione della decisione derivata da campi strutturati, riferimenti alle fonti e distinzione fra dati riportati, stime e limiti. |
| [publication_tools.py](../thesis_agents/orchestration/publication_tools.py) | Payload Pydantic strutturati esposti a CAMEL e serializzazione nell'adapter verso la sessione, senza cambiare i contratti degli artefatti. |
| [workforce.py](../thesis_agents/orchestration/workforce.py) | Ruoli, task, DAG esplicito, componenti gestionali CAMEL, tool concessi ai worker e verifica finale del run. |
| [chat_agent.py](../thesis_agents/orchestration/chat_agent.py) | Sottoclasse CAMEL che conserva memoria integrale e opzioni dei cloni, senza sintesi automatica degli artefatti. |
| [strategic_policy.py](../thesis_agents/orchestration/strategic_policy.py) | Determina il prossimo tool dagli artefatti validati e limita il recupero dopo risposte testuali premature; non esegue il dominio. |
| [bounded_model.py](../thesis_agents/orchestration/bounded_model.py) | Controllo opzionale del budget prima del provider: richiesta completa stimata, risposta riservata e margine. |
| [task_results.py](../thesis_agents/orchestration/task_results.py) | Distingue le chiamate ai tool dal riepilogo finale e rifiuta il successo del worker quando mancano gli artefatti richiesti. |

Tre strutture non vanno confuse: la memoria conversazionale di ChatAgent contiene i messaggi del modello; `TaskResult` è il risultato gestionale del task; `ArtifactSession` contiene gli output di dominio autorevoli, validati da Pydantic. Il successo della Workforce viene accettato solo se esistono anche tutti gli artefatti previsti.

`ArtifactWorkforce` adatta la gestione dei fallimenti della pipeline: i task
dipendenti da produttori definitivamente falliti vengono bloccati. Il gestore
`ArtifactTaskHandler` verifica inoltre gli input prima dell'inferenza del worker;
non costruisce o pubblica gli artefatti mancanti.

`_commit` e `require` sono funzioni interne per scrivere e leggere modelli. I metodi pubblici di pubblicazione applicano vincoli aggiuntivi specifici: per esempio, una `RuntimeEvidence` può essere valida per Pydantic ma comunque rifiutata perché altera la versione dell'input.

## Ruoli degli agenti

| File | Responsabilità |
|---|---|
| [telemetry.py](../thesis_agents/agents/telemetry.py) | Normalizzare i fatti osservati e pubblicare solo `RuntimeEvidence`. |
| [vulnerability.py](../thesis_agents/agents/vulnerability.py) | Usare l'osservazione software per il lookup e pubblicare un rapporto separato, preservando i finding restituiti. |
| [countermeasure.py](../thesis_agents/agents/countermeasure.py) | Generare alternative da evidence e report, senza decidere ranking o validità semantica. |
| [strategic.py](../thesis_agents/agents/strategic.py) | Leggere tre input distinti, coordinare i tool, scegliere il primo candidato accettato e registrare decisione/provenienza. |

Questi file non creano direttamente agenti: espongono `PROMPT` e `TOOLS`. La Workforce li usa per costruire quattro veri `ChatAgent`. Le tuple `TOOLS` limitano le operazioni disponibili a ogni ruolo; i controlli della sessione ne verificano i risultati.

## Modelli Pydantic

| File | Contratti e controlli |
|---|---|
| [base.py](../thesis_agents/schemas/base.py) | Identificatori, testo non vuoto, score finiti, rifiuto dei campi extra e helper per l'unicità. |
| [telemetry.py](../thesis_agents/schemas/telemetry.py) | Input statico, osservazione software, evidence e identificatori non duplicati. |
| [telemetry_source.py](../thesis_agents/schemas/telemetry_source.py) | Selettore OTel, snapshot, fonte e finestra temporale; fatti sconosciuti conservati come `null`. |
| [cti.py](../thesis_agents/schemas/cti.py) | Identità CTI, regole valutate, metadati mancanti e provenienza del dataset. |
| [supply_chain.py](../thesis_agents/schemas/supply_chain.py) | Associazione SBOM, query e paginazione OSV, snapshot e proiezione per gli agenti. |
| [vulnerability.py](../thesis_agents/schemas/vulnerability.py) | Finding, risultato del lookup e report; distinzione fra caso correlato e caso non supportato. |
| [countermeasure.py](../thesis_agents/schemas/countermeasure.py) | Categorie di azione, candidate, stime, prerequisiti e contesto del controllo semantico. |
| [argumentation.py](../thesis_agents/schemas/argumentation.py) | Nodi, archi e ranking; integrità dei riferimenti e ordinamento con tie-break. |
| [decision.py](../thesis_agents/schemas/decision.py) | Singolo esito, registro dei tentativi e decisione con vincoli sulla selezione. |
| [provenance.py](../thesis_agents/schemas/provenance.py) | Entità/file/digest e attività con input, output e ruolo produttore. |

I validatori Pydantic controllano i dati di un modello. I confronti fra modelli pubblicati, come la corrispondenza del ranking con le candidate, richiedono la sessione. I campi testuali restano testo: il superamento della validazione strutturale non certifica la correttezza scientifica di una motivazione generata.

## Interfacce, adapter e backend locali

| File | Responsabilità e limite |
|---|---|
| [interfaces.py](../thesis_agents/tools/interfaces.py) | Sei `Protocol`: telemetria, supply chain, vulnerabilità, ranking, semantica e provenienza, separati da CAMEL. |
| [telemetry_http.py](../thesis_agents/tools/telemetry_http.py) | Acquisizione HTTP e mapping validato dello snapshot in runtime evidence. |
| [cti_mcp.py](../thesis_agents/tools/cti_mcp.py) | Lookup cve2owl tramite MCP, snapshot e mapping conservativo nel report. |
| [sbom_http.py](../thesis_agents/tools/sbom_http.py) | Acquisizione della fonte SBOM/OSV da un gateway separato. |
| [strategic_mcp.py](../thesis_agents/tools/strategic_mcp.py) | Contratti remoti dei tool strategici; il trasporto MCP non rende reale un backend mock. |
| [vulnerability_mock.py](../thesis_agents/tools/vulnerability_mock.py) | Corrispondenza esatta su una coppia pacchetto/versione e conservazione del riferimento all'evidenza. |
| [ranking_mock.py](../thesis_agents/tools/ranking_mock.py) | Proiezione delle stime in nodi/archi, somma pesata a un passo, clamp e tie-break; non è il BWAF reale. |
| [semantic_mock.py](../thesis_agents/tools/semantic_mock.py) | Requisiti obbligatori, capacità disponibili e azioni proibite; non interpreta ontologie o caveat liberi. |
| [provenance_mock.py](../thesis_agents/tools/provenance_mock.py) | Scrittura locale idempotente del record e ricevuta; non esegue transazioni Fabric. |

La dependency injection avviene nella sessione e in `connect_backends`, prima
della Workforce. Senza profilo rimangono input statico e tool mock; gli ingressi
remoti sono espliciti. I processi degli agenti conoscono i contratti pubblici,
non importano gli algoritmi dei repository backend. Dettagli in
[architettura](architecture.md) e [piano MCP](mcp-integration-plan.md).

La [prova Ollama dei tre ingressi](observed-app-ollama.md) è il riferimento per
inferenza effettiva, tempi, dati consegnati agli agenti e criticità recuperate.
L'audit di `demo_audit.py` nel suo insieme resta specifico della matrice mock;
il run remoto conserva un audit dedicato, senza assumere risultati mock del lookup.

## Test

| File | Che cosa dimostra |
|---|---|
| [conftest.py](../tests/conftest.py) | Preparazione di un caso e di una directory temporanea indipendenti per ogni test. |
| [test_contracts.py](../tests/test_contracts.py) | Regole di dominio, casi negativi, idempotenza, fallback, provenienza e presenza dei tre input strategici. Ogni test spiega lo scenario che sta simulando. |
| [test_explanations.py](../tests/test_explanations.py) | Separazione del commento non verificato, rifiuto di claim alterati e compatibilità esplicita dei JSON storici. |
| [test_demo_runner.py](../tests/test_demo_runner.py) | Matrice fixture, timeout, fallimenti parziali, conservazione degli output e regressioni dell'audit. |
| [test_cli.py](../tests/test_cli.py) | Codici di uscita, protezione degli output, export degli schemi e mancanza di configurazione. |
| [test_camel_integration.py](../tests/test_camel_integration.py) | Workforce e tool calling reali con inferenza programmata; controllo dei dati effettivamente consegnati allo StrategicAgent. |

Alcuni test alterano deliberatamente `_artifacts`: è una simulazione di stato incoerente per verificare i controlli, non un modo previsto di usare l'applicazione. Il backend programmato dei test non viene usato dal normale comando `python main.py`.

## File di package, progetto e documentazione

| File | Scopo |
|---|---|
| [thesis_agents/__init__.py](../thesis_agents/__init__.py) | Identifica la radice del package senza avviare l'applicazione. |
| [agents/__init__.py](../thesis_agents/agents/__init__.py) | Documenta la raccolta dei ruoli definiti tramite prompt/tool. |
| [orchestration/__init__.py](../thesis_agents/orchestration/__init__.py) | Distingue configurazione Workforce da gestione degli artefatti. |
| [schemas/__init__.py](../thesis_agents/schemas/__init__.py) | Riesporta i modelli pubblici e spiega l'elenco `__all__`. |
| [tools/__init__.py](../thesis_agents/tools/__init__.py) | Identifica le implementazioni sostituibili dei backend. |
| [pyproject.toml](../pyproject.toml) | Packaging, dipendenze dirette, comando installato, risorse JSON e configurazione pytest/Ruff. |
| [requirements.lock](../requirements.lock) | Versioni esatte verificate, incluse dipendenze transitive e strumenti di sviluppo. |
| [.env.example](../.env.example) | Configurazione d'esempio per modello, credenziale, endpoint e timeout. |
| [.gitignore](../.gitignore) | Esclusione da Git di credenziali locali, ambiente, cache, output e file generati. |
| [README.md](../README.md) | Istruzioni per installare, eseguire e verificare il prototipo. |
| [architecture.md](architecture.md) | Contratti architetturali, DAG, limiti del mock e futuri punti di integrazione. |
| [data/README.md](../thesis_agents/data/README.md) | Spiegazione campo per campo del JSON, che non può contenere commenti inline. |
| [reading-guide.md](reading-guide.md) | Questa mappa, che collega la documentazione ai commenti nei sorgenti. |
| [relazione-mockup.md](relazione-mockup.md) | Prima relazione complessiva: motivazioni, architettura, agenti/LLM, comandi, attività, risultati e integrazioni future. |

Le cartelle `.venv`, `.git`, le cache e gli output generati non sono sorgenti da annotare: gli output si interpretano attraverso i modelli e la documentazione del progetto.
