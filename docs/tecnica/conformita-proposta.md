# Proposta iniziale, contributi e limiti alla chiusura

Riferimento: [proposta](../riferimenti/proposta-agentic-cti.pdf), §4, §14–16;
stato del 13 novembre 2026. La [valutazione finale](valutazione-finale.md)
contiene misure e copertura analitica; questa matrice distingue disponibilita
del prototipo, riuso delle baseline e requisiti ancora parziali.

## Corrispondenza architetturale e terminologica (§14)

| Requisito | Evidenza implementata | Confine o scostamento |
| --- | --- | --- |
| Osservabilita runtime | OTel SDK, gateway, export con hash e acquisizione dichiarata | I collaudi elaborano export gia raccolti: batch/replay, non real-time |
| Comunita di agenti | TelemetryAgent, VulnerabilityAgent, CountermeasureAgent, SemanticPreparationAgent e ruolo StrategicAgent; contratti e DAG espliciti | Quattro fasi strategiche appartengono a un ruolo; otto nodi non sono otto agenti distinti |
| Threat Agent (§4.3) | Parte dei metadati e trattata nel lookup CTI e negli artefatti | Non esiste un ThreatAgent separato; requisito architetturale non integralmente implementato |
| LLM | CAMEL e Ollama nei launcher completi C1/C4 e nelle tre prove isolate del worker | Retrieval CTI, policy, controlli di digest e generazione deterministica non sono capacita LLM |
| KG semantico | Lookup del KG locale, binding espliciti CVE/individui e generatore preesistente | Copertura limitata, identita ambigue e una sola candidata utile C1/C4 |
| Argomenti runtime e grafo | Grafo canonico con soluzione KG e nodo CVE; lineage degli ingressi | Nessun nodo libero esplicito delle tracce runtime nel grafo C1/C4; replay a identita/CTI fissi produce lo stesso grafo |
| BWAF e spiegazioni | Motore nativo della baseline su cinque grafi multicandidata; adapter di verifica e conservazione raw | C1/C4 usano convenzione a candidata singola; core Graph.cpp indisponibile, spiegazioni parziali e sensibili all'ordine |
| Semantica | Tiny-ME, abduzione applicativa; Bonus e contrazione esercitati nelle diagnostiche native | Bonus non invocato da ExplainAffinity; nessuna accettazione o fallback applicativo reale |
| SBOM/OSV | SBOM fornita, correlazione runtime/SBOM e chiamate OSV live nei launcher archiviati | Nuovi confronti finali a SBOM/KG fissi, senza nuova interrogazione OSV; SBOM non generata dalla telemetria |
| Decisione e azione | Selezione per CVE, astensione esplicita e raccomandazione in dry-run | Nessun attuatore o mitigazione eseguita; C1/C4 hanno selected_strategy_id nullo |
| Provenance | PROV-O realmente generata, decisione e provenance persistite insieme; ricevute e riletture | Metadati SaaS locali distinti dallo stato Fabric; costo della sola PROV-O non isolato |
| Switch richiesto dal professore | `--backend-mode mockup|real` nella stessa CLI; `--mode` distingue fixture/CAMEL | Nessun cambio branch per lo switch; real richiede servizi e ingressi configurati e non ripiega sui mock |

## Matrice dei contributi (§16)

Le attribuzioni seguono i repository e manifest disponibili. I riferimenti
individuali non verificati non sono attribuiti per inferenza. Vedere il
[registro delle fonti](../fonti-e-scelte.md), il
[registro baseline](../riferimenti/baseline-locali.json) e il
[resoconto del porting](../porting-principe-costa.md).

| Componente | Baseline riutilizzata | Contributo del prototipo di tesi |
| --- | --- | --- |
| Telemetria | Moduli della pipeline CTI agentica; OTel SDK | Gateway con origine esplicita, contratti degli asset e correlazione con SBOM; replay e casi controllati |
| CTI KG | Dataset cve2owl e moduli semantici preesistenti | Adapter MCP, gestione di ambiguita/astensione, verifiche di identita/versione e digest del dataset |
| Generazione | Generatore del grafo, owl_extension e proiezione ALN del repository pipeline | Preparazione canonica con manifest verificato, contratti, binding e checkpoint riusabili |
| Agenti e coordinamento | CAMEL e tool della pipeline | Contratti Pydantic, policy di pubblicazione, DAG dei produttori e delle fasi native, switch mockup/reale |
| Ranking | Contratto Go/C++, Tiny-ME/libgraph della baseline ledger | Collegamento SaaS/MCP, controllo degli input e delle riletture; associazione verificata delle explanation, raw e audit persistiti |
| Validazione | Servizi Tiny-ME, ontologie e contratti esistenti | Binding IRI, contesto/policy operativi separati, checkpoint di validazione e selezione della prima candidata effettivamente accettata |
| Finalizzazione | Fabric, contratto e servizio condiviso della baseline | Record decisione/PROV-O, idempotenza, digest e verifiche condivise attraverso MCP |
| Valutazione | Cinque coppie di grafi e ontologie delle baseline | Quattro casi, campione assistito, rubric delle spiegazioni, benchmark, confronti controllati e archivio ricalcolabile |

Nessuna nuova semantica BWAF e attribuita alla tesi. La formula euristica del
mockup rimane distinta dal motore nativo. Gli harness dell'ultima valutazione
riusano le interfacce esistenti e non aggiungono funzioni all'applicazione.

## Consegna e riproducibilita (§16)

| Deliverable | Stato e posizione |
| --- | --- |
| Asset, vulnerabilita e candidate | Artefatti in `sources/` dei run; C2/C3 terminano legittimamente senza candidate |
| OWL, ALN e grafo | `preparation/`, richieste native e grafi riletti; grafo annotato nel benchmark multicandidata |
| Ranking e spiegazione | Ledger, output nativo e audit del benchmark; convenzione singola distinta nei casi applicativi |
| Validazione e decisione finale | C1/C4-r3 completi, decisione condizionata; nessuna strategia accettata inventata |
| Provenance | Finalizzazioni reali, commit e cinque nuove riletture indipendenti identiche |
| Installazione e comando dimostrativo | README e [procedura finale](riproduzione-finale.md); configurazioni di esempio richiedono percorsi e servizi locali |
| Script e dati sperimentali | `evaluation/`, dati compatti in `evaluation/final-results-v1/`, archivi completi locali in `output/` |
| Test | Test esistenti, benchmark e verifiche dei dati; nella chiusura nessuna suite SaaS eseguita sullo store live |
| Baseline iniziale | Commit e hash registrati nei manifest e nel registro baseline; non confusi con il working tree corrente |
| Branch di tesi | Esterni su `costa-thesis`; framework su `full` |
| Cronologia delle modifiche | Modifiche locali ancora da selezionare e committare; nessun commit/push creato in questa fase |
| Autori e licenze | Repository e fonti registrati; attribuzione individuale e permessi/licenze dei componenti privati da confermare prima di redistribuirli; i manifest non conferiscono una licenza |
| Relazione | Markdown con risultati e matrice pronto; i due DOCX manuali sono rimasti intatti |

La raccolta e chiusa senza aprire altre estensioni. Le lacune scientifiche e
architetturali restano limitazioni esplicite del lavoro. Prima della consegna
rimangono l'inserimento nel testo di tesi e le operazioni editoriali/versionamento,
non una nuova campagna sperimentale obbligatoria nel perimetro concordato.
