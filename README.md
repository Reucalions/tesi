# Thesis Agents

Prototipo CTI per la tesi: quattro agenti CAMEL elaborano evidenze runtime,
vulnerabilita e candidate di remediation; lo Strategic coordina ranking,
validazione e raccomandazione. Gli artefatti sono validati con Pydantic e
tracciati con provenance PROV-O. Le raccomandazioni sono in dry-run.

## Da dove iniziare

1. [Stato del progetto](docs/stato-progetto.md): cosa funziona e cosa manca.
2. [Architettura](docs/architettura-implementata.md): agenti, dati e servizi.
3. [Guida al codice](docs/reading-guide.md): file e responsabilita.
4. [Prossime azioni](docs/prossime-azioni.md): integrazioni e criteri di completamento.

L'[indice della documentazione](docs/README.md) raccoglie le guide specialistiche,
gli esperimenti e i materiali della relazione. [resoconto.md](resoconto.md)
conserva il contesto operativo per riprendere il lavoro.

## Stato attuale

- Workforce CAMEL, controlli sugli artefatti e profili mock implementati.
- Ingressi OTel e CTI, assessment Ubuntu e contesto SBOM/OSV disponibili in profili distinti.
- Caso Apache con Ollama concluso con `insufficient_evidence`: applicabilita runtime
  non verificata, quattro richieste pendenti, nessuna remediation selezionata.
- Bridge MCP e backend SaaS condivisi trasferiti sui due branch esterni
  `costa-thesis`; contratti corretti e client framework stdio dei quattro tool
  nativi collaudato con bridge/SaaS effettivi e Fabric simulato.
- Preparazione canonica Bottalico e profilo Strategic nativo collegati: ranking
  per CVE, score originali e riletture MCP. [Guida](docs/integrazioni/strategic-native.md).
- Validazione nativa con IRI e contesto operativo implementata: esiti Tiny-ME e
  policy SaaS distinti. [Guida](docs/integrazioni/strategic-validation.md).
- Selezione della prima candidata effettivamente accettata per CVE, DAG completo
  e switch `--backend-mode mockup|real` implementati.
  [Comandi ed esiti](docs/integrazioni/strategic-selection-dag.md).
- Finalizzazione condivisa e provenance collegate al DAG: documento immutabile per CVE,
  commit/rilettura tramite backend, idempotenza e riavvio collaudati con Fabric simulato.
  [Guida ed evidenze](docs/integrazioni/strategic-finalization.md).
- Consolidamento scientifico offline: cinque coppie di grafi, aspettative motivate,
  controlli di ranking/cammini e parsing delle penalita rafforzati. Profili ALN
  omogenei e anello per ID limitano le conclusioni sulle preferenze fra azioni.
  [Esiti e limiti](docs/tecnica/consolidamento-scientifico-grafo.md).
- Perimetro congelato per decisione dell'utente: nessuna nuova estensione semantica.
  Prossimo lavoro: casi controllati, collaudo del percorso esistente e relazione,
  mantenendo espliciti i limiti del ranking. Riusare la dashboard disponibile.
- Primo avvio reale Fabric/SaaS dal costa-thesis e sei chiamate MCP passati:
  scrittura/rilettura e ranking nativo su un grafo esistente. I tentativi con
  fonti reali e Ollama sono distinti dal percorso MAS completo fino alla
  finalizzazione. [Esiti e problemi](docs/integrazioni/collaudo-reale.md).
  [Collegamento stdio](docs/integrazioni/mcp-strategic.md#collegamento-stdio-e-bridge-saas-condiviso).

I mock permettono test e confronti riproducibili. Le prove con un servizio reale
sono distinte dai test che ne simulano le risposte.

## Installazione

Richiede Python 3.11 o 3.12. Per usare le dipendenze congelate:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
python -m pip install --no-deps -e .
```

Per sviluppare senza riprodurre esattamente il lock: `python -m pip install -e '.[dev]'`.
CAMEL e fissato a `0.2.90`; MCP usa la serie 1, compatibile con questa versione.

## Prova senza LLM

```bash
.venv/bin/python main.py --mode fixtures
```

Esercita contratti e tool con dati prefissati; non esegue gli agenti LLM.
Gli output vengono scritti in `output/`.

Lo switch esplicito e `--backend-mode mockup` per i mock locali e
`--backend-mode real --backends <profilo-reale.json> --input <telemetry-input.json>`
per il percorso con backend reali fino alla raccomandazione. Quest'ultimo richiede
`--mode camel` e un profilo compilato da `config/backends.real.example.json`.
`--mode` sceglie l'inferenza; lo switch non cambia branch. Consultare la
[guida del DAG](docs/integrazioni/strategic-selection-dag.md) per configurazione,
limiti e artefatti di risultato.

## Agenti con Ollama locale

Con Ollama disponibile e il modello `qwen3:4b-instruct` installato:

```bash
ollama create tesi-qwen3:4b -f Modelfile
cp .env.example .env
```

Impostare in `.env`:

```dotenv
LLM_MODEL=tesi-qwen3:4b
LLM_API_KEY=local
LLM_BASE_URL=http://localhost:11434/v1
LLM_TEMPERATURE=0
LLM_TIMEOUT_SECONDS=300
LLM_MAX_TOKENS=2048
LLM_CONTEXT_TOKENS=16384
```

```bash
.venv/bin/python main.py --mode camel --workflow pipeline
```

Esegue quattro agenti con inferenza locale e tool di dominio mock predefiniti.
Le variabili della shell prevalgono su `.env`; il modello e il contesto devono
essere coerenti con il profilo Ollama. La [guida LLM](docs/tecnica/ollama-contract-tests.md)
descrive budget, memoria e limiti. I profili in `config/` selezionano ingressi e backend;
le istruzioni sono nelle [guide di integrazione](docs/README.md#guide-di-integrazione).

## Verifica e demo

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
.venv/bin/python -m pip check
.venv/bin/python -m thesis_agents.demo --mode fixtures --repetitions 1
```

I test usano anche server su loopback e modelli programmati; non richiedono
inferenza a pagamento. Per escludere i test MCP/HTTP: `pytest -m 'not mcp_http' -q`.
La [demo](docs/tecnica/demo-runner.md) e gli [scenari](docs/tecnica/demo-scenarios.md)
spiegano esecuzione e audit. I risultati registrati sono in [esperimenti](docs/esperimenti.md).

## Struttura

| Percorso | Contenuto |
| --- | --- |
| `thesis_agents/` | Agenti, orchestrazione, schemi, client e adapter |
| `services/` | Gateway e componenti di servizio; alcuni profili Fabric sono sperimentali |
| `config/` | Profili degli ingressi e dei backend |
| `tests/` | Test, fixture e strumenti di collaudo |
| `examples/observed-app/` | Applicazione controllata per OTel e SBOM |
| `docs/` | Stato, architettura, guide e roadmap |
| `docs/materiali/` | Relazione, figure e materiali di presentazione |
| `docs/riferimenti/` | Proposta di tesi e fonti |
| `output/` | Artefatti locali degli esperimenti, esclusi da Git |
