# Verifiche Ollama dei contratti e del budget di contesto

Queste prove proseguono il [run sui tre ingressi](observed-app-ollama.md).
L'obiettivo è verificare il comportamento gestionale sui dati sconosciuti e
sugli insiemi vuoti, rendere esplicito il budget delle richieste e passare poi
alla generazione di strategie su finding CTI reali. I risultati non modificano
retroattivamente gli artefatti della prima prova.

**Esito: i controlli bloccano le pubblicazioni scorrette, ma l'inferenza non è
ancora affidabile.** Due ripetizioni negative comparabili hanno dato un successo
e un fallimento; i due tentativi sul caso con finding si sono fermati prima
degli agenti successivi a Telemetry. La suite automatica di quella revisione
passa con 259 test: è una verifica distinta dal comportamento del modello.

Questo resoconto conserva le prove della revisione precedente. L'implementazione
degli interventi individuati e le verifiche successive sono documentate in
[pubblicazioni per fonte e fasi dello Strategic](agent-tool-phases.md).

## Modifiche circoscritte

I task e il prompt gestionale distinguono ora la mancanza di dati nella fonte
dalla mancata esecuzione di un task. Flag `null`, metadati CTI assenti e liste
vuote richieste dal caso sono esiti leciti; non giustificano la creazione di
fatti, CVE o strategie. Con ranking vuoto lo Strategic deve selezionare `null`
e registrare la provenienza, senza invocare validazioni di candidate inesistenti.

La valutazione gestionale resta un'inferenza CAMEL: non ne vengono forzati i
punteggi né convertiti automaticamente i rifiuti in successi. I controlli
Pydantic e fra artefatti restano autorevoli. Non sono cambiati quattro ruoli,
DAG, modalità pipeline o contratti dei backend.

`ModelSettings` accetta `LLM_CONTEXT_TOKENS`. Se configurato per un endpoint
compatibile, costruisce `BoundedCompatibleModel`, una sottoclasse del backend
CAMEL che conserva l'implementazione delle richieste HTTP. Prima di ciascuna
chiamata sincrona o asincrona, il controllo richiede:

```text
stima della richiesta + LLM_MAX_TOKENS + 1024 <= LLM_CONTEXT_TOKENS
```

La stima comprende messaggi, schemi dei tool e schema dell'eventuale risposta
strutturata, serializzati in JSON. Il contatore è quello OpenAI usato dal backend
compatibile CAMEL: **non è il tokenizer esatto Qwen**. Il margine di 1024 token
è una scelta prudenziale del prototipo, non una garanzia matematica o un valore
derivato da un paper. Un superamento genera un errore prima del provider;
nessun messaggio viene eliminato per rientrare nel limite. Il limite restituito
dal backend è esplicito anche per i cloni degli agenti.

La configurazione richiede `LLM_BASE_URL`, `LLM_MAX_TOKENS` positivo e spazio
residuo per il margine. Senza `LLM_CONTEXT_TOKENS` il comportamento del backend
preesistente resta disponibile. Il parametro non modifica `num_ctx` in Ollama:
il valore del modello sul server deve essere controllato separatamente.

## Problema scoperto nella prima prova

La prima esecuzione con il limite a 16.384 token ha attivato un comportamento
dell'SDK prima nascosto dal limite teorico molto elevato del modello non
riconosciuto: `ChatAgent` avvia di default la sintesi della memoria al 50% del
contesto. Vulnerability ha ripetuto `get_context` alternandolo ai riassunti,
senza completare il task. Nel primo tentativo il nuovo controllo ha respinto
una richiesta stimata a 15.346 token: aggiungendo risposta e margine avrebbe
superato il budget. Il retry ha ripreso lo stesso ciclo di riassunti. La prova
è stata interrotta tramite SIGTERM al solo
processo CLI dopo **294,57 secondi**. Non è un timeout automatico né un successo.

Le evidenze parziali sono in
[observed-app-ollama-20261009-r1](../output/observed-app-ollama-20261009-r1/),
con `execution.json`, `audit.json`, `intervention.json` e conversazioni integrali.
Il numero `r1` identifica questo tentativo preliminare, non la prima ripetizione
riuscita della revisione con prompt e memoria aggiornati.

La correzione introduce `ArtifactChatAgent`, sottoclasse CAMEL che disabilita
la sintesi automatica e preserva questa opzione nei cloni usati dal pool.
Configurare soltanto l'agente originale sarebbe insufficiente: il `clone()`
dell'SDK fissato ricrea un `ChatAgent` con il valore predefinito di sintesi.
La memoria dei worker resta separata, mentre lo stato condiviso validato resta
in `ArtifactSession`. Le richieste troppo grandi sono respinte dal backend;
il prototipo non riassume gli artefatti per aggirare il controllo.

La prova `r2`, con la memoria integrale, ha superato Telemetry, Vulnerability e
Countermeasure senza retry qualitativi. Lo Strategic ha però scritto una
chiamata a `publish_final_decision` nel testo della risposta, senza eseguirla;
anche il retry è rimasto testuale. La sessione ha rifiutato il successo per
assenza di decisione e provenienza: **226,88 secondi, 22 richieste LLM, run fallito**.
Questo non è un superamento del budget di contesto. Il task Strategic e le
istruzioni comuni sono stati poi chiariti, nominando le due chiamate finali
effettive e distinguendole da un oggetto JSON scritto nella risposta.

Anche [r2](../output/observed-app-ollama-20261009-r2/) è conservata integralmente;
non è stata completata a mano o conteggiata tra le prove riuscite. I tentativi
`r1`, `r2` e quelli successivi non usano tutti la stessa revisione dei prompt:
i manifest conservano gli hash che permettono di distinguerli.

## Ripetizioni con prompt e memoria aggiornati

Le due esecuzioni comparabili con gli ultimi prompt hanno dato **un successo
e un fallimento**. I manifest confermano identità degli hash dei sorgenti,
del digest del modello, dei parametri e della directory delle fonti. Due prove
non consentono di stimare un tasso generale di affidabilità.

| Prova | Esito verificato | Durata | Richieste LLM | Retry |
|---|---|---:|---:|---|
| [r3](../output/observed-app-ollama-20261009-r3/audit.json) | Completa, audit passato, `no_findings` | 218,04 s | 23 | Nessuno |
| [r4](../output/observed-app-ollama-20261009-r4/audit.json) | Fallita, mancano decisione, provenienza e report semantico | 233,66 s | 24 | Strategic: due tentativi falliti per pubblicazioni mancanti |

In entrambe Telemetry, Vulnerability e Countermeasure hanno completato i task
al primo tentativo. Non compaiono retry qualitativi, riassunti automatici,
superamenti del budget o risposte terminate per il limite di generazione.
Non vengono importate conversazioni da un run all'altro; Ollama risultava
residente prima di entrambi. Temperatura zero non implica identità delle
tracce: ID di sessione e metadati delle acquisizioni cambiano fra le prove.

In `r3` l'audit verifica tutti gli artefatti e la consegna separata di runtime
evidence, report CTI e candidate allo Strategic. L'esito è `no_findings`,
limitato alle query eseguite. In `r4` lo Strategic ha ricevuto gli stessi tipi
di evidenza e ha chiamato i tool di grafo e ranking, ma ha scritto la chiamata
finale come testo. Nel retry ha dichiarato decisione e provenienza completate
senza chiamare i relativi tool. `ArtifactTaskHandler` ha respinto entrambi i
tentativi e la CLI è uscita con codice 1; gli artefatti mancanti non sono stati
creati dall'audit. **Il chiarimento dei prompt non ha risolto l'affidabilità
delle pubblicazioni finali.**

L'audit iniziale di questa prova cercava il contesto aggiuntivo soltanto nella
risposta di `get_context`. Countermeasure lo ha invece ricevuto direttamente
da `collect_countermeasure_context`, prima di pubblicare le candidate.
Il controllo è stato corretto per riconoscere entrambi i percorsi, verificando
nome e ID della chiamata e uguaglianza integrale con il contesto validato
salvato. Per lo Strategic rimane richiesto `get_context`. Nessun artefatto o
messaggio LLM è stato modificato; l'esito iniziale è conservato in
`audit-before-delivery-check-fix.json`. Il prompt richiedeva una seconda lettura
di `get_context` anche al Countermeasure: l'omissione resta una deviazione
dall'istruzione, pur non avendo impedito la consegna dei dati verificata qui.

Anche con giudizi gestionali pari a 100, il commento libero dello Strategic
contiene formulazioni troppo ampie, come «no vulnerabilities to address».
`agent_commentary` rimane marcato `unverified`; l'`explanation` autorevole,
derivata dagli artefatti, delimita invece `no_findings` alle regole valutate.
L'audit dimostra coerenza e consegna degli artefatti, non la correttezza di ogni
frase generata né la sicurezza del software.

## Caso con finding: selezione dei tool di acquisizione

Il primo tentativo sul caso statico, conservato in
[cti-positive-ollama-20261009-r1](../output/cti-positive-ollama-20261009-r1/),
è fallito in **49,83 secondi**, con **7 richieste LLM**, prima del lookup CTI.
Telemetry ha letto l'input statico ma ha chiamato due volte
`collect_runtime_evidence`, disponibile nell'elenco dei tool anche senza un
gateway OTel configurato. Il tool ha rifiutato entrambe le chiamate e il DAG
ha bloccato Vulnerability, Countermeasure e Strategic. Questo run **non ha
esercitato la generazione di strategie né interrogato CTI/OSV**.

È stato quindi aggiunto un filtro alla registrazione dei tool nella Workforce:
`collect_runtime_evidence` è esposto solo per `TelemetryInput` con backend
configurato; `collect_countermeasure_context` solo con il relativo backend
configurato. I tool di pubblicazione restano agli agenti, i metodi di sessione
mantengono i propri controlli e un servizio configurato che fallisce continua
a produrre un errore. Il filtro non attiva fallback, non acquisisce dati e
non trasforma il flusso in codice procedurale.

Questa modifica è successiva alle due ripetizioni negative: i loro hash
documentano la revisione precedente. La nuova prova positiva usa una sessione
indipendente e conserva il fallimento iniziale, senza riutilizzarne artefatti.

La prova dopo il filtro,
[cti-positive-ollama-20261009-r2](../output/cti-positive-ollama-20261009-r2/audit.json),
è fallita in **93,00 secondi**, con **9 richieste LLM**. Non ha più chiamato
il tool OTel, ma ha tentato quattro pubblicazioni con metadati OTel inventati
per l'input statico. Le prime due sono state respinte dai vincoli Pydantic sugli
hash; le successive, pur formalmente valide, dal controllo di coerenza della
sessione, che richiede `telemetry=null` per questo input. Non è stato salvato
alcun `RuntimeEvidence` e i tre discendenti sono rimasti bloccati.

| Tentativo positivo | Revisione | Punto raggiunto | Copertura ottenuta |
|---|---|---|---|
| r1 | Prima del filtro | Chiamata OTel non configurata, due tentativi di task | Rifiuto del tool e blocco DAG |
| r2 | Con filtro dei tool | Pubblicazione di metadati inventati, due tentativi di task | Validazione Pydantic, verifica dei fatti e blocco DAG |

Nessuno dei due tentativi dimostra la generazione di strategie su finding reali.
I precedenti collaudi CTI/OSV restano validi nel loro perimetro; qui **manca ancora
una prova LLM completa del caso positivo**. Non si è esteso il contesto né
cambiato modello per nascondere questi esiti; i log non segnalano esaurimento
del budget o risposte troncate in questi due run.

## Prove automatiche

La suite completa dopo le correzioni conclude con **259 test passati in 57,13 s**.
Le nuove prove verificano che richieste troppo grandi per messaggi, tool o
schema della risposta non raggiungano il provider, sia nel percorso sincrono
sia in quello asincrono; le richieste ammesse arrivano invece immutate.
Sono controllati anche la configurazione, la conservazione del limite nei cloni,
l'assenza di riassunti oltre metà finestra e l'indipendenza della memoria clonata.
Quattro ulteriori casi verificano sui cloni CAMEL la disponibilità dei tool
di acquisizione in funzione dell'input e dei backend configurati.

Le prove d'integrazione CAMEL preesistenti continuano a esercitare il DAG,
i tool, le pubblicazioni e il blocco dei discendenti dopo fallimenti effettivi.
Un modello programmato non dimostra che un LLM seguirà sempre il nuovo prompt:
le prove Ollama sono evidenze distinte.

```sh
.venv/bin/pytest -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
```

## Metodo delle prove LLM

Le ripetizioni negative usano `tesi-qwen3:4b`, temperatura zero, contesto server
16.384 e massimo di risposta 2048. Riutilizzano le fonti di
`observed-app-sources-20261007-02`, con nuove sessioni CAMEL e nuove interrogazioni
CTI/OSV. Non sono nuove osservazioni dell'applicazione. I retry interni riusano
gli snapshot della sessione. Il modello può rimanere residente fra processi,
come documentato da `ollama-before.json`; non viene azzerata la cache di Ollama.

Il caso con finding usa invece `config/input.cti-sbom-demo.json`, che dichiara
`Apache Log4j Core 2.14.1`, capacità operative e policy. La telemetria è **statica**
e la SBOM è **dimostrativa**; CTI e OSV sono reali. Non si esegue una versione
vulnerabile dell'applicazione per questa prova. Il caso verifica un ramo diverso
della pipeline e non va presentato come terzo ingresso runtime reale.

I tempi includono il processo Python, CAMEL, il modello, i tool e gli eventuali
retry. Non sono benchmark controllati: cambiano prompt e limite di risposta
rispetto al primo run; lo stato delle cache varia e la suite automatica è stata
eseguita anche in sovrapposizione ad alcuni tentativi di sviluppo e positivi.
Non si può attribuire una differenza
di durata a una sola modifica.

Nel caso negativo riuscito `r3`, il provider riporta un massimo di 10.767 token
di prompt e 135.185 token totali cumulativi; in `r4`, rispettivamente 10.774
e 141.513. Il cumulativo include il reinvio delle conversazioni e non misura
token unici di evidenza. Nelle due prove la maggiore sottostima osservata nel
conteggio offline è di 490 e 499 token. Sono misure delle richieste conservate,
non una dimostrazione che il margine scelto sia sufficiente per ogni input.

## Evidenze e lavoro successivo

Il [riepilogo JSON](../output/ollama-contract-tests-20261009/summary.json)
confronta la prova originaria, i quattro tentativi negativi e i due positivi;
[report.py](../output/ollama-contract-tests-20261009/report.py) lo rigenera dai
manifest, dagli audit e dalle conversazioni salvate. Ogni directory mantiene
comando, hash dei sorgenti, parametri Ollama, stato del modello residente,
tempi del processo, log e artefatti eventualmente parziali. I 34 record di
richiesta del tentativo interrotto `r1` includono due senza risposta; non sono
34 inferenze completate. I file `output/` sono locali ed esclusi da Git; questo
documento conserva gli esiti principali nel repository.

L'audit è ripetibile offline, senza inferenza né pubblicazioni:

```sh
.venv/bin/python output/observed-app-ollama-20261009-r3/audit.py
.venv/bin/python output/observed-app-ollama-20261009-r4/audit.py
.venv/bin/python output/cti-positive-ollama-20261009-r2/audit.py
.venv/bin/python output/ollama-contract-tests-20261009/report.py
```

Gli audit di run falliti terminano intenzionalmente con codice 1. I gateway
temporanei sulle porte 8003–8006 sono stati fermati dopo il collaudo; Ollama
preesistente è rimasto attivo. `.env` e i backend esterni non sono stati modificati.

I prossimi interventi sono circoscritti ai problemi osservati:

1. Distinguere meglio la pubblicazione da input statico da quella OTel nello
   schema esposto al modello, mantenendo `RuntimeEvidence` come artefatto unico
   e senza completare a mano metadati generati erroneamente.
2. Vincolare le chiamate disponibili per fase dello Strategic e verificare le
   transizioni con CAMEL, così che una risposta testuale non sostituisca le
   pubblicazioni. I controlli finali devono continuare a respingere il falso
   successo; nessun codice esterno deve scegliere una strategia al posto dell'agente.
3. Ripetere i casi statici storici e il caso positivo, poi costruire una matrice
   con revisione e parametri fissati prima delle ulteriori integrazioni strategiche.

BWAF reale, Tiny-ME, PROV-O, Fabric e attuazione delle mitigazioni restano
fuori da queste prove. La riduzione dei retry gestionali sul caso vuoto non
costituisce una validazione scientifica delle raccomandazioni o degli score.

## Riproduzione e riferimenti

Con i servizi del caso negativo avviati come nella
[guida degli ingressi](observed-app-integration.md#ripetere-il-collaudo), una nuova
esecuzione con budget esplicito si avvia dalla radice del repository:

```sh
LLM_CONTEXT_TOKENS=16384 LLM_MAX_TOKENS=2048 \
CAMEL_MODEL_LOG_ENABLED=true \
CAMEL_LOG_DIR="$PWD/output/observed-bounded-next/llm" \
.venv/bin/python main.py --mode camel --workflow pipeline \
  --backends output/observed-app-sources-20261007-02/backends.json \
  --input output/observed-app-sources-20261007-02/input.json \
  --output output/observed-bounded-next/artifacts
```

Usare una directory nuova. Le variabili valgono per il processo e non richiedono
di sovrascrivere `.env`. Il server deve usare lo stesso contesto, verificabile
con `ollama show tesi-qwen3:4b --parameters`. Non basta aumentare il solo budget
client per ottenere più memoria dal modello.

Per riprodurre il caso con finding, mantenere il servizio CTI sulla porta 8003
e avviare un gateway SBOM separato:

```sh
.venv/bin/python services/sbom_gateway/server.py \
  --sbom services/sbom_gateway/data/log4j-demo.cdx.json \
  --source-id log4j-demo --sbom-kind demo \
  --service-name payment-api --runtime-package 'Apache Log4j Core' \
  --component-ref log4j-core --port 8006
```

La configurazione conservata in `output/cti-positive-sources-20261009/backends.json`
è una copia di `config/backends.cti-sbom-osv.json` con il solo URL SBOM sulla porta
8006. Per nuove prove è possibile crearne una copia equivalente. Con quel profilo:

```sh
LLM_CONTEXT_TOKENS=16384 LLM_MAX_TOKENS=2048 \
CAMEL_MODEL_LOG_ENABLED=true \
CAMEL_LOG_DIR="$PWD/output/cti-positive-next/llm" \
.venv/bin/python main.py --mode camel --workflow pipeline \
  --backends output/cti-positive-sources-20261009/backends.json \
  --input config/input.cti-sbom-demo.json \
  --output output/cti-positive-next/artifacts
```

Anche qui occorrono una directory nuova e OSV raggiungibile. Non avviare il
workload Java vulnerabile: l'input di questa prova è dichiarato e statico.
Le configurazioni possono restituire risposte nuove da OSV a parità di modello.

Le modifiche si trovano in [config.py](../thesis_agents/config.py),
[bounded_model.py](../thesis_agents/orchestration/bounded_model.py),
[chat_agent.py](../thesis_agents/orchestration/chat_agent.py),
[workforce.py](../thesis_agents/orchestration/workforce.py) e
[test_context_budget.py](../tests/test_context_budget.py).
Sono state verificate sul codice installato CAMEL `0.2.90`: `ChatAgent.__init__`,
`clone`, `_get_context_with_summarization`, `ScoreBasedContextCreator` e
`OpenAICompatibleModel`. Il controllo del budget e le istruzioni del dominio
sono aggiunte del prototipo, non algoritmi BWAF o modifiche al codice dei backend.
