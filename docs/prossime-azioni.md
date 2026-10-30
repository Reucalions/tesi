# Prossime azioni dopo il porting dei servizi condivisi

Stato di riferimento: 30 ottobre 2026. Il piano considera il codice verificato,
la proposta di tesi e le successive indicazioni del professore. La dimostrazione
attesa termina con una raccomandazione in dry-run; non richiede l'applicazione
automatica di contromisure al sistema.

## 1. Punto di partenza e risultato da raggiungere

Il framework in `tesi` rimane sul branch `full`; i due repository esterni sono
su `costa-thesis`. Il porting non ha spostato il framework sul branch esterno.

| Area | Stato verificato | Lavoro ancora necessario |
| --- | --- | --- |
| Agenti CAMEL | Quattro ruoli, artefatti validati e orchestrazione implementati | Collegare il percorso strategico ai servizi condivisi e inserire la responsabilita generativa richiesta |
| Telemetria e CTI | Ingressi OTel, lookup CTI, identita Apache e assessment Ubuntu disponibili | Caso principale con inventario, build e componente realmente osservato coerenti |
| Servizi condivisi | Sorgenti MCP e SaaS trasferiti nei due `costa-thesis` | Configurazione e collaudo sulla rete esistente |
| Verifica del porting | Build dei due componenti, discovery di 19 tool e 66 test in 13 suite | Test effettivi di ranking, Tiny-ME e ledger; Fabric e simulato nella suite importata |
| Provenance | Export locale e servizio condiviso di lettura disponibili | Provenance della raccomandazione completa, commit e rilettura dal backend |
| Dashboard | Dashboard Grafana Fabric presente nella baseline | Identificare la UI indicata dal professore e collegarla alle decisioni |
| Casi di argumentation | Cinque grafi e varianti riordinate disponibili | Ranking atteso documentato e collaudo attraverso i contratti condivisi |

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

Questo e il primo intervento tecnico sui servizi importati.

1. Verificare la rete effettivamente disponibile, i chaincode installati,
   le versioni e l'ontologia caricata. La configurazione su file non prova che
   i corrispondenti contratti siano distribuiti e raggiungibili.
2. Allineare i binding del backend: il sorgente importato usa
   `chaincode-argumentation` e `chaincode-semantic`, mentre `fablo-config.json`
   di costa-thesis definisce `argumentation` e `user-registry`. Confermare quali
   contratti sono realmente esposti, senza limitarsi a sostituire due stringhe.
3. Correggere il binding `ExplainAffinity`: il chaincode richiede
   `ontologyKey`, `resourceIRI`, `requestIRI`; il servizio passa solo due IRI.
   Verificare che gli IRI esistano nello snapshot ontologico utilizzato.
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

Il client attuale del framework usa HTTP; il bridge importato espone stdio.
Serve quindi un adattamento del trasporto e del contratto.

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

**Criterio di completamento:** un test del framework esegue una chiamata al bridge
effettivo, ne valida l'output e dimostra che e stato usato il backend condiviso.
Prima collaudo senza inferenza, poi orchestrazione CAMEL con modello programmato.

## 5. Identificare e integrare la pipeline generativa come agente

Questa attivita puo iniziare mentre si allinea il backend. Nel codice esaminato,
l'LLM estrae asset; annotazioni OWL e grafi vengono prodotti da trasformazioni
deterministiche. Non e ancora identificato con certezza il modulo LLM specifico
per annotazioni e argomenti indicato dal professore.

- Individuare repository, branch, entry point e versione del componente Bottalico.
  Se non emerge dai sorgenti disponibili, chiedere al professore il riferimento
  preciso; le altre integrazioni possono proseguire.
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

**Criterio di completamento:** lo stesso caso produce un grafo interpretabile e
il ranking concordato tramite il servizio reale, con spiegazioni riconducibili
agli input. L'ordine dei nodi e degli archi non modifica il risultato semantico.

## 7. Completare la selezione strategica dopo il ranking

La policy generale esiste gia: percorrere le candidate ordinate e selezionare la
prima accettata. Occorre collegarla ai contratti condivisi senza perderne i vincoli.

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

## 8. Completare la provenance condivisa e la verifica sul ledger

Il backend distingue gia decisione e provenance, ma la lettura attuale costruisce
provenance dal record applicativo. Non prova da sola la registrazione on-chain
della raccomandazione dopo la validazione semantica.

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

La sequenza consigliata e:

1. Consolidamento del porting e contratti, seguito dai binding backend/rete.
2. Trasporto MCP stdio e prime chiamate dal framework.
3. Identificazione della pipeline generativa, integrazione come agente e adapter
   canonico; caso di ranking con risultato atteso.
4. Ranking reale, validazione e selezione strategica.
5. Provenance condivisa, commit e rilettura.
6. Quattro scenari controllati end-to-end.
7. Dashboard, esperimenti comparativi e relazione finale.

Preparazione dei dati controllati e ricerca del componente generativo possono
procedere durante il lavoro sui servizi. Occorre chiarire con il professore
soltanto i riferimenti non ancora identificati: modulo generativo esatto,
dashboard decisionale se diversa da Grafana e contratto condiviso di finalizzazione
della raccomandazione qualora assente. Questi dubbi non bloccano i primi interventi.

La prossima attivita concreta e dunque allineare i binding del backend condiviso,
iniziando da chaincode, ontologia ed `ExplainAffinity`, e verificarli sulla rete
esistente prima di una nuova prova LLM completa.

Riferimenti: [porting verificato](porting-principe-costa.md),
[resoconto](../resoconto.md), [proposta di tesi](riferimenti/proposta-agentic-cti.pdf).
