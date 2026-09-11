# Guida alla lettura del codice commentato

I file Python contengono commenti in italiano su responsabilità, input/output, controlli e scelte implementative. I commenti sono esterni alle stringhe `PROMPT` e alle docstring operative dei tool: queste ultime vengono usate da CAMEL per descrivere le funzioni al modello. Anche le docstring dei modelli possono influenzare i JSON Schema, quindi sono state preservate.

## Ordine di lettura suggerito

1. `thesis_agents/main.py`: come nasce un run e come vengono scelte le modalità.
2. `schemas/`: quali dati possono attraversare i confini fra componenti.
3. `orchestration/artifacts.py`: chi può pubblicare cosa e quali invarianti vengono controllati.
4. `orchestration/workforce.py` e `agents/`: come CAMEL assegna i task e i tre produttori convergono nello StrategicAgent.
5. `tools/`: che cosa simulano i backend e quali operazioni rimangono deterministiche.
6. `tests/`: esempi eseguibili di casi ammessi, errori e controlli del DAG.

## Avvio, configurazione e dimostrazione

| File | Cosa osservare nei commenti |
|---|---|
| [main.py](../main.py) | Wrapper dello script locale e conversione del risultato in codice di uscita. |
| [thesis_agents/main.py](../thesis_agents/main.py) | Parsing degli argomenti, export degli schemi, `.env`, risorsa JSON, directory del run, scelta CAMEL/fixtures ed errori gestiti. |
| [config.py](../thesis_agents/config.py) | Configurazione immutabile del modello, precedenza delle chiavi, URL opzionale e costruzione differita del backend. |
| [fixtures.py](../thesis_agents/fixtures.py) | Proposte statiche, pubblicazioni attraverso gli stessi contratti, ranking e fallback senza inferenza. |
| [log4j_case.json](../thesis_agents/data/log4j_case.json) | Input dimostrativo: la [guida dei dati](../thesis_agents/data/README.md) descrive ogni campo e variazioni del caso. |

`mode` e `workflow` hanno scopi diversi. `mode=camel` usa inferenza tramite CAMEL; `mode=fixtures` esercita i contratti con dati prefissati. Solo nella prima modalità `workflow` decide se usare task dichiarati nella pipeline o decomposizione gestita dal modello.

## Stato e orchestrazione

| File | Cosa osservare nei commenti |
|---|---|
| [artifacts.py](../thesis_agents/orchestration/artifacts.py) | Copie profonde, scritture idempotenti, cache del lookup, contesto separato per produttore, validazioni in ordine e controlli della decisione. |
| [workforce.py](../thesis_agents/orchestration/workforce.py) | Ruoli, task, DAG esplicito, componenti gestionali CAMEL, tool concessi ai worker e verifica finale del run. |
| [task_results.py](../thesis_agents/orchestration/task_results.py) | Distingue le chiamate ai tool dal riepilogo finale e rifiuta il successo del worker quando mancano gli artefatti richiesti. |

Tre strutture non vanno confuse: la memoria conversazionale di ChatAgent contiene i messaggi del modello; `TaskResult` è il risultato gestionale del task; `ArtifactSession` contiene gli output di dominio autorevoli, validati da Pydantic. Il successo della Workforce viene accettato solo se esistono anche tutti gli artefatti previsti.

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
| [vulnerability.py](../thesis_agents/schemas/vulnerability.py) | Finding, risultato del lookup e report; distinzione fra caso correlato e caso non supportato. |
| [countermeasure.py](../thesis_agents/schemas/countermeasure.py) | Categorie di azione, candidate, stime, prerequisiti e contesto del controllo semantico. |
| [argumentation.py](../thesis_agents/schemas/argumentation.py) | Nodi, archi e ranking; integrità dei riferimenti e ordinamento con tie-break. |
| [decision.py](../thesis_agents/schemas/decision.py) | Singolo esito, registro dei tentativi e decisione con vincoli sulla selezione. |
| [provenance.py](../thesis_agents/schemas/provenance.py) | Entità/file/digest e attività con input, output e ruolo produttore. |

I validatori Pydantic controllano i dati di un modello. I confronti fra modelli pubblicati, come la corrispondenza del ranking con le candidate, richiedono la sessione. I campi testuali restano testo: il superamento della validazione strutturale non certifica la correttezza scientifica di una motivazione generata.

## Interfacce e backend locali

| File | Responsabilità e limite |
|---|---|
| [interfaces.py](../thesis_agents/tools/interfaces.py) | Quattro `Protocol` per separare i backend dal framework degli agenti, senza imporre ereditarietà alle implementazioni. |
| [vulnerability_mock.py](../thesis_agents/tools/vulnerability_mock.py) | Corrispondenza esatta su una coppia pacchetto/versione e conservazione del riferimento all'evidenza. |
| [ranking_mock.py](../thesis_agents/tools/ranking_mock.py) | Proiezione delle stime in nodi/archi, somma pesata a un passo, clamp e tie-break; non è il BWAF reale. |
| [semantic_mock.py](../thesis_agents/tools/semantic_mock.py) | Requisiti obbligatori, capacità disponibili e azioni proibite; non interpreta ontologie o caveat liberi. |
| [provenance_mock.py](../thesis_agents/tools/provenance_mock.py) | Scrittura locale idempotente del record e ricevuta; non esegue transazioni Fabric. |

La dependency injection avviene nel costruttore di `ArtifactSession`: riceve implementazioni dei quattro contratti o usa i mock predefiniti. Cambiare un backend in futuro richiederà un adapter, non un nuovo prompt che chieda all'LLM di calcolare al suo posto.

## Test

| File | Che cosa dimostra |
|---|---|
| [conftest.py](../tests/conftest.py) | Preparazione di un caso e di una directory temporanea indipendenti per ogni test. |
| [test_contracts.py](../tests/test_contracts.py) | Regole di dominio, casi negativi, idempotenza, fallback, provenienza e presenza dei tre input strategici. Ogni test spiega lo scenario che sta simulando. |
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

Le cartelle `.venv`, `.git`, le cache e gli output generati non sono sorgenti da annotare: gli output si interpretano attraverso i modelli e la documentazione del progetto.
