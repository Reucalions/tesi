# Prossime azioni dopo il porting dei servizi condivisi

## Proposta per il nuovo perimetro del professore — 16 novembre 2026

Ispezionate le revisioni remote aggiornate di Principe, incluso il testbed a due
organizzazioni. [Analisi, sequenza proposta ed effort](tecnica/ispezione-d3fend-conoscenza-condivisa.md).
Prima dell'implementazione va definita la visibilità consortile o privata dei
contesti; seguono profili D3FEND, asset strategici versionati, recupero/feedback
nei due tenant e confronto CAMEL/deterministico. Il catalogo condiviso e la
composizione non sono ancora implementati. La raccolta chiusa sotto rimane
quella precedente, senza nuove prove Fabric o CAMEL eseguite in questa ispezione.

## Raccolta conclusa — 13 novembre 2026

La sintesi finale e stata completata, compresi confronti runtime, semantica,
pesi degli archi e stima circoscritta del costo del ledger. Non servono altre
raccolte per chiudere questo task. Consultare [valutazione finale](tecnica/valutazione-finale.md),
[conformita alla proposta](tecnica/conformita-proposta.md) e
[riproduzione](tecnica/riproduzione-finale.md).

Restano attivita di consegna: inserire risultati e limiti nella relazione manuale,
confermare attribuzioni/licenze private, selezionare e registrare le modifiche
locali in commit. I due DOCX sono intatti. Le lacune architetturali/scientifiche
sono limitazioni dichiarate, senza nuove estensioni richieste in questa fase.
La roadmap sottostante e storica; le richieste di misure ormai concluse non
costituiscono nuovi task aperti.

## Correzione circoscritta conclusa: 13 novembre 2026

Implementata e distribuita l'associazione verificata delle spiegazioni nel
chaincode esistente costa-thesis, con JSON nativo integro e audit rileggibili
via get_graph. Nuova campagna: 30 prove, 60/60 cammini associati correttamente,
score/pesi invariati e commit/riletture verificati. Diciassette test Go principali
passati. [Risultati](tecnica/correzione-spiegazioni-native.md).

Non occorre ripetere questa raccolta o estendere il core per chiudere il task.
Conservare i limiti separati: significato di against, copertura incompleta e
scelta di cammini/candidata spiegata ancora dipendente dall'ordine. Solo 6/15
coppie hanno explanation identiche, pur con tutte le associazioni ora valide.

Proseguire con sintesi finale delle metriche e dei confronti disponibili,
relazione e procedura dimostrativa con switch mock/real. Riportare criteri non
misurati senza inventare baseline o aggiungere profili semantici per ottenere
accettazioni. Le indicazioni sotto sul difetto di associazione descrivono lo
stato del 12 novembre, ora superato da questa verifica dell'adattamento.

## Benchmark concluso: 12 novembre 2026

Conclusa la campagna nativa richiesta: 30 prove, cinque coppie originali/riordinate,
tre repliche, punteggi e pesi identici nei 45 confronti. Commit e riletture
verificati, latenze archiviate. [Risultati](tecnica/risultati-benchmark-ranking.md).
Non occorre ripetere questa stessa serie per chiuderne la raccolta.

Resta un limite specifico: spiegazioni associate alla candidata errata in tutti
i riordinati, pur con archi e prodotti corretti; against positivo gia noto.
Conservare gli output e dichiarare separatamente stabilita dei punteggi e
mancata invarianza delle spiegazioni. Nessuna nuova patch al core in questo task.

Proseguire con la sintesi finale delle metriche e dei confronti effettivamente
sostenibili, riportando quelli non misurati (pesi impostabili, overhead equivalente,
ablation runtime). Preparare relazione e procedura dimostrativa con switch
mock/real gia disponibile. Non ampliare KG o profili semantici per produrre
artificialmente un caso accettato. Un'eventuale correzione delle spiegazioni nel
core e un intervento separato; non presentare il criterio come superato.
L'inventario storico dell'8 novembre resta invariato; le sezioni sotto ne
conservano lo stato e i precedenti passi ora svolti.

## C4 integrale concluso: 12 novembre 2026

L'ultimo tentativo C4-r3 e riuscito: un solo launcher real/camel/pipeline,
otto nodi completed, finalizzazione e rilettura verificate, exit code 0.
Timeout LLM 600 s, durata osservata 1224,254 s, nessuna ripresa manuale.
Il nuovo commit e nel blocco 28; gli archivi precedenti restano intatti.
[Report corrente](../output/c4-collaudo-20261112-r2/report.md).

Non occorre un altro tentativo C4 per chiudere questo collaudo. Conservare
`requires_prerequisites`, i prerequisiti semantici e il limite lessicale operativo
come risultati effettivi; non introdurre estensioni per produrre un'accettazione.
La valutazione ancora aperta riguarda ranking nativo su grafi riordinati e crescenti,
repliche omogenee, confronti sostenibili e relazione finale. Le metriche del
campione assistito e l'inventario storico dell'8 novembre restano separati.
Le sezioni sotto conservano i precedenti stati di C4, ora superati da C4-r3.

## C4: finalizzazione ripresa e verificata, 12 novembre 2026

Conclusa la ripresa CAMEL del solo ultimo nodo C4-r2: exit code 0,
finalizzazione/rilettura identiche al commit originale nel blocco 25.
Esito `requires_prerequisites`, `maintenance_window` mancante, nessuna candidata
selezionata. Il launcher originale e il DAG restano failed per timeout Ollama;
sette nodi originali e l'ultimo completato nella ripresa sono verificati separatamente.
[Evidenze e perimetro](../output/c4-collaudo-20261112-r1/report.md).

Resta non dimostrata una riuscita C4 in un unico launcher: una ripetizione dovra
usare una nuova directory, risorse locali adeguate e dichiarare il timeout LLM.
Nessuna nuova funzione o estensione semantica e necessaria per questa verifica.
Ranking nativo su grafi riordinati e crescenti, repliche, confronti e relazione
restano separati da questa ripresa e dai risultati assistiti dei componenti.
L'inventario dell'8 novembre resta una fotografia storica, senza nuovi conteggi
di copertura ricavati automaticamente dal solo esito C4. Le sezioni sotto
conservano gli stati precedenti.

## Prima misura completata: 12 novembre 2026

Calcolate [precisione/recall/F1 e accuratezze dei componenti](tecnica/risultati-metriche-componenti.md)
sul riferimento assistito v2, senza modificare etichette o backend. Archiviati
predizioni, audit MCP, protocollo, conteggi, CSV e hash. Disaccordi su vendor/
identita parziali, certezza delle versioni fuori intervallo e astensioni lessicali
rimangono nei risultati; non correggerli o eliminare casi per migliorare lo score.
I criteri non ancora misurati della sezione 15 restano aperti: ranking su coppie
riordinate e dimensioni crescenti, repliche omogenee, ablation e overhead equivalente.
Il corpus manuale umano resta non dimostrato; la misura attuale e su annotazioni
assistite verificate sulle fonti. Le sezioni sotto conservano la cronologia.

## Revisione delegata conclusa: 12 novembre 2026

L'utente ha delegato i controlli all'assistente: [v2 verificata e congelata](../evaluation/annotated-sample-v2/README.md),
28 casi confermati contro fonti e protocollo, nessun nuovo output del sistema.
Non richiedere che l'utente ripeta la verifica tecnica. Lavoro successivo:
raccogliere predizioni dai componenti esistenti, tenere le etichette fuori dagli
ingressi, calcolare le metriche senza cambiare i denominatori. Dichiarare che il
riferimento e assistito e non revisionato da un annotatore umano indipendente;
non presentarlo come pieno soddisfacimento del corpus manuale della proposta.
Le indicazioni sotto sulla revisione umana descrivono la precedente preparazione
della v1, ora conservata come bozza storica. Semantica e backend restano invariati.

## Campione di valutazione: 12 novembre 2026

Preparata la [bozza annotata v1](../evaluation/annotated-sample-v1/README.md),
con 28 casi, ingressi separati dalle risposte attese e motivazioni basate sulle
fonti grezze, senza usare output del matcher/evaluator per generare etichette.
Prossimo passo: revisione umana della scheda, risoluzione delle correzioni e
congelamento di una nuova revisione approvata prima delle predizioni. Mantenere
distinti dati reali/derivati, unknown/negativo e matching/classificazione della
versione. Nessun punteggio e ancora disponibile; non espandere la semantica di C1.

## Valutazione finale: 8 novembre 2026

L'utente mantiene il limite semantico di C1 e passa alla valutazione del prototipo.
Completati [inventario e copertura delle metriche](tecnica/valutazione-metriche.md):
698 file, 32 requisiti, 30 durate esplicite, 42 controlli di integrita coerenti.
Nessuna nuova esecuzione o modifica dei backend. Prossimo passo: definire un
campione annotato indipendente per estrazione/matching e il protocollo delle
misure mancanti, prima di nuovi run. C4 resta non completato; le due riprese non
valgono come launcher riusciti. Non introdurre nuovi profili semantici per chiudere
artificialmente il caso positivo; dichiarare i criteri ancora non dimostrati.

## Chiusura C1 verificata: 7 novembre 2026

C1-r2 ha completato il launcher reale CAMEL/Ollama e tutti gli otto nodi del DAG
con `dry_run_completed` e finalizzazione condivisa `completed`.
Esito decisionale: **requires_prerequisites**, con `selected_strategy_id=null`.
Tiny-ME restituisce abduzione 38 e score 62; il controllo operativo restituisce
`requires_review`. Il completamento tecnico non attesta una contromisura accettata.
C2/C3 restano completati; C4 e i suoi tentativi di ripresa restano non completati.

[Report corrente](../output/case-improvements-20261106/report-C1.md). Le sezioni datate sotto conservano la preparazione
e gli esiti precedenti; Logback e ora adottato nel protocollo v2.

Stato di riferimento: 6 novembre 2026. Il piano considera il codice verificato,
la proposta di tesi e le successive indicazioni del professore. La dimostrazione
attesa termina con una raccomandazione in dry-run; non richiede l'applicazione
automatica di contromisure al sistema.

**Decisione di chiusura dell'utente, 5 novembre:** nessuna ulteriore estensione
semantica o nuovo componente. Profili d'azione distinti, topologie alternative e
nodi runtime aggiuntivi restano sviluppi futuri, non prerequisiti di implementazione
per la chiusura concordata. La copertura parziale rispetto alla proposta e i limiti
scientifici restano espliciti. Completare casi controllati, collaudo del percorso
esistente, misure sostenibili e relazione; correggere soltanto difetti che impediscono
queste verifiche. I servizi reali si verificano a fine progettazione.

**Primo collaudo reale del 5–6 novembre:** dopo la richiesta dell'utente sono state
realizzate le due build Java coerenti e avviata la configurazione Fabric originale
dal repository costa-thesis, seguendo la guida. SaaS e MCP operativi, sei chiamate
reali con ranking nativo verificate. I tentativi dei produttori CAMEL/Ollama e i
limiti sono nel [report](../output/real-cases-20261105-r1/report.md). Il prossimo
lavoro riguarda gli ostacoli riprodotti alla pubblicazione delle candidate e la
copertura dei rimedi nel KG, senza nuove estensioni semantiche. Il percorso
positivo completo e le ricevute MAS restano da collaudare.

**Audit KG del 6 novembre:** scansione integrale e query del motore esistente
confermano rimedi assenti per le tre CVE Log4j. Individuata la coppia
Logback-core 1.5.24/1.5.25: CTI completo e proiezione ALN positiva verificati,
un solo rimedio di aggiornamento. Consigliata come adattamento contenuto del
caso Java, senza ampliare il KG; scelta non ancora applicata. C4 puo verificare
l'upgrade bloccato senza manutenzione, non un fallback. Prima dei nuovi run
servono fonti realmente osservate, binding/distribuzione nativa e correzioni LLM.
[Prove, alternative e limiti](../output/kg-coverage-20261106/report.md).

## 1. Punto di partenza e risultato da raggiungere

Il framework in `tesi` rimane sul branch `full`; i due repository esterni sono
su `costa-thesis`. Il porting non ha spostato il framework sul branch esterno.

| Area | Stato verificato | Lavoro ancora necessario |
| --- | --- | --- |
| Agenti CAMEL | Quattro ruoli, SemanticPreparationAgent e DAG composto fino alla finalizzazione condivisa; switch mockup/reale | Collaudo reale del percorso completo |
| Telemetria e CTI | Ingressi OTel, lookup CTI, identita Apache e assessment Ubuntu disponibili | Caso principale con inventario, build e componente realmente osservato coerenti |
| Servizi condivisi | Sorgenti MCP e SaaS trasferiti nei due `costa-thesis` | Configurazione e collaudo sulla rete esistente |
| Verifica del porting | Mapping MAS/canonico, finalizzazione, build SaaS e collaudo HTTP/stdio con riavvio; 652 test Python e 167 SaaS, Fabric simulato | Collaudo finale su rete reale |
| Provenance | Raccomandazione/provenance immutabili, commit/rilettura e riavvio verificati con fixture | Collaudo su rete reale e gestione operativa degli archivi |
| Dashboard | Dashboard Grafana Fabric presente nella baseline | Identificare la UI indicata dal professore e collegarla alle decisioni |
| Casi di argumentation | Cinque coppie verificate, aspettative qualitative e controlli client consolidati offline | Profili d'azione distinti, relazioni motivate e verifica numerica del core |

Il risultato finale deve consentire di ricostruire questa catena:

```text
Build e componente in esecuzione
  -> OTel e SBOM coerenti
  -> evidenza e rapporto CTI
  -> candidate e argomenti tracciabili
  -> grafo canonico e ranking condiviso
  -> validazione semantica delle candidate ordinate
  -> raccomandazione dry-run
  -> provenance condivisa, commit verificato e rilettura
  -> visualizzazione nella dashboard esistente
```

I mock restano strumenti di test e confronto. Il gateway Fabric sperimentale e
il chaincode di provenance separato non devono diventare dipendenze obbligatorie
del percorso principale, che deve usare i servizi condivisi.

## 2. Consolidare il porting e congelare i contratti

Prima fase del 31 ottobre: consolidati i contratti dei quattro agenti in un
registro condiviso, i controlli di corrispondenza fra lookup ed evidenza anche
per backend Python e i limiti dei tool acquisiti dai ruoli. Il confronto con
i contratti SaaS/MCP e documentato in
[architettura dei contratti](tecnica/architecture.md#consolidamento-degli-agenti-prima-del-collegamento-saas).
Corretti successivamente i binding e i comportamenti del SaaS che mascheravano
errori come ranking vuoto o rifiuto semantico, insieme ai contratti del bridge.
Build, 105 test backend, 12 test bridge e smoke REST/MCP sono passati con Fabric
simulato. Anche trasporto stdio e client nativo del framework sono implementati
e collaudati. Per decisione dell'utente la verifica dei servizi disponibili e
rinviata alla fine della progettazione: ora generazione e grafo canonico.
L'ispezione approfondita successiva ha individuato la pipeline ibrida Bottalico,
il wrapper LLM ProductionExtractor e i costruttori deterministici OWL/grafo/ALN.
Il [rapporto](../output/generator-inspection-20261031/report.md) conserva versioni,
prove e limiti; non emerge un generatore LLM separato di argomenti BWAF.

Prima di ampliare il codice, rendere riproducibile quanto importato:

- Revisionare i diff separatamente nei due repository, conservando attribuzione
  delle sorgenti, revisioni e adattamenti locali descritti in `PORTING-COSTA.md`.
- Preparare commit distinti e circoscritti per il porting, evitando di includere
  i file Identity/Ubuntu preesistenti o altre modifiche non pertinenti. I commit
  non sono stati ancora creati; neppure un push e stato eseguito.
- Confermare installazione da lock, build e test su Node.js almeno 22.12.0,
  documentando anche la versione del runtime utilizzato dal bridge MCP.
- Fissare input/output, identificatori, errori, timeout e responsabilita dei
  quattro tool principali: `rank_remediations`, `validate_countermeasure`,
  `get_decision`, `get_provenance`.
- Definire la corrispondenza tra `run_id`, asset, CVE, candidate, decisioni,
  snapshot di conoscenza e digest dell'ontologia.
- Gestire esplicitamente la cardinalita: il servizio di ranking accetta una CVE
  per richiesta, mentre un rapporto del framework puo contenerne molte.
  Definire il perimetro di ogni decisione prima di aggregare risultati.

**Criterio di completamento:** un esempio versionato attraversa i contratti
senza perdita di identificatori o semantica; i campi mancanti e gli errori sono
rappresentati esplicitamente. Nessun componente richiede un contratto alternativo
per lo stesso servizio condiviso.

## 3. Rendere operativo il backend sulla rete Fabric esistente

La verifica dei servizi disponibili e della rete reale e rinviata alla fine
della progettazione, come richiesto dall'utente. Questa sezione ne conserva
i controlli da eseguire in quel momento.
Le correzioni di binding e parsing dei punti seguenti sono implementate dal
31 ottobre e testate con Fabric simulato. Rimane da verificarle sulla rete reale;
non sostituire questa verifica con le sole build o con la discovery MCP.

1. Verificare la rete effettivamente disponibile, i chaincode installati,
   le versioni e l'ontologia caricata. La configurazione su file non prova che
   i corrispondenti contratti siano distribuiti e raggiungibili.
2. Confermare i contratti realmente esposti: il backend ora usa binding
   configurabili con default `argumentation` e `user-registry`, coerenti con
   fablo-config.json. Questi valori non provano il deployment.
3. Collaudare il binding `ExplainAffinity`, che ora passa
   `ontologyKey`, `resourceIRI`, `requestIRI`. Verificare che gli IRI esistano
   nello snapshot ontologico utilizzato e abbiano i ruoli di dominio attesi.
4. Verificare il formato reale della risposta Tiny-ME, inclusi score,
   penalita, prerequisiti e spiegazioni. Non usare valori predefiniti favorevoli
   quando mancano i campi necessari a stabilire la validita.
5. Separare incompatibilita semantica, prerequisiti mancanti ed errore tecnico.
   Un timeout o un chaincode irraggiungibile non dimostra che la candidata sia
   semanticamente incompatibile.
6. Configurare autenticazione, CA, peer, certificati TLS e porte nel backend.
   Questi dettagli non devono entrare negli input dello Strategic Agent.
7. Verificare una richiesta di ranking e una di validazione tramite la superficie
   di dominio del backend, conservando richiesta, risposta e riferimenti.

**Criterio di completamento:** i servizi condivisi eseguono una richiesta reale
sulla rete disponibile, con risposta leggibile e errori tecnici distinguibili.
Non occorre creare una seconda rete o duplicare gli smart contract.

## 4. Collegare il framework al bridge MCP condiviso

Completato il 31 ottobre: trasporto HTTP/stdio, configurazione del processo,
timeout e chiusura tramite SDK, audit e stderr separato. Il client nativo
`SharedServicesClient` usa una sola sessione per i quattro tool condivisi,
con schemi di discovery congelati e output Pydantic. Il probe dedicato e
`python -m thesis_agents.mcp.shared_probe`; esempio in
`config/mcp.shared-stdio.example.json`. [Guida](integrazioni/mcp-strategic.md).
La lista seguente descrive i requisiti implementati:

- Aggiungere supporto stdio alla configurazione e al ciclo di vita del client,
  conservando i profili HTTP utilizzati dagli ingressi gia collaudati.
- Avviare il processo MCP da configurazione controllata; l'LLM non deve scegliere
  comandi di shell o parametri di rete.
- Normalizzare le risposte testuali JSON `{ok, action, payload}` e gli errori
  del bridge, mantenendo la validazione locale dei dati.
- Adattare la discovery: il client attuale confronta anche `outputSchema` con
  i propri contratti v1. Non basta modificare l'URL o disabilitare tutti i controlli.
- Introdurre un profilo esplicito per i servizi condivisi e associare ai ruoli
  solo i tool necessari; la discovery di 19 tool non implica esporli tutti agli agenti.
- Conservare audit delle chiamate, timeout, chiusura del processo e comportamento
  in caso di errore, senza sostituzione silenziosa del servizio reale con un mock.

**Criterio raggiunto:** collaudo framework -> bridge effettivo -> SaaS effettivo,
con Fabric/autenticazione simulati, ranking REST/MCP coerente, riletture,
tre esiti semantici e guasti tecnici rifiutati. CAMEL programmato collaudato
con quattro backend MVP stdio. Il mapping degli artefatti MAS verso il contratto
nativo resta ai punti successivi; il trasporto non lo sostituisce.

## 5. Identificare e integrare la pipeline generativa come agente

Implementato il checkpoint autonomo SemanticPreparationAgent: contratti,
binding espliciti MAS/KG, richiamo dei moduli originali portati su costa-thesis,
OWL/ALN e richieste native per CVE. CLI e ruolo CAMEL verificati. Il profilo
Strategic nativo consuma ora il checkpoint per ranking e riletture per CVE,
con score originali. Validazione, selezione e DAG composto del comando principale
sono ora implementati: [guida](integrazioni/strategic-selection-dag.md).
[Guida e limiti](integrazioni/canonical-preparation.md). Qualsiasi integrazione
nei due repository esterni deve restare su costa-thesis, come ribadito dall'utente.

Ispezione completata su working tree, branch e storia locale dei due repository:
la pipeline e in `agent-based-cti-argumentation-pipeline/app/`.
`ProductionExtractor.extract_chunk` invoca LangExtract per vendor/product/version;
`owl_extension.py`, `argumentation_graph.py` e `tools/build_aln_projection.py`
costruiscono deterministicamente asserzioni, grafi e profili semantici degli
argomenti. La versione piu recente disponibile localmente e origin/main `090b684`,
con differenze rispetto a main, principe-thesis e costa-thesis.
Il vecchio agente Agno/Gemini trovato nella storia orchestrava ranking di grafi
gia costruiti ed e stato rimosso. Non risulta un modulo LLM separato che generi
direttamente argomenti BWAF. Il 3 novembre l'utente ha confermato che va utilizzata
la pipeline ibrida disponibile: questo punto e deciso e non richiede altri chiarimenti.

- Usare i componenti individuati e fissare la versione da riusare per ciascuno.
  Preparare un porting selettivo: costa-thesis contiene estensioni Identity/Ubuntu
  e correzioni MCP da conservare, non e un aggiornamento lineare a origin/main.
- Definire un ruolo agente esplicito per l'invocazione della pipeline riutilizzata,
  senza riscriverne la generazione o duplicare l'estrazione gia svolta da Telemetry.
- Concordare input: evidenza validata, rapporto CTI, contesto operativo e candidate,
  secondo il contratto effettivo del componente.
- Concordare output: annotazioni e argomenti con identificativi, fonti, relazioni
  proposte, versione del generatore e modello utilizzato.
- Distinguere fatti osservati, risultati del KG e ipotesi del modello. Un'asserzione
  LLM non diventa una misura OTel o una prova di sfruttamento.
- Inserire il nuovo artefatto e le dipendenze nel DAG prima della decisione strategica.
  Il CountermeasureAgent mantiene la responsabilita delle candidate; lo Strategic
  conserva orchestrazione e selezione.
- Rendere esplicita anche la copertura delle responsabilita Threat descritte nella
  proposta: assegnarle ai ruoli esistenti oppure motivare un ruolo distinto,
  senza aggiungere agenti soltanto per riprodurre le etichette del diagramma.

**Criterio di completamento:** il ruolo invoca il componente riutilizzato e pubblica
un artefatto tracciabile consumato dal percorso strategico. Eventuali fixture
servono ai test e non valgono come prova della generazione LLM reale.

## 6. Definire l'adapter verso il grafo canonico di argumentation

**Consolidamento offline del 5 novembre completato:** significati, fonti, scale e
aspettative indipendenti sono nel [contratto scientifico](tecnica/consolidamento-scientifico-grafo.md)
e nel [catalogo dei casi](../config/scientific-graph-cases.v1.json). Corretti confronto
asimmetrico degli score, gestione di dati mancanti, controlli dei cammini e parsing
delle penalita nel percorso ExplainAffinity. Gli score nativi restano inalterati.
Il criterio numerico su servizio reale descritto sotto rimane da soddisfare.

L'ispezione ha dimostrato che le quattro candidate della demo hanno lo stesso
profilo ALN asserito e che riassegnare ID puo cambiare l'anello. Dimostrare preferenze
applicative richiederebbe profili distinti e relazioni giustificate da fonti.
L'utente ha escluso questa estensione dal lavoro corrente: il limite va dichiarato,
senza presentare i pareggi o lo spareggio per ID come superiorita di un'azione.
Runtime e vincoli, pur tracciati e valutati nella policy, non sono ancora nodi
autonomi del BWAF canonico.

La costruzione deterministica dell'adapter e distinta dalla generazione degli
argomenti. L'adapter traduce una rappresentazione in un'altra; non introduce
un algoritmo di ranking alternativo.

- Definire tipi e significato dei nodi: evidenze, vulnerabilita, vincoli e strategie.
- Definire direzione, supporto e attacco di ogni relazione. Il grafo semplificato
  non deve essere presentato come BWAF completo senza questa corrispondenza.
- Documentare dove risiedono le relazioni nel contratto effettivo e nell'ontologia.
  Se il JSON trasporta soltanto `id/type` e `from/to`, spiegare come il servizio
  ricostruisce i significati necessari; non inventare campi ignorati dal backend.
- Esplicitare origine e normalizzazione dei pesi: reasoning semantico, dati CTI,
  metriche, policy oppure stime del modello. Non attribuire al framework pesi
  calcolati internamente dal servizio, ne introdurre costanti prive di motivazione.
- Conservare il legame tra ogni nodo/relazione e la fonte che lo giustifica.
- Definire trattamento di dati mancanti, contraddizioni, candidate duplicate,
  pareggi e risposte incomplete. Una graduatoria vuota inattesa deve essere
  distinta dal caso legittimo senza candidate.
- Usare i grafi gia presenti in `chaincode-argumentation/client/tests`, scegliendo
  un caso di riferimento con ranking atteso motivato e verificabile.
- Provare anche le versioni con nodi e archi riordinati. Il riferimento non deve
  essere semplicemente il primo output restituito dal servizio.

L'ispezione ha rilevato che graph_test_4_reordered.json mancava di due archi
rispetto all'originale (41/43). Corretto su costa-thesis il 1 novembre (43/43),
con backup della baseline originale. L'anello tra strategie ordinate per ID e
ora qualificato come policy sperimentale, senza attribuirgli relazioni di dominio
non osservate. Il costruttore SaaS legacy conserva la direzione CVE/strategia
opposta e non e qualificato come baseline: il percorso canonico trasmette sempre
il grafo esplicito. Nessuna nuova prova del ranking nativo reale eseguita.

**Criterio di completamento:** lo stesso caso produce un grafo interpretabile e
il ranking concordato tramite il servizio reale, con spiegazioni riconducibili
agli input. L'ordine dei nodi e degli archi non modifica il risultato semantico.

## 7. Selezione strategica dopo il ranking: implementata

Il 3 novembre e stato completato il collegamento ai contratti condivisi: scelta
della prima effectiveStatus=accepted per CVE, esiti distinti per prerequisiti,
revisione e nessuna valida, errori tecnici bloccanti. Tutti i tentativi sono
conservati e gli score non vengono modificati. Lo switch applicativo collega
le fasi nel DAG composto. [Comandi e prove](integrazioni/strategic-selection-dag.md).
I punti seguenti sono i criteri implementati, da riconfermare nel collaudo live:

- Per ogni candidata esaminata, conservare ranking, validazione e motivazione.
- Se la prima e incompatibile, valutare la successiva. Se richiede prerequisiti
  mancanti, riportarli e applicare una policy esplicita; non dichiararla accettata
  incondizionatamente.
- Se tutte sono respinte, produrre l'esito previsto senza inventare un vincitore.
- Se il servizio e indisponibile, segnalare un fallimento tecnico del run o dello
  step: non convertirlo in `insufficient_evidence` o in un rifiuto ontologico.
- Mantenere distinte astensione per evidenza insufficiente, assenza di finding,
  assenza di strategie valide e raccomandazione selezionata.
- Conservare l'astensione legittima del caso Apache storico. L'obiettivo non e
  rimuovere quella stringa, ma ottenere un esito positivo quando gli input lo giustificano.

**Criterio di completamento:** un caso accetta la prima candidata e un altro
respinge la prima e raccomanda una successiva, con motivazioni verificabili.
In entrambi i casi l'azione rimane in dry-run.

## 8. Provenance condivisa implementata; verifica su rete reale da completare

Estensione autorizzata e implementata nei componenti condivisi esistenti dopo
l'ispezione approfondita del 3 novembre (70 commit, 371 versioni uniche e KVContract
storico). Nuovi tool `finalize_recommendation` e `get_finalization`, persistenza
backend delle validazioni, metodi StoreRecommendation/ReadRecommendation nello
stesso contratto argumentation, ricevuta Gateway e doppia rilettura. La PROV-O lega
la scelta effettiva, ogni valutazione e gli otto artefatti originali; corretti
attivita non osservate, graphId e JSON-LD. Nessun nuovo servizio autonomo.

Il DAG completo include la quarta fase Strategic; il checkpoint finale distingue
`shared_finalization=completed`, verifica riferita dal backend, deployment non
verificato e azione mai eseguita. Cinque esiti, scelta alternativa, idempotenza,
conflitti e riavvio effettivo del SaaS sono collaudati con Fabric/Tiny-ME simulati.
[Contratti, comandi e limiti](integrazioni/strategic-finalization.md).

I criteri seguenti sono implementati e restano da ripetere nel collaudo live:

1. Verificare se esiste un'operazione condivisa per finalizzare la decisione con
   strategia raccomandata e tutti gli esiti di validazione.
2. Se manca, proporre una piccola estensione del contratto SaaS/MCP condiviso,
   concordandone responsabilita e persistenza. Non creare automaticamente un
   nuovo servizio di provenance o un chaincode separato.
3. Associare entita, attivita e agenti a evidenza OTel, SBOM, CTI, argomenti,
   grafo, ranking, validazioni e decisione finale.
4. Verificare la corrispondenza tra record locale e condiviso: run, strategia,
   snapshot, versioni e digest. Un ID di decisione di ranking non basta a
   certificare la selezione finale effettuata dal MAS.
5. Conservare transaction ID e stato di commit valido per gli artefatti
   effettivamente registrati, distinguendoli dai dati conservati fuori dal ledger.
6. Rileggere decisione e provenance tramite backend/MCP e confrontarne i campi
   stabili e i digest; verificare anche la persistenza dopo un riavvio controllato.
7. Provare una ripetizione della richiesta e definire idempotenza e correlazione
   delle chiamate, evitando duplicazioni causate da retry.

**Criterio di completamento:** dalla ricevuta si arriva a un record riletto e
coerente con la raccomandazione; e documentato quali dati sono on-chain e quali
off-chain. Nessuna attivita PROV-O descrive come applicata una contromisura soltanto proposta.

## 9. Preparare il caso sperimentale controllato

Il 5 novembre sono stati preparati il
[protocollo dei quattro casi](../config/controlled-cases.v1.json) e la
[guida di confronto con i mock](tecnica/casi-controllati.md). Verificati quattro
run CLI mockup, quattro mapping di catture CTI e le fonti Java/SBOM/OTel negative
archiviate. Il mock non supporta una valutazione negativa: per C2 il suo
insufficient_evidence e distinto dal no_findings della cattura CTI. Restano da
materializzare build vulnerabile e fonti coerenti C1/C4 e degradazione C3; i quattro
run reali non sono pronti o eseguiti. Nessun nuovo backend o arricchimento semantico.

Riutilizzare dove possibile l'applicazione locale gia presente. Scegliere il
componente principale dopo aver verificato copertura CTI, disponibilita delle
contromisure e rappresentabilita nell'ontologia utilizzata dai servizi condivisi.

Per ogni esecuzione conservare un manifest con identificativo di build, revisione,
digest dell'artefatto o immagine, SBOM, versione effettivamente caricata, identita
del processo/servizio, finestra temporale OTel e snapshot CTI/ontologico.
Log che dichiarano una versione non sostituiscono la verifica del componente caricato.
I dati possono essere registrati e riprodotti staticamente, purche derivino dalla
stessa esecuzione controllata e il replay sia dichiarato come tale.

| Scenario | Preparazione | Esito da verificare |
| --- | --- | --- |
| Vulnerabile, evidenza sufficiente | Versione affetta realmente caricata e fonti coerenti | Candidate, ranking, validazione e raccomandazione dry-run |
| Non vulnerabile rispetto al caso | Versione corretta e CTI in grado di valutarla | Nessuna raccomandazione basata sulla CVE del caso; limite dello snapshot esplicito |
| Evidenza incompleta | Rimuovere un'informazione necessaria e dichiarare la modifica | Astensione motivata e richieste di verifica, senza dati inventati |
| Vulnerabile con vincoli operativi | Stessa evidenza del primo caso, vincolo esplicito sulla remediation | Rigetto o condizionamento della prima opzione e valutazione delle alternative |

Il quarto scenario deve essere rappresentato nelle informazioni effettivamente
fornite al servizio semantico. Inserire soltanto una frase nel prompt non dimostra
che Tiny-ME abbia verificato quel vincolo.

**Criterio di completamento:** quattro ingressi riproducibili e una tabella degli
esiti attesi definita prima dell'esperimento, con artefatti e fonti conservati.

## 10. Eseguire il collaudo end-to-end per livelli

Eseguire prima servizi e adapter senza LLM, poi orchestrazione con modello
programmato, infine inferenza LLM reale sull'intera catena. I tre livelli risolvono
domande diverse e non devono essere confusi nella relazione.

Per ogni scenario verificare identita dell'asset, completezza degli artefatti,
servizi effettivamente invocati, semantica del grafo, ranking, tentativi di
validazione, decisione, provenance e rilettura. Confrontare REST e MCP usando le
superfici effettive: due chiamate dirette allo stesso metodo non dimostrano da
sole la parita dei trasporti.

Aggiungere casi di errore mirati: tool assente, payload incompatibile, timeout,
IRI inesistente, ranking vuoto inatteso e commit non valido. Nessun fallimento
deve essere mascherato come successo o sostituito da un risultato mock.

**Criterio di completamento:** un audit ricostruisce l'intero percorso dai file
del run e dalle riletture del backend, distinguendo test simulati e servizi reali.

## 11. Riutilizzare la dashboard indicata dal professore

Nel materiale verificato e presente Grafana per le metriche Fabric. Prima di
sviluppare una nuova interfaccia, identificare se il professore intende questa
dashboard oppure una UI decisionale in un'altra directory o revisione.

Collegare la dashboard esistente ai risultati tramite il backend condiviso,
mostrando asset, CVE, fonti, grafo, classifica, validazioni, strategia raccomandata,
motivazione, provenance e stato della registrazione. Dati mancanti, errori tecnici
e dry-run devono risultare visibili. I grafi non devono ricostruire un ranking
diverso da quello restituito dal servizio.

**Criterio di completamento:** dalla UI si apre una decisione reale e si segue
il riferimento alla provenance riletta dal backend. Le metriche Fabric affiancano
il risultato decisionale senza sostituirlo.

## 12. Esperimenti e aggiornamento della relazione

Definire numero di ripetizioni e criteri di valutazione prima della raccolta.
Misurare almeno:

- correttezza di estrazione e matching su un campione annotato: precisione,
  recall, F1 e accuratezza della valutazione delle versioni;
- correttezza della decisione nei quattro scenari e qualita delle spiegazioni;
- determinismo del servizio a grafo fissato, anche riordinando nodi e archi;
- variabilita della pipeline LLM, separata dal determinismo del ranking;
- accettazione della prima candidata, fallback e condizioni mancanti;
- latenza di ingestione, agenti, annotazioni, costruzione grafo, MCP, ranking,
  semantica, commit, rilettura e durata totale, distinguendo retry e fallimenti;
- sensibilita ai pesi e dimensioni crescenti dei grafi, entro quanto esposto
  dall'implementazione condivisa;
- confronto tra mockup e servizi condivisi sugli stessi ingressi, esplicitando
  differenze degli algoritmi e dei contratti;
- confronto prima/dopo validazione semantica e, dove possibile, costo della
  registrazione blockchain rispetto al percorso equivalente senza registrazione.

Conservare anche i run falliti; evitare di misurare soltanto le esecuzioni riuscite.
Riportare statistiche e numero dei campioni; percentili solo se il campione li rende
informativi. Il confronto con il mockup non e una prova di accuratezza del BWAF.

Aggiornare poi relazione e diagrammi: distinguere componente riutilizzato,
contributo della tesi, modulo simulato, risultato collaudato e limite residuo.
La nuova roadmap prevale sulle sezioni storiche che propongono una rete o un
chaincode di provenance separati come percorso principale.

## 13. Ordine operativo e chiarimenti circoscritti

Per chiudere senza ampliamenti, la sequenza operativa e:

1. Porting, contratti e trasporto MCP stdio completati e collaudati con Fabric simulato.
2. Pipeline ibrida identificata: contratto/ruolo agente e adapter
   canonico; caso di ranking con risultato atteso.
3. Mapping degli artefatti MAS, ranking, validazione e selezione strategica.
4. Finalizzazione/provenance e consolidamento scientifico offline completati;
   preparare i quattro scenari con fixture e ingressi esistenti, dichiarandone i limiti.
5. Riusare la dashboard esistente e preparare gli esperimenti senza nuove UI.
6. Alla fine della progettazione: servizi disponibili, rete/ontologia/TLS reali,
   collaudo end-to-end, commit/rilettura, esperimenti e relazione finale.

Preparazione dei dati controllati e ricerca del componente generativo possono
procedere durante il lavoro sui servizi. Occorre chiarire con il professore
soltanto la dashboard decisionale se diversa da Grafana. La pipeline ibrida
disponibile e confermata dall'utente. L'estensione dei componenti esistenti per la
finalizzazione e stata autorizzata, implementata e collaudata con fixture.

Il raccordo checkpoint -> Strategic -> ranking/riletture native e implementato
e collaudato con processo MCP stdio e SaaS simulato: [guida](integrazioni/strategic-native.md).
Implementati anche binding IRI e contesto operativo nella validazione nativa:
[guida](integrazioni/strategic-validation.md). Esiti Tiny-ME e policy SaaS rimangono
distinti; vincoli non mappati richiedono revisione. Selezione su effectiveStatus,
integrazione nel DAG e comando di switch sono implementati e collaudati con
servizi sintetici: [guida](integrazioni/strategic-selection-dag.md). Completata anche
la [finalizzazione condivisa](integrazioni/strategic-finalization.md). La prossima
attivita concreta e predisporre i casi controllati e collegare la dashboard esistente.
Il controllo di equivalenza dei cinque
grafi e stato corretto. La verifica live dei servizi seguira a progettazione completata.

Riferimenti: [porting verificato](porting-principe-costa.md),
[resoconto](../resoconto.md), [proposta di tesi](riferimenti/proposta-agentic-cti.pdf).
