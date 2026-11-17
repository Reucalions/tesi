# Valutazione finale del prototipo — 13 novembre 2026

La raccolta e il consolidamento delle misure sono conclusi nel perimetro concordato,
senza nuovi profili semantici, agenti o modifiche al core. Le prove dimostrano
il funzionamento dei componenti e della pipeline reale in dry-run, con i limiti
indicati sotto. **Non attestano il soddisfacimento integrale della proposta iniziale.**

Fonte dei criteri: [proposta iniziale](../riferimenti/proposta-agentic-cti.pdf),
§14–16, SHA-256 `9eed32a42b3dd3655e725c393306cdea8b5426d434a609d0434faf701cabf5bf`.
Il catalogo corrente e [metrics-evidence.v2.json](../../config/metrics-evidence.v2.json).
Il catalogo v1 e l'inventario dell'8 novembre restano fotografie storiche.

I [risultati conservati nel repository](../../evaluation/final-results-v1/README.md)
comprendono JSON, CSV, manifest e ingressi compressi per ricalcolare le tabelle
offline, senza servizi o credenziali. Gli archivi completi locali sono in
`output/final-evaluation-20261113-r1/`, sintesi `consolidated-r2/`.
3293 file inventariati, 32 criteri, 227 osservazioni temporali e 45 confronti
appaiati. Le copie di lineage non contano come nuove esecuzioni.

## Estrazione e matching (§15.1)

Campione v2: 12 documenti di estrazione (4 export SDK e 8 derivati controllati),
16 interrogazioni CTI. Annotazioni congelate prima della misura, verificate
dall'assistente sulle fonti; **nessuna revisione umana indipendente**. Questi sono
risultati di componenti deterministici, non precisione degli agenti LLM.

| Misura | Conteggi | Risultato |
| --- | --- | ---: |
| Precisione entita | TP=7, FP=1 | 0.875000 |
| Recall entita | TP=7, FN=3 | 0.700000 |
| F1 entita micro | 2TP/(2TP+FP+FN) | 0.777778 |
| Exact match documenti | 9/12 | 0.750000 |
| Identita prodotto | 13/16 | 0.812500 |
| Classificazione versione, tre classi | 10/13 | 0.769231 |
| Classificazione versione, binaria | 7/8 | 0.875000 |

La binaria esclude i casi non eleggibili: non sostituisce il risultato a tre
classi. Nei soli quattro SDK originali P/R/F1 sono 1; negli otto derivati sono
0.75/0.50/0.60. L'accuracy identita e 12/13 nei casi diretti e 1/3 nei casi di
policy. Gli errori tecnici sono zero, mentre restano errori su informazioni
parziali, vendor, certezza fuori intervallo e astensione lessicale. Tuple e
campi usano le regole del [campione v2](../../evaluation/annotated-sample-v2/README.md).
Nessuna misura di accuratezza generale su traffico o popolazioni indipendenti.

## Ranking nativo, persistenza e spiegazioni (§15.2)

La campagna corretta del 13 novembre usa cinque grafi baseline preesistenti,
originali e riordinati, tre repliche per input: 30 prove, 30 confronti fra
repliche e 15 confronti di permutazione. Score e pesi identici in 45/45;
insiemi dei massimi stabili. I grafi maggiori presentano pareggi entro 1e-6:
non si forza una scelta unica e lo score non e una probabilita.

60 commit VALID nei blocchi 89–148 e 30 riletture indipendenti verificate.
Dopo l'adattamento Go, 60/60 cammini hanno archi, prodotti e destinazione
coerenti con la candidata esposta. JSON nativo esatto e audit sono conservati
nello stesso commit del ranking. La precedente campagna del 12 novembre,
con associazione corretta 30/60, rimane archiviata separatamente.

Restano 12 cammini `against` con prodotto positivo, 156/186 occorrenze di
candidate senza cammini e solo 6/15 coppie con explanation interamente identiche
per label. L'ordine puo influire sulla prova scelta pur lasciando score e massimi
identici. Non si certifica l'equivalenza numerica al paper: `Graph.cpp` non e
stato reperito nei repository locali. [Correzione e audit](correzione-spiegazioni-native.md).

La sensibilita e stata misurata con il getter e le proprieta degli archi gia
esposti dall'SDK nativo, senza cambiare libreria o distribuzione. Un solo grafo
baseline (6 nodi, 11 archi), cinque varianti per tre repliche; topologia, nodi
e altri pesi invariati, pesi intervenuti riscontrati nell'output, risultati
identici nelle repliche. Non e una nuova API applicativa di regolazione dei pesi.

| Intervento | Fattore | Massima variazione assoluta score | Vincitore |
| --- | ---: | ---: | --- |
| baseline | 1 | 0.000000000 | AutomatedCountermeasure |
| attack-half | 0.5 | 0.009324670 | AutomatedCountermeasure |
| attack-stronger | 1.5 | 0.011376977 | AutomatedCountermeasure |
| support-half | 0.5 | 0.005605340 | AutomatedCountermeasure |
| support-stronger | 1.05 | 0.000162482 | AutomatedCountermeasure |

Attacco 3→0, supporto 5→3. I pesi iniziali dei nodi non sono parametri esposti:
questa parte di R04 rimane non valutata, senza inventare una semantica alternativa.

## Validazione semantica (§15.3)

C1 e C4 producono una candidata `S_UPGRADE`, rango 1 con score **convenzionale**
1.0 (`single_candidate_convention_v1`), non una competizione BWAF. Tiny-ME
restituisce ipotesi non vuota e penalita di abduzione 38; la candidata rimane
`requires_prerequisites` e `selected_strategy_id=null`. I vincoli operativi sono
valutati separatamente dalla semantica. C4 conserva la manutenzione mancante e
il limite lessicale di `package_upgrade capability` rispetto a `package_upgrade`.
La finalizzazione riuscita non trasforma l'esito in una mitigazione accettata.

Sono stati esercitati i servizi nativi esistenti via `AnalyzeOntology` su
ontologie gia disponibili, tre ripetizioni per caso, sei query reali:

| Servizio | Input | Output osservato | Confine |
| --- | --- | --- | --- |
| Abduzione | Asset e rimedio Logback di C1 | Ipotesi, Penalty 38 | Diagnostica reale e percorso C1 |
| Bonus | Stessa coppia Logback | Surplus ObservedSoftwareAsset, Incentive 1 | Diagnostica low-level |
| Contrazione | Coppia baseline esplicitamente disgiunta | Keep, Give up, Penalty 2 | Diagnostica low-level |

Query evaluate senza commit, con ontologia transiente. Nel percorso applicativo
`ExplainAffinity`, Bonus resta `bonusEvaluated=false`; la contrazione di C1 non
e invocata. Un valore vuoto o zero di un ramo non invocato non e una misura.

Altri controlli reali MCP usano ranking persistiti e l'ontologia baseline
originale, registrata senza modifiche con chiave distinta. Risorsa AI:
baseline 2 accetta subito AI; baseline 1 rifiuta Automated, condiziona Blockchain
e ZeroTrust, poi accetta AI. L'accettazione e **riflessivita resource=request**,
senza contesto operativo. La visita del ranking e un'osservazione di valutazione,
non una selezione/fallback del MAS su un asset vulnerabile. S02/S04 restano
parziali: nessuna accettazione applicativa o alternativa reale dimostrata.

## Prestazioni e stima del costo del ledger (§15.4)

Ambiente locale: host arm64 con 18 GiB RAM, container linux/amd64 emulati;
Ollama, CTI, SaaS, Fabric reali. Campioni piccoli e sequenziali; prima osservazione
e caricamenti inclusi, nessun warm-up scartato. Distribuzioni complete
(minimo, mediana, massimo, deviazione campionaria) nei CSV; nessun p95,
throughput, intervallo di confidenza o test di significativita.

| Misura | n | Risultato in secondi | Confine |
| --- | ---: | ---: | --- |
| Gateway telemetria | 3 | mediana 0.027668, min 0.019959, max 0.135874 | HTTP su replay SDK |
| TelemetryAgent isolato | 3 | mediana 57.370528, min 56.668928, max 71.086058 | Step del worker reale, tool e pubblicazione inclusi; manager esclusi |
| OWL osservato | 1 per braccio | 0.000322 / 0.000414 | Funzione generatrice esistente |
| Proiezione ALN | 1 per braccio | 102.026871 / 105.498657 | Funzione esistente, wrapper timer incluso |
| Grafo e lookup KG | 1 per braccio | 8.542962 / 9.517914 | Costruttore e interrogazione KG insieme |

Worker reale con modello `tesi-apache-qwen3:4b-32k`, contesto 32768,
max token 4096, temperatura 0; prompt/tool di produzione. Tre pubblicazioni
riuscite, senza aggiungerle al campione P/R/F1. I timer di matching CTI,
validazione, finalizzazione e preparazione aggregata si trovano in `series.csv`,
separati per coorte. Finalizzazione significa decisione piu PROV-O atomiche e
riletture: non isola il solo costo di scrittura provenance. Le misure sovrapposte
non vanno sommate e il residuo non puo essere chiamato tempo LLM.

Confronto off-chain: stesso `RankGraph` Go, stessa libreria e immagine, stessi
30 input e output nativi esatti, stato in memoria `shimtest.MockStub` al posto
di Fabric. E calcolo nativo reale, distinto dal ranking euristico del mockup.
Le esecuzioni on-chain provengono dalla campagna congelata precedente, non sono
intervallate con le nuove off-chain. La differenza comprende client, trasporto,
stato e Fabric; non e un costo puro del consenso o una prova causale di velocita.

Secondo confronto: 15 coppie appaiate nello stesso client REST, medesimo
`RankGraph` in evaluate e invoke, cinque grafi per tre ripetizioni, ordine
alternato. Dopo evaluate nessuno dei quattro stati derivati e presente; dopo
invoke output/audit/stato e commit verificati. La differenza include il percorso
aggiuntivo di endorsement, submit e commit; nessuna differenza negativa eliminata.

| Grafo: nodi/archi | Rank MCP mediana, n=6 | Rank in memoria mediana, n=6 | Mediana differenze appaiate MCP−memoria | REST invoke−evaluate, n=3 |
| --- | ---: | ---: | ---: | ---: |
| 1: 6/11 | 0.115473 | 0.032637 | 0.080185 | 0.068940 |
| 2: 8/20 | 0.145062 | 0.061768 | 0.082569 | 0.064593 |
| 3: 12/21 | 0.131587 | 0.045445 | 0.083831 | 0.061327 |
| 4: 24/43 | 0.183548 | 0.092566 | 0.087453 | 0.064111 |
| 5: 40/75 | 0.290056 | 0.196302 | 0.099257 | 0.069293 |

La mediana delle differenze non coincide necessariamente con la differenza
delle mediane. I cinque grafi variano anche contenuto e topologia: nessuna legge
di scalabilita ricavata dalla sola numerosita dei nodi. Il test dei pesi misura
separatamente `ComputeRank` includendo i log, escludendo caricamento e costruzione;
non si mescola con questi timer di contratto o MCP.

## Due confronti richiesti (§15.5)

**Con e senza runtime.** Un replay controllato dal confine degli artefatti
rimuove riferimenti, contesto e osservazioni OTel, mantenendo identici SBOM,
CTI/KG, candidate, binding e policy operatore. Entrambi i bracci percorrono il
generatore canonico, MCP reale, ranking, validazione, selezione e finalizzazione.
Una esecuzione per braccio, rispettivamente 205.544073 e 209.079830 s, commit nei
blocchi 153 e 157. Nessun nuovo run upstream LLM o completo CAMEL.

Il confronto verifica byte identici di richieste/grafo, OWL osservato e ALN:
stesso rango, stessa abduzione 38, stessa decisione condizionata, nessuna selezione.
Il contesto runtime rimosso non cambia questi output a inventario/CTI fissati.
Il generatore corrente rappresenta soprattutto identita e contesto CVE; i nodi
liberi espliciti delle tracce runtime proposti non sono presenti nel grafo C1/C4.
Questo limita l'evidenza del contributo semantico del runtime. La modalita reale
upstream richiede OTel: il braccio senza runtime e una baseline sperimentale
al confine degli artefatti, non una nuova modalita applicativa supportata.

Un confronto informativo aggiuntivo usa lo stesso SBOM: 14 componenti con
versione dichiarata, uno collegato positivamente da cinque log SDK (`logback-core`
1.5.24). La policy sperimentale con runtime interroga il solo componente
osservato, con lookup matched; la scansione statica ne interroga 14: 1 matched,
1 no_findings, 12 ambiguous. Totale 15 query CTI reali. Non osservato non significa
assente, sicuro o falso positivo; la copertura KG non e accuratezza. Non si
conclude che il runtime sia inutile, completo o piu veloce nell'intero sistema.

**Prima e dopo validazione.** Sui medesimi artefatti: proposta `S_UPGRADE`
rango 1/score convenzionale 1.0 → semantica `requires_prerequisites` → policy
`requires_review` per vincolo testuale non mappato → esito effettivo
`requires_prerequisites`, selezionata nulla. La precedenza e quella del contratto
esistente. E un confronto descrittivo esplicito: nessuna disabilitazione delle
guardie e nessuna proposta di ranking rinominata decisione accettata.

## Quattro casi reali e verifica condivisa

| Caso primario | Stato tecnico | Esito | Secondi runner | Finalizzazione |
| --- | --- | --- | ---: | --- |
| C1-r2 | dry_run_completed | requires_prerequisites | 1274.172 | completed |
| C2-r1 | assessment_completed | no_findings | 298.132 | not_applicable |
| C3-r1 | assessment_completed | insufficient_evidence | 296.697 | not_applicable |
| C4-r3 | dry_run_completed | requires_prerequisites | 1224.254 | completed |

C1 e C4-r3 completano gli otto nodi del DAG nel launcher; C4-r3 usa timeout LLM
600 s senza ripresa esterna. C2/C3 concludono l'assessment e saltano correttamente
le fasi native non applicabili. C3 degrada sinteticamente la sola identita.
Durate runner con teardown, non tempo originale evento-decisione; nessuna media
fra percorsi diversi. I tentativi falliti e la ripresa separata di C4-r2 restano
archiviati; il primo avvio fallito dell'ablation per un errore del collector
resta separato da `ablation-r2`, che ha completato i due bracci.

Cinque nuove riletture in una sessione MCP indipendente confermano record,
provenance e ricevuta identici per C1, C4-r2, C4-r3 e i due replay. Sei nuovi file
di metadati SaaS autentici sono salvati con hash. Nessuna contromisura eseguita.

## Copertura analitica delle 32 voci

`Disponibile, circoscritta` indica una misura reale entro il confine dichiarato,
non conformita completa o validita generale. `Parziale` conserva la lacuna.
Non si calcola una percentuale globale su criteri con significati diversi.
Le evidenze di ciascuna riga sono risolte nei gruppi del catalogo v2 e
nell'[inventario con hash](../../evaluation/final-results-v1/inventory.csv).

| ID | § | Criterio | Stato | Evidenza attuale | Limite |
| --- | --- | --- | --- | --- | --- |
| E01 | 15.1 | Precisione estrazione | Parziale | TP 7, FP 1, FN 3: precisione 0.875 su 12 documenti. | Riferimento assistito e verificato sulle fonti; revisione umana indipendente assente. |
| E02 | 15.1 | Recall estrazione | Parziale | Recall 7/10 = 0.7; quattro export SDK e otto derivati controllati. | Campione piccolo non rappresentativo; riferimento non umano indipendente. |
| E03 | 15.1 | F1 estrazione | Parziale | F1 micro entita 14/18 = 0.777778. | Misura del componente deterministico, non accuratezza degli agenti LLM. |
| E04 | 15.1 | Accuratezza matching prodotto | Parziale | Identita prodotto 13/16 = 0.8125; diretti 12/13, policy 1/3. | Riferimento assistito; ambiguita e astensioni incluse secondo protocollo. |
| E05 | 15.1 | Accuratezza classificazione versioni | Parziale | Versioni tre classi 10/13 = 0.769231; binaria 7/8 = 0.875. | Denominatori diversi; non usare solo la binaria come risultato complessivo. |
| E06 | 15.1 | Categorie di errore e casi rappresentativi | Disponibile, circoscritta | Errori tecnici 0 nel campione componenti; fallimenti launcher e ambiguita archiviati. | Zero errori tecnici non implica zero errori semantici o LLM. |
| R01 | 15.2 | Determinismo con nodi/archi riordinati | Disponibile, circoscritta | 45/45 confronti score/pesi identici, 30 ripetizioni e 15 permutazioni. | Explanation completa identica in 6/15 coppie; core non certificato contro oracle numerico. |
| R02 | 15.2 | Persistenza grafi e risultati sul ledger | Disponibile, circoscritta | 30 riletture ranking e cinque nuove riletture finalizzazioni identiche. | Metadati locali SaaS separati dallo stato Fabric; nessun test di disaster recovery. |
| R03 | 15.2 | Stabilita del vincitore tra ripetizioni | Disponibile, circoscritta | Insiemi dei massimi stabili nelle repliche dei cinque grafi. | Pareggi entro tolleranza; score prossimi a 1 non probabilita. |
| R04 | 15.2 | Sensibilita ai pesi di nodi e archi | Parziale | 15 prove: quattro interventi sugli archi e baseline, tre repliche; score cambiano, vincitore stabile. | Parametri iniziali dei nodi non esposti; intervento da harness esistente SDK, non API online. |
| R05 | 15.2 | Comportamento al crescere del grafo | Disponibile, circoscritta | 6/8/12/24/40 nodi, 11/20/21/43/75 archi, sei osservazioni MCP per dimensione. | Cinque grafi non isolano la sola dimensione e non provano scalabilita generale. |
| R06 | 15.2 | Qualita delle spiegazioni del ranking | Parziale | 60/60 cammini con destinazione e prodotto validi dopo adattamento; output nativo conservato. | 12 against con prodotto positivo; 156/186 occorrenze senza cammini; scelta sensibile all ordine. |
| S01 | 15.3 | Graduatoria prima e decisione dopo validazione | Disponibile, circoscritta | C1/C4 e replay: proposta rango 1, poi requires_prerequisites e selected nullo. | Score 1 convenzionale a candidata singola; non ordinamento BWAF multicandidata. |
| S02 | 15.3 | Prima candidata accettata | Parziale | Controllo reale baseline 2: prima AI accettata semanticamente. | Accettazione per riflessivita resource=request; nessuna accettazione applicativa C1/C4. |
| S03 | 15.3 | Candidata condizionata | Disponibile, circoscritta | C1 e C4 completi fino a finalizzazione: abduzione 38 e decisione condizionata. | Policy e capacita testuali non equivalgono alla semantica del rimedio. |
| S04 | 15.3 | Candidata rifiutata e fallback | Parziale | Baseline 1: Automated rifiutata, Blockchain e ZeroTrust condizionate, AI accettata. | Traversal semantico di valutazione; nessun fallback applicativo del MAS con contesto operativo. |
| S05 | 15.3 | Spiegazione di abduzione | Disponibile, circoscritta | Abduzione reale Logback: ipotesi non vuota, penalita 38 in tre repliche. | Differenze di classi contestuali non sono automaticamente capacita operative mancanti. |
| S06 | 15.3 | Spiegazione Bonus | Disponibile, circoscritta | AnalyzeOntology: Bonus Surplus ObservedSoftwareAsset, Incentive 1 in tre repliche reali. | Diagnostica low-level; ExplainAffinity applicativo mantiene bonusEvaluated=false. |
| S07 | 15.3 | Spiegazione di contrazione | Disponibile, circoscritta | Clash esplicito baseline: contrazione invocata, Give up e Keep, penalita 2 in tre repliche. | C1 compatibile non invoca contrazione; zero restituito non e misura di quel ramo. |
| P01 | 15.4 | Latenza ingestione telemetria | Parziale | Tre timer collect_telemetry HTTP su export SDK gia raccolto. | Non misura acquisizione originale SDK o tempo evento-decisione. |
| P02 | 15.4 | Latenza estrazione asset | Disponibile, circoscritta | Tre step isolati TelemetryAgent reale: 71.0861, 56.6689, 57.3705 s. | Esclude manager e altri worker; non coincide con timer della sola estrazione deterministica. |
| P03 | 15.4 | Latenza matching vulnerabilita | Disponibile, circoscritta | Timer assess_software nei launcher e confronto inventario, stesso tool CTI reale. | Chiamata MCP aggregata, non intero VulnerabilityAgent. |
| P04 | 15.4 | Latenza generazione OWL | Disponibile, circoscritta | Due timer observed_asset_owl e due aln_projection nel generatore esistente. | Una osservazione per braccio, wrapper incluso; non generalizzare ad altre ontologie. |
| P05 | 15.4 | Latenza costruzione grafo | Disponibile, circoscritta | graph_build_and_kg_lookup: 8.54296 e 9.51791 s. | Include lookup KG e costruzione, non costo puro della topologia. |
| P06 | 15.4 | Latenza memorizzazione grafo | Disponibile, circoscritta | 30 StoreGraph MCP e 30 StoreGraph in memoria su input equivalenti. | Confini di trasporto/stato differenti; non puro costo scrittura ledger. |
| P07 | 15.4 | Latenza ranking | Disponibile, circoscritta | 30 RankGraph MCP, 30 stesso contratto in memoria; 15 ComputeRank isolati per interventi archi. | Tempi funzione diversi dai tempi di dominio; non mischiare la convenzione singola C1. |
| P08 | 15.4 | Latenza validazione semantica | Disponibile, circoscritta | validate_countermeasure MCP e AnalyzeOntology REST temporizzati. | Non tempo puro del reasoner: include client, peer e policy applicabile. |
| P09 | 15.4 | Latenza registrazione provenance | Parziale | Due nuove finalizzazioni reali con commit/rilettura e timer aggregato; C1/C4 preservati. | Costo di sola scrittura PROV-O non isolato dalla decisione atomica. |
| P10 | 15.4 | Durata end-to-end | Disponibile, circoscritta | C1-r2 1274.172, C2-r1 298.132, C3-r1 296.697, C4-r3 1224.254 s. | Un launcher primario per caso; input replay, teardown incluso; nessuna popolazione di E2E. |
| P11 | 15.4 | Overhead blockchain on-chain/off-chain | Disponibile, circoscritta | 30 confronti stesso core/output; 15 coppie REST RankGraph invoke/evaluate con stato controllato. | Differenza include percorsi client/stato/endorsement/commit, non puro consenso. |
| A01 | 15.5 | Con e senza evidenza runtime | Parziale | Coppia replay con inventario/CTI fissi, grafo OWL ALN identici; confronto sorgenti 1 osservato su 14 dichiarati. | Nessuna ablation dell intero CAMEL; modalita reale richiede OTel; mancata osservazione non prova assenza. |
| A02 | 15.5 | Prima e dopo validazione semantica | Disponibile, circoscritta | Confronto sugli stessi artefatti: proposta S_UPGRADE rango 1, semantica condizionata, policy review, selected nullo. | Confronto descrittivo prima/dopo; non due workflow con validazione disabilitata. |

## Chiusura e limiti della proposta

Misure, confronti disponibili e dossier riproducibile sono completati. Restano
dichiarati: campione assistito senza annotatore umano indipendente, pesi iniziali
dei nodi non esposti, spiegazioni parziali, assenza di accepted/fallback su asset
reale, ablation limitata al confine degli artefatti, ingestione SDK originale e
sola scrittura PROV-O non isolate. Il prototipo non comprende un ThreatAgent
separato o tutti i nodi contestuali runtime proposti. Queste non sono misure
da trasformare in successi tramite nuove regole.

La [matrice di conformita e contributi](conformita-proposta.md) distingue il
prototipo dalla proposta e dalle baseline. La [procedura finale](riproduzione-finale.md)
distingue ricalcolo offline, demo mock e demo reale. La relazione Word manuale
non e stata modificata; i testi e le tabelle qui sono pronti per il suo uso.
Le modifiche locali vanno ancora selezionate e registrate in commit prima
della consegna: nessun commit o push eseguito in questa fase.
