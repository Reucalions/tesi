# Prima inferenza Ollama con i tre ingressi collegati

La prova registrata il **7 ottobre 2026** ha completato la Workforce CAMEL con
inferenza locale effettiva su `tesi-qwen3:4b`, log OpenTelemetry dell'applicazione
Java, servizio CTI cve2owl reale e SBOM della build con interrogazione OSV live.
È un singolo caso negativo, distinto dal precedente collaudo con modello
programmato e dalla matrice storica dei quattro scenari mock.

Le [verifiche successive](ollama-contract-tests.md) documentano gli interventi
su giudizio gestionale e contesto. Il presente resoconto e i suoi artefatti
restano riferiti alla revisione precedente, senza correzioni retroattive.
L'incremento seguente introduce
[pubblicazioni distinte per fonte e tool strategici per fase](agent-tool-phases.md).
Quest'ultimo collaudo completa quattro inferenze su quattro, con audit superati
e senza retry, conservando i risultati storici descritti qui. Include due
ripetizioni sulle stesse fonti OTel e due su un input statico con finding;
documenta anche la variabilità delle strategie selezionate.

**Esito: `no_findings`, nessuna strategia selezionata.** Tutti gli otto artefatti
principali, l'input e i quattro artefatti aggiuntivi sono validi. La conclusione
riguarda i risultati delle query sul componente osservato; non certifica la
sicurezza dell'applicazione. L'audit è passato, ma il run ha richiesto retry e
ha prodotto una chiamata tool errata, respinta dai controlli.

## Configurazione e metodo

| Elemento | Configurazione effettiva |
|---|---|
| Modello | `tesi-qwen3:4b`, Qwen3 4B, quantizzazione `Q4_K_M` |
| Digest Ollama | `31475760af12be9b5c1621f74b389d3f0a764dc521aca4f55c32cc2f5363f2fc` |
| Endpoint LLM | `http://localhost:11434/v1`, Ollama `0.34.4` |
| Parametri | Temperatura `0`, `num_ctx=16384`; `max_tokens` omesso come nella configurazione corrente |
| Limiti | Backend 300 s per richiesta; processo CLI 1200 s |
| Orchestrazione | CAMEL `0.2.90`, `pipeline`, quattro ruoli e DAG esistente |
| Fonti | `output/observed-app-sources-20261007-02/`, già verificate |
| Telemetria | Gateway HTTP, `sdk-file`, cinque osservazioni di `Apache Log4j Core 2.26.1` |
| CTI | MCP HTTP, dataset `cve2owl_20260523_143950`, hash fissato nel profilo |
| SBOM/OSV | Gateway HTTP, SBOM Maven `provided`, OSV `live` |
| Tool strategici | Ranking, semantica e provenienza mock locali |

Sono state riutilizzate la SBOM e le osservazioni della precedente esecuzione
Java: **non è stata effettuata una nuova raccolta runtime**. È stata creata
una nuova `ArtifactSession`, senza importare conversazioni o artefatti decisionali
dal collaudo programmato. I servizi sono stati interrogati nuovamente. Durante
i retry interni, invece, la stessa sessione ha riusato gli snapshot già acquisiti
e le pubblicazioni immutabili.

Prima del run `/api/ps` non mostrava modelli residenti. Questo documenta lo
stato del server Ollama, non l'assenza di cache del sistema operativo. Durante
il run Ollama ha riportato `context_length=16384` e `size_vram=5050204159`, uguale
alla dimensione residente riportata. È una misura del server, non un benchmark
separato di utilizzo GPU/CPU.

I sorgenti applicativi non sono stati modificati fra avvio e fine della prova.
Il riproduttore avvia la CLI in un processo separato; non usa `ScriptedToolModel`
e non pubblica artefatti al posto degli agenti. Il controllo finale della CLI
include `ArtifactSession.assert_complete()`. L'audit successivo è in sola lettura.

## Risultati misurati

| Misura | Risultato |
|---|---:|
| Durata del processo CLI | **475,59 s**, cioè 7 min 55,59 s |
| Richieste LLM con risposta registrata | **46** |
| Richieste Telemetry / Vulnerability / Countermeasure / Strategic | 8 / 8 / 8 / 13 |
| Richieste gestionali CAMEL | 9 |
| Chiamate tool proposte dal modello | 29, incluse ripetizioni e una chiamata respinta |
| Retry richiesti dall'analisi qualitativa | 4, uno per task |
| Artefatti principali validi | 8/8 |
| Token prompt / completamento riportati dall'endpoint | 300.423 / 7.052 |
| Massimo prompt riportato per richiesta | 14.467 token |

La durata è misurata dal processo padre con orologio monotono attorno alla CLI:
include import, avvio CAMEL, connessioni, chiamate LLM, tool e retry. Esclude
la build precedente, l'avvio manuale dei server e l'audit successivo. La somma
dei token prompt include cronologie ripetute e token eventualmente in cache;
non è il numero di token unici né una misura del lavoro computazionale o di un
costo API. È stata usata soltanto inferenza LLM locale.

Il lookup CTI ha restituito `no_findings` entro l'identità risolta e le regole
valutate; OSV non ha restituito advisory per il componente/versione richiesto.
Il Countermeasure ha pubblicato `strategies=[]`. Il grafo, il ranking e il
registro semantico sono vuoti. La decisione conserva `selected_strategy_id=null`
e stato `no_findings`, seguita dalla registrazione della provenienza.

Sono state osservate una chiamata HTTP di telemetria, una chiamata MCP
`assess_software` e una chiamata HTTP di arricchimento SBOM/OSV. Le rispettive
durate lato client sono 0,037091 s, 0,076227 s e 0,607120 s. Le chiamate ripetute
dai worker hanno riusato la cache della sessione; non equivalgono a nuove
consultazioni dei servizi. Questi tempi non isolano le fasi interne dei backend.

## Controlli effettuati

L'audit rilegge i file con i modelli Pydantic e confronta:

- input e hash delle fonti con quelli preparati per l'applicazione;
- `RuntimeEvidence` con il mapping dello snapshot OTel;
- `VulnerabilityReport` con il mapping della risposta CTI salvata;
- documento SBOM, versione osservata e query OSV con i relativi input;
- contesto Countermeasure con la proiezione deterministica dello snapshot;
- decisione e insiemi vuoti con l'esito negativo del caso;
- hash della provenienza, identità dei produttori e dipendenze della decisione.

Nei log SDK sono presenti inferenze di tutti i quattro ruoli. Le richieste
allo Strategic includono i tre artefatti distinti, identici ai file pubblicati,
con i produttori corretti. Countermeasure e Strategic ricevono anche il
contesto SBOM/OSV. La decisione restituita dal tool coincide con il file finale.
Le occorrenze ripetute dei messaggi nella cronologia non vengono interpretate
come altrettante chiamate nuove.

## Criticità osservate

**Valutazione qualitativa gestionale.** L'LLM usato da CAMEL ha richiesto
`replan`, convertito dall'SDK nell'unica strategia abilitata, `retry`, per tutti
i task. Le motivazioni includevano flag runtime `null`, CVSS/CWE/confidenza
mancanti e assenza di candidate. Queste condizioni sono ammesse dai contratti
del caso: un dato mancante non va inventato e un report senza finding richiede
candidate vuote. Alcuni giudizi chiedevano inoltre grafo o ranking che erano
già stati pubblicati vuoti. I punteggi non sono misure scientifiche della qualità.

Telemetry, Countermeasure e Strategic sono stati accettati alla seconda
valutazione. Per Vulnerability il log registra un secondo punteggio di 40 e
`completed with low quality score ... (retry limit reached)`: la Workforce ha
proseguito al limite dei retry. Il report era coerente con la fonte e il
controllo finale degli artefatti è passato. Questo comportamento gestionale va
distinto sia da un errore di pubblicazione sia da una piena approvazione
qualitativa del modello.

**Chiamata priva di candidato.** Durante il retry Strategic il modello ha
richiesto `validate_countermeasure` con `strategy_id="str001"`, assente dalle
candidate. La sessione ha respinto la chiamata perché il ranking era vuoto,
indicando di pubblicare la decisione con selezione nulla. Non è stata accettata
una validazione fittizia né modificato lo stato finale. La chiamata errata è
conservata nei log e nell'audit.

**Commento libero.** `agent_commentary` è marcato `unverified`. Contiene la
formulazione «no valid strategy exists», più forte di ciò che dimostra un
insieme vuoto generato per assenza di finding. La spiegazione autorevole
`artifact-derived-v1` conserva invece l'esito circoscritto e le limitazioni.
La validità dell'artefatto non certifica ogni frase prodotta dall'LLM.

**Finestra di contesto.** CAMEL non riconosce il nome personalizzato del modello
e usa un limite teorico di fallback molto elevato; Ollama applica invece 16.384
token. In questa prova tutte le richieste hanno ricevuto risposta e nessuna ha
`finish_reason=length`. Questo non dimostra in generale l'assenza di troncamenti
interni dell'input. Prima di ampliare gli artefatti va allineata esplicitamente
la gestione del contesto; il massimo prompt osservato è già vicino al limite.

## Evidenze e riproduzione

Le evidenze sono in
[output/observed-app-ollama-20261007-01](../output/observed-app-ollama-20261007-01/):

| File | Utilità |
|---|---|
| [summary.json](../output/observed-app-ollama-20261007-01/summary.json), [audit.json](../output/observed-app-ollama-20261007-01/audit.json) | Esito, misure, controlli e anomalie conservate |
| [manifest.json](../output/observed-app-ollama-20261007-01/manifest.json) | Versioni, parametri, hash dei sorgenti e origine dei dati |
| [command.json](../output/observed-app-ollama-20261007-01/command.json), [run.py](../output/observed-app-ollama-20261007-01/run.py) | Comando effettivo e riproduttore del processo |
| [run.log](../output/observed-app-ollama-20261007-01/run.log), `llm/` | Retry, errore tool e conversazioni SDK integrali |
| [StrategicAgent_context.json](../output/observed-app-ollama-20261007-01/StrategicAgent_context.json) | Contesto effettivamente consegnato allo Strategic |
| [CountermeasureAgent_context.json](../output/observed-app-ollama-20261007-01/CountermeasureAgent_context.json) | Contesto consegnato al Countermeasure, con fonte aggiuntiva |
| [artifacts/](../output/observed-app-ollama-20261007-01/artifacts/) | Artefatti, snapshot e audit dei servizi |

I file in `output/` sono locali ed esclusi da Git; il presente resoconto conserva
le misure essenziali nel repository. Il riproduttore rifiuta di sovrascrivere
il run esistente. L'audit può essere ripetuto senza rete o inferenza:

```sh
.venv/bin/python output/observed-app-ollama-20261007-01/audit.py
```

Per una nuova prova, avviare i servizi e configurare Ollama come nella
[guida degli ingressi](observed-app-integration.md#ripetere-il-collaudo).
Usare una nuova directory, ad esempio dalla radice di `tesi`:

```sh
CAMEL_MODEL_LOG_ENABLED=true \
CAMEL_LOG_DIR="$PWD/output/observed-app-ollama-next/llm" \
.venv/bin/python main.py --mode camel --workflow pipeline \
  --backends output/observed-app-sources-20261007-02/backends.json \
  --input output/observed-app-sources-20261007-02/input.json \
  --output output/observed-app-ollama-next/artifacts
```

Il comando usa i parametri di `.env`; il run conservato non imponeva il limite
2048 usato nella matrice storica. Per nuove osservazioni eseguire prima
`prepare.py` e aggiornare i percorsi dei servizi, del profilo e dell'input.
Una nuova risposta OSV o un modello/configurazione diversi possono cambiare
il risultato; una singola prova non costituisce una matrice di affidabilità.

I prossimi incrementi sono l'allineamento del giudizio gestionale ai contratti
del dominio, la configurazione esplicita del limite di contesto e un caso con
finding confermati per valutare la generazione delle strategie. BWAF reale,
Tiny-ME, smart contract, PROV-O, Fabric e attuazione delle mitigazioni restano
separati da questo risultato. Nessuna modifica ai prompt o agli algoritmi è
stata applicata per far passare questo run.

I risultati descritti derivano dai file del collaudo e dall'SDK CAMEL installato
alla versione fissata, in particolare `societies/workforce/workforce.py`
(`_analyze_task` e gestione della valutazione finale) e `prompts.py`
(`TASK_ANALYSIS_PROMPT`). Le fonti di OpenTelemetry, CycloneDX e OSV sono
riportate nelle guide degli ingressi. Non si attribuiscono a paper esterni
i controlli originali di questo prototipo o le misure di questa esecuzione.
