# Esperimenti e risultati verificati

Questo registro consolida i resoconti delle singole fasi. I risultati si riferiscono
alle revisioni e alle esecuzioni originali, conservate senza correzioni retroattive.
Non sono state eseguite nuove inferenze per la pulizia del repository.

## Prove rappresentative

| Prova | Componenti effettivi | Risultato e limite | Evidenze locali |
| --- | --- | --- | --- |
| Primo Ollama, 11 settembre | CAMEL e LLM locali; dominio mock | `selected`, upgrade; recupero Strategic dopo pubblicazioni omesse | `output/ollama-qwen3-retry-20260911/` |
| Matrice iniziale, 14 settembre | Quattro scenari con Ollama e tool mock | Fallimenti e recuperi conservati; pubblicazioni e dimensioni delle risposte da migliorare | `output/demo-ollama-20260914T084356Z/` |
| Pubblicazioni strutturate, 15 settembre | CAMEL, payload Pydantic, blocco dei task dipendenti | Verificato il flusso; restavano errori nelle pubblicazioni LLM | `output/structured-pipeline-20260915T151927Z/`, `output/structured-pipeline-lookup-20260915T152323Z/` |
| Matrice con runner, 16 settembre | Quattro scenari per due ripetizioni; tutti i servizi di dominio mock | 8/8 run verificati; 212 richieste LLM, 985,35 s complessivi | `output/demo-matrix-20260916T074247Z-80665fa1/` |
| Lookup CTI, 5 ottobre | Client/server MCP e indice cve2owl reali; nessun LLM | Sette richieste con risposta valida; test del lookup, non dell'intera Workforce | `output/cti-real-smoke-20261005T101110Z-f74ed28d/` |
| Applicazione Java, 7 ottobre | OTel SDK, SBOM della build, CTI e OSV reali, Ollama | `no_findings`, audit passato; 475,59 s, 46 richieste, quattro retry qualitativi | `output/observed-app-ollama-20261007-01/` |
| Tool per fase, 11 ottobre | CAMEL/Ollama, casi CTI positivi e OTel senza finding | Quattro inferenze complete e audit superati senza retry; strategie positive diverse fra ripetizioni | `output/cti-phase-tools-20261011-r1/`, `output/cti-phase-tools-20261011-r2/`, `output/otel-phase-tools-20261011-r1/`, `output/otel-phase-tools-20261011-r2/` |
| Apache, 18 ottobre, r1 | OTel registrato, CTI Ubuntu e LLM locale | Fallimento Countermeasure, Strategic bloccato; 593,92 s e 17 richieste | `output/apache-ollama-20261018-r1/` |
| Apache, 18 ottobre, r2 | OTel, CTI Ubuntu, gate strategico e archivio PROV-O MCP, Ollama | `insufficient_evidence`, audit passato; 1.284,92 s, 28 richieste e due retry per timeout | `output/apache-ollama-20261018-r2/` |
| Porting, 30 ottobre | Bridge MCP e backend SaaS importati | Build, discovery di 19 tool e 66 test in 13 suite; Fabric simulato | `output/porting-principe-costa-20261030/verification.json` |
| Contratti backend, 31 ottobre | SaaS e bridge corretti; REST e MCP stdio effettivi | Build, 105 test SaaS/14 suite, 12 test bridge; ranking/rilettura, tre esiti semantici e guasti 502/503. Fabric e autenticazione simulati; Docker locale indisponibile | `output/backend-contracts-20261031/verification.json`, `transport-smoke-r4/results.json` |

Le prove fallite, i log LLM, gli snapshot e le ricevute rimangono nelle directory
originali. Il successo della Workforce non dimostra da solo correttezza scientifica
delle strategie o ripetibilita delle stime del modello.

## Caso Apache: interpretazione

Tre log di avvio della baseline sono stati ricondotti ai file AIT originali
dell'host `webserver`. Banner: Apache 2.4.29; inventario associato:
`apache2 2.4.29-1ubuntu4.21`, Ubuntu Bionic. Inventario e log non attestano
automaticamente lo stesso stato storico del processo.

Il lookup letterale produceva `no_match`; la variante interpretata `ambiguous`.
Il resolver v2 risolve sei identita equivalenti fra 113 candidate. L'assessment
Ubuntu sulle 120 CVE distingue 34 `fixed`, 28 `not_affected`,
46 `potentially_affected` e 12 `unknown`.

Le quattro richieste pendenti riguardano 58 CVE uniche. Non sono contromisure
e non entrano nel ranking. Il run r2 non seleziona o applica azioni e non invoca
BWAF/Tiny-ME; la provenance e riletta da un archivio su file, non dal ledger reale.

Dettagli operativi: [ingresso Apache](integrazioni/apache-recorded-integration.md),
[resolver v2](integrazioni/cti-identity-resolution-v2.md),
[assessment Ubuntu](integrazioni/ubuntu-package-applicability.md),
[astensione e PROV-O](integrazioni/apache-strategic-agent.md).
La verifica preliminare e conservata in `output/baseline-apache-verification/`;
il binding alle fonti e in `output/baseline-apache-metadata/source-binding.json`.

## Dati CTI e limiti delle versioni

L'indice SQLite reale misura 397.623.296 byte e ha SHA-256
`e3566009408385c7aea7901a9e6499132f0ae4bb07ccbd80d22e2171e5f7990c`.
Il puntatore Git LFS non e il database. Dataset, risposte integrali e regole
valutate devono rimanere associati alla decisione.

Una versione corretta dal distributore puo mantenere il numero upstream affetto:
per Ubuntu il confronto deve usare la revisione Debian completa. `no_findings`
riguarda le regole effettivamente valutate, non la sicurezza globale del software.

## Riproduzione e audit

- Per i quattro casi mock usare il [runner](tecnica/demo-runner.md).
- Per OTel, SBOM e CTI seguire le [guide di integrazione](README.md#guide-di-integrazione).
- Per un nuovo caso Apache usare `tests/support/apache_ollama_run.py` e verificare
  con `tests/support/apache_ollama_audit.py`; scegliere una nuova directory output.
- Manifest, audit e log dei run originali restano la fonte delle misure.

Il porting conserva patch, backup, manifest e risultati dei test. Le dipendenze,
la cache npm e il runtime Node temporanei usati per il collaudo sono stati rimossi;
per rieseguire i test installare le dipendenze da lock nei componenti importati.

## Confronti ancora da eseguire

Il 3 novembre sono passati 617 test Python, inclusi selezione per CVE, switch
mockup/reale e DAG completo con inferenza e servizi sintetici. Nove esempi del
launcher e quattro raccomandazioni offline dai checkpoint SaaS sono conservati
in [output/selection-dag-20261103](../output/selection-dag-20261103/README.md).
SDK CAMEL, tool, processi stdio e HTTP locali sono effettivi; Fabric, Tiny-ME,
CTI, OSV e modello sono simulati. Nessun nuovo esperimento LLM o deployment reale.
Dettagli nella [guida del percorso completo](integrazioni/strategic-selection-dag.md).

I quattro scenari con servizi strategici condivisi, validazione Tiny-ME,
commit e rilettura sono lavoro aperto. Il piano sperimentale e in
[prossime azioni](prossime-azioni.md). I resoconti cronologici integrali precedenti
sono recuperabili dalla revisione Git `32e6dbc311cf01af4d80519fde9eadd351097b12`.
