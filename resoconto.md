# Resoconto operativo

## Punto di ripresa: roadmap concordata nei tre punti del professore — 17 novembre 2026

**Leggere prima questa sezione per riprendere il lavoro.** Riassume le decisioni
della chat successive all'ispezione del 16 novembre; le sezioni sotto conservano
la cronologia e possono riportare stati precedenti. Il report accademico è
considerato soddisfacente dall'utente. Non sono iniziate le nuove implementazioni.
L'ultima richiesta autorizza soltanto questo aggiornamento di `resoconto.md`.

### Perimetro e decisioni concordate

Il professore chiede di mantenere come struttura i **tre punti iniziali**:

1. Stesso caso CTI su due tenant con comunità CAMEL distinte e contesti/policy
   differenti, verificando coerenza delle decisioni e separazione di workflow,
   artefatti e provenance.
2. Confronto tra esecuzione CAMEL effettiva e percorso deterministico/prefissato
   sullo stesso scenario: candidate, tool, retry/recuperi, esito e tempi.
3. Caso con due/tre contromisure: ranking, validazione semantica/operativa e
   prima candidata applicabile oppure astensione; se il caso lo consente,
   dimostrare il passaggio a una candidata successiva alla prima nel ranking.

D3FEND, conoscenza condivisa, feedback, riuso e composizione vanno integrati
**dentro questi tre punti**, non trasformati in ulteriori progetti autonomi.
Il professore richiede anche la valutazione di ATT&CK, da integrare se possibile,
e il monitoraggio delle metriche prestazionali, riusando l'osservabilità di
Principe. «Def3nder» è stato chiarito come MITRE D3FEND, non un altro strumento.

L'utente ha accettato una roadmap per un **dimostratore circoscritto in una
settimana lavorativa**, con un solo caso, due tenant, due/tre strategie, un ciclo
di feedback e una composizione dichiarata di due azioni. È un obiettivo
condizionato, non una garanzia di completamento già verificata. Le stime di
10–15 giornate della sezione successiva riguardano l'estensione più generale.

### Riscontri disponibili: non ripetere l'ispezione completa

Teste remote ricontrollate in sola lettura il 17 novembre, invariate dal 16:

| Repository locale | Branch di lavoro da conservare | Testa remota `principe-thesis` verificata |
| --- | --- | --- |
| `/Users/reucalion/Desktop/agent-based-cti-argumentation-pipeline` | `costa-thesis` | `18384d7c168225deacb347c5218e10f897b2a6c3` |
| `/Users/reucalion/Desktop/semantic-cti-ledger-argumentation` | `costa-thesis` | `5a31ca8403bf34f6344683787412be0967936d89` |

Il framework è sul branch `full`. Qualsiasi integrazione nei due repository
esterni deve avvenire esclusivamente su `costa-thesis`; lo switch mockup/reale
resta un comando applicativo e non richiede cambi di branch.

Il riferimento locale ledger `origin/principe-thesis` è obsoleto (`a16be9e`).
Usare per la lettura della revisione verificata la copia bare esistente
`output/integration-inspection-20261116/ledger.git`, ref `audit-principe`, oppure
i sorgenti estratti. Non sovrascrivere il codice Costa con quello upstream:
vanno conservate le correzioni di contratti, identità, parsing, commit,
validazione operativa e finalizzazione. Il connettore GitHub non vede i due
repository; l'accesso Git remoto configurato ha funzionato. Non eseguiti fetch
nei repository esterni né cambi di branch.

Materiali da consultare con letture mirate:

- [Ispezione tecnica dettagliata](docs/tecnica/ispezione-d3fend-conoscenza-condivisa.md).
- [Indice delle evidenze](output/integration-inspection-20261116/README.md):
  revisioni, manifest, sorgenti, differenze dal porting e prova D3FEND.
- `output/integration-inspection-20261116/principe-ledger/testbed/`: configurazione
  consortile, due org/quattro peer, un channel `consortium`, due SaaS su 8801/8802.
- D3FENDEnricher e SelectiveRecomputationEngine di Costa sono già identici alle
  versioni remote verificate. Il classificatore mappa upgrade/isolamento, mentre
  monitoraggio generico resta `unmapped`; mapping e confidenza non provano
  applicabilità o efficacia. Il grafo canonico attuale salta l'arricchimento
  automatico e non trasferisce le annotazioni D3FEND nelle candidate native.
- L'asset store SaaS esistente descrive software in RAM/disco; non è ancora un
  catalogo ledger di strategie. Le finalizzazioni hanno lettura di dominio
  riservata al proprietario: la condivisione richiede una pubblicazione esplicita.
- ATT&CK è predisposto nell'ontologia di base (`AttackPattern`,
  `hasMITREATTCKID`, `hasSubTechniqueID`), ma non è operativo nel percorso canonico
  collaudato. Le caratteristiche CVSS `hasAttackVector`/`AttackVectorLocal`
  non sono tecniche ATT&CK; C1 non contiene questi mapping ATT&CK.

### Osservabilità verificata il 17 novembre

Nella pipeline di Principe, lettura con `git show origin/principe-thesis:<path>`:

- `app/src/utils/e2e_metrics.py`: timer delle quattro fasi e campionamento RSS
  del solo processo Python; è collegato a `app/src/main.py`. Il sampler usa
  `/proc/self/statm`: va adattato o eseguito in ambiente compatibile per macOS.
- `app/src/utils/monitoring.py`: contatori e durate dell'estrazione per chunk.
- `opentelemetry/otel-collector-config.yaml`: acquisizione di log ed export su
  file; non equivale al monitoraggio delle prestazioni delle comunità CAMEL.

Nel ledger di Principe, lettura della copia bare `audit-principe`:

- `testbed/docker-compose.monitoring.yaml` e `testbed/prometheus.yml`:
  Prometheus/Grafana, scraping di orderer e dei quattro peer. Non comprende
  ancora le metriche dei nostri run CAMEL o dei due SaaS.
- `monitoring/` include anche Pushgateway e un target REST; la presenza di un
  target configurato non prova l'esistenza dell'endpoint applicativo `/metrics`.
- Esiste una dashboard Fabric con 16 pannelli, intitolata per la versione 1.4:
  verificare query/compatibilità con i servizi effettivi prima di riutilizzarla.
- Nel framework `RunAudit` e il client MCP registrano già run, stati, errori e
  `elapsed_seconds`. Da raccordare all'esposizione delle metriche e alla dashboard.

Quindi la base di osservabilità esiste; resta l'integrazione con tenant,
modalità, fasi, tool e run del framework. Nessuna nuova rete, dashboard o
esecuzione sperimentale è stata avviata durante questa verifica.

### Task di implementazione dentro i tre punti

**Punto 1 — Tenant e comunità.** Riusare il testbed e le indicazioni che darà il
professore; collegare due Workforce, identità, sessioni MCP e memorie separate.
Conservare artefatti/provenance distinti; aggiungere volumi SaaS separati e
verificare accessi incrociati, commit e riletture. Il nuovo script di setup ha
operazioni di pulizia ampie e il generatore multi-channel ha raccordi mancanti:
non avviarlo senza circoscrivere la rete e seguire la configurazione confermata.

Per il piano settimanale l'ipotesi è un canale consortile con dati controllati e
schede strategiche pubblicate esplicitamente, mantenendo separazione applicativa
dei tenant. La visibilità va fissata al giorno 1: lo stato pubblico del canale
è visibile ai peer membri. La riservatezza rispetto ai loro amministratori
richiederebbe collection/transient e non è inclusa nella settimana proposta.

**Punto 2 — Confronto e metriche.** Realizzare una baseline deterministica sui
medesimi backend reali, con scenario, fonti, policy e catalogo fissati. La CLI
attuale impone CAMEL per `--backend-mode real`; le fixture mock non costituiscono
la baseline richiesta. Riutilizzare sessioni e operazioni esistenti, mantenendo
esplicita l'assenza di inferenza nel percorso prefissato.

Integrare Prometheus/Grafana con durata end-to-end e delle fasi, tool invocati,
errori, retry/recuperi, memoria del processo osservato e metriche Fabric già
disponibili. Correlare tenant/modalità/run e conservare gli eventi originali.
Verificare la raccolta effettiva, non la sola presenza della dashboard.

**Punto 3 — Candidate, semantica e feedback.** Scegliere due/tre alternative
documentate, raccordare D3FEND al preparatore canonico e mantenere ranking,
validazioni e prima selezione applicabile effettivi. Inserire un piccolo
registro ledger di strategie/versioni con condizioni, annotazioni e provenance
pubblicabile; recuperarle tramite MCP come input del CountermeasureAgent.
A pubblica una strategia qualificata, B la istanzia/rivalida nel proprio contesto
e può pubblicare un adattamento collegato all'origine. Un template riusabile
richiede individui contestuali: il proiettore oggi rifiuta lo stesso individuo
strategico condiviso tra CVE differenti. Non indebolire silenziosamente i binding
KG e i controlli canonici per introdurre candidate arbitrarie.

Per la composizione limitarsi a una sequenza predefinita di due azioni, con
ordine, precondizioni, effetti e compatibilità espliciti. Per ATT&CK valutare
subito una/due associazioni documentabili, versionate e pertinenti al caso;
integrare soltanto se supportate dalle fonti. Una CVE non dimostra che una tecnica
sia stata osservata; distinguere contesto ipotizzato da evidenza osservata.
Riutilizzare i ruoli esistenti, senza aprire un progetto autonomo ATT&CK.

### Sequenza settimanale accettata

| Giorno | Attività | Risultato atteso |
| --- | --- | --- |
| 1 | Fissare perimetro/visibilità; verificare rete, caso semantico e metriche; valutare ATT&CK | Prerequisiti verificati e scenario fissato |
| 2 | Collegare i tenant, raccordare D3FEND e avviare strumentazione delle metriche | Primo percorso completo sui due contesti |
| 3 | Pubblicazione, recupero e riferimenti versionati delle strategie | Primo riuso A → ledger → B |
| 4 | Baseline deterministica, fallback, composizione limitata e dashboard | Quattro condizioni principali eseguibili |
| 5 | Repliche, ciclo di feedback, isolamento e sintesi | Evidenze e confronto conclusivo |

Raccolta minima proposta: due tenant × due modalità × tre ripetizioni (12 run),
più una dimostrazione separata del feedback. Le sei esecuzioni CAMEL, ai tempi
storici di circa 20–21 minuti ciascuna, richiedono già circa due ore, oltre a
baseline e controlli. Tenere fisso lo snapshot del catalogo nei confronti ed
evitare che il feedback di una replica contamini le successive.

**Primo passo alla ripresa: giorno 1, verifica dei prerequisiti, prima di nuovi
sviluppi.** Il caso C1 attuale rimane semanticamente condizionato e non dimostra
una candidata accettata: serve scegliere un caso con profili adeguati e fonti
verificabili per mostrare selezione, alternativa e pubblicazione qualificata.
Se rete o caso semantico richiedono interventi sostanziali, rivalutare subito
la fattibilità settimanale. Non fabbricare accettazioni o modificare gli score.

### Vincoli da mantenere nella ripresa

- Nuove integrazioni esterne solo su `costa-thesis`; ispezionare prima i
  componenti disponibili e riusare framework, backend, contratti e osservabilità.
- Separare attività proposte, implementate e collaudate. La roadmap è accettata,
  ma l'esecuzione non è ancora iniziata: non interpretare questa nota come
  un collaudo o come avvio dei servizi.
- Lo stato resta dry-run: strategia proposta/validata/selezionata o riusata nel
  ragionamento non significa azione applicata né efficacia misurata sul campo.
- Fuori dal dimostratore settimanale: catalogo generale, composizione automatica,
  integrazione estesa ATT&CK e riservatezza completa sul ledger.
- Preservare report approvato, Word manuali, risultati/log/snapshot storici e
  ledger esistente. Non eseguire test SaaS negli store live o reset distruttivi.

## Ispezione D3FEND, multi-tenant e feedback condiviso — 16 novembre 2026

Esaminate le nuove richieste del professore: due comunità CAMEL, confronto con
percorso deterministico sugli stessi backend, più candidate e riuso/composizione
delle strategie come conoscenza condivisa sul ledger. D3FEND confermato come
significato di «Def3nder». Analisi e proposta, senza implementazione delle nuove
funzioni o modifica del report accademico.

Verificate le teste remote: pipeline `18384d7`, ledger `5a31ca8`. Il riferimento
locale ledger era fermo a `a16be9e`; la revisione aggiornata è stata acquisita
soltanto nella copia di ispezione nel workspace. Entrambi gli esterni restano su
costa-thesis, senza merge, porting o aggiornamento dei loro riferimenti Git.
Individuato il testbed consortile già predisposto: due organizzazioni, quattro
peer, un channel e due SaaS. D3FENDEnricher e SelectiveRecomputationEngine correnti
coincidono con quelli remoti. Prova isolata: upgrade e isolamento mappati,
monitoraggio generico non mappato; le tecniche custom non sono classi MITRE
automaticamente certificate. Nessun SaaS, Fabric o LLM invocato.

Mancano un catalogo ledger di strategie versionate, pubblicazione/visibilità
esplicite, recupero negli agenti e riqualificazione nel contesto destinatario.
L'asset store esistente descrive software e usa RAM/disco del SaaS. Il grafo
canonico salta l'arricchimento D3FEND automatico e vincola oggi le candidate ai
rimedi KG. I template riusabili devono avere istanze ontologiche contestuali.
Distinta separazione API tenant da riservatezza del ledger consortile; rilevati
volumi SaaS mancanti, raccordi di configurazione e limiti del generatore multi-channel.

Proposta circoscritta: D3FEND per classificazione/ricerca, selezione dopo ranking
e validazione del nuovo contesto, pubblicazione autorizzata di asset qualificati,
feedback con provenance e una composizione di due passi. Lo stato corrente
resta dry-run: nessuna efficacia operativa o azione eseguita viene rivendicata.
Effort indicativo 10–15 giornate-persona per demo con visibilità consortile;
riservatezza ledger con collection/transient richiede ulteriori 5–8 giornate,
da affinare sulla configurazione che fornirà il professore. Le stime precedenti
riguardavano il perimetro sperimentale più ristretto.

[Ispezione e proposta dettagliata](docs/tecnica/ispezione-d3fend-conoscenza-condivisa.md).
Evidenze, sorgenti congelati e verifiche in `output/integration-inspection-20261116/`.

## Nomenclatura tecnica riconoscibile nel report

Uniformata la tipografia di testo, tabelle, didascalie e sei diagrammi: ruoli e
termini ontologici in grassetto petrolio; identificatori, stati e capacità con
fondo tenue; alias come a, c e r in grassetto corsivo. PT Sans conservato in
tutte le varianti. Le lettere comuni del testo non sono trattate come simboli.

Rigenerati PDF, Word, Markdown e anteprime. PDF sempre di 29 pagine entro il
limite di 30. Controllati gli stili effettivi PDF/Word su dieci esempi, font
incorporati, impaginazione e integrità delle fonti. Testo della narrativa,
testo Word e contenuto testuale delle 29 pagine PDF identici alla revisione
precedente; verifiche delle metriche e del caso C1 superate. Nessuna modifica
ai dati scientifici o ai backend. Copia precedente e confronto conservati in
`output/report-tipografia-r1/`.
[Report aggiornato](docs/materiali/report-finale/README.md).

## Dettaglio semantico del report: caso C1 completo

Integrato il report con un capitolo di cinque pagine, basato esclusivamente
sulla stessa run C1 completata negli otto nodi del DAG. Mostrati dati iniziali,
regola di versione, arricchimento SBOM/OSV, alias degli individui effettivi,
tre asserzioni ABox, estratti ALN e conseguenze della TBox. Esplicito il limite:
il collegamento al pacchetto non trasferisce automaticamente all'asset il
contesto del rimedio. Il grafo effettivo ha due nodi e un arco, con score singolo
convenzionale distinto dall'affinità Tiny-ME 62/100 e dalla penalità 38.

C1 conserva entrambe le capacità operative, ma un vincolo testuale non mappato
richiede revisione; lo stato semantico condizionato prevale. Inclusi esempi PROV-O,
otto digest, commit e rilettura. Estratti verificati contro 15 sorgenti immutate,
senza nuove inferenze, esperimenti, assiomi o modifiche ai backend.

PDF corrente: 29 pagine entro il nuovo massimo di 30, sei figure e 26 tabelle
numerate. Aggiornati DOCX, Markdown, indice e segnalibri. Font PT Sans e metadati
accademici conservati; i due DOCX manuali intatti. Versione di 24 pagine salvata
separatamente; la sezione seguente ne conserva il resoconto storico.
[Report e verifiche](docs/materiali/report-finale/README.md).

## Nuovo report accademico completo

Realizzato un documento autonomo in italiano formale, con PT Sans, frontespizio
per il prof. Saverio Ieva e il corso Information Systems Design and Big Data.
PDF verificato di 24 pagine complessive, quattro figure e venti tabelle numerate;
DOCX modificabile con font incorporati e testo Markdown disponibili nella stessa
cartella. Struttura: introduzione, problema/soluzione, mockup, architettura
completa, risultati/metriche, conclusioni con limiti e sviluppi futuri.

[Report e note editoriali](docs/materiali/report-finale/README.md).
Le tabelle numeriche sono confrontate con le misure congelate; nessun nuovo
esperimento o modifica ai backend. I due DOCX manuali rimangono invariati.
Conteggio e resa PDF verificati; il riscontro nativo Word non e disponibile per
timeout dell'applicazione. Nel testo del report sono esclusi cronologia operativa,
nomi di file e nomi interni dei repository/branch; le basi software sono descritte
per funzione. I limiti scientifici rimangono espliciti.

## Valutazione finale consolidata — 13 novembre 2026

Conclusa la raccolta nel perimetro concordato: sensibilita degli archi (15 prove),
stesso contratto nativo in memoria contro MCP (30 confronti), costo del percorso
REST invoke/evaluate (15 coppie), Bonus/contrazione reali e controlli semantici
baseline. Completati due replay con/senza runtime a inventario/CTI fissati,
confronto inventario osservato/dichiarato e tre step TelemetryAgent reali.
Grafo, OWL e ALN identici nei due replay: limite del contributo contestuale attuale.
Nessuna estensione architetturale, modifica al core o nuova accettazione artificiale.

[Report finale](docs/tecnica/valutazione-finale.md),
[conformita e contributi](docs/tecnica/conformita-proposta.md),
[riproduzione](docs/tecnica/riproduzione-finale.md).
Catalogo v2: 32 criteri; sintesi con 227 timer, 45 confronti appaiati e inventario
3293 file. Dati essenziali e ingressi compatti in evaluation/final-results-v1,
ricalcolabili offline; vecchie raccolte e fallimenti conservati. Cinque nuove
riletture ledger identiche e sei metadati SaaS autentici salvati.

La raccolta e conclusa; la proposta resta parziale per revisione umana del
campione, pesi dei nodi, accepted/fallback applicativi, ThreatAgent separato
e nodi runtime espliciti. Pesi/overhead/Bonus prima indicati come non misurati
sono ora documentati entro i rispettivi confini. Restano stesura manuale della
relazione e registrazione delle modifiche locali in commit; nessun commit/push
eseguito. Le sezioni seguenti conservano gli stati storici.

## Associazione delle spiegazioni corretta e collaudata: 13 novembre 2026

Su autorizzazione dell'utente, implementato l'adattamento circoscritto nel
chaincode Go esistente, esclusivamente sul repository ledger costa-thesis.
Nuovo native_explanation.go applicato nel punto RankGraph: controlla topologia,
nodi/label/candidate, archi orientati, prodotti (tolleranza assoluta 1e-5) e
concordanza di tutti i cammini su una destinazione univoca. Nessun cambio a
libgraph.so, algoritmo, score, ordine delle candidate, pesi, cammini o categorie.
Le spiegazioni ambigue/invalide sono escluse dal ranking esposto e segnalate
come unvalidated con motivo; restano integre nell'output originale.

Per ogni nuovo ranking nativo, nella stessa transazione si conservano
<graphKey>_native_output (JSON esatto) e <graphKey>_explanation_audit (metodo
native-explanation-destination-v1 e digest), oltre a ranking e annotato.
Lettura con il tool get_graph gia esistente, usando la chiave completa.
Nessun nuovo endpoint, agente o servizio. Convenzione a candidata singola
separata e invariata; elimina eventuali vecchie evidenze native su chiavi riusate.

Nuova campagna congelata prima della raccolta: 30/30 prove reali e riletture,
cinque originali/riordinati con tre repliche. Score e pesi identici nei 45
confronti e identici a quelli del 12 novembre. Tutti i 60 cammini ora associati
alla candidata raggiunta (prima 30/60): 15 spiegazioni riordinate riassociate,
15 originali conservate. Verificati 30 digest originali e 60 commit VALID nei
blocchi 89–148 con tutti i write set. Controllo live singola candidata separato
confermato; nessuna nuova esecuzione completa CAMEL.

Limiti distinti conservati: 12 against con prodotto positivo; 156/186
occorrenze di candidate senza cammini. Solo 6/15 coppie hanno explanation
identiche anche per label: nei casi 3–5 puo variare la scelta dei cammini o
della candidata spiegata, pur rimanendo l'associazione verificata. Non si
certifica invarianza dell'intero output o equivalenza al paper. Sensibilita
ai pesi, overhead equivalente e ablation runtime non misurati.

Diciassette test Go principali con sottocasi passati, inclusi i dieci output
reali archiviati e i casi ambigui/malformati. Build offline dal repository
montato in sola lettura. Immagine attiva argumentation-chaincode:explanation-20261113-r1;
binario SHA 272f2780a2b83b019bd24e39680805355232244989e65f49b516597f8311ff92.
Container precedente conservato per rollback, rete/ledger esistenti mantenuti.
A fine benchmark nuovo binario attivo con ontologia Logback invariata; nessuna
suite SaaS nello store live. Assurance SaaS ancora distinta dall'impronta reale.

1.662 file precedenti protetti invariati, incluse evidenze del benchmark
originale, Word e metadati; C1/C4-r2/C4-r3 riletti con record, provenance e
ricevute identici. Framework full e due esterni costa-thesis, head invariati.
Prossimo passo: sintesi finale delle metriche, confronti sostenibili, limiti e
procedura dimostrativa. Non ampliare il lavoro per rendere identici tutti i cammini.

[Sintesi versionata](docs/tecnica/correzione-spiegazioni-native.md),
[implementazione e deployment](output/native-explanation-fix-20261113-r1/report.md),
[nuovo benchmark](output/native-explanation-benchmark-20261113-r1/report.md),
[verifica completa](output/native-explanation-benchmark-20261113-r1/verification.json).
Le sezioni successive conservano i precedenti esiti, incluso il difetto ora
corretto nell'output adattato; nessun dato storico e stato riscritto.

## Benchmark nativo completato: 12 novembre 2026

Eseguite 30/30 prove tecniche tramite MCP stdio/SaaS/Fabric: cinque coppie di
grafi esistenti, tre repliche per originale e riordinato, 6–40 nodi. Protocollo,
input e hash fissati prima della raccolta, nessun retry di scrittura o warm-up
escluso. Raccoglitore di misura riusato dallo smoke e dalla sequenza del client;
nessuna modifica del ranking o dei repository esterni, entrambi costa-thesis.

Punteggi e pesi esattamente identici nei 45 confronti (30 fra repliche, 15 fra
permutazioni); massimi stabili, con pareggi/tolleranza dichiarati. Verificati
60 commit VALID nei blocchi 29–88 e relativi write set, 30/30 riletture da una
nuova sessione dopo ripristino del container Logback originale. Ontologia del
benchmark: client_final_ontology.owl originale, distinta dalla generata C1/C4;
stesso binario e immagine immutabile, selezione temporanea senza reset Fabric.

Nuovo limite osservato: gli score sono stabili, ma le spiegazioni non sono
invarianti. I 30 cammini degli originali hanno destinazione coerente; i 30 dei
riordinati sono associati a una candidata diversa da quella raggiunta. Archi e
prodotti numerici validi 60/60; nessuna rimappatura per far passare il controllo.
Dodici cammini against hanno prodotto positivo, limite gia noto. Solo 30/186
occorrenze di candidate hanno explanation. Controllo completo: 15/15 originali
passati, 0/15 riordinati. Nessuna patch al core, Graph.cpp non disponibile.

Mediane RankGraph originali/riordinati: circa 122/121, 152/156, 135/135,
181/190 e 266/294 ms; i valori precisi sono nella tabella del report. Tempi MCP
comprendono OWL/core, REST e consenso: C++ puro e overhead off-chain/on-chain
non isolati. Sensibilita ai pesi non valutata, API priva di pesi impostabili.
Non sono run CAMEL, né una prova di accettazione semantica delle strategie.

1.336 file protetti invariati, incluso codice, Word e metadati live; riletture
C1/C4-r2/C4-r3 identiche per record, provenance e ricevute. Dodici test numerici
del raccoglitore e Ruff passati. Nessuna suite SaaS nello store live. Risultati
assistiti e inventario storico restano immutati. Prossimo lavoro: sintesi finale
delle misure e dei confronti sostenibili, limiti e procedura dimostrativa;
l'eventuale correzione del core resta distinta da questa campagna conclusa.

[Report completo](output/native-ranking-benchmark-20261112-r1/report.md),
[sintesi versionata](docs/tecnica/risultati-benchmark-ranking.md),
[metriche e latenze](output/native-ranking-benchmark-20261112-r1/metrics.json),
[verifiche](output/native-ranking-benchmark-20261112-r1/verification.json).
Le sezioni successive conservano la cronologia precedente.

## C4-r3 completato in un unico launcher: 12 novembre 2026

L'ultimo tentativo integrale real/camel/pipeline e terminato con exit code 0,
`dry_run_completed` e `shared_finalization=completed`. Tutti gli otto nodi
del DAG originale C4-r3 sono `completed` nella stessa invocazione, senza
riprese da checkpoint esterni. Durata osservata: 1224,254 s (20 min 24 s).
I normali recuperi automatici CAMEL su qualita CTI e binding restano nel log.

Usato il runner esistente in una nuova directory con timeout LLM 600 s,
modello/context/output/temperatura invariati, fonti SDK originali e backend reali.
Nessuna modifica dei componenti, della semantica o dei risultati per ottenere
il successo. Framework full e repository esterni costa-thesis, head invariati.

Nuovo commit nel blocco 28, validation_code=0, transaction ID
`220b4df9cc71cbd8b85fd005a06b42443650016073f200a892342196c80c725c`.
Riletture indipendenti MCP di record/provenance/ricevuta e grafi verificate;
anche il rinnovo dopo rifiuto controllato 403 restituisce lo stesso record.
Backup byte per byte dei tre metadati SaaS, 789 file precedenti e metadati
live C1/C4-r2 invariati. Nessuna suite SaaS nello store live o reset Fabric.

Esito di dominio `requires_prerequisites`, `selected_strategy_id=null`,
nessuna remediation. Manca `maintenance_window`; il testo del prerequisito
`package_upgrade capability` e inoltre trattato letteralmente come distinto
dalla capacita `package_upgrade` disponibile. Questo limite lessicale resta
visibile nei risultati. Tiny-ME: abduzione 38, contrazione 0, score 62.
Ranking singola candidata con convenzione Bottalico, senza pesi BWAF calcolati.

C1 e C4 hanno ora un launcher completo con finalizzazione/rilettura; C2/C3
conservano gli assessment conclusi, con fasi native non applicabili.
Il collaudo non sostituisce benchmark nativi, repliche o i restanti criteri
scientifici della proposta. I tentativi falliti e la ripresa restano conservati.
[Report C4-r3](output/c4-collaudo-20261112-r2/report.md) e
[verifica completa](output/c4-collaudo-20261112-r2/verification.json).
Le sezioni sotto descrivono la cronologia precedente, ora superata da C4-r3.

## Ripresa C4 verificata: 12 novembre 2026

Completata la finalizzazione C4-r2 tramite ripresa CAMEL dell'ultimo nodo:
exit code 0, `dry_run_completed`, finalizzazione condivisa `completed`.
Il launcher originale resta `failed` per APITimeoutError di Ollama, con sette
nodi del DAG completati e finalizzazione gia registrata; il suo DAG non e stato
riscritto. La ripresa riusa checkpoint, NativeFinalizationSession e agente esistenti,
con timeout LLM 600 s invece di 180 s. Non e un nuovo launcher integrale riuscito.

Commit originale conservato: blocco 25, validation_code=0, transaction ID
`b5db2d62657d1c3d4931b51ef7efa254c12da1a8e594ff213ffaec782ef42639`.
Record, provenance e ricevuta identici nella rilettura MCP indipendente; grafo
originale coerente con il canonico, grafo annotato verificato. Anche il rinnovo
client dopo rifiuto controllato 403 e la rilettura con nuova identita sono passati.

Esito: `requires_prerequisites`, `selected_strategy_id=null`; manca la capacita
operativa `maintenance_window`. Tiny-ME: abduzione 38, contrazione 0, score 62.
Ranking della sola candidata con convenzione Bottalico, senza pesi BWAF calcolati.
Nessuna remediation o estensione semantica. Durate separate: launcher fallito
3385,390 s; ripresa 256,003 s. Condizioni locali e timeout conservati nei log.

Salvati i tre metadati SaaS realmente scritti; verificati invariati 550 file
precedenti, 164 file C4-r2 e i metadati live C1. Nessuna suite SaaS nello store
live, reset Fabric, modifica dei componenti o cambio branch. Framework full;
entrambi i repository esterni costa-thesis. Le misure del campione restano separate.

[Report e limiti](output/c4-collaudo-20261112-r1/report.md),
[verifica](output/c4-collaudo-20261112-r1/verification.json) e
[copertura dei nodi tra launcher e ripresa](output/c4-collaudo-20261112-r1/case-stage-verification.json).
Le sezioni successive conservano gli stati precedenti; una riuscita C4 in un
unico launcher resta non dimostrata.

## Metriche dei componenti: 12 novembre 2026

Aggiornato al 12 novembre 2026. **Prima raccolta delle metriche dei componenti completata.**

Eseguito il calcolo sul campione assistito v2 congelato, con ingressi separati
dalle etichette. L'estrazione usa la funzione di produzione del gateway OTel
identify(resource,record), non CAMEL/LangExtract. CTI: sedici nuove query via MCP
al servizio reale 127.0.0.1:18043, pin del dataset e hash del motore verificati.
Protocollo e hash del codice fissati prima delle predizioni; scoring successivo.

Risultati: 7 TP, 1 FP, 3 FN; precisione 87,50%, recall 70%, F1 77,78%; documenti
esatti 9/12. Quattro SDK originali: 4/4; otto derivati controllati: 5/8 documenti
esatti, precisione 75%, recall 50%, F1 60%. Matching 13/16 (81,25%); versioni
a tre classi 10/13 (76,92%), binarie 7/8 (87,50%). Zero errori tecnici in raccolta.
Sei test delle formule e dei casi limite passati; frazioni e conteggi verificati
indipendentemente. Nessun test SaaS o intervento sulla directory del servizio.

Errori/disaccordi conservati: vendor E05 omesso; identita parziali E06/E12
omesse; C04/C05 diventano not_vulnerable nel backend nonostante default unknown
del riferimento; C11 alias non risolto; C15/C16 restano ambiguous invece di
not_found. Queste ultime sono astensioni prudenti, non finding inventati.
Matching diretto 12/13, casi di policy 1/3. Nessun caso eliminato a posteriori.

Artefatti in output/component-metrics-20261112-r1/: risposte e audit per query,
predizioni, protocollo, metriche JSON, CSV, report e manifest. Raccoglitore/scorer
evaluation/run_metrics.py; test tests/test_evaluation_metrics.py. Nessuna etichetta,
input gold, backend esterno, Word o archivio precedente modificato. Nessuna inferenza
LLM, Tiny-ME, ranking o chiamata Fabric; C1/C4 restano nello stato precedente.
Riferimento assistito e campione piccolo: corpus manuale umano, holdout cieco e
generalizzazione statistica non dimostrati. Restano le altre misure della sezione 15.

[Risultati e limiti](docs/tecnica/risultati-metriche-componenti.md),
[report completo](output/component-metrics-20261112-r1/report.md),
[metriche JSON](output/component-metrics-20261112-r1/metrics.json),
[CSV sintetico](output/component-metrics-20261112-r1/metrics-summary.csv).

## Revisione tecnica del campione: 12 novembre 2026

L'utente ha chiesto di svolgere direttamente i controlli sulle annotazioni.
Riesaminati i 28 casi: quattro sorgenti SDK originali, dodici ingressi di
estrazione, righe e regole grezze delle tre CVE; hash completi dell'OWL da 5 GB
e dell'indice SQLite nuovamente verificati. I 33 literal OWL/SQLite concordano.
Verificati alias Maven, due identita letterali logback e vendor sintetico assente.

Congelata `evaluation/annotated-sample-v2/`, con 33 file hashati, scheda compilata
dall'assistente, rapporto caso per caso e manifest collegato alla v1 immutata.
Nessuna etichetta o ingresso modificato. Chiariti C08/C11/C16: ambiguita sotto
policy, alias documentato e vendor come vincolo; nessuna pretesa di organizzazioni
realmente diverse. Le categorie descrivono la risoluzione, non matching.status
letterale. Errori tecnici/risposte assenti/identita sbagliate non valgono come
unknown corretto. Denominatori invariati: documenti 12, matching 16, versioni
a tre classi 13, binarie 8; riportare anche i tre casi matching di policy separati.

Campione pronto per uno studio controllato con riferimento assistito verificato
sulle fonti. Non e una revisione umana indipendente, un blind holdout o un accordo
tra annotatori; human_review_completed=false. Non dichiarare soddisfatto il requisito
di annotazione manuale umana della proposta. Non chiedere all'utente di rifare la
verifica tecnica gia delegata. Nessuna inferenza, misura o accesso ai servizi;
restano da raccogliere le predizioni e calcolare le metriche. Backend, semantica
C1, Word manuali e archivi precedenti invariati.

[Protocollo v2](evaluation/annotated-sample-v2/README.md),
[rapporto](evaluation/annotated-sample-v2/review-report.md),
[scheda compilata](evaluation/annotated-sample-v2/review.csv),
[manifest](evaluation/annotated-sample-v2/manifest.json).

## Preparazione della bozza: 12 novembre 2026

Preparata `evaluation/annotated-sample-v1/`: 12 documenti per l'estrazione
(4 raccolte SDK originali, 8 variazioni sintetiche dichiarate), 10 entita gold
proposte, 3 documenti negativi e 16 query CTI. Per la versione: 5 vulnerable,
3 not_vulnerable, 5 unknown, 3 not_evaluable. Denominatori prefissati: matching
16, accuracy versione a tre classi 13, binaria 8. Niente score o predizioni.

Le annotazioni sono una bozza assistita da fonti, **non una revisione umana gia
effettuata** e non un blind holdout: il disegno usa i casi diagnostici noti.
Nessuna risposta dei servizi e usata per generare il gold. Verificato SHA del KG
originale completo e del database; 33 campi grezzi OWL/SQLite concordano.
Ingressi separati, puntatori ai literal, sorgenti copiate, `review.csv` e manifest
con 31 file verificabili. I cinque log di una build non valgono come cinque
osservazioni indipendenti; le variazioni sintetiche non sono nuovi run reali.

Importante: per CVE-2026-1225 il default e unknown; versioni fuori dalle due
regole esplicite non sono automaticamente negative. Un nome ambiguo o assente
non produce una CVE negativa. Nessun matcher, evaluator, agente o servizio e
stato eseguito; backend esterni, originali, esportazioni dell'8 novembre e Word
manuali restano invariati. Prossimo passo: revisione umana e congelamento delle
etichette in una nuova revisione approvata, poi raccolta degli output.

[Protocollo e campione](evaluation/annotated-sample-v1/README.md),
[annotazioni](evaluation/annotated-sample-v1/annotations.json),
[scheda revisione](evaluation/annotated-sample-v1/review.csv),
[manifest](evaluation/annotated-sample-v1/manifest.json),
[preparazione/verifica offline](evaluation/prepare_annotated_sample.py).

## Inventario delle metriche: 8 novembre 2026

L'utente mantiene il limite semantico di C1 e passa alla valutazione finale della
proposta, sezioni 15.1–15.5. Raccolta offline completata: 698 file univoci con
SHA-256 in 14 gruppi, 32 voci di copertura, 30 durate esplicite, 9 eventi senza
timer isolato e 42 controlli di integrita coerenti. Cinque tentativi Logback
(tre launcher completati), due riprese della sola finalizzazione e cinque tentativi
Log4j precedenti sono separati; nessuna media fra revisioni/casi differenti.

La copertura contiene 8 voci disponibili entro limiti dichiarati, 14 parziali,
6 mancanti, 3 coperte solo da test/mock e 1 non eseguita. Precisione, recall, F1,
accuratezze e overhead blockchain restano non misurati; nessun valore inventato.
Servono corpus annotato indipendente, repliche omogenee e confronti controllati.
Nuovo raccoglitore offline standard library, nessun import degli agenti o contatto
con servizi; catalogo versionato e JSON/CSV conservati in output. Nessuna modifica
ai backend esterni, alle fonti dei run o ai Word manuali; nessun nuovo esperimento.

[Guida e copertura](docs/tecnica/valutazione-metriche.md),
[report corrente r2](output/metrics-inventory-20261108-r2/report.md),
[manifest](output/metrics-inventory-20261108-r2/manifest.json),
[catalogo](config/metrics-evidence.v1.json),
[raccoglitore](evaluation/collect_inventory.py).
La prima esportazione `output/metrics-inventory-20261108/` resta conservata;
r2 aggiunge le osservazioni di decisione e usa il raccoglitore consolidato.

## Stato C1 e collaudo precedente: 7 novembre 2026

C1-r2 ha completato il launcher reale CAMEL/Ollama e tutti gli otto nodi del DAG
con `dry_run_completed` e finalizzazione condivisa `completed`.
Esito decisionale: **requires_prerequisites**, con `selected_strategy_id=null`.
Tiny-ME restituisce abduzione 38 e score 62; il controllo operativo restituisce
`requires_review`. Il completamento tecnico non attesta una contromisura accettata.
C2/C3 restano completati; C4 e i suoi tentativi di ripresa restano non completati.
[Report C1](output/case-improvements-20261106/report-C1.md),
[verifica](output/case-improvements-20261106/verification-C1.json).

Corrette pubblicazioni degli agenti, cache Gateway su scadenza/cambio certificato,
rinnovo bridge sul rifiuto auth esplicito e viste compatte dei tool finali, con
archivi completi. Verifiche: 667 Python, 169 SaaS, 25 bridge e 13 Go.
Incidente dichiarato: test SaaS eseguiti nella directory live hanno pulito
metadati locali precedenti; ledger e archivi conservati, nuovi dati C1 protetti
con backup SHA. Ulteriori test SaaS richiedono una copia isolata. Restano i limiti
semantici e scientifici dichiarati; nessuna nuova estensione richiesta.

## Workspace e ultime decisioni

- Ultima richiesta del 7 novembre: concludere il task per C1 e verificarne
  l'esito effettivo. Completato il launcher C1-r2 e le riletture; nessun altro run C4
  da avviare durante questa chiusura. C4 originale resta failed, con commit
  conservato sul ledger e copie degli output. Run/diagnostiche in
  `output/case-improvements-20261106/`; non sovrascrivere i tentativi falliti.
- Ultima richiesta del 5–6 novembre: primo collaudo reale dei quattro casi, con
  avvio Fabric dalla root del repository costa-thesis seguendo i README. Autorizzato
  l'avvio della configurazione fablo-config.json esistente dopo aver verificato che
  Docker non contenesse una rete Fabric. Rete/SaaS lasciati attivi e gestibili con
  i tool applicativi MCP; start/stop container restano comandi Fablo. Il precedente
  rinvio dei servizi e stato superato da questa richiesta esplicita.
- Decisione dell'utente dopo il consolidamento scientifico del 5 novembre:
  **concludere quanto prima, senza ulteriori estensioni**. Nessun nuovo profilo
  semantico d'azione, topologia alternativa, nodo runtime o componente da introdurre
  come requisito aggiuntivo. I limiti ALN/anello e la copertura parziale della proposta
  restano documentati; non dichiarare risolta la discriminazione semantica fra azioni.
  Priorita a scenari controllati, collaudo esistente, misure e relazione; sole correzioni
  necessarie. Servizi reali sempre a fine progettazione. La proposta di arricchimento
  semantico descritta sotto e uno sviluppo futuro, non il prossimo task.
- Vincolo ribadito dall'utente il 1 novembre: **qualsiasi integrazione nei due
  repository esterni deve essere effettuata sul branch costa-thesis**.
  Altri branch/riferimenti possono essere letti come sorgenti. Verificare il
  branch prima di ogni scrittura; nessun checkout/commit/push implicito.
- Framework `/Users/reucalion/tesi`, branch `full`, ultimo HEAD verificato `32e6dbc`
  (avanti di un commit). Pulizia nel working tree; cancellazioni spesso dovute
  a spostamenti intenzionali. Solo rimozione dal versionamento del lock Word staged.
  Nessun commit/push dell'assistente; ricontrollare Git prima di modificare.
- Dopo l'ispezione in sola lettura di `principe-thesis`, l'utente ha richiesto il
  porting selettivo sui due `costa-thesis` in `/Users/reucalion/Desktop/`:
  `agent-based-cti-argumentation-pipeline` (MCP, sorgente `4410132`) e
  `semantic-cti-ledger-argumentation` (SaaS `fablo-rest`, sorgente `023b711`).
  Modifiche esterne locali; Identity/Ubuntu, credenziali e rete preservati.
- Porting verificato: build, discovery di 19 tool, 66 test/13 suite con Fabric simulato.
  Corretti build/dipendenze e collisioni ID mediante UUID; richiesto Node >=22.12.
  Il framework non e ancora collegato. [Dettagli](docs/porting-principe-costa.md).
- Concordata la roadmap e completata la pulizia: nove documenti consolidati,
  23 guide spostate, 12 riepiloghi chat rimossi; Markdown principali da 38 a otto.
  Liberati circa 820 MiB di temporanei. Verifica: 400 test Python, Ruff senza errori,
  459 link validi; hash invariati per 160 file applicativi e 63 materiali.
  Registro: `output/pulizia-20261030/`.

## Ripresa del 31 ottobre: agenti e contratti

- L'utente ha richiesto di iniziare da contratti/backend, verificando e
  consolidando prima gli agenti e collegandoli successivamente ai servizi.
- I quattro ruoli ora condividono `thesis_agents/agents/contracts.py`: task,
  input/output, moduli prompt/tool, produttori e DAG derivato. Handler CAMEL,
  policy e attribuzioni dei tre produttori usano le stesse definizioni.
- Corretta una lacuna riprodotta: un backend Python poteva restituire finding
  con evidenza estranea. La sessione ricontrolla modelli annidati, pacchetto,
  versione, evidence ID, asset e osservazione CTI prima di memorizzare il lookup.
  Un errore non inquina la cache e non pubblica un'astensione.
- `prepare_package_verification` esposto soltanto ai profili con lookup runtime;
  prompt Strategic allineato al rifiuto del ranking vuoto con candidate presenti.
- Aggiunti 12 test su tool/handler dei cloni CAMEL, finding incoerenti, mutazioni,
  timeout, retry e blocco dei discendenti. Nessuna nuova inferenza LLM.
- Verifica finale: 412 test passati (400 iniziali), Ruff senza errori e 122
  destinazioni di link locali valide nei documenti controllati. Due warning
  di deprecazione RDFLib gia presenti. I test HTTP/MCP richiedono porte loopback,
  bloccate dal sandbox: la suite completa e passata con tali porte abilitate.
  Evidenze: `output/consolidamento-agenti-20261031/verification.json`.
- Confrontati in sola lettura i contratti SaaS/MCP nei due repository esterni.
  Restano mapping per singola CVE, grafo canonico, IRI e condizioni operative,
  identificatori/snapshot e finalizzazione. Confermati nel SaaS parsing con
  ripiego su ranking vuoto/score zero, valori semantici favorevoli predefiniti
  e conversione degli errori tecnici in rifiuti: correggerli prima del collegamento.
  [Matrice dei contratti](docs/tecnica/architecture.md#consolidamento-degli-agenti-prima-del-collegamento-saas).
- Il framework non e ancora collegato ai servizi condivisi. Le modifiche della
  sessione sono locali al framework; nessun commit/push o modifica alla rete.

## Backend SaaS/MCP: modifiche applicate il 31 ottobre

- Applicati 23 file verificati nei due repository esterni `costa-thesis`, con
  backup e controllo degli hash. Nessun commit/push; 24 file protetti invariati,
  inclusi configurazione di rete, riferimenti Git, credenziali e sorgenti CTI.
- Binding configurabili: `ARGUMENTATION_CHAINCODE=argumentation`,
  `SEMANTIC_CHAINCODE=user-registry`; default coerenti con fablo-config.json,
  deployment effettivo ancora da verificare. ExplainAffinity riceve chiave
  ontologica esplicita/configurata e i due IRI; preservato l'ordine storico
  asset/resource e contromisura/request, da verificare sul caso ontologico reale.
- Risposta nativa Go verificata: score 0..100, penalita di abduzione/contrazione,
  topPenalty e spiegazioni. Affinita esposta score/100, penalita conservate native;
  condizioni mancanti distinte dall'accettazione. Nessun servizio Bonus implicito.
- Ranking con ID/nome esatti e score finiti; nessuna sottostringa, lista vuota
  o score zero di ripiego. Conferme StoreGraph/RankGraph controllate; niente
  record decisionale dopo risposte non valide. Score di ranking non normalizzati.
- Errori HTTP/MCP espliciti: 400 input non valido, 502 risposta backend incoerente,
  503 guasto tecnico; rifiuto semantico distinto. Snapshot sconosciuto/revocato
  rifiutato, riferimenti snapshot/ontologia propagati dal bridge, timeout HTTP
  configurabile e rotte legacy allineate al REST.
- Corretta l'assenza di dotenv nel package/lock del SaaS. Digest dell'input
  calcolato prima dell'arricchimento; assurance originale conservata nella
  decisione e riletta nella provenance. Nessun verified=true inventato per
  codice non verificato o vecchi record privi di assurance.
- Verifiche su Node 22.12.0: entrambe le build, 105 test Jest/14 suite e 12 test
  del bridge. Prova effettiva REST/MCP stdio: 19 tool, ranking, get_graph,
  rilettura decisione/provenance, tre esiti semantici e guasti 502/503. Fabric
  e autenticazione simulati; nessuna nuova prova LLM o commit reale sul ledger.
- Docker daemon non raggiungibile; porte localhost 8800, 7040 e 7041 rifiutano
  connessioni. Le configurazioni esistenti indicano servizi locali e TLS.
  Node di sistema e 20.12.2: usare >=22.12 per questi componenti. Non modificati
  rete o ambiente globale. Restano ontologia/IRI reali, TLS, adapter del grafo,
  client framework stdio e finalizzazione della raccomandazione.
- Evidenze: `output/backend-contracts-20261031/` contiene patch, backup,
  manifest, test e smoke test (incluso il primo avvio fallito per dotenv).
  Runner: `tests/support/saas_contract_smoke.py`; fixture Fabric esplicitamente
  simulata in `tests/support/saas_fixture.cjs`.
  Dipendenze npm, cache, runtime Node temporaneo e build isolati rimossi dopo
  la verifica; sorgenti della copia di collaudo e risultati conservati.

## Collegamento MCP stdio del framework: 31 ottobre

- L'utente ha rinviato la verifica dei servizi disponibili alla fine della
  progettazione, chiedendo prima stdio e poi generazione/grafo canonico.
- `MCPClient` supporta HTTP e stdio tramite SDK MCP e portal sincrono compatibile
  con CAMEL. Comando/argomenti configurati dall'operatore senza shell; `cwd`
  opzionale assoluto, credenziali tramite `env_from`, stderr separato per backend.
  Nessun retry automatico o fallback locale. Test verificano la rimozione dei
  processi dopo chiusura, discovery fallita, timeout e crash.
- Profilo MVP eseguibile `config/backends.mcp-stdio-mock.json`: quattro backend
  remoti collaudati con CAMEL programmato e backend locali del processo padre
  disabilitati. I profili HTTP esistenti restano compatibili.
- Client di dominio `SharedServicesClient` e profilo
  `config/mcp.shared-stdio.example.json`: un processo/sessione per
  `rank_remediations`, `validate_countermeasure`, `get_decision`, `get_provenance`.
  Probe senza LLM: `python -m thesis_agents.mcp.shared_probe`; handshake/discovery
  con `--check-config`, chiamata esplicita con `--tool`, `--request`, `--output-dir`.
- Discovery effettiva del bridge: 19 tool, schemi di input dei quattro tool
  congelati in `thesis_agents/data/shared-mcp-schemas-v1.json`; outputSchema
  assente, risposte validate con modelli Pydantic dedicati. Envelope/azione,
  ID/nome/CVE, digest REST equivalente, snapshot, IRI/ontologia e assurance delle
  riletture controllati. Score ranking nativi preservati anche oltre 1;
  `accepted`, `requires_prerequisites`, `rejected` distinti dagli errori tecnici.
- Collaudo effettivo framework -> bridge stdio -> SaaS REST: nove chiamate,
  parita ranking REST/MCP, decisione/provenance rilette, tre esiti semantici,
  errori 502/503 e ranking malformato rifiutato. Fabric e autenticazione simulati;
  nessuna prova di commit reale o disponibilita della rete. Node 22.12.0 isolato,
  nessun cambiamento all'ambiente globale o ai repository esterni in questa fase.
- Il collegamento dei contratti nativi e completo al livello di client/probe.
  La traduzione degli artefatti MAS richiede ancora perimetro per CVE, generatore,
  grafo canonico e vincoli operativi rappresentati nell'ontologia. Non convertire
  silenziosamente il grafo mock o usare `get_provenance` come finalizzazione MAS.
- Evidenze e log, inclusa la discovery iniziale fallita per configurazione REST
  assente: `output/mcp-stdio-20261031/`. Runner:
  `tests/support/saas_stdio_framework_smoke.py`. Guida:
  [MCP strategico](docs/integrazioni/mcp-strategic.md).
- Verifica finale: 454 test Python passati, di cui 42 nuovi, Ruff senza errori,
  66 link locali controllati. Rimangono soltanto i due warning RDFLib gia presenti.
  Build dei due componenti riuscite su Node 22.12.0; hash di 49 file sorgenti delle
  copie di collaudo corrispondenti ai repository esterni. Dettagli in
  `output/mcp-stdio-20261031/verification.json`. Rimossi circa 606 MiB di runtime,
  dipendenze npm, cache e build temporanei; sorgenti, risultati e fallimenti conservati.

## Individuazione del generatore e ispezione dei grafi: 31 ottobre

- Su richiesta dell'utente esaminati approfonditamente entrambi i repository
  locali: working tree, file applicativi aggiunti/ignorati, tutti i branch locali
  e riferimenti remoti disponibili, 70 commit raggiungibili (28 pipeline, 42 ledger)
  e 236 versioni di sorgenti applicativi storici. Esaminati anche prompt, import
  AST, documenti ODT/PDF, archivio RAR e quattro pacchetti Fabric storici.
  Nessun fetch, checkout, modifica esterna o avvio dei servizi.
- Pipeline individuata in `agent-based-cti-argumentation-pipeline/app/`:
  `ProductionExtractor.extract_chunk` in `app/src/extractor/engine.py` invoca
  LangExtract per vendor/product/version e relativi attributi. Nella versione
  recente supporta Ollama/Gemini e grounding delle estrazioni nel testo.
- Le versioni piu recenti non sono nel working tree costa-thesis: main locale
  `9b68780`, origin/principe-thesis `4410132` e origin/main `090b684` contengono
  grafi per CVE e `app/tools/build_aln_projection.py`. Origin/main aggiunge
  estrattore aggiornato, metriche/e2e e anello diretto tra strategie. Riferimenti
  gia presenti sul disco, nessuna verifica dello stato remoto attuale.
- I costruttori identificati sono `build_observed_asset_axioms` (OWL),
  `build_argumentation_graphs_from_assessment_data` (grafo), `build_projection`
  (profili ALN VulnerabilityArgument/Solutions/Workarounds). Questi moduli sono
  deterministici: non trovato un generatore LLM separato di argomenti BWAF,
  supporto/attacco o pesi. La pipeline riutilizzabile e dunque ibrida.
- Trovato anche un vecchio agente Agno/Gemini in ledger.py (introdotto da
  `314bf60`, rimosso da `62c04ab`): riceveva grafi gia costruiti e orchestrava
  store/rank/get. Non generava le annotazioni o gli argomenti. Nel repository
  ledger origin/bottalico-thesis coincide con la baseline `a3dab4a`; non contiene
  un generatore LLM ulteriore.
- Prova offline sui moduli originali copiati da `090b684`: fixture sintetica,
  una CVE/tre strategie, 4 nodi, 6 archi, 11 asserzioni OWL e proiezione ALN
  ripetibile; CVE assente rifiutata e versione non valutata esclusa dall'append.
  Nessuna nuova chiamata LLM/rete/Fabric o verifica del ranking. Esempi e2e gia
  versionati esaminati separatamente come evidenza storica, incluso un ranking
  locale convenzionale per una sola strategia, da non importare nel nostro MAS.
- Ispezione preliminare dei dieci grafi baseline: la coppia 4 original/reordered
  differisce di due archi (43/41). Non usarla come prova dell'indipendenza
  dall'ordine prima di correggere una copia controllata. Topologia della pipeline
  CVE -> strategie, mentre il costruttore SaaS usa strategie -> CVE: il mapping
  canonico richiede una scelta esplicita. L'anello lessicografico e una convenzione
  tecnica del generatore recente, non una relazione di dominio dimostrata.
- Rapporto, sorgenti/versioni/hash, ricerca storica e risultati:
  [ispezione del generatore](output/generator-inspection-20261031/report.md).
  Conservati anche i tentativi falliti: fixture iniziale senza evaluated=true e
  lettura PDF Swift fallita; corretti rispettivamente la fixture e il metodo
  locale di lettura PDF, senza modificare sorgenti o toolchain di sistema.
- Prossimo lavoro: progettare il ruolo/contratto della pipeline ibrida e il
  mapping canonico, riusando moduli selezionati senza duplicare telemetria/CTI o
  il percorso SaaS condiviso. L'eventuale intenzione di richiedere un generatore
  LLM diretto di argomenti distinto dalla pipeline resta da confermare con un
  riferimento preciso; non corrisponde a un altro modulo trovato qui.

## Checkpoint canonico e porting selettivo: 1 novembre

- Implementati `thesis_agents/canonical/` e SemanticPreparationAgent. Il checkpoint
  autonomo riprende i tre artefatti MAS, verifica hash/schemi/evidenze e richiede
  binding espliciti candidata/CVE -> individuo KG. L'agente CAMEL e i cloni hanno
  soltanto get_context e prepare_argumentation, senza argomenti scelti dal modello.
  La Workforce principale conserva quattro ruoli; il raccordo e il prossimo task.
- Applicati 12 file con controllo di branch/hash e backup: 10 nuovi sotto
  `pipeline/app/semantic_preparation/` e due nel ledger (grafo 4 riordinato e README).
  Entrambi i repository su costa-thesis prima/durante/dopo l'applicazione. Nessun
  commit/push o avvio servizi. Preservati app/src, Identity/Ubuntu, MCP/SaaS,
  credenziali e rete. Cinque file originali riusati da `090b684`, con hash/manifest.
- Profilo topologico bottalico-directed-ring-v1: archi CVE -> strategia dal KG,
  anello di confronto fra strategie dalla policy del generatore, ordine canonico
  di serializzazione. Origine degli archi esplicita; polarita rinviata al reasoner,
  nessun peso BWAF inventato/importato dalle stime LLM. ID nativi KG distinti da
  quelli MAS, con tabella di corrispondenza. Il profilo non prova ancora la
  correttezza scientifica della topologia o del ranking reale.
- Copertura esatta di CVE, coppie candidata/CVE e remediation KG; verificati asset,
  software/versione/evidenza, ownership degli affected e link alle versioni.
  I verdetti CTI sono riusati; i binding rimangono configurazioni dell'operatore.
  Nessun fuzzy matching, scarto implicito, ranking locale o fallback tecnico.
- CLI `python -m thesis_agents.canonical`, modalita tool/camel. Output:
  canonical_preparation.json, frammento observed_assets.owl, ALN completo,
  ranking-requests/<CVE>.json, ingressi/richiesta/profilo e audit. KG e ALN hanno
  digest distinti; deployment_verified=false e pesi non calcolati. Restano
  vincoli operativi/IRI della validazione e corrispondenza col backend distribuito.
- Corretta la coppia 4 original/reordered (43 archi in entrambi) e il README per
  gli 11 archi del grafo 1; backup degli originali conservati.
- Verifica: 482 test Python passati, 28 nuovi, Ruff senza errori; due warning
  RDFLib gia presenti. Demo CLI contro il generatore davvero installato su
  costa-thesis: fixture sintetica, una CVE/quattro strategie, cinque nodi/otto
  archi e richieste native rilette. Test CAMEL programmato; nessuna nuova
  inferenza LLM, rete/Fabric o valutazione dei pesi.
- Evidenze: `output/canonical-preparation-20261101/`, con piano/applicazione,
  backup, manifest, demo e log anche dei test inizialmente falliti e poi corretti.
  [Guida del checkpoint](docs/integrazioni/canonical-preparation.md).

### Raccordo del checkpoint con lo Strategic nativo (1 novembre 2026)

- Aggiunto il profilo Strategic nativo in `thesis_agents/strategic/`: sessione,
  contratti, ruolo CAMEL con policy e CLI. Consuma realmente il checkpoint
  SemanticPreparationAgent; prompt e tool del ruolo in `agents/strategic_native.py`.
  Non usa lo schema MVP con score limitati a [0,1]. Il DAG principale conserva
  il percorso precedente; integrazione automatica dopo il contratto semantico.
- Sequenza per CVE: rank_remediations -> get_decision -> get_provenance, poi
  publish_native_ranking dopo copertura completa. Un processo MCP condiviso,
  grafo/richiesta immutabili risolti dal tool; il modello passa soltanto la CVE.
  Cloni e risposte testuali premature non aggirano la policy di pubblicazione.
- Preservati run/asset, CVE, associazioni ID MAS/KG, score nativi e pareggi per
  ID KG. Il SaaS non riceve un run ID MAS nel contratto attuale: la correlazione
  e nel checkpoint locale. Anche una sola candidata passa dal servizio, senza
  score convenzionale; nessuna aggregazione di punteggi tra CVE diverse.
- Verifica di richiesta/profilo/digest e tre ingressi MAS, OWL/ALN ed esportazioni;
  copie conservate e ricontrollate a ogni fase. Tenant, snapshot ID/digest e digest
  ontologico del backend sono pin espliciti dell'operatore. Non attestano da soli
  deployment del KG/ALN. Duplicati ID SaaS, rilettura STALE o dati alterati falliscono.
- Risposte native, audit e diagnostica rimangono anche in caso di errore. Nessun
  retry/fallback automatico dopo errore remoto, nessuna astensione tecnica.
  Chiamate concorrenti duplicate non possono inviare due ranking della stessa fase.
- Output `native_strategic_ranking.json`: deployment_verified=false,
  semantic_validation/recommendation=pending, provenance_scope=saas_ranking_record,
  action_execution=not_performed. La provenance del ranking non certifica la
  raccomandazione finale o il commit on-chain. Vincoli operativi e IRI rimangono
  necessari prima di collegare validate_countermeasure e selezione.
- Demo CLI sul checkpoint prodotto dal generatore esterno installato su
  costa-thesis: una CVE/quattro strategie, tre chiamate MCP native e score originali;
  server stdio effettivo, SaaS simulato. Nessuna inferenza o rete Fabric reale.
- Nessuna scrittura nei due repository esterni; entrambi verificati su costa-thesis.
  Nessun commit/push e nessuna modifica ai Word manuali.
- Verifica: 522 test Python passati (40 nuovi), due warning RDFLib preesistenti,
  Ruff e git diff --check senza errori; 185 link locali verificati. I 40 test
  nativi sono stati rieseguiti dopo il riordino finale del modulo prompt/tool.
  La suite completa usa `.venv/bin/python -m pytest -q`: il primo lancio tramite
  entrypoint pytest non risolveva services; quello in sandbox non poteva aprire
  porte loopback. Riesecuzione con permesso locale passata, log precedenti conservati.
- Evidenze, inclusi tentativi iniziali falliti, in `output/strategic-native-20261101/`.
  [Guida del profilo nativo](docs/integrazioni/strategic-native.md).

### Vincoli operativi e IRI nella validazione (2 novembre 2026)

- Esteso validate_countermeasure con operational_context opzionale nel bridge,
  inoltrato integralmente come operationalContext al SaaS. Le chiamate precedenti
  senza contesto mantengono il contratto originario. Discovery aggiornata dal
  bridge effettivo compilato: 19 tool, quattro autorizzati. Nessun tool duplicato.
- Nuovo profilo Strategic di validazione: legge ranking/preparazione e i tre input
  MAS, controlla digest/copertura, associa run/asset/CVE/ID MAS/KG e IRI assoluti.
  CLI `python -m thesis_agents.strategic.validation`, modalita tool/camel.
  Profilo operatore in `config/strategic-native-validation.example.json`, da
  compilare sul ranking gia pubblicato. Nessuna invenzione/espansione fuzzy di IRI.
- Capacita e divieti sono configurazioni esplicite dell'operatore (policy_source),
  non campi osservati di RuntimeEvidence. Il contesto conserva prerequisiti e caveat
  originali delle candidate, digest delle fonti/policy e decision ID SaaS del ranking.
  Il backend controlla tenant, stato CURRENT, CVE e presenza della candidata nel
  ranking applicativo prima di interrogare ExplainAffinity.
- Policy SaaS operational-action-policy-v1: requisiti fissi per upgrade/isolate/
  block_deployment/monitor, uniti a prerequisiti e mapping espliciti dei caveat.
  Requisiti versionati del caso di tesi, non leggi universali. I vincoli testuali
  senza mapping restano unassessed_constraints e richiedono revisione. Nessuna
  interpretazione automatica del linguaggio naturale o asserzione OWL inventata.
- Risposta: valid/status/reasoning.native restano Tiny-ME; operational descrive i
  controlli del SaaS; effectiveStatus combina rejected, requires_prerequisites,
  requires_review, accepted in quest'ordine. Un valid=true semantico non supera
  un blocco operativo. Il framework verifica il contratto senza usare un fallback.
  Tiny-ME continua a ricevere i due IRI: le liste JSON sono valutate dal SaaS,
  non presentate come vincoli inferiti dall'ontologia.
- Individuato/corretto nel chaincode il lookup che confrontava solo il frammento
  dopo #. Ora gli IRI completi (anche URN e con rendering tra <>) sono confrontati
  esattamente, senza fallback per namespace diversi. API legacy per frammenti
  univoci mantenuta; nomi locali ambigui rifiutati. Helper Go verificato su 12 casi;
  compilazione CGO/Tiny-ME e deployment reali ancora nel collaudo finale.
- Il checkpoint valida tutte le candidate in ordine nativo per CVE e conserva
  richieste, esiti, ingressi copiati, profili e audit. Modifiche degli input,
  omissioni/incoerenze del backend e guasti bloccano la pubblicazione; nessun
  retry o astensione tecnica. Cloni CAMEL e chiamate concorrenti non aggirano le fasi.
  native_strategic_validation.json lascia recommendation/shared_finalization
  pending, deployment_verified=false e action_execution=not_performed.
- Applicati 10 file sorgente/test nei due repository esterni solo su costa-thesis:
  7 ledger (4 SaaS, 3 chaincode) e 3 pipeline (bridge/schema/test). Backup/hash e
  refs verificati, nessun commit/push. Nessuna modifica ai Word manuali.
- Verifica: 562 test Python passati (40 nuovi; due warning RDFLib preesistenti),
  Ruff e diff workspace senza errori. Build Node 22 passate; 131 test SaaS e 13
  bridge passati. Le nuove righe della patch esterna non introducono whitespace;
  il diff globale pipeline conserva whitespace preesistente del porting.
- Smoke framework -> bridge stdio -> SaaS HTTP effettivi: 24 chiamate, quattro
  casi operativi da quattro candidate, condizioni/conflitti semantici, parita
  REST/MCP, IRI relativo e contesto estraneo respinti. Smoke legacy di nove chiamate
  passato. Fabric, Tiny-ME e autenticazione simulati; snapshot sintetico registrato
  esplicitamente nella fixture. Non e prova del deployment del KG/ALN o del commit.
- Evidenze in `output/operational-validation-20261102/`: manifest, stage, piano,
  applicazione, backup, patch incrementale, discovery, test e fallimenti conservati.
  [Guida della validazione](docs/integrazioni/strategic-validation.md).

## 3 novembre: selezione, DAG e switch applicativo

- Chiarimento dell'utente: il professore richiede un comando che cambi i backend
  della stessa architettura tra solo mock e servizi reali, non uno switch di branch.
  Implementato `main.py --backend-mode mockup|real`; `--mode camel|fixtures`
  resta la scelta dell'inferenza. Il percorso reale richiede CAMEL e profilo/input
  espliciti; non costruisce mock e non fa fallback. I profili storici senza il nuovo
  switch mantengono il comportamento precedente.
- `execution_profiles.py` valida il profilo `real-execution-v1`: OTel HTTP, CTI
  MCP atteso reale, SBOM fornita/OSV atteso live, preparazione Bottalico,
  snapshot/digest, bridge condiviso stdio, binding MAS/KG/IRI e policy operatore.
  Controlli locali prima dei processi: coerenza delle policy input/profilo,
  ontologia/manifest e branch costa-thesis del generatore. Nessuna disponibilita
  remota verificata. Il profilo di esempio contiene placeholder da compilare.
- `execution_runtime.py` collega i tre produttori, preparazione, ranking/riletture,
  validazione e selezione. Run ID e digest dei profili di fase sono derivati dagli
  artefatti realmente pubblicati. Il CountermeasureAgent riceve i binding configurati
  e deve preservare gli ID, senza inventare candidate per colmare un perimetro errato.
- DAG eseguibile in `orchestration/native_dag.py`: sette contratti, cinque ruoli
  di dominio (Strategic in tre fasi). E un DAG composto: Workforce CAMEL dei tre
  produttori e successivi agenti CAMEL con tool/policy native. Non una singola
  Workforce a sette worker. Le dipendenze derivano dai produttori degli artefatti;
  input e pubblicazioni sono verificati prima/dopo ogni nodo, errori bloccano i
  discendenti. `dag.json` conserva ruoli, input/output, archi e stati.
- `NativeSelectionSession` verifica l'intero checkpoint archiviato: digest,
  ranking/preparazione, profilo, backend atteso, richieste esatte, IRI, risposte e
  ordine/copertura dei tentativi. Copia e protegge gli input, non contatta servizi.
  La stessa costruzione delle richieste e riusata dalla sessione di validazione.
- Policy `first-effective-accepted-per-cve-v1`: prima `effectiveStatus=accepted`
  nel ranking nativo di ciascuna CVE, senza modificare score, pari merito o binding.
  Si mantengono tutte le validazioni anche dopo la scelta. Esiti: recommended,
  requires_review, requires_prerequisites, no_valid_strategy. Nei casi misti senza
  accettazione la revisione prevale sui prerequisiti; tutti i dettagli restano
  disponibili. Non e una nuova precedenza interna alla singola validazione.
  Un guasto tecnico/checkpoint incompleto non produce astensione o raccomandazione.
- `native_strategic_recommendation.json` conserva ogni ranking e tentativo, scelta
  per CVE e lineage locale; `status=dry_run_completed`, shared_finalization=pending,
  provenance_scope=local_artifact_lineage, deployment_verified=false,
  action_execution=not_performed. Ranking e validazione storici non vengono
  riscritti: i loro precedenti campi pending restano corretti per quella fase.
  CLI offline: `python -m thesis_agents.strategic.selection --validation-run ...
  --output ...`; modalita CAMEL opzionale con tool, senza ID scelti dal modello.
- Candidate vuote: conserva evidenza/rapporto/candidate, salta i nodi nativi e
  conclude assessment_completed con no_findings o insufficient_evidence secondo
  la copertura. Il contratto lookup-v1 esprime solo matched/unsupported:
  unsupported non viene convertito in assenza di vulnerabilita.
- Verifica: **617 test Python passati, 55 nuovi rispetto ai 562 del 2 novembre**;
  due warning RDFLib preesistenti. Ruff, pip check e diff workspace passati.
  SDK CAMEL, tool, MCP stdio e HTTP loopback effettivi; inferenza e servizi
  CTI/OSV/Fabric/Tiny-ME sintetici. Il launcher attraversa i moduli Bottalico
  installati e copiati in repository temporanei costa-thesis. Provati prima
  accettata, alternativa operativa/semantica, CVE indipendenti, prerequisiti,
  revisione, tutte rigettate, score negativi/pari merito, alterazioni e fallimenti.
- Evidenze in `output/selection-dag-20261103/`: verification.json, log completi
  e intermedi, source-snapshot, nove esempi launcher con DAG/esiti/diagnostica,
  quattro selezioni offline dai checkpoint del precedente smoke SaaS.
  [Guida e comandi](docs/integrazioni/strategic-selection-dag.md).
  Nessuna modifica ai repository esterni in questo incremento: entrambi verificati
  ancora su costa-thesis. Nessun nuovo avvio di servizi reali, commit/push o modifica
  dei Word manuali. Restano i limiti scientifici/ontologici e la finalizzazione
  condivisa elencati sotto. La verifica dei servizi rimane a fine progettazione.

## 3 novembre: pipeline confermata e ispezione della finalizzazione

- L'utente conferma di usare la pipeline ibrida Bottalico disponibile: non resta
  da cercare o concordare un diverso generatore diretto LLM di argomenti.
- Autorizzata l'ispezione approfondita per finalizzazione/provenance, con richiesta
  esplicita di non creare funzionalita da zero prima di aver controllato entrambi
  i repository e di chiedere il permesso nel caso serva aggiungere quanto manca.
- Ispezione completata senza modifiche al codice applicativo: working tree e
  file non versionati pertinenti, 15 riferimenti locali complessivi, 28 commit
  pipeline e 42 ledger, 371 versioni uniche di sorgenti/documentazione, reflog e
  ricerca di oggetti Git non raggiungibili (nessun oggetto aggiuntivo trovato).
  Nessun accesso ai servizi reali o ai repository remoti. Entrambi i branch
  esterni restano costa-thesis, HEAD/working tree/riferimenti invariati.
- Da riusare SaaSServiceAdapter, ProvenanceService, store decisionale, NetworkPool,
  rotte/bridge MCP e ArgumentationContract. Trovato anche KVContract storico con
  Put/Get generici in 01c7cae; a3dab4a lo rimuove. Pattern di persistenza utile,
  non una finalizzazione gia implementata. FinalizeNegotiation/SelectService
  attivano accordi e servizi, PerformAndStoreDiscovery salva discovery: non sono
  la raccomandazione dry-run. StoreGraph elimina i metadati estranei al grafo.
- Mancano un'operazione di finalizzazione e la persistenza backend delle validazioni
  eseguite. NetworkPool attende gia il commit valido, ma restituisce solo il payload
  e perde la ricevuta. persistDecision nasconde gli errori di scrittura. La
  provenance usa la testa del ranking e un graphId costruito, non la scelta MAS
  e la chiave GRAPH effettiva. La nuova finalizzazione deve legare il tenant
  all'identita autenticata, preservando digest e riferimenti originali.
- Probe locale del ProvenanceService esistente: cinque attivita anche senza
  validationReport; con report l'entita e scollegata. L'export opzionale toJsonLd
  riletto da RDFLib produce 1 tripla, solo Bundle, 0 entita/attivita/agenti.
  Il GET attuale restituisce il record strutturato, non quell'export: gli array
  JSON del GET non sono vuoti. Usata la build gia collaudata il 2 novembre,
  con sorgente TypeScript identico a quello corrente; nessuna nuova build/installazione.
- Rapporto, proposta circoscritta, inventari/hash, scansioni storiche e probe in
  `output/finalization-inspection-20261103/`. Proposta: estendere i componenti
  condivisi esistenti, con scrittura/lettura finale nel contratto argumentation,
  ricevuta di commit, correlazione delle validazioni, provenance corretta e nodo
  Strategic di finalizzazione/rilettura. Nessun nuovo servizio/chaincode autonomo.
  **Al termine dell'ispezione l'estensione attendeva il permesso; successivamente
  autorizzata e implementata come descritto nella sezione seguente.**
  [Rapporto e proposta](output/finalization-inspection-20261103/report.md).
  Nessun commit/push, avvio di servizi reali o modifica ai Word manuali; i 617 test
  rimangono l'ultima regressione del codice, non sono stati rieseguiti per questa ispezione.

## 3-5 novembre: finalizzazione e provenance condivise completate

- L'utente ha autorizzato l'estensione proposta dopo l'ispezione approfondita dei
  due repository e ha richiesto di terminarla. Riutilizzati SaaSServiceAdapter,
  ProvenanceService, NetworkPool, bridge MCP e ArgumentationContract. Nessun nuovo
  servizio o chaincode autonomo; nessun riuso improprio delle negoziazioni che
  modificano lo stato dei servizi.
- Aggiunti finalize_recommendation(document_json) e get_finalization(decision_id,
  finalization_id). Discovery effettiva: 21 tool; client base ancora limitato ai
  quattro precedenti, opt-in finale a sei. Schemi aggiuntivi congelati. I vecchi
  get_decision/get_provenance restano riferiti al ranking.
- Documento per CVE fissato dal checkpoint verificato: tenant/run/asset/CVE,
  decisione e chiave GRAPH effettiva, snapshot/digest ontologico, scelta MAS o
  astensione, score originali e tutte le validazioni. Otto digest SHA-256 legano
  i byte originali dei produttori, preparazione, ranking, validazione, profilo e
  raccomandazione. JSON originale preservato per evitare normalizzazioni numeriche
  diverse tra Python, JavaScript e Go. Gli artefatti sorgente restano off-chain;
  il manifesto non equivale a una firma dei produttori.
- Ranking e validazioni contestuali conservati atomicamente dal backend prima
  della risposta; errori I/O propagati. Finalizzazione ammessa soltanto con
  evidenze effettivamente registrate e coerenti. Tenant dall'identita autenticata;
  header estranei rifiutati. Record storici senza evidenze: FINALIZATION_NOT_READY.
- StoreRecommendation/ReadRecommendation nello stesso contratto argumentation:
  riusato pattern KV storico, controllo MSP, ranking su ledger, identita FIN_
  deterministica e JSON immutabili. Namespace recommendation: riservato rispetto
  ai metodi generici dei grafi. Stessa richiesta idempotente; contenuto diverso
  per la stessa identita in conflitto. Nessun retry automatico di commit incerti.
- Ricevuta: transaction ID, blocco decimale, validation code 0 e successo. API
  pubblica Gateway 1.8.0 per lo stato; readback ledger; successivo tool MCP di
  rilettura confrontato con la prima risposta e il documento originale. Cache
  Gateway isolata per MSP, utente e canale con chiave non ambigua.
- PROV-O estende il builder esistente: scelta effettiva, otto artefatti, attivita,
  produttori e ogni valutazione backend; Tiny-ME e policy operativa distinti.
  Rimosse attivita non osservate del template, graphId inventato e falsa assurance
  da snapshot attivo. JSON-LD con termini e riferimenti RDF espliciti e named graph:
  roundtrip Dataset RDFLib, 184 triple, 17 entita, 10 attivita, 10 software agent.
- NativeFinalizationSession e quarta fase Strategic nel DAG (otto nodi, stessi
  cinque ruoli di dominio): finalize -> read -> publish per CVE. Input/risposte
  immutabili, policy CAMEL/clone e chiamate reali dei tool; guasti impediscono il
  checkpoint finale, conservando diagnostiche ed eventuali record gia registrati.
  CLI dedicata per selezioni archiviate; launcher real completa la fase finale.
  Candidate vuote: finalizzazione non applicabile e backend condiviso non avviato.
- Collaudo: 640 test Python, due warning RDFLib preesistenti; 163 test Jest in
  17 suite SaaS, 19 Vitest bridge; build Node 22.12.0, Ruff e pip check passati.
  Metodi Go testati con contract-api/MockStub, inclusi MSP, serializzazione reale
  del contratto e protezione del namespace. Il boundary CGO e escluso nell'harness:
  non e una build o una prova del reasoner nativo.
- Smoke framework -> stdio -> HTTP SaaS effettivi: accettazione, alternativa,
  prerequisiti, revisione e nessuna valida; cinque record e riletture, ripetizione
  idempotente, conflitto su contenuti cambiati, header spoof rifiutato. Riavvio
  effettivo del processo backend: stessi record/ricevute, zero nuove scritture.
  Autenticazione, Fabric e Tiny-ME sono fixture: nessuna prova di deployment/live.
- Applicazione controllata: 28 file nei due repository esterni, entrambi sempre
  costa-thesis; HEAD/riferimenti invariati, originali e backup confrontati con hash.
  Framework rimasto full. Preservati Identity/Ubuntu, credenziali, rete, dati
  storici e Word manuali. Nessun commit/push, deployment o probe di servizi reali.
- Risultato esplicito: shared_finalization=completed dopo tutte le riletture;
  verification_scope=backend_reported_commit_and_readback; deployment_verified=false,
  action_execution=not_performed. Il framework non verifica indipendentemente firme
  dei blocchi o endorsement. I controlli tenant sono applicativi, non privacy tra
  organizzazioni che condividono il ledger di canale.
- [Guida](docs/integrazioni/strategic-finalization.md),
  [report ed evidenze](output/shared-finalization-20261103/report.md).
  Directory avviata il 3 novembre e completata il 5: conserva log falliti, backup,
  sorgenti collaudati, piano/applicazione, smoke e manifest di verifica.

## Consolidamento scientifico del grafo e della semantica: 5 novembre

- Riletti proposta, moduli e storia dei due repository, proiezioni ALN e risultati
  e2e gia versionati; riutilizzati parser, builder, client di test e servizi esistenti.
  Nessun nuovo generatore, reasoner, ranking o assegnazione manuale di pesi.
- Riferimento specifico verificato: Fasciano et al., 2025, *A propagation-based
  ranking semantics in Explainable Bipolar Weighted Argumentation*, DOI
  10.1016/j.engappai.2024.109767. Il grafo esplicito indica interazioni orientate;
  segno e peso spettano al core su descrizioni OWL. Ranking reale finito distinto
  da affinityScore e dallo UnitScore mock. Aggiornata la bibliografia senza
  rigenerare i Word manuali.
- Nella storia locale manca Graph.cpp: disponibili header e libreria ELF Linux
  x86-64. Firme e dati storici non attestano equivalenza del binario al paper.
  Nessuna esecuzione numerica della libreria o build CGO del reasoner effettuata.
- Cinque coppie originali/riordinate: 6/11, 8/20, 12/21, 24/43, 40/75 nodi/archi,
  stessi insiemi orientati e tutti gli ID dichiarati/asserti nella baseline OWL.
  Catalogo `config/scientific-graph-cases.v1.json` con hash e 13 archi complessivi
  con clash diretto documentabile, attesi come attacchi se il core adotta il mapping
  pubblicato. Le altre polarita non sono dedotte dall'assenza di clash.
  Ranking numerici attesi null: nessun output del servizio ricopiato come oracle.
- La policy bottalico-directed-ring-v1 e conservata e qualificata come sperimentale.
  Riordinare gli array non cambia il grafo; riassegnare etichette puo cambiare
  l'anello lessicografico. Questo prova una dipendenza topologica, non una variazione
  del ranking reale. Il fallback SaaS con direzione opposta resta legacy, escluso
  dalla qualificazione; il percorso MAS invia sempre il grafo esplicito.
- Le quattro candidate della demo hanno la stessa descrizione ALN asserita:
  il proiettore copia contesto CVE/prodotto/vendor/CWE/CVSS, senza requisiti o effetti
  distinti delle azioni. Nel caso simmetrico una semantica indipendente dalle
  etichette deve produrre pareggio; spareggio tecnico per ID non e preferenza.
  Verificata anche la presenza della coppia esistenziale/universale sui ruoli CVSS.
- Nove run storici upstream S/M/L: 162 record, 69 scorciatoie locali score 1,
  93 etichettati MCP e 81 completamente in pareggio. Sono osservazioni archiviate,
  non prove attuali. Nel caso CVE-2024-8695 due Workarounds con profili asseriti uguali
  e posizioni diverse hanno score registrati 0.9962096214 e 0.9964718819; nessuna
  attribuzione causale a effetti dell'azione.
- Corretto il client Go esistente: confronto assoluto simmetrico con tolleranza
  1e-6, nomi/score univoci e finiti, input originali/riordinati realmente equivalenti,
  errori propagati e label mancanti senza panic. Cammini forniti verificati per
  archi orientati, destinazione, C1, prodotto dei pesi (1e-5) e segno favor/against.
  Assenza di explanation conteggiata; non sono verificati C2, fading o ranking
  completo. Conservato il probe che dimostra il falso positivo del confronto vecchio.
- ExplainAffinity cached/uncached richiedono una sola penalita numerica finita e
  non negativa. Mancante, duplicata o malformata: errore tecnico, non penalita 100
  trasformata in rifiuto. Discovery legacy separata e invariata. SaaS e client
  controllano anche la formula v1 gia esistente: abduction se positiva, altrimenti
  contraction, score max(0,100-penalita), tolleranza 1e-9; nessuna formula modificata.
- Verifiche: 652 test Python (due warning RDFLib preesistenti), 167 Jest/17 suite,
  nove client Go e tre parser numerico Go; build SaaS, Ruff e pip check passati.
  Collaudo framework -> bridge stdio -> HTTP SaaS con cinque esiti, 61 chiamate MCP,
  cinque record, idempotenza, conflitto e riavvio effettivo: cinque riletture e zero
  nuove scritture. Fabric/Tiny-ME/autenticazione simulati; bridge invariato rispetto
  ai 19 test del task precedente. Nessuna verifica di disponibilita reale anticipata.
- Applicati soltanto dieci file nel ledger su costa-thesis, con backup/hash e
  controllo di branch/HEAD/riferimenti prima delle scritture. Pipeline Bottalico
  invariata, entrambi gli esterni ancora costa-thesis, framework full; nessun
  commit/push/deployment o modifica a Identity/Ubuntu, credenziali, rete o Word.
- Copertura da estendere: il canonico contiene CVE e strategie; runtime e vincoli
  nella provenance/policy non sono ancora nodi indipendenti del ranking previsti
  dalla proposta. Per preferenze fra azioni occorrono profili distinti e fonti per
  requisiti/effetti/relazioni. Il modulo corrispondente non e emerso dall'ispezione:
  estensione non implementata, schema/fonti da concordare secondo il vincolo utente.
  Versione/parametri del core, ontologia realmente caricata, ranking e binding IRI
  restano al collaudo finale. Bonus non valutato dal percorso corrente.
- [Contratto scientifico e limiti](docs/tecnica/consolidamento-scientifico-grafo.md),
  [report](output/scientific-consolidation-20261105/report.md),
  [manifest di verifica](output/scientific-consolidation-20261105/verification.json).
  Directory con sorgenti, patch, backup, cataloghi e log, inclusi i fallimenti iniziali.

## Preparazione dei quattro casi controllati: 5 novembre

- L'utente ha chiesto di iniziare dai casi e confrontarne la struttura con i mock.
  Preparati `config/controlled-cases.v1.json` e `docs/tecnica/casi-controllati.md`:
  input/fonti, variazione, esiti separati per modalita e materiale ancora necessario.
  Nessuna nuova funzione applicativa, servizio, schema di dominio o integrazione esterna.
- C1 nominale e C4 senza manutenzione riusano demo_01/demo_02; C3 riusa demo_04
  come analogo mock e la cattura CTI ambigua del nome log4j-core. C2 e un negativo
  nello snapshot, distinto dal vecchio caso di tutte le azioni vietate.
- Il mock riconosce soltanto log4j-core 2.14.1: l'input di confronto C2, con sola
  versione cambiata a 2.26.1, produce unsupported/insufficient_evidence. Non e
  no_findings e il mock non viene esteso. C2 reale riusa l'applicazione Java e le
  fonti coerenti archiviate in observed-app-sources-20261007-02, con cattura negativa
  della stessa versione, identita risolta e regole complete. Replay esplicito.
- Le catture CTI positive Apache Log4j Core 2.14.1 contengono tre finding
  (CVE-2025-68161, CVE-2026-34477, CVE-2026-34480); non forzare la CVE-2021-44228
  della fixture o i binding illustrativi del profilo reale di esempio.
- Verificati quattro run CLI mockup e quattro mapping offline delle catture:
  C1 selected/S_UPGRADE, C2 e C3 insufficient_evidence, C4 selected/S_ISOLATE.
  Controllati hash del manifest Java archiviato, JAR/SBOM, cinque record OTel,
  versione, finestra, selettore e binding con inspect_sources esistente.
  Passati i 30 test esistenti di demo, adapter CTI e fonti, senza nuovi test o codice
  applicativo; git diff --check senza errori.
- Fonti ancora da materializzare: build vulnerabile coerente C1; C4 riusa gli
  stessi dati cambiando soltanto maintenance_window; C3 con degradazione dichiarata
  dell'identita. Non chiamare quattro run reali pronti/eseguiti la sola matrice.
  Servizi reali, configurazione, digest e IRI rimangono alla fase finale.
- Esiti reali senza candidate: assessment_completed con no_findings oppure
  insufficient_evidence, fasi native skipped e finalizzazione not_applicable.
  Nessuna ricevuta inventata. C4 prova fallback soltanto se viene scartata una
  candidata precedente e accettata una successiva; non imporre ordine o ID del mock.
- Evidenze: `output/controlled-cases-20261105/report.md`, verification.json,
  source-hashes.json, copie delle fonti, quattro output completi e log. Conservato
  primo tentativo fallito del verificatore; corretto il riuso a hash identico
  della cattura condivisa C1/C4. Nessuna inferenza, nuova build o query live.

## Primo collaudo reale, rete Fabric e MCP: 5–6 novembre

- L'utente ha richiesto i primi quattro tentativi reali per rilevare problemi,
  poi precisato che Fabric va avviata dalla root del repository costa-thesis,
  seguendo i README. Docker Desktop era spento e non esisteva una rete Fabric,
  neppure arrestata. Autorizzato l'avvio della configurazione esistente.
- Avviata Docker Desktop; Fablo 2.4.1 installato nella root del ledger come nella
  guida di argumentation/schema. Build delle due immagini originali linux/amd64
  e `./fablo up fablo-config.json` dalla root costa-thesis. Nessun clone isolato
  usato per la rete; nessun prune/reset o cancellazione di dati.
- Il primo hook e fallito con BSD sed del Mac: compilato GNU sed 4.9 soltanto
  nella directory del collaudo, poi rieseguito l'hook originale con quel PATH.
  Configurazione, README, .env e compose originale preservati. Canale my-channel;
  argumentation e user-registry committed versione 1.0, sequenza 1.
- La prima vera build CGO ha trovato import strconv rimosso ma ancora necessario
  e un booleano Go da convertire esplicitamente in C.bool nel callback IRI.
  Due correzioni minime su costa-thesis, backup e patch. Ora entrambe le immagini
  compilano e sono effettivamente distribuite nella rete locale.
- SaaS compilato con Node 22.12.0 e avviato con PM2 come da guida, porta 8800,
  peer grpcs e certificato generato da Fablo. PM2 locale alla directory di output,
  senza installazione globale o modifica ai file .env. Bridge compilato sul
  secondo costa-thesis, discovery di 21 tool.
- Sei chiamate MCP reali passate: get_active_snapshot, store_graph, get_graph,
  rank_graph, get_rank_result, get_annotated_graph. Primo grafo di benchmark
  esistente, nuova chiave, autenticazione/Fabric/core nativo reali. Roundtrip,
  candidati, score finiti, clash negativo e prodotti dei cammini controllati.
  Non e ancora finalizzazione MAS/ExplainAffinity reale o prova di tutti i grafi.
- Nuovo limite osservato: il core restituisce un against con prodotto positivo,
  coerente con i pesi dei suoi archi. Il significato della categoria non e quindi
  attestato dalla semplice regola di segno dei controlli offline. Non modificato
  il binario per soddisfare il verificatore; evidenza conservata e limite aperto.
- Due build isolate del workload Java esistente, 2.14.1 e 2.26.1, con JAR caricato,
  SBOM, cinque log SDK, hash, istanza e finestra coerenti. POM originale invariato.
  C4 riusa la raccolta vulnerabile senza maintenance_window; C3 cambia il solo
  nome prodotto su una copia dei log, dichiarandola degradazione sintetica.
- CTI reale avviato in sola lettura dal database locale e3566009..., KG originale
  ritrovato in Downloads (5 GB, sha256 0ffa87d0...). Il probe MCP conferma tre CVE
  per Apache Log4j Core 2.14.1; il builder Bottalico sul KG non trova rimedi collegati
  a nessuna delle tre. Nessun binding/rimedio nuovo inventato per aggirare il blocco.
- Primo C1 interrotto da un errore nel launcher: il parametro del costruttore CTI
  era dataset_sha256 anziche expected_dataset_sha256. Corretto il collegamento;
  aggiunte due regressioni HTTP/MCP su pin corretto e digest diverso. Suite Python
  completa: 654 passati, due warning RDFLib preesistenti; quattro test Go helper.
  Build SaaS/bridge passate, sorgenti SaaS/bridge invariati e suite non rieseguite.
- Tentativi diagnostici con CAMEL, modello locale tesi-apache-qwen3:4b-32k e
  servizi CTI/OSV reali. Eseguita la Workforce dei tre produttori, senza mock o
  modello programmato. Non sono quattro run completi del launcher fino alla
  finalizzazione: C1 fallisce sulla pubblicazione di verifiche Ubuntu prive di
  evidenza; C2 completa l'assessment con no_findings e candidate vuote; C3 trova
  identita ambigua ma fallisce sulla pubblicazione. C4 fallisce in VulnerabilityAgent:
  Ollama HTTP 500 per JSON incompleto di publish_vulnerability_report anche dopo
  retry; CountermeasureAgent bloccato, vincolo operativo non ancora verificato live.
  Fallimenti non trasformati in astensioni o raccomandazioni.
- Rete Fabric, backend SaaS e CTI lasciati attivi. Gestione applicativa via MCP;
  start/stop dei container tramite Fablo. Conservare fablo-target, dati SaaS e
  runtime/PM2 locali. Nessun commit/push, esecuzione di contromisure o modifica ai Word.
- [Guida operativa](docs/integrazioni/collaudo-reale.md),
  [report](output/real-cases-20261105-r1/report.md),
  [verifica conclusiva](output/real-cases-20261105-r1/verification.json).
  Avviato il 5 e concluso il 6 novembre: directory conserva anche i fallimenti,
  sorgenti collaudati, backup, patch, log SDK e ricevute del collaudo MCP.

## Audit della copertura KG e alternative: 6 novembre

- Esaminati anche i file ignorati dei due working tree costa-thesis, le ontologie
  del ledger e i riferimenti locali origin/main e origin/principe-thesis, senza
  checkout, modifiche esterne, fetch o nuovi componenti di produzione.
- Scansione integrale del cve2owl originale di 5.062.301.486 byte, digest
  0ffa87d0ff610cd7860dc3cae4bd84e65ab223569ba19ef2f4240fba6da59350.
  Riconosciute con il formato del generatore 18.758 asserzioni di rimedio per
  16.502 CVE, 2.107 con almeno due rimedi. I conteggi sono strutturali, non
  attestano azioni applicabili o distinte. Alcuni Workarounds dichiarano assenza
  di mitigazioni. Il piccolo seed storico non sostituisce il dataset reale.
- Indice reale: 352.234 record CVE, 584.678 affected_product e 1.134.883 versioni.
  Il file omonimo Downloads e un puntatore LFS, non un secondo database; digest
  e dimensione dichiarati corrispondono al database effettivo della pipeline.
- Confermati zero rimedi per CVE-2025-68161, CVE-2026-34477 e CVE-2026-34480.
  Anche il proiettore ALN esistente, eseguito sul file originale completo senza
  arresto anticipato, rifiuta le tre CVE per assenza di Solution/Workaround.
- Eseguite 20 query diagnostiche in-process con LookupService reale e indice
  invariato; risposte validate anche da map_assessment del framework. Non sono
  chiamate MCP di rete o nuove osservazioni SDK. Commons IO, MINA, Jena e Velocity
  non risolvono la copertura congiunta CTI/rimedi; Kubernetes Java Client resta
  parziale e la CVE positiva non ha un CVSS supportato dal proiettore.
- Individuata coppia Logback-core, vendor QOS.CH Sarl: 1.5.24 produce soltanto
  CVE-2026-1225, 1.5.25 produce no_findings; identita risolta e copertura regole
  completa in entrambi. La CVE possiede un rimedio esplicito di aggiornamento e
  CVSS proiettabile; ALN generata dai moduli originali senza correzioni semantiche.
  Non e ancora verificata la nuova build/SBOM/telemetria o il manifest del JAR.
- Alternativa Plack::Middleware::Session 0.34/0.35 verificata per CTI e ALN, ma
  richiede workload Perl e un workaround fuori dalle categorie operative correnti;
  meno adatta alla chiusura rapida. Logback e consigliato per riusare il workload
  Java con adattamenti circoscritti e senza nuovo KG. Una sola candidata significa
  nessun confronto/fallback: C4 puo concludere senza upgrade accettabile quando
  manca maintenance_window. Nessuna sostituzione del protocollo gia applicata.
- Se fosse necessario conservare Log4j, alternativa da discutere: supplemento
  KG minimo con fonti ufficiali, IRI, provenance e nuovo snapshot verificato;
  originali preservati. Nessun arricchimento implementato o nuova estensione
  autorizzata. Conservare il limite senza raccomandazione e corretto, ma non
  sostituisce la prova del percorso positivo.
- Nessuna modifica a sorgenti applicativi/esterni, rete o ledger. Audit e prove
  in [output/kg-coverage-20261106/report.md](output/kg-coverage-20261106/report.md).
  Da risolvere: scelta finale del caso, identita osservata e binding/distribuzione
  nativa, affidabilita delle pubblicazioni LLM e run completi con ricevute.

## Miglioramenti e verifica C1: 6–7 novembre 2026

- Riusati Logback-core 1.5.24/1.5.25 e il rimedio CVE-2026-1225 gia nel KG,
  senza arricchimenti o nuovi profili d'azione. Fonti reali in
  `output/case-improvements-20261106/sources/`; v1 controllato resta immutato,
  protocollo attuale in `config/controlled-cases.v2.json`.
- Pubblicazione CTI acquisita con chiamata esplicita senza argomenti; controlli
  originali di snapshot/evidenza/immutabilita preservati. CountermeasureAgent
  deve pubblicare anche strategies=[]; nessuna richiesta Ubuntu senza contesto.
  Candidate incompatibili con binding/CVE rifiutate prima del commit.
- OWL originale hashato in streaming. Ontologia ALN + asserzioni osservate
  riusate, SHA 83b4f962..., distribuita e riletta; Tiny-ME reale: abduzione 38,
  contrazione 0, score 62, requires_prerequisites. Resta un limite semantico.
- C++ SIGSEGV su una sola strategia: portata la convenzione esistente Bottalico
  origin/main 090b6844...::_single_strategy_outcome. Metodo e fonte espliciti;
  score 1 convenzionale, weightsComputed=false, nessun cammino inventato.
- Correzioni su costa-thesis: CachedNetwork.gateway.close() su scadenza;
  chiave cache include SHA del certificato per associare identita e firmatario;
  bridge rinnova una sola volta dopo l'esatto rifiuto auth prima dell'esecuzione.
  Timeout, ACCESS_DENIED e guasti backend non vengono reinviati automaticamente.
- C4 ha evidenziato il token opaco SaaS (TTL 600 s), poi il riuso improprio del
  firmatario dopo nuovo enrollment. Ricevute CAMEL ora in vista ID/digest/commit;
  get_context e documenti registrati restano integrali. Due regressioni dedicate.
- Suite eseguite: 667 Python, 169 SaaS/17 suite, 25 bridge/3 file, 13 Go.
  La suite SaaS usa clearStore su directory predefinite in alcuni test: eseguirla
  nella directory live e stato un errore operativo e ha rimosso metadati locali.
  Non ricostruire evidenze backend inventate per mascherarlo. Ledger e archivi
  del framework conservati; prova di lettura del record C4 in
  `ledger-C4-readback-after-metadata-loss.json`. C4 non e completato.
- Docker recuperato senza reset/prune/volumi cancellati dopo esaurimento swap;
  C1-r1 interrotto e conservato. Binario nativo recuperato da sorgenti reali
  montati read-only sul builder integro; hash confrontato con il container.
- C1-r2 concluso: launcher real/camel/pipeline, otto nodi completati, commit e
  rilettura verificati. Esito requires_prerequisites; nessuna scelta accettata.
  Backup dei nuovi metadati SaaS C1 con hash. Report C1 e manifest sono i
  riferimenti correnti; non dichiarare completati C4 o tutti i criteri nominali.
- Framework full; due repository esterni costa-thesis. Nessun commit/push,
  nuova UI o modifica ai Word manuali. Le sezioni precedenti sono cronologia.

## Indicazioni del professore

- Riutilizzare servizi, rete/chaincode, dashboard e casi di argumentation esistenti.
  Strategic -> MCP/REST di dominio -> SaaS -> Fabric; dettagli infrastrutturali nel backend.
- Adapter BWAF canonico: semantica nodi/archi, supporto/attacco, origine dei pesi
  e ranking atteso espliciti. Nessun ranking/reasoner/provenance parallelo.
- Integrare la pipeline Bottalico LLM per annotazioni/argomenti come agente.
  Ispezione completata: pipeline e moduli individuati; l'LLM estrae asset e le
  fasi OWL/grafo/ALN sono deterministiche. Il 3 novembre l'utente ha confermato
  l'uso di questa pipeline disponibile; non serve un diverso generatore diretto.
- Tiny-ME dietro validazione di dominio con condizioni, conflitti e spiegazione.
- Demo dry-run: strategia raccomandata, mai dichiarata applicata; commit e rilettura
  verificati oltre al transaction ID.

## Stato funzionale

Quattro agenti CAMEL/Ollama nel percorso mock; preparazione canonica aggiuntiva
e quattro fasi Strategic nel DAG nativo composto, fino alla finalizzazione per CVE.
Switch applicativo mockup/real indipendente dai branch e dall'inferenza.
OTel/CTI e SBOM/OSV disponibili in profili distinti; caso Java con fonti della build.
Apache: identita v2 risolta, 120 CVE Ubuntu (34 fixed, 28 not_affected,
46 potentially_affected, 12 unknown); quattro richieste su 58 CVE uniche, non strategie.
Stato runtime storico non verificato: `insufficient_evidence` legittimo.
Ollama r1 fallito; r2 con audit, due retry, 1.284,92 s e 28 richieste; nessuna remediation.
PROV-O riletto da archivio su file; BWAF/Tiny-ME/ledger reali ancora aperti.
Gateway Fabric sperimentale e chaincode PROV-O separato conservati per test/confronto,
fuori dal percorso principale. [Esperimenti](docs/esperimenti.md).

## Prossimi passi ordinati

1. C1 e completato tecnicamente e documentato; valutare i limiti decisionali
   effettivi senza forzare l'accettazione o introdurre nuove estensioni.
2. C2/C3 completati. C4 resta distinto e non completato; i suoi dati ledger sono
   conservati, i metadati SaaS precedenti richiedono ripristino o un nuovo run.
3. Consolidare misure sostenibili e relazione; riusare la dashboard esistente.
   I Word manuali restano sotto controllo dell'utente. Nessun nuovo profilo
   semantico d'azione o topologia richiesto per la chiusura concordata.
4. Non eseguire test SaaS nella directory live. Conservare il backup C1, i
   dati Fabric e le directory usate da servizi, runtime e montaggi ontologici.

[Report conclusivo C1](output/case-improvements-20261106/report-C1.md).

## Conservazione e letture mirate

Non sovrascrivere/rigenerare `docs/materiali/relazione.docx` e
`docs/materiali/relazione-aggiornata-20261029.docx`: revisioni manuali.
Lock Word conservato sul disco, escluso da Git; binari invariati nella pulizia.
Non eliminare snapshot, log LLM o run falliti in `output/`, assenti nei cloni.
`output/porting-principe-costa-20261030/` conserva patch, backup, manifest e risultati;
dipendenze, cache, runtime Node e copie temporanee del collaudo sono stati rimossi.

[Indice](docs/README.md), [stato](docs/stato-progetto.md),
[architettura](docs/architettura-implementata.md), [codice](docs/reading-guide.md).
Guide in `docs/integrazioni/`, approfondimenti in `docs/tecnica/`, storia in `docs/archivio/`.
Vecchio piano MCP assorbito nella roadmap, cronache in `docs/esperimenti.md`;
originali recuperabili da Git `32e6dbc`.
