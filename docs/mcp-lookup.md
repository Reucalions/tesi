# Primo collegamento MCP: lookup remoto con server mock

Il client e il server MCP sono implementati sul branch `full`. Questa guida
documenta il primo incremento, dedicato al lookup delle vulnerabilità. Il server
usa la fixture Log4j esistente; non interroga OSV, KG, smart contract o Fabric.
Il comportamento locale predefinito del mockup resta disponibile.

È ora disponibile anche il [MCP Tool Layer dello Strategic](mcp-strategic.md):
ranking, validazione e provenienza hanno adapter e un server mock dedicati.
Il profilo qui descritto conserva il solo lookup remoto per compatibilità.

## Avvio e prova senza LLM

Dalla radice del repository, in un terminale avvia il server separato:

```bash
.venv/bin/python -m thesis_agents.mcp.mock_server --port 8001
```

In un secondo terminale esegui il client di prova:

```bash
.venv/bin/python -m thesis_agents.mcp.probe --backends config/backends.mcp-mock.json
.venv/bin/python -m thesis_agents.mcp.probe --backends config/backends.mcp-mock.json --version 9.9.9
```

Il primo comando restituisce `matched` con la fixture CVE-2021-44228; il secondo
`unsupported`. Non sono inferenze né esecuzioni degli agenti. Il probe stampa
anche gli eventi MCP e termina con codice 1 su errori di rete o di contratto.
Il client non avvia il server: se è spento la chiamata fallisce esplicitamente.
Per terminare il server usa Ctrl-C nel suo terminale.

## Uso con gli agenti CAMEL

Con il server già attivo e `.env` configurato per il modello:

```bash
.venv/bin/python -m thesis_agents.main --mode camel --backends config/backends.mcp-mock.json
```

Per usare tutti i backend locali:

```bash
.venv/bin/python -m thesis_agents.main --mode camel --backends config/backends.local-mock.json
```

Omettendo `--backends` si mantiene esattamente la selezione locale precedente.
`--mode fixtures` accetta soltanto backend locali: per provare MCP senza LLM si
usa il probe o la suite di integrazione. Il runner `thesis_agents.demo` non
inoltra ancora profili backend; questi comandi usano la CLI `thesis_agents.main`.

## Percorso della chiamata

```text
VulnerabilityAgent → lookup_vulnerabilities() senza argomenti
  → ArtifactSession legge SoftwareObservation dal RuntimeEvidence
  → MCPVulnerabilityTool prepara LookupRequest
  → MCPClient invia tools/call via Streamable HTTP
  → server separato esegue il mock e restituisce LookupResponse
  → adapter verifica contratto, tipo di backend e riferimenti all'evidenza
  → ArtifactSession prepara VulnerabilityReport
  → l'agente pubblica il report tramite il tool esistente
```

L'output pubblico MCP contiene `contract: vulnerability-lookup-v1`,
`backend_kind`, `backend` e `result`. L'adapter restituisce alla sessione il
`LookupResult` già previsto dall'interfaccia, conservando il DAG e i tre input
distinti dello Strategic. `get_context` e le pubblicazioni restano locali.

Il client usa l'SDK MCP, non chiamate HTTP che simulano MCP: effettua handshake,
discovery paginata, controllo degli schemi e chiamata del tool. La connessione
resta aperta per il run in un loop dedicato AnyIO, utilizzabile dai tool sincroni
anche mentre CAMEL sta eseguendo un loop asincrono.

Il contratto v1 richiede uno schema di output dichiarato e confronta gli schemi
attesi ignorando titoli e descrizioni. È una verifica conservativa: un servizio
con un formato differente richiede un adapter/versione esplicita. Sono gestiti
`structuredContent` e un singolo blocco JSON di testo; con `outputSchema` l'SDK
richiede comunque il contenuto strutturato conforme. Testo libero, `isError`,
`ok: false`, stato/finding incoerenti o evidenze alterate non diventano report.

Dopo un errore di chiamata la connessione viene chiusa; una nuova connessione
richiede un nuovo contesto client/run. Non ci sono retry automatici né fallback
locali. L'errore raggiunge i controlli di task CAMEL e non si trasforma in un
risultato di dominio `unsupported`.

## Configurazione e tracciamento

`config/backends.mcp-mock.json` seleziona HTTP soltanto per `vulnerability`;
ranking, validazione e provenienza sono esplicitamente `local-mock`. Il campo
`expected_kind` impedisce di accettare un server che si dichiara mock quando si
richiede un backend reale, ma non certifica la veridicità di quella dichiarazione.
Non esiste ancora un profilo full con tutti i servizi dello schema finale.

Il client legge eventualmente un bearer token dalla variabile indicata in
`token_env`. Nel file di configurazione si mette il nome della variabile, non il
segreto. Sono ammessi solo URL HTTP(S) senza credenziali incorporate, query o
fragment. Il server mock non implementa autenticazione e per default ascolta
solo su `127.0.0.1`; l'autenticazione del servizio reale va concordata con il
relativo endpoint. Nessuno script dei repository esterni è importato o avviato.

Per i run con profilo esplicito, accanto agli artefatti vengono salvati:

- `backends.json`: configurazione effettiva e `run_id`, senza token;
- `mcp_events.jsonl`: per MCP, identità dichiarata del server/protocollo,
  identificativi delle chiamate, orari, durata, esiti, digest e metadati della
  risposta accettata. Gli errori riportano il tipo senza inoltrare contenuti
  arbitrari o traceback del servizio al modello.

I digest usano JSON UTF-8 compatto, con chiavi ordinate e senza NaN/Infinity.
`input_sha256` riguarda gli argomenti MCP; `response_sha256` riguarda
`CallToolResult.model_dump(mode="json")`. Non sono gli hash dei file degli
artefatti. I log non conservano ogni payload remoto e non sono un registro
firmato. Questi file supplementari non entrano negli otto artefatti di dominio
né nell'attuale record di provenienza: preparano l'integrazione futura, ma non
costituiscono ancora PROV-O o una ricevuta del ledger.

## Verifica

Al termine del primo incremento la suite aveva **122 test superati**:
95 preesistenti e 27 nel modulo MCP. Sono passati anche `ruff check`,
`ruff format --check` e `git diff --check`. Con l'incremento strategico la suite
è arrivata a **147 test superati**; le ulteriori prove sono descritte nella
[guida dello Strategic](mcp-strategic.md). Nessuna nuova inferenza Ollama è stata
avviata in queste verifiche.

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest tests/test_mcp.py -q
.venv/bin/python -m pytest -m 'not mcp_http' -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
```

I test MCP avviano processi server separati su porte loopback riservate dal
test; non richiedono Internet o inferenza. Richiedono il permesso di aprire porte
locali. Il comando con `not mcp_http` esegue la suite precedente senza questi
test. Sono coperti lookup supportato/non supportato, isolamento fra run,
discovery incompatibile, riferimenti errati, errori del tool, timeout,
disconnessione e chiusura dopo un'interruzione durante l'elaborazione della risposta.

La prova della CLI attraversa la Workforce CAMEL reale e verifica i tre
artefatti ricevuti dallo Strategic. Solo l'inferenza è programmata tramite il
backend dei test: non è una nuova valutazione del modello Ollama.

Sono stati verificati anche i comandi effettivi `mock_server` e `probe` in
processi separati. Le evidenze locali sono in
[`output/mcp-smoke-20260930T074315Z-af0d8485`](../output/mcp-smoke-20260930T074315Z-af0d8485):
lookup `2.14.1 → matched` e `9.9.9 → unsupported`, entrambi validati.
Il server di quella prova è stato terminato al termine della verifica.

## File principali e riferimenti

- [Client](../thesis_agents/mcp/client.py), [server mock](../thesis_agents/mcp/mock_server.py)
  e [contratti MCP](../thesis_agents/mcp/contracts.py).
- [Adapter del lookup](../thesis_agents/tools/vulnerability_mcp.py) e
  [configurazione dei backend](../thesis_agents/backends.py).
- [Test](../tests/test_mcp.py) e [piano delle integrazioni successive](mcp-integration-plan.md).
- [SDK MCP 1.30.0](https://github.com/modelcontextprotocol/python-sdk/tree/v1.30.0)
  e [specifica dei tool](https://modelcontextprotocol.io/specification/2025-06-18/server/tools).
