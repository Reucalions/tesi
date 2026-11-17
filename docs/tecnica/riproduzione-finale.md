# Riprodurre tabelle e dimostrazione finale

Stato del 13 novembre 2026. [Risultati](valutazione-finale.md) e
[corrispondenza alla proposta](conformita-proposta.md).
Il ricalcolo offline non accede ai servizi. La riesecuzione live crea nuove
transazioni e usa servizi, modelli e dataset locali: non e il ricalcolo dei CSV.

## Ricalcolo offline, anche da un nuovo clone

Python 3.11 o 3.12, sola libreria standard. Dalla radice del repository,
usare una directory nuova per estrazione e risultati:

```bash
python3 -m evaluation.verify_final_bundle
```

Il comando verifica il manifest del pacchetto, estrae in una directory temporanea
con percorsi controllati, verifica gli hash degli 84 ingressi numerici, rilancia
il consolidamento senza repository esterni usando l'inventario congelato e
confronta JSON e CSV byte per byte. Ricalcola statistiche per coorte, differenze
firmate, controlli dei pesi e coerenza degli esiti. Non modifica le annotazioni,
gli archivi o il ledger. Eventuali errori di integrita fanno fallire il comando.

L'archivio compresso contiene anche protocolli e collector di questa campagna;
non e un'immagine completa dei servizi, del KG o della rete Fabric. Il risultato
ricalcolato e verificabile nel clone; la ricostruzione dell'ambiente live resta
dipendente dai repository/dataset privati e dalle istruzioni sotto.

Con tutti gli archivi originali e le due copie locali presenti si puo ricreare
anche l'inventario corrente, usando un output nuovo:

```bash
python3 evaluation/consolidate_final.py --output /tmp/tesi-final-recalculation
```

Percorsi esterni diversi si specificano con `--pipeline` e `--ledger`.
Questo comando legge e calcola hash ma non contatta MCP o Docker. L'inventario
del filesystem puo variare se si aggiungono file; le tabelle dei campioni
congelati non vengono aggiornate con nuove misure automaticamente.

## Switch dell'applicazione

Installazione ripetibile secondo [README](../../README.md) e `requirements.lock`.
Da un ambiente gia configurato:

```bash
.venv/bin/python main.py --backend-mode mockup --mode fixtures
```

Per la pipeline con agenti e backend reali, compilare il profilo di esempio e
usare un `TelemetryInput` acquisito e una directory nuova:

```bash
.venv/bin/python main.py --backend-mode real --mode camel --workflow pipeline \
  --backends percorso/profilo-reale.json \
  --input percorso/telemetry-input.json --output output/demo-reale-nuova
```

`--backend-mode` sceglie i backend, `--mode` l'inferenza. `real` non ammette
fixture e non ripiega sui mock. Il profilo
[backends.real.example.json](../../config/backends.real.example.json) contiene
placeholder: non e un profilo pronto per la rete locale. I manifest, gli IRI,
gli assessment e le capacita operative devono coincidere con gli ingressi.

## Preparazione della demo reale locale

1. Verificare i branch delle due copie esterne: `costa-thesis`. Non serve
   cambiare branch per lo switch. Snapshot delle tre revisioni alla raccolta
   nell'archivio `source-inputs.tar.gz`, percorso
   `output/final-evaluation-20261113-r1/repositories-before.json`.
2. Seguire il README del repository ledger per Docker/Fablo e SaaS. Per la rete
   **gia generata** di questo collaudo, dalla radice del repository ledger,
   il comando di ripartenza e `DOCKER_DEFAULT_PLATFORM=linux/amd64 ./fablo start`.
   La procedura di creazione iniziale nel README (`fablo up fablo-config.json`)
   e distinta dalla ripartenza della rete esistente. Non ricreare/prunare la
   rete per consultare le evidenze o ripetere la demo.
3. Controllare rete `fablo_network_202611052222_basic` e servizi. Questo collaudo
   usa SaaS 8800, CTI MCP 18043, Ollama 11434 e bridge MCP stdio gia compilato.
   Credenziali e identita si caricano localmente dalla configurazione privata:
   non sono incluse negli archivi finali.
4. Verificare il runtime di argomentazione corretto: immagine
   `argumentation-chaincode:explanation-20261113-r1`, binario SHA-256
   `272f2780a2b83b019bd24e39680805355232244989e65f49b516597f8311ff92`,
   `libgraph.so` SHA-256
   `56182283f2c96444868d5a522adb468f27118f14710f16837242b666c3e78221`,
   ontologia attiva `/chaincode/onto/controlled-logback.owl` SHA-256
   `83b4f9629816003ed30eeab4b541d35450a4f39cf4efe317879ac019884e9ee9`.
   La sola presenza del tag non verifica binario o ontologia; i manifest di
   distribuzione sono negli archivi del benchmark corretto.
5. Usare il vero SQLite KG locale della pipeline, non il puntatore Git LFS di
   134 byte in Downloads. Dataset CTI SHA-256
   `e3566009408385c7aea7901a9e6499132f0ae4bb07ccbd80d22e2171e5f7990c`;
   OWL sorgente SHA-256
   `0ffa87d0ff610cd7860dc3cae4bd84e65ab223569ba19ef2f4240fba6da59350`.
   Manifest del generatore installato SHA-256
   `84d03335cb79787c114429b291a67957d22e896e9355d3c3abbb18fc43eb376e`.
6. Mantenere modello, prompt, contesto e timeout espliciti. Per C4-r3 e le
   ultime misure worker: `tesi-apache-qwen3:4b-32k`, contesto 32768,
   timeout LLM 600 s; protocolli e log conservano gli altri parametri.

Per i quattro casi gia predisposti esiste il launcher locale archiviato:

```bash
PYTHONPATH=. .venv/bin/python output/c4-collaudo-20261112-r2/run_case.py C1 --attempt 10
```

E un esempio per l'ambiente e i percorsi originali, da usare soltanto con numero
di tentativo libero. Il launcher rifiuta directory esistenti, apre gateway OTel
e SBOM effimeri, invoca il comando principale e li chiude. `C1` puo essere
sostituito con C2/C3/C4; il numero 10 non e riservato. Richiede anche accesso
OSV live e puo produrre output LLM diversi. Non occorre rieseguire questi casi
per verificare le tabelle finali. Nessuna suite SaaS va eseguita nella directory
`fablo-rest` live: i suoi test possono cancellare i metadati locali delle decisioni.

## Dove leggere gli esiti

`execution.json` e `dag.json` descrivono stato e fasi; `sources/` contiene asset,
assessment e candidate; `preparation/` contiene OWL, ALN e richieste; `strategic/`,
`validation/`, `recommendation/` e `finalization/` conservano i checkpoint.
La raccomandazione locale resta un checkpoint distinto dalla finalizzazione.
Confrontare record, digest, provenance e ricevuta tramite `get_finalization`
nella sessione MCP; per ranking e grafi usare i tool gia disponibili.

Per i casi primari: C1-r2, C2-r1, C3-r1, C4-r3 sotto
`output/case-improvements-20261106/`. Una decisione condizionata con commit
valido e un risultato tecnico riuscito, non un'azione applicata. C2/C3 possono
concludere senza ranking quando l'assessment non produce candidate.
Gli archivi completi conservano anche tutti i tentativi falliti e le riprese.
