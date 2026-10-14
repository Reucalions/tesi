# Thesis Agents — primo prototipo CAMEL

Il progetto realizza quattro ruoli CAMEL, messaggi JSON validati con Pydantic e
backend mock selezionabili in locale o su server MCP HTTP separati.

Lo sviluppo delle integrazioni prosegue su `full`; `mockup` conserva la baseline
dimostrativa. Il [piano di integrazione MCP](docs/mcp-integration-plan.md) definisce
servizi remoti, switch dei backend e prove incrementali. Sono disponibili il
[MCP Tool Layer dello Strategic](docs/mcp-strategic.md) per ranking, validazione
e provenienza, e il [lookup MCP](docs/mcp-lookup.md). Il profilo consigliato per
il collaudo strategico è `--backends config/backends.mcp-strategic-mock.json`.

Il [servizio cve2owl](docs/owl-cti-integration.md) è collegato al VulnerabilityAgent
tramite il [nuovo adapter e profilo CTI](docs/cti-workforce.md). Le prove attraversano
CAMEL e MCP sul database reale, prima con inferenza programmata e poi nella
[prova Ollama con i tre ingressi](docs/observed-app-ollama.md). Il report distingue identità ambigue, regole non valutabili
e finding confermati, conservando risposta originale e riferimenti al dataset.
Il default resta locale; smart contract e ledger reali non sono ancora collegati.

Il [primo ingresso OpenTelemetry](docs/opentelemetry-integration.md) acquisisce
via HTTP gli export registrati del Collector della baseline, con snapshot e
provenienza conservati. `config/backends.otel-cti.json` combina questo ingresso
con il lookup CTI reale. Il primo collaudo usa CAMEL con un modello programmato
e osservazioni storiche del Collector.

L'[ingresso SBOM/OSV](docs/sbom-osv-integration.md) aggiunge al CountermeasureAgent
un contesto HTTP separato: inventario CycloneDX dimostrativo, query OSV e
correlazioni con il report CTI. Il profilo `config/backends.cti-sbom-osv.json`
è collaudato con CTI e OSV reali, telemetria statica e modello CAMEL programmato.
Le fonti restano distinte; nessun advisory OSV aggiunge implicitamente finding al report.

La [prova con tre ingressi coerenti](docs/observed-app-integration.md) usa ora
un'applicazione Java locale, cinque log emessi dall'SDK OpenTelemetry e una SBOM
generata dalla build Maven. Versione e hash del JAR osservato coincidono con
l'inventario. Dopo il collaudo programmato, la **prova Ollama effettiva** ha
concluso con `no_findings`: 475,59 secondi, 46 richieste LLM e audit passato.
I tool strategici restano mock. Il [resoconto](docs/observed-app-ollama.md)
documenta quattro retry qualitativi, una chiamata respinta e i limiti del risultato.
Le [verifiche successive](docs/ollama-contract-tests.md) aggiungono criteri
gestionali coerenti con i contratti, budget esplicito e memoria senza sintesi
automatica nei cloni CAMEL, conservando anche i tentativi falliti.
Il [controllo delle pubblicazioni per fonte e per fase](docs/agent-tool-phases.md)
separa il payload statico da quello OTel e limita i tool dello Strategic in base
agli artefatti già pubblicati, mantenendo l'esecuzione nel ciclo CAMEL.
Il relativo collaudo conclude con **4 inferenze complete su 4**, due con finding
CTI e due senza finding su fonti OTel, con audit superati e nessun retry.
Le due prove positive selezionano strategie diverse perché cambiano le
candidate e le stime generate: è verificato il flusso, non la ripetibilità
della raccomandazione. Tempi, comandi e limiti sono nel
[resoconto delle nuove prove](docs/agent-tool-phases.md#risultati-delle-nuove-inferenze).

La [prima relazione tecnica](docs/relazione-mockup.md) raccoglie teoria del
prototipo, architettura, ruolo di CAMEL/LLM, comandi, attività svolte e risultati
della matrice dimostrativa, distinguendo componenti effettivi e mock.

I [materiali per la presentazione](docs/materiali/README.md) comprendono un
PowerPoint modificabile da 15 minuti, la relazione PDF/Word, il copione e una
demo guidata con visualizzatore offline degli output registrati.

Il diagramma seguente rappresenta il profilo mock predefinito; i collegamenti
dei tre ingressi reali sono nella guida appena citata.

```mermaid
flowchart LR
    I[Input statico] --> T[TelemetryAgent]
    T -->|RuntimeEvidence per lookup| V[VulnerabilityAgent]
    V <--> K[Mock Knowledge Graph]
    T -->|RuntimeEvidence| C[CountermeasureAgent]
    V -->|VulnerabilityReport| C
    T -->|RuntimeEvidence| S[StrategicAgent]
    V -->|VulnerabilityReport| S
    C -->|CandidateStrategies| S
    S <--> R[Mock ranking]
    S <--> M[Mock validazione]
    S --> D[Decisione JSON]
    S --> P[Mock provenienza]
```

## Avvio

Usa **Python 3.11 o 3.12**. In questa workspace è già presente `.venv`, creata con Python 3.12.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

Per verificare subito il caso statico, senza credenziali e senza chiamate LLM:

```bash
python main.py --mode fixtures
```

Questa modalità esercita gli stessi contratti e tool della Workforce usando output prefissati. **Non è un'esecuzione degli agenti**: anche la provenienza riporta `mode: fixtures` e ruoli `fixture:*`.

Per eseguire gli agenti CAMEL:

```bash
cp .env.example .env
# Imposta LLM_MODEL, LLM_API_KEY ed eventualmente LLM_BASE_URL nel file .env.
python main.py
```

Il modello scelto deve supportare tool calling e risposte JSON. `LLM_BASE_URL` consente di usare un endpoint compatibile, anche locale; per un server locale senza autenticazione imposta una chiave fittizia esplicita. Non è previsto un modello implicito e le credenziali non vengono salvate negli artefatti.

### LLM locale con Ollama, senza costi API

Con Ollama avviato e `qwen3:4b-instruct` installato, crea il profilo locale con contesto
a 16K token (riusa i pesi esistenti):

```bash
ollama create tesi-qwen3:4b -f Modelfile
```

Se il modello non è presente, scaricalo prima con `ollama pull qwen3:4b-instruct`.
Configura `.env`:

```dotenv
LLM_MODEL=tesi-qwen3:4b
LLM_API_KEY=local
LLM_BASE_URL=http://localhost:11434/v1
LLM_TIMEOUT_SECONDS=300
LLM_TEMPERATURE=0
LLM_MAX_TOKENS=2048
```

Avvia `python main.py --mode camel --workflow pipeline`. Il valore `local` è
una credenziale fittizia per il client compatibile OpenAI: l'inferenza avviene
su Ollama, senza utilizzare la chiave OpenAI. È un'esecuzione LLM reale dei
quattro agenti CAMEL; i tool di dominio restano mock. Velocità e affidabilità
dipendono dal modello e dalle risorse locali. Le variabili già esportate nella
shell prevalgono su `.env`: rimuovi eventuali impostazioni di un provider cloud
prima di usare questa configurazione.

La temperatura viene inviata esplicitamente all'endpoint: non si presume che
il default dell'API compatibile coincida con quello del Modelfile. Lascia
`LLM_TEMPERATURE` vuota per provider che non supportano questo parametro.

`LLM_MAX_TOKENS` limita la lunghezza di ciascuna risposta, incluse le chiamate ai
tool. Per Ollama il valore di prova è 2048; lasciarlo vuoto omette il parametro.
Non è la finestra di contesto e non garantisce che una risposta troncata sia valida.
`LLM_CONTEXT_TOKENS=16384`, insieme a `LLM_MAX_TOKENS=2048` e all'endpoint
compatibile, abilita il controllo stimato della richiesta completa con un margine
di 1024 token. Non modifica il `num_ctx` di Ollama: i due valori vanno allineati.
Le richieste oltre budget vengono respinte prima del provider, senza tagliare
messaggi; il contatore CAMEL resta una stima per Qwen. Dettagli e comandi nella
[guida delle verifiche](docs/ollama-contract-tests.md).

La prima esecuzione completa verificata con `tesi-qwen3:4b` è descritta nel
[resoconto della prova Ollama](docs/ollama-first-run.md). Lo Strategic ha richiesto
un tentativo aggiuntivo per pubblicare decisione e provenienza. Il successo va
verificato sugli otto artefatti validati, non sui soli messaggi dei worker; un run
riuscito non dimostra l'affidabilità del modello su altri casi.

Per diagnosticare le chiamate puoi impostare `CAMEL_MODEL_LOG_ENABLED=true` e
`CAMEL_LOG_DIR=output/llm-logs` prima dell'avvio. I log SDK contengono prompt,
risposte e messaggi dei tool; sono distinti dall'artefatto di provenienza di dominio.

Ogni esecuzione crea una cartella distinta `output/<timestamp>-<id>/`. Puoi specificare `--input percorso/caso.json` e `--output percorso/cartella-vuota`. Una cartella non vuota viene rifiutata per preservare le esecuzioni precedenti.

## Cosa è implementato

| Componente | Comportamento nel prototipo |
|---|---|
| TelemetryAgent | Normalizza l'input statico oppure acquisisce osservazioni OTel via HTTP; la pubblicazione preserva i fatti e la fonte |
| VulnerabilityAgent | Interroga il tool e pubblica il rapporto senza modificare CVE, fonte o punteggi |
| CountermeasureAgent | Acquisisce il contesto SBOM/OSV se configurato e genera strategie, motivazioni e stime tramite il modello |
| StrategicAgent | Invoca costruzione del grafo, ranking, validazione in ordine e registrazione della decisione |
| Mock KG | Corrispondenza esatta `log4j-core` / `2.14.1` → fixture `CVE-2021-44228` |
| MCP lookup | Client HTTP e server mock separato, stesso contratto di lookup, selezione da configurazione |
| Ingresso OTel | Gateway HTTP separato sugli export della baseline; snapshot validato, valori mancanti espliciti, collaudo su dati registrati |
| Ingresso SBOM/OSV | Gateway HTTP con associazione esplicita asset/componente Maven; snapshot, query OSV e contesto validati |
| MCP Strategic | Ranking, validazione e provenienza su server HTTP separato; ricevuta mock persistita in SQLite |
| Mock ranking | Somma pesata deterministica a un passo; **non implementa l'algoritmo BWAF reale** |
| Mock semantico | Controlla capacità disponibili e azioni proibite; **non implementa Tiny-ME** |
| Mock provenienza | Registra input, hash SHA-256, attività e ruoli in JSON locale; nessuna transazione Fabric |

Il grafo esplicita, per ogni strategia, un argomento strategia, un supporto per il beneficio e un attacco per l'impatto operativo. Il tool applica:

```text
score = clamp(0.5 + 0.5 × security_benefit − 0.5 × operational_impact, 0, 1)
```

I pareggi vengono risolti per ID. La formula serve a esercitare il contratto del ranking. Le stime candidate sono generate dal modello nella modalità CAMEL: ranking deterministico non significa che l'intera esecuzione LLM sia riproducibile o che tali stime siano oggettive.

La Workforce predefinita usa la modalità CAMEL `PIPELINE`: quattro task assegnati ed eseguiti da CAMEL con un DAG esplicito. `vulnerability` dipende da `telemetry` per il lookup; `countermeasure` dipende da entrambi; `strategic` dipende direttamente da tutti e tre. L'ordine di esecuzione resta vincolato da questi prerequisiti, ma ogni artefatto mantiene la propria identità e disponibilità. Lo StrategicAgent legge separatamente `RuntimeEvidence`, `VulnerabilityReport` e `CandidateStrategies` tramite `get_context`, che espone anche `artifact_producers`. Per sperimentare anche la decomposizione tramite il task agent:

```bash
python main.py --workflow auto
```

Il coordinatore e il task agent sono componenti gestionali CAMEL, oltre ai quattro ruoli di dominio. Gli agenti condividono gli artefatti validati tramite `get_context`; il risultato testuale di un task non è fonte autorevole per il dominio. Le pubblicazioni avvengono con tool che validano JSON/Pydantic e impediscono modifiche incompatibili. La modalità `auto` conserva gli stessi vincoli sui dati, ma richiede una valutazione con il modello scelto.

I tre tool di pubblicazione ricevono `payload` come oggetto JSON strutturato.
L'adapter locale esegue la serializzazione per `ArtifactSession`; l'LLM non deve
produrre JSON racchiuso in una stringa. Nella pipeline, un produttore che fallisce
definitivamente blocca i task dipendenti senza avviarne gli LLM. I retry del
produttore restano CAMEL; il controllo degli artefatti richiesti precede inoltre
l'inferenza di ciascun worker, anche in modalità auto.

## Artefatti prodotti

Oltre a `input.json`, copia dell'input validato:

1. `runtime_evidence.json`
2. `vulnerability_report.json`
3. `candidate_strategies.json`
4. `argumentation_graph.json`
5. `ranking.json`
6. `semantic_validation.json` — conserva anche i tentativi rifiutati
7. `final_decision.json`
8. `provenance.json`

Il caso fixture seleziona `S_UPGRADE`, con score `0.875`. Rimuovendo `maintenance_window` dalle capacità dell'input, l'upgrade viene rifiutato e si passa a `S_ISOLATE`. Con tutte le capacità assenti l'esito è `no_valid_strategy`. Un pacchetto/versione non coperto dalla fixture produce `insufficient_evidence`: l'assenza di una corrispondenza non equivale all'assenza di vulnerabilità.

Nessuna contromisura viene eseguita. `selected` indica una proposta che supera i controlli del mock, non una remediation effettuata o una prova semantica completa. Il campo `constraints` contiene caveat testuali; il validatore locale controlla soltanto `prerequisites`, requisiti propri delle categorie di azione e `prohibited_actions`.

## Contratti e struttura

Per studiare il codice, parti dalla [guida alla lettura dei file commentati](docs/reading-guide.md). I sorgenti contengono spiegazioni in italiano; il [caso JSON è documentato campo per campo](thesis_agents/data/README.md) senza alterarne il formato.

```text
main.py                         # Entry point dalla cartella del progetto
thesis_agents/
  agents/                       # Prompt e tool dei quattro ruoli CAMEL
  schemas/                      # Contratti Pydantic, senza dipendenze CAMEL
  tools/interfaces.py           # Protocol per sostituire i backend
  tools/*_mock.py               # Implementazioni locali
  orchestration/artifacts.py    # Stato condiviso e pubblicazioni validate
  orchestration/explanations.py # Spiegazione derivata dagli artefatti, con fonti
  orchestration/publication_tools.py # Adapter degli oggetti Pydantic per i tool CAMEL
  orchestration/workforce.py    # Workforce, task e dipendenze CAMEL
  data/log4j_case.json          # Input iniziale
  config.py                     # Configurazione del backend LLM
  fixtures.py                   # Solo dimostrazione dei contratti senza LLM
tests/                          # Contratti, CLI e integrazione CAMEL
```

I contratti e i punti di sostituzione sono descritti in [docs/architecture.md](docs/architecture.md). Per esportare i JSON Schema senza credenziali:

```bash
python main.py --export-schemas output/schemas
```

## Verifiche

Per la presentazione sono disponibili [quattro scenari dimostrativi](docs/demo-scenarios.md),
con input pronti, esiti attesi dei mock e criteri per le successive prove con Ollama.
Il [runner della demo](docs/demo-runner.md) li esegue con un comando unico,
salvando configurazione, log, artefatti e riepilogo dei controlli:

```bash
.venv/bin/python -m thesis_agents.demo --mode camel --repetitions 2
```

Per la verifica senza LLM usare `--mode fixtures --repetitions 1`.
La matrice eseguita con il runner è documentata in
[docs/demo-matrix-runs.md](docs/demo-matrix-runs.md).
Il [resoconto delle prove LLM](docs/ollama-demo-runs.md) distingue gli esiti reali,
i fallimenti osservati e le correzioni verificate.
Le verifiche del nuovo formato dei tool e del blocco dei task dipendenti sono
nel [resoconto del 15 settembre](docs/structured-tools-runs.md).
La [verifica delle spiegazioni](docs/artifact-explanations.md) documenta la
separazione fra spiegazione derivata dagli artefatti e commento LLM non verificato.

```bash
python -m pytest -q
ruff check .
ruff format --check .
python -m pip check
```

I test verificano il caso completo, il fallback dopo un rifiuto, tutti i candidati
rifiutati, lookup sconosciuti, riferimenti e stime invalidi, integrità della
provenienza e pubblicazioni immutabili. L'integrazione esegue la **Workforce
CAMEL reale con un backend LLM a risposte programmate**. Le prove MCP avviano
server separati su loopback e verificano i quattro scenari con due run distinti.
Non richiedono Internet e non misurano la qualità di un LLM effettivo. Per
escludere le prove con socket locali usa `pytest -m 'not mcp_http' -q`.

CAMEL è fissato a `0.2.90`; MCP è limitato alla serie 1 perché la serie 2 risolta inizialmente rendeva impossibile importare `FastMCP` da CAMEL. OpenAI SDK è limitato alla serie 1/2 verificata nel progetto. Per riprodurre le versioni usate nei test, installa prima `requirements.lock` e poi il progetto con `python -m pip install --no-deps -e .`.

Riferimenti tecnici: [Workforce CAMEL](https://docs.camel-ai.org/key_modules/workforce), [API Workforce e modalità pipeline](https://docs.camel-ai.org/reference/camel.societies.workforce.workforce), [ChatAgent e output strutturati](https://docs.camel-ai.org/key_modules/agents). La fixture riprende i dati esemplificativi della chat; non è un feed aggiornato di vulnerabilità.
