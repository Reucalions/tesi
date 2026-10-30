# Prova completa Apache con inferenza Ollama

Il **18 ottobre 2026** è stata eseguita la Workforce CAMEL con quattro agenti
e inferenza Ollama locale effettiva sul caso Apache registrato. La seconda
prova completa tutti gli artefatti e supera l'audit offline. La prima fallisce
nel CountermeasureAgent ed è conservata separatamente.

**Il flusso funziona su questo caso, ma non è ancora affidabile senza recuperi:**
il run riuscito richiede due retry per timeout e circa 21 minuti. Il risultato
è `insufficient_evidence`, con quattro richieste di verifica pendenti e nessuna
contromisura selezionata. Non è una prova di assenza di vulnerabilità.

## Caso e configurazione

| Elemento | Configurazione effettiva |
|---|---|
| Modello | `tesi-apache-qwen3:4b-32k`, alias locale di `tesi-qwen3:4b` |
| Contesto / risposta | `num_ctx=32768`, `LLM_CONTEXT_TOKENS=32768`, `LLM_MAX_TOKENS=8192` |
| Temperatura | 0 |
| Endpoint | Ollama locale su `127.0.0.1:11434`, nessuna inferenza cloud |
| Orchestrazione | CAMEL `0.2.90`, pipeline con quattro ruoli e DAG esistente |
| Profilo | `config/backends.otel-apache-strategic.json` |
| Input | Tre log Apache verificati contro gli originali e inventario Ubuntu associato |
| Software | Banner `Apache 2.4.29`; inventario `apache2 2.4.29-1ubuntu4.21`, Ubuntu Bionic |
| Backend | OTel HTTP, CTI Ubuntu MCP, astensione e archivio PROV-O MCP |
| Limiti | Timeout backend/step 300 s, processo CLI 1800 s |

L'alias a 32.768 token riusa i pesi già installati; non modifica il modello
dei run precedenti. Il digest e i parametri effettivi sono nei manifest e in
`ollama-model.json`. La finestra esplicita considera i nuovi report con tutti
gli ID CVE e le richieste di verifica. Il controllo preventivo del contesto
resta una stima con margine, non il tokenizer esatto Qwen.

Le osservazioni sono **reali ma registrate**: non è stata effettuata una nuova
acquisizione del processo Apache. L'inventario del 25 gennaio 2022 è successivo
ai log del 22–24 gennaio. La valutazione Ubuntu è retrospettiva rispetto a
quelle date. I servizi vengono interrogati nuovamente in ogni run; non si
importano conversazioni o artefatti decisionali dal collaudo programmato.

## Tentativi e correzione

| Prova | Esito | Durata CLI | Richieste registrate | Recuperi |
|---|---|---:|---:|---|
| `apache-ollama-20261018-r1` | Fallita; Strategic bloccato | 593,92 s | 17 | Due tentativi Countermeasure senza pubblicazione |
| `apache-ollama-20261018-r2` | Completa; audit passato | 1.284,92 s | 28, di cui 26 con risposta | Un retry Countermeasure e uno Strategic per timeout |

Nel primo run Telemetry acquisisce e pubblica l'evidenza; Vulnerability
interroga MCP e pubblica correttamente il report delle 120 CVE. Il Countermeasure
scrive due volte una chiamata `publish_candidate_strategies` come testo,
senza eseguirla. La sessione non crea l'artefatto e il DAG blocca lo Strategic.
Non sono stati completati manualmente gli output mancanti.

La correzione introduce `CountermeasureToolPolicy` soltanto per il percorso
che richiede il contesto runtime verificato. Espone un tool per fase:
lettura, preparazione delle verifiche, nuova lettura, pubblicazione. Un clone
deve rileggere il contesto; testo ed errori non fanno avanzare lo stato.
L'agente deve ancora generare gli argomenti e invocare il tool. La policy
non pubblica al suo posto, non ripara JSON e non modifica le classificazioni.
Il percorso precedente per i casi statici conserva i suoi tool.

Nel secondo run il primo tentativo Countermeasure produce ancora un payload
come testo e termina poi per timeout di 300 s. Il retry legge il contesto
già preparato e pubblica tramite il tool reale. Lo Strategic pubblica decisione
e provenienza nel primo tentativo, ma va in timeout nella successiva risposta
gestionale; il retry rilegge gli artefatti già validi e conclude il task.
Le pubblicazioni immutabili e le cache evitano acquisizioni o scritture duplicate.
La correzione consente il completamento, ma non elimina tutti i problemi del modello.

Le prove hanno revisioni diverse e stati Ollama iniziali diversi: il modello
non era residente prima di r1, mentre era residente prima di r2. In r2 è stata
eseguita anche la suite automatica in parallelo. Le durate sono misure osservate
del processo, non un confronto controllato di prestazioni. Due run non
permettono di stimare un tasso generale di affidabilità.

## Risultati del caso reale registrato

| Stato del pacchetto inventariato | CVE |
|---|---:|
| Corrette (`fixed`) | 34 |
| Non applicabili secondo Ubuntu (`not_affected`) | 28 |
| Potenzialmente applicabili (`potentially_affected`) | 46 |
| Indeterminate (`unknown`) | 12 |

Tutte le valutazioni per CVE, le sei identità selezionate e il pin delle
fonti coincidono con il collaudo programmato. Le quattro richieste pendenti
sono conservate integralmente: stato storico del processo per 58 CVE,
condizioni runtime per 46, stato Bionic per 12 e compatibilità di un eventuale
upgrade per 46. I gruppi si sovrappongono: sono 58 CVE uniche.

Due esempi mostrano il contributo della valutazione della distribuzione:

- `CVE-2021-44790` risulta `fixed` nel pacchetto inventariato: la soglia Ubuntu
  è `2.4.29-1ubuntu4.21`, uguale alla revisione dell'inventario;
- `CVE-2022-22720` risulta `potentially_affected`: la soglia è
  `2.4.29-1ubuntu4.22`, successiva alla revisione inventariata.

Sono esiti delle fonti Ubuntu conservate nello snapshot, non attestazioni
del processo storico o indicazioni di una versione globalmente sicura.
Le condizioni di sfruttamento non sono state acquisite o verificate.

La decisione finale è `insufficient_evidence`, con strategie, ranking e
validazioni vuoti. L'astensione è esplicita e le richieste non entrano nel
ranking come contromisure. La provenienza viene scritta e riletta via MCP;
l'export RDF conserva 11 entità, 10 attività e 143 triple nel grafo del run.
La ricevuta indica `artifact-files` e `ledger_status=not_submitted`.

## Audit, misure e limiti

L'audit controlla i contratti Pydantic, la corrispondenza fra telemetria e
snapshot, report e risposta MCP, richieste e contesto, spiegazione e fonti,
hash della provenienza, JSON-LD e ricevuta. Verifica inoltre nei messaggi
SDK che Countermeasure e Strategic abbiano ricevuto separatamente gli input
dei rispettivi produttori e che la decisione sia stata restituita dal tool.

Per r2:

- otto artefatti principali validi, input e tre snapshot/contesti ausiliari validi;
- 28 richieste LLM registrate: Telemetry 4, Vulnerability 4, Countermeasure 7,
  Strategic 8 e gestione CAMEL 5; due richieste senza risposta per timeout;
- nessuna risposta terminata con `finish_reason=length`;
- massimo prompt riportato: 20.064 token;
- somma dei token riportati: 231.278 prompt e 10.629 completamento;
- quattro chiamate MCP di dominio validate: valutazione Ubuntu, astensione,
  scrittura e rilettura della provenienza.

La somma dei prompt comprende cronologie ripetute e token in cache: non
misura token unici, lavoro computazionale o costo API. I punteggi qualitativi
CAMEL non costituiscono una verifica indipendente delle conclusioni.
Il commento libero dello Strategic resta `unverified`: la formula «no identified
vulnerabilities» si riferisce alla lista dei finding, ma può risultare ambigua
rispetto alle 46 CVE potenziali. La spiegazione derivata dagli artefatti
mantiene esplicitamente questa distinzione e le quattro verifiche aperte.

Questa prova non esegue BWAF, Tiny-ME, Fabric o mitigazioni. Verifica il
percorso con evidenze insufficienti; non esercita il ramo con scelta e
validazione di una contromisura su finding runtime confermati.

## Artefatti e riproduzione

Risultati locali, normalmente ignorati da Git:

- [audit r1 fallito](../output/apache-ollama-20261018-r1/audit.json);
- [audit r2 completo](../output/apache-ollama-20261018-r2/audit.json);
- [decisione r2](../output/apache-ollama-20261018-r2/artifacts/final_decision.json);
- [confronto con il collaudo programmato](../output/apache-ollama-20261018-r2/comparison.json).

Ogni directory conserva manifest, comando, parametri e stato Ollama, log CLI,
conversazioni SDK, stato del processo e sorgenti in `source-snapshot`,
verificati contro gli hash del manifest. Gli artefatti di dominio non sono
modificati dall'audit. Il run r1 è stato conservato con i sorgenti originali
verificati contro il manifest prima delle ulteriori modifiche al runner.

Avviare i tre servizi secondo la [guida Strategic](apache-strategic-agent.md#riproduzione).
Con l'alias locale già installato, scegliere una directory nuova:

```sh
.venv/bin/python tests/support/apache_ollama_run.py \
  --output output/apache-ollama-nuova-prova
.venv/bin/python tests/support/apache_ollama_audit.py \
  output/apache-ollama-nuova-prova
```

Il runner imposta endpoint e credenziali fittizie locali esplicite; non usa
chiavi cloud o modifica `.env`. La suite dopo la correzione conclude con
**376 test superati**, inclusi sei nuovi test sulle fasi del Countermeasure,
con due deprecazioni del parser RDFLib. Ruff e controlli di integrità superati.

I prossimi interventi riguardano latenza e timeout, riduzione della copia
di dati autorevoli nei payload di pubblicazione, ripetizioni controllate e
un caso con finding confermati. L'integrazione dei motori strategici nativi
resta distinta da questi risultati.
