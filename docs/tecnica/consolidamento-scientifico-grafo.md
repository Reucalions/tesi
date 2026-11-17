# Contratto scientifico del grafo e della validazione semantica

## Associazione corretta, limiti mantenuti: 13 novembre 2026

Applicato nel chaincode Go esistente un controllo/adattamento dei cammini
nativi, con output originale e audit conservati. [Verifica corrente](correzione-spiegazioni-native.md):
30/30 prove, 60/60 destinazioni coerenti con la candidata, score/pesi invariati,
60 commit VALID. Nessuna modifica della libreria o dell'algoritmo.

Rimangono significato di against e scelta dei cammini/candidata spiegata sensibile
all'ordine; solo 6/15 coppie con explanation identiche per label. Non si attesta
invarianza completa, copertura di tutte le candidate o equivalenza al paper.
Le sezioni sotto conservano lo stato precedente e i criteri scientifici originari.

## Aggiornamento live: benchmark del 12 novembre 2026

La campagna ora eseguita e descritta nei [risultati del benchmark](risultati-benchmark-ranking.md):
30 prove, cinque coppie con tre repliche, punteggi e pesi identici nei 45 confronti,
60 commit VALID e 30 riletture indipendenti. Ontologia baseline originale e
binario effettivo fissati, con ripristino del container Logback a fine raccolta.

Le spiegazioni non superano il controllo completo nei riordinati: 30 cammini
associati a una candidata diversa dalla destinazione, pur con archi/prodotti
corretti. L'ambiguita against resta presente. Quindi i punteggi sono invarianti,
mentre l'oggetto completo non lo e; nessuna attestazione della libreria al paper.
Le sezioni successive conservano analisi e criteri del 5 novembre: le indicazioni
di esecuzione live ancora pendente sono superate nei soli limiti di questa serie.

Revisione del 5 novembre 2026. Questo documento fissa il significato della
rappresentazione utilizzata, le aspettative indipendenti e i controlli riproducibili.
Il consolidamento offline non equivale a una validazione numerica del motore nativo:
questa resta nel collaudo live previsto a fine progettazione.

## 1. Fonti e perimetro

Sono stati riletti la proposta di tesi, i due repository locali, la storia dei
file di grafo/proiezione e i risultati e2e gia versionati. La ricerca locale non
ha individuato `Graph.cpp`: sono disponibili `Graph.h`, wrapper Go/C++ e
`libgraph.so`. Il binario e ELF Linux x86-64; hash e revisioni sono fissati nel
[catalogo dei casi](../../config/scientific-graph-cases.v1.json).

Il riferimento teorico pertinente e **Fasciano et al., 2025**, *A propagation-based
ranking semantics in Explainable Bipolar Weighted Argumentation*, DOI
[10.1016/j.engappai.2024.109767](https://doi.org/10.1016/j.engappai.2024.109767).
Sono state lette le sezioni 4–5 del PDF degli autori. In quel modello un arco va
nell'orientamento dell'interazione fra annotazioni: sorgente come risorsa S,
destinazione come richiesta R. Il confronto logico determina supporto o attacco e
peso con segno; il prodotto dei pesi valuta un cammino. I nodi free non hanno archi
entranti, quelli connected ne hanno almeno uno. Il ranking nativo e reale, con
neutralita iniziale 1; non e una probabilita. [Postprint](https://sisinflab.poliba.it/publications/2025/FLPRS25/Fasciano_et_al_EngAppAI2025_preprint.pdf).

Le firme locali `computeW_att`, `computeW_supp`, `calculateSP` e
`newCalculateRank_new` sono coerenti con questo ambito, ma non provano che il
binario implementi esattamente versione, parametri, normalizzazione e arresto del
paper. La corrispondenza va attestata prima di attribuirgli quelle proprieta.
I riferimenti generali sulle [semantiche modulari](https://arxiv.org/abs/1807.06685)
non autorizzano a imporre una scala [0,1] al nostro ranking o a sostituirne la formula.

## 2. Che cosa rappresenta il grafo attuale

Il checkpoint Bottalico per una CVE contiene un nodo vulnerabilita e gli individui
Solutions/Workarounds esplicitamente collegati dal KG. Gli ID MAS sono associati
agli individui KG mediante binding dell'operatore. Ogni arco ha un'origine:
`kg_remediation` per CVE -> strategia; `generator_comparison_ring` per l'anello.

Il JSON nativo trasporta soltanto `id/type` e `from/to`. La presenza di un arco non
ne dichiara gia il segno. `hasSolutions`/`hasWorkarounds` giustificano il collegamento
di pertinenza, non assegnano automaticamente un peso positivo. La classificazione
bipolare e i pesi spettano al core e alle descrizioni OWL effettivamente caricate.
Gli eventuali campi aggiuntivi di peso nel JSON non costituiscono un'integrazione:
il contratto Go serializza solo i campi riconosciuti.

La direzione esprime quale argomento riceve influenza, non la relazione operativa
"questa azione mitiga quella CVE". Per valutare una strategia nel modello citato,
la strategia deve ricevere informazione contestuale. Il generatore e la proposta
usano CVE -> strategia. Il costruttore SaaS legacy, quando manca un grafo esplicito,
usa strategia -> CVE: non e equivalente. Il percorso MAS canonico trasmette sempre
il grafo esplicito e non dipende da quel fallback, che non viene qualificato come
baseline scientifica di questo percorso.

Free e connected sono ruoli topologici, non sinonimi dei valori di `type`.
Un'etichetta `strategy` non rende connected un nodo senza ingressi. Allo stesso
modo, un artefatto OTel conservato nella provenance non diventa automaticamente
un nodo di evidenza del BWAF.

La proposta, sezioni 5.1–5.3, contempla anche runtime, pacchetti, endpoint e vincoli
come argomenti contestuali. Attualmente il checkpoint canonico produce solo CVE e
strategie. Runtime e vincoli contribuiscono a selezione delle CVE, tracciabilita e
validazione operativa; non sono argomenti indipendenti del ranking. Questo e un
limite di copertura rispetto al disegno completo, da mantenere esplicito.

## 3. Anello: determinismo e limite di interpretazione

Il profilo resta `bottalico-directed-ring-v1`, gia fissato e confermato. L'anello
ordina gli individui per ID, evita nodi terminali e limita l'espansione dei cammini
secondo il commento del generatore. Questa motivazione tecnica non documenta
interazioni osservate fra azioni, incompatibilita operativa o preferenza.

Riordinare gli array JSON con gli stessi identificativi e gli stessi archi conserva
il grafo. Riassegnare etichette a concetti equivalenti puo invece cambiare l'anello
perche cambia l'ordine lessicografico. Un controesempio a quattro strategie e
registrato in [ring-invariance.json](../../output/scientific-consolidation-20261105/ring-invariance.json).
Dimostra un cambiamento della topologia, non che il ranking sia effettivamente
cambiato: quest'ultimo richiede il motore. La canonicalizzazione sintattica non e
una prova di anonimato o invarianza semantica.

L'anello viene quindi qualificato come **policy sperimentale di confronto**.
Non si aggiungono qui relazioni di dominio o pesi per motivarlo retroattivamente.
Prima di usarlo per conclusioni applicative bisogna confrontarlo con relazioni
giustificate da fonti e verificare il comportamento del core anche sui nodi terminali.

## 4. Profili ALN e potere discriminante

Riutilizzando il parser originale della proiezione si e verificato che le quattro
candidate della demo canonica hanno **la stessa descrizione asserita**. Il builder
copia su ciascuna Solutions il contesto CVE, prodotto, vendor, CWE e metriche.
Non ne deriva requisiti di esecuzione, effetti o costi specifici dell'azione.
Questo confronto sintattico e sufficiente per rilevare la duplicazione; non e
una nuova implementazione di equivalenza DL.

Questa demo puo verificare trasporto, simmetria e scelta dopo i vincoli, ma non
puo dimostrare che il ranking sappia preferire un upgrade a un isolamento.
Con profili identici e un anello simmetrico, la rotazione delle strategie conserva
grafo e descrizioni. Una semantica indipendente dalle etichette deve quindi dare
un pareggio fra tali strategie. E l'aspettativa qualitativa indipendente del caso
simmetrico; non viene inventato uno score numerico. Lo spareggio per ID nel SaaS
serve alla ripetibilita e non dimostra superiorita semantica.

La proiezione attuale usa, per ogni dimensione CVSS proiettata, la coppia
`ObjectSomeValuesFrom(r owl:Thing)` e `ObjectAllValuesFrom(r C)`.
Questa combinazione rende esplicita anche l'esistenza di un filler. Un universale
da solo non la impone: non si puo dedurre un conflitto soltanto da due universali
con range disgiunti quando il ruolo puo essere vuoto. Nella baseline ontologica
sono presenti anche restrizioni universali dirette; non vanno interpretate come
misure osservate o requisiti esistenziali impliciti.
[OWL 2 Direct Semantics, 2.2.3](https://www.w3.org/TR/owl2-direct-semantics/#Class_Expressions).

Un clash esplicito di classi fornisce invece un'aspettativa locale controllabile:
`AIBasedCountermeasure` e `AutomatedCountermeasure` sono disgiunte e asserite nei
rispettivi individui della baseline. Il loro confronto e incompatibile rispetto
a quegli assiomi. Per l'arco Automated -> AI del caso 1 si attende quindi un attacco
se il core adotta il mapping del riferimento. La semplice assenza di un clash
sintattico non viene usata per certificare compatibilita o supporto.

## 5. Scale e significati da mantenere distinti

| Quantita | Contratto | Interpretazione |
| --- | --- | --- |
| Peso di relazione BWAF | Nativo con segno, in [-1,1] | Influenza dell'arco; il valore zero resta neutro/non classificato |
| Score del ranking | Reale finito nativo, anche fuori [0,1] | Accettabilita secondo il core; nessun clamp o conversione in probabilita |
| Score ExplainAffinity v1 | [0,100] | Funzione del chaincode user-registry, distinta dai pesi BWAF |
| affinityScore SaaS | Score ExplainAffinity / 100 | Conversione di scala, non probabilita e non ranking |
| Stato semantico | accepted / requires_prerequisites / rejected | Compatibilita e condizioni del confronto richiesto |
| Stato operativo | Policy SaaS esplicita | Capacita, divieti e vincoli; separato da Tiny-ME |
| UnitScore del mock | [0,1] | Contratto dimostrativo separato; non formula del core |

Il codice `calculateScore` di ExplainAffinity v1 usa la penalita di abduzione se
positiva, altrimenti quella di contrazione, e calcola `max(0, 100 - penalita)` per
penalita non negative. I parametri storici `gWeight/hWeight` non partecipano al
calcolo corrente. Questa funzione non implementa le formule dei pesi BWAF del paper.
Backend e client verificano ora anche la corrispondenza score/penalita, con tolleranza
assoluta 1e-9, oltre alla conversione /100 e alla coerenza degli stati.

Il percorso ExplainAffinity cached e quello uncached richiedono un'unica penalita
numerica finita e non negativa nell'output nativo. Campo mancante, duplicato o
malformato produce un errore tecnico. Non viene convertito nella penalita 100 e
poi in un rifiuto semantico. Il parser di discovery legacy resta separato: questi
controlli riguardano il percorso di validazione usato dal framework.

Nel confronto Tiny-ME l'asset e la risorsa, la contromisura la richiesta. Gli header
Tiny-ME locali confermano l'ordine resource/request delle API. La verifica live
deve accertare che gli individui caricati descrivano davvero capacita disponibili
e requisiti dell'azione. La sola presenza dell'IRI non lo dimostra. L'ABox osservata
Bottalico collega software, affected e version statement; non costituisce da sola
un profilo completo delle capacita operative. I vincoli testuali non diventano
assiomi DL automaticamente; le mappature operative restano nella policy SaaS.

## 6. Cinque casi riutilizzati e aspettative indipendenti

| Caso | Nodi | Archi | Coppia riordinata equivalente | Archi con clash diretto documentabile |
| --- | --- | --- | --- | --- |
| 1 | 6 | 11 | Si | 1 |
| 2 | 8 | 20 | Si | 4 |
| 3 | 12 | 21 | Si | 2 |
| 4 | 24 | 43 | Si | 3 |
| 5 | 40 | 75 | Si | 3 |

Tutti gli ID hanno dichiarazione di individuo e class assertions nell'ontologia
della baseline. Le cinque coppie hanno gli stessi insiemi di nodi/tipi e archi
orientati. La correzione precedente del caso 4 e conservata; corretta anche la
tabella residua `client/tests.md`, che indicava ancora 10 archi per il caso 1.

Il catalogo JSON fissa hash di input, ontologia, libreria e generatore, archi con
prova di clash e proprieta attese. Gli score numerici attesi restano `null`:
non sono ottenuti copiando il primo output del servizio.

I cinque grafi possono contenere piu CVE e sono benchmark del core nativo. Non
vanno presentati come cinque richieste MAS a singola CVE con binding gia risolti.
Il checkpoint canonico continua a separare le decisioni per CVE.

I risultati storici S/M/L dei nove run upstream sono osservazioni, non oracle:
il rapporto distingue risultati etichettati MCP e scorciatoie locali a score 1.
Non certificano disponibilita attuale, identita del binario distribuito o
correttezza matematica. Nel run L/1, due Workarounds di CVE-2024-8695 hanno le
stesse class expressions asserite ma posizioni diverse nel grafo e score registrati
0.9962096214 e 0.9964718819. Non e una prova di effetti diversi delle azioni:
le relazioni di contesto e la topologia contano, e non sono giustificate dal solo
ID. [Osservazione riproducibile](../../output/scientific-consolidation-20261105/historical-position-observation.json).
I conteggi sono in
[historical-ranking-observations.json](../../output/scientific-consolidation-20261105/historical-ranking-observations.json).

## 7. Controlli corretti nel client di test esistente

Il confronto precedente verificava solo `(score1 - score2) > 1e-6`: poteva quindi
accettare una differenza nell'altro verso. Il probe della baseline fallisce su
questo caso; la versione corretta usa lo scarto assoluto e non modifica gli input.
Rifiuta ranking vuoti, nomi duplicati, score mancanti e non finiti.

Il test delle permutazioni richiede ora prima che gli input siano lo stesso grafo.
Non confonde una topologia differente con un riordinamento, non ignora errori di
lettura e non certifica determinismo confrontando due risultati mancanti.
Senza il secondo file il test e dichiarato skipped.

Il grafo annotato richiede ID/label univoci, estremi esistenti e pesi finiti nei
limiti: una label mancante genera un fallimento controllato, non un nil dereference.
Per le explanation fornite vengono verificati cammini orientati esistenti,
destinazione corretta, prodotto dei pesi e segno favor/against. La tolleranza sul
prodotto e assoluta 1e-5, per la rappresentazione float nativa. Le candidate prive
di explanation vengono contate esplicitamente: nessuna copertura completa inventata.

Questi controlli verificano le prove restituite. Non ricalcolano il ranking e non
certificano C2, fading, parametri o criteri di arresto del core. Anche il formato
degli indici dei cammini deve essere confermato nel collaudo live: nessun offset
viene indovinato per far passare il test.

## 8. Criteri per chiudere la verifica numerica a fine progettazione

1. Identificare versione/build del core, disponibilita dei sorgenti o attestazione
   del fornitore e relazione con il paper; fissare hash, parametri e ambiente.
2. Confermare che il file OWL realmente caricato dal ranking corrisponda alla
   proiezione prevista. Il digest dell'ALN generato e diverso dall'ontologia fissa
   `onto/client_final_ontology.owl`; avere entrambi su disco non prova il binding.
3. Eseguire i cinque casi originali/riordinati tramite il client esistente e il
   servizio condiviso. Confrontare per label, non per indice dipendente dall'ordine.
4. Controllare i clash previsti, il caso simmetrico, score, cammini e prodotti;
   aggiungere casi di supporto/incompatibilita con assiomi espliciti e documentati.
5. Verificare nodi terminali, una sola strategia, pareggi e perturbazioni di
   contesto. Non usare la scorciatoia locale score 1 come prova del core.
6. Confrontare la policy dell'anello con relazioni giustificate nel dominio e
   attestare l'effettiva copertura delle evidenze runtime nel ranking.

## 9. Estensione semantica distinta, da decidere

Per dimostrare una preferenza fra azioni servono descrizioni diverse e tracciabili:
requisiti, effetti attesi, incompatibilita e fonti per ciascuna candidata, non la
sola ripetizione del contesto CVE. Va inoltre giustificato quali coppie interagiscono.

L'ispezione non ha trovato un modulo disponibile che produca gia questi profili:
l'LLM individuato estrae asset, mentre il proiettore riusa il contesto. Una possibile
estensione riuserebbe parser, binding e reasoner esistenti, aggiungendo un manifesto
curato di requisiti/effetti e relazioni con riferimenti alle fonti. Non assegnerebbe
pesi a mano. Schema e fonti vanno concordati prima di introdurre nuova conoscenza,
in rispetto della richiesta dell'utente di autorizzare componenti mancanti.
Questa estensione non e stata implementata nel consolidamento corrente.

[Report delle verifiche](../../output/scientific-consolidation-20261105/report.md),
[registro fonti](../riferimenti/README.md), [roadmap](../prossime-azioni.md).
