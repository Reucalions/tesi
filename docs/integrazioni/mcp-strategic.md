# MCP Tool Layer dello StrategicAgent

Sul branch `full` sono disponibili client HTTP/stdio, server mock separato e adapter
per `rank_graph`, `validate_countermeasure` e `record_provenance`. Il collegamento
usa l'SDK MCP: handshake, discovery degli schemi e `tools/call`
sono effettivi. Gli algoritmi restano dimostrativi; non sono collegati BWAF reale,
Tiny-ME, Fabric o un exporter PROV-O.

Dal 31 ottobre e disponibile anche il client nativo del bridge SaaS condiviso,
collaudato con bridge e REST effettivi, Fabric e autenticazione simulati.
I suoi quattro tool hanno un contratto diverso dagli adapter MVP descritti sotto.

## Collegamento stdio e bridge SaaS condiviso

Per provare il trasporto con i quattro backend mock, senza avviare server a mano:

```bash
.venv/bin/python -m thesis_agents.mcp.probe \
  --backends config/backends.mcp-stdio-mock.json --check-config
```

Il profilo funziona dalla radice del repository e usa `.venv/bin/python`.
La CLI CAMEL accetta lo stesso `--backends`: ogni backend avvia un processo
indipendente, con i contratti MVP e i soli tool del ruolo. Il client chiude i
processi anche dopo timeout, crash o risposte non valide. I record mock restano
in `output/mcp-stdio-mock-store/`; `--mode fixtures` richiede backend locali.

Per il bridge condiviso usare il profilo dedicato
`config/mcp.shared-stdio.example.json`, adattando eseguibile Node >=22.12,
percorso `build/index.js` e `cwd` alla propria installazione gia compilata.
`env_from` associa variabili del processo figlio a nomi di variabili del padre:
l'esempio richiede `FABLO_REST_URL`, `FABLO_USER`, `FABLO_PASSWORD` nell'ambiente
o nel `.env` del framework. Il file salvato contiene i nomi, mai i valori.
In alternativa si puo omettere `env_from` e usare il `.env` caricato dal bridge
nel proprio `cwd`. L'SDK eredita le proprie variabili standard e aggiunge solo
quelle indicate; non copia indiscriminatamente l'ambiente del framework.

```bash
.venv/bin/python -m thesis_agents.mcp.shared_probe \
  --profile config/mcp.shared-stdio.example.json --check-config \
  --output-dir output/shared-discovery
```

La discovery non chiama REST/Fabric e non dimostra la disponibilita dei servizi.
Controlla identita del server e schemi congelati dei quattro tool: il bridge
ne espone 19, il client ne autorizza quattro. `outputSchema` e assente nel bridge;
gli output vengono verificati con modelli Pydantic dedicati. I contratti HTTP/MVP
mantengono i controlli precedenti. `expected_kind` nel profilo condiviso e una
aspettativa dell'operatore: il wire condiviso non contiene `backend_kind`.

Per una singola richiesta gia preparata secondo il contratto nativo:

```bash
.venv/bin/python -m thesis_agents.mcp.shared_probe \
  --profile config/mcp.shared-stdio.example.json \
  --tool rank_remediations --request /percorso/rank-request.json \
  --output-dir output/shared-rank
```

Ogni directory deve essere nuova. Sono conservati profilo, richiesta, risposta,
audit con digest/esito e stderr separato del processo; anche gli audit dei
fallimenti restano disponibili. Comando e argomenti sono separati e non passano
attraverso una shell. I timeout chiudono la sessione; il client non ritenta
automaticamente chiamate che potrebbero avere gia prodotto effetti remoti.

| Tool condiviso | Input essenziale | Verifiche locali |
| --- | --- | --- |
| `rank_remediations` | `cve_id`, `candidates: [{id,name}]`; opzionali `graph`, `asset_context`, `knowledge_snapshot_id`, `ontology_version` | Una CVE, ID/nomi esatti, score nativi finiti senza normalizzazione, ordine/rank, digest REST equivalente, snapshot richiesto |
| `validate_countermeasure` | `asset_iri`, `countermeasure_iri`, opzionale `ontology_id` | IRI e ontologia richiesti, campi nativi ExplainAffinity, esito coerente con penalita e condizioni |
| `get_decision` | `decision_id` | Identita, ranking, digest e assurance; confronto con il ranking della stessa sessione |
| `get_provenance` | `decision_id` | Identita, snapshot e assurance originale; confronto con il ranking della stessa sessione |

`SharedServicesClient` riusa un solo processo/sessione per i quattro tool.
L'envelope deve essere `{ok,action,payload}` con azione esatta. Gli errori tecnici
espongono soltanto il codice validato (`MCPToolError.code`); `rejected` e
`requires_prerequisites` restano risultati semantici. Il contesto asset accettato
contiene solo `assetIri`, `productName`, `vendor`, `version`, `cpe` come stringhe.
Il grafo nativo controlla riferimenti e candidate, ma la sua topologia non
costituisce ancora il mapping canonico di supporto, attacco e pesi.

Il client di dominio e utilizzabile dal framework e dal probe. Il passaggio dagli
artefatti di `ArtifactSession` a questi tool richiede ancora generatore, perimetro
per CVE, grafo canonico e rappresentazione dei vincoli negli IRI ontologici.
`get_provenance` legge il record SaaS di ranking; la finalizzazione della
raccomandazione MAS e il commit/rilettura on-chain restano da completare.

Verifiche: 42 test aggiunti su stdio e contratti condivisi; collaudo ripetibile
in `tests/support/saas_stdio_framework_smoke.py`, evidenze in
`output/mcp-stdio-20261031/`. La verifica dei servizi reali e rinviata alla fine
della progettazione per indicazione dell'utente.

## Avvio

Dalla radice del repository, avvia il server in un terminale:

```bash
.venv/bin/python -m thesis_agents.mcp.strategic_mock_server \
  --port 8002 --data-dir output/mcp-mock-store
```

Il server ascolta su `127.0.0.1` e conserva i record ricevuti in
`output/mcp-mock-store/provenance.sqlite3`. Il database appartiene al processo
server e sopravvive al suo riavvio. Si termina il server con Ctrl-C.

In un secondo terminale verifica la configurazione senza LLM:

```bash
.venv/bin/python -m thesis_agents.mcp.probe \
  --backends config/backends.mcp-strategic-mock.json --check-config
```

Questo comando esegue handshake e discovery per i tre backend; non invoca tool
di dominio e non registra record. Non verifica il comportamento degli algoritmi
né il tipo effettivo di backend: `expected_kind` viene confrontato anche con
la dichiarazione presente nella risposta di ciascuna successiva invocazione.

Per usare il profilo con CAMEL e il modello configurato in `.env`:

```bash
.venv/bin/python -m thesis_agents.main --mode camel \
  --backends config/backends.mcp-strategic-mock.json
```

Con i profili HTTP la CLI non avvia il server. Se uno dei servizi richiesti non è raggiungibile o
non espone il contratto atteso, la Workforce non parte. `--mode fixtures` resta
riservato ai backend locali. Il runner `thesis_agents.demo` non inoltra ancora
`--backends`: per questa integrazione si usa `thesis_agents.main`.

## Profili disponibili

| File in `config/` | Lookup | Ranking, validazione, provenienza |
|---|---|---|
| `backends.local-mock.json` | Locale | Locali |
| `backends.mcp-mock.json` | MCP mock, porta 8001 | Locali; conserva il primo esperimento |
| `backends.mcp-strategic-mock.json` | Locale | MCP mock, porta 8002 |
| `backends.mcp-all-mock.json` | MCP mock, porta 8001 | MCP mock, porta 8002 |
| `backends.mcp-stdio-mock.json` | Processo MCP mock | Processi MCP mock |

Il profilo strategico è il punto di partenza coerente con lo schema della tesi.
Il profilo `all-mock` include anche il lookup remoto del primo incremento e
richiede entrambi i server. Per avviare quello del lookup:

```bash
.venv/bin/python -m thesis_agents.mcp.mock_server --port 8001
```

`all-mock` significa tutti i quattro backend **attualmente configurabili**;
OpenTelemetry, OWL CTI e SBOM/OSV reali restano integrazioni successive. I tre
ingressi useranno servizi remoti con contratti propri, tramite API o MCP secondo
l'interfaccia disponibile. Non sono obbligati a passare dal server strategico.

Ogni voce del profilo può essere `{"transport": "local-mock"}` oppure una
configurazione MCP HTTP con `url`, `expected_kind`, `timeout_seconds` e, se necessario,
`token_env`, oppure stdio con `transport: "mcp-stdio"`, `command`, `args`, `cwd`
assoluto opzionale, `env_from`, `expected_kind`, `timeout_seconds`.
La vecchia stringa `"local-mock"` viene normalizzata per compatibilità.
Si può quindi migrare un solo servizio per volta, anche verso endpoint differenti.
Il client apre una sessione MCP per backend, con il solo tool autorizzato per quel
ruolo; non espone automaticamente agli agenti gli altri tool scoperti sul server.

Per un servizio reale occorrono endpoint e contratti compatibili verificati:
impostare `expected_kind: "real"` non realizza l'integrazione. Il tipo dichiarato
dal servizio non è una certificazione. Un bearer token viene letto dall'ambiente
tramite il nome in `token_env`, senza scriverne il valore nel profilo o nell'audit.
I server mock non implementano autenticazione e sono predisposti per loopback.

## Flusso degli agenti e contratti

```text
TelemetryAgent → RuntimeEvidence ────────────────┐
                     ↓                          │
VulnerabilityAgent → VulnerabilityReport ────────┼→ StrategicAgent
                     ↓                          │     ↓ tool di ruolo
CountermeasureAgent → CandidateStrategies ───────┘  ArtifactSession
                                                      ↓ adapter
                                                 client MCP HTTP
                                                      ↓
                                               server mock separato
```

Il CountermeasureAgent legge sia `RuntimeEvidence` sia `VulnerabilityReport`.
Lo Strategic continua a leggere i tre artefatti distinti tramite `get_context`.
Costruzione del grafo, pubblicazioni e decisione finale rimangono nella sessione.
Scheduling CAMEL, DAG, ranking in ordine e fallback dopo un rifiuto mantengono
la semantica precedente. Nel prompt dello Strategic l'identità dei backend
deriva dai risultati dei tool: non si assume più che siano tutti locali.

| Tool MCP | Richiesta | Risposta di dominio | Versione |
|---|---|---|---|
| `rank_graph` | `graph: ArgumentationGraph` | `RankingResult` | `argumentation-ranking-v1` |
| `validate_countermeasure` | `strategy: CountermeasureCandidate`, `context: DecisionContext` | `SemanticValidationResult` | `semantic-validation-v1` |
| `record_provenance` | `record: ProvenanceRecord` | `ProvenanceReceipt` | `provenance-record-v1` |

`DecisionContext` contiene evidence, report, capacità e policy come campi distinti.
La sessione sceglie questi input dallo stato validato; il modello continua a
richiedere la validazione soltanto tramite l'ID della candidata.

L'envelope remoto contiene `contract`, `backend_kind`, `backend`,
`request_sha256` e `result`. Il digest copre il JSON degli argomenti, compresi
pesi, candidate e policy. Il client controlla digest, identità del backend,
grafo e insieme delle strategie, oppure l'ID della candidata validata.
Pydantic ricontrolla gli invarianti dei risultati. Un hash corrispondente lega
la risposta all'input dichiarato; non dimostra che il servizio abbia calcolato
correttamente il risultato.

La discovery confronta conservativamente gli schemi v1, ignorando titoli e
descrizioni. Un backend con formato diverso richiede un adapter concordato.
I nomi di questi contratti non implicano compatibilità già verificata con gli
smart contract dei repository privati.

## Provenienza e ricevute

Il server mock riusa senza cambiarli i backend numerici e semantici esistenti.
Per la provenienza scrive il documento JSON in SQLite, indicizzato per `run_id`:
stesso run e stesso contenuto restituiscono la medesima ricevuta; contenuti
diversi per lo stesso run vengono rifiutati. L'inserimento è transazionale.

La ricevuta contiene `run_id`, `stored`, `record_sha256`, `receipt_id` e
`backend`. Il client accetta solo `stored: true` con run e digest corrispondenti.
La ricevuta mock è riconoscibile dal prefisso `mock:` e dal backend
`sqlite-provenance-mock-v1`; non è un transaction ID Fabric.

Nel run vengono conservati:

- `backends.json`: profilo effettivo normalizzato e `run_id`;
- `mcp_events.jsonl`: connessioni, ruolo del backend, chiamate, digest ed esiti;
- `provenance.json`: copia locale del documento inviato;
- `provenance_receipt.json`: ricevuta remota verificata, separata dal documento.

Con MCP, `ProvenanceRecord.backend` indica il canale configurato
(`mcp-provenance-mock-v1` o `mcp-provenance-real-v1`); la ricevuta identifica il
backend dichiarato dal servizio. Il default dei record locali rimane
`local-provenance-mock-v1`, e gli output storici restano leggibili.

`record_sha256` usa il JSON UTF-8 con chiavi ordinate, separatori compatti e
senza NaN/Infinity, come `digest()` nel client. Non è l'hash dei byte indentati
di `provenance.json`. Gli hash delle entità contenuti nel documento riguardano
invece i byte dei singoli artefatti, secondo il contratto precedente.

Una ripetizione di `record_provenance` nella sessione restituisce la ricevuta
già ottenuta. Il client non ritenta automaticamente le chiamate fallite e non
ripiega sul mock locale. Dopo un errore di rete su una scrittura, il servizio
potrebbe averla già eseguita: il run non la dichiara confermata senza ricevuta.
Il mock permette una successiva verifica idempotente reinviando lo stesso record.
Un backend ledger dovrà concordare anche il recupero dello stato di transazione.

## Prova di singoli tool senza inferenza

Il probe accetta un file con l'oggetto richiesta descritto nella tabella:

```bash
.venv/bin/python -m thesis_agents.mcp.probe \
  --backends config/backends.mcp-strategic-mock.json \
  --service ranking --request /percorso/ranking-request.json
```

`ranking-request.json` deve contenere `{"graph": ...}`; per la validazione si
usano `--service semantic` e un oggetto con `strategy` e `context`. Il probe
valida il file prima di effettuare la chiamata. Per registrare un documento:

```bash
.venv/bin/python -m thesis_agents.mcp.probe \
  --backends config/backends.mcp-strategic-mock.json \
  --service provenance --request /percorso/provenance-request.json \
  --receipt /percorso/nuova-ricevuta.json
```

Quest'ultimo comando **esegue una scrittura** sul backend configurato. La richiesta
contiene `{"record": ...}`. Il file della ricevuta deve trovarsi in una directory
esistente e non può essere sovrascritto con una ricevuta differente.

## Verifiche e limiti

Verifica conclusa: **147 test superati** con `pytest -q --tb=short`;
`ruff check`, `ruff format --check`, `git diff --check` e `pip check` superati.

I test attraversano CLI, quattro agenti e Workforce CAMEL con inferenza
programmata e server MCP su processi separati. I quattro scenari dimostrativi
sono ripetuti due volte con nuove sessioni e output separati. Non è una nuova
matrice di valutazione LLM: le candidate sono quelle deterministiche dei test.
La prova impedisce ai backend locali nel processo client di eseguire operazioni,
per verificare che le richieste passino effettivamente dalla rete.

Sono verificati anche riferimenti errati, digest incoerenti, tipo del backend,
ricevute non confermate, conflitti di persistenza, discovery incompleta,
chiusura delle connessioni dopo un avvio parziale e compatibilità del default.

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest tests/test_mcp.py tests/test_mcp_strategic.py -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
```

Sono stati collaudati anche gli entrypoint pubblici `strategic_mock_server`
e `probe` in processi separati: discovery dei tre contratti, ranking nominale,
validazione accettata, registrazione e reinvio idempotente della provenienza.
Richieste, risposte, comandi ed esito sono conservati in
[questa prova CLI](../../output/mcp-strategic-smoke-20261002T122012Z-709aa205/summary.json).
Il server è stato chiuso al termine. Gli input provengono da fixture; nessuna
inferenza LLM è stata eseguita nel collaudo MCP.

Restano successivi: mapping al grafo BWAF reale, collegamenti ai contratti e a
Fabric, store/retrieve remoto degli asset generici, export PROV-O, ingressi
OpenTelemetry/OWL CTI/SBOM/OSV e applicazione delle mitigazioni. Questo incremento
completa i collegamenti MCP dei quattro backend esistenti, non l'intera
architettura finale della tesi. Il ledger manterrà il ruolo di audit; la memoria
operativa rimane in `ArtifactSession`.

## File e riferimenti

- [Contratti](../../thesis_agents/mcp/contracts.py),
  [adapter strategici](../../thesis_agents/tools/strategic_mcp.py),
  [server](../../thesis_agents/mcp/strategic_mock_server.py).
- [Configurazione](../../thesis_agents/backends.py),
  [probe](../../thesis_agents/mcp/probe.py),
  [test strategici](../../tests/test_mcp_strategic.py).
- [Primo esperimento di lookup](mcp-lookup.md),
  [piano di integrazione e vincoli delle baseline](../prossime-azioni.md).
- [SDK MCP 1.30.0](https://github.com/modelcontextprotocol/python-sdk/tree/v1.30.0),
  [specifica dei tool](https://modelcontextprotocol.io/specification/2025-06-18/server/tools).

I contratti v1, gli adapter e la ricevuta mock sono scelte implementative di
questo progetto, non algoritmi o formati attribuiti ai repository esterni.
