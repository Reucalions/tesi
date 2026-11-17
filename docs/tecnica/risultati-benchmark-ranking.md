# Risultati del benchmark del ranking nativo

## Aggiornamento dopo la correzione: 13 novembre 2026

Il difetto di associazione osservato sotto e ora corretto nell'output adattato
del chaincode esistente. [Nuova implementazione e campagna](correzione-spiegazioni-native.md):
30/30 prove, 60/60 cammini associati alla candidata corretta, score/pesi invariati,
60 commit VALID e 30 output originali/audit con digest verificati. Nessuna
modifica del core nativo; i dati del 12 novembre restano conservati.

Rimangono against positivo, copertura parziale e cammini validi diversi nei
riordinamenti: solo 6/15 coppie hanno explanation identiche per label. Le tabelle
e i conteggi successivi descrivono esclusivamente la campagna del 12 novembre.

Campagna del 12 novembre 2026: **30/30 prove tecniche concluse**, cinque coppie
di grafi esistenti da 6 a 40 nodi, tre repliche per originale e riordinato,
tramite MCP stdio, SaaS e Fabric reali. Nessuna modifica ai componenti esterni.
Protocollo e ingressi congelati prima delle misure; nessuna esclusione o retry.

**Punteggi e pesi identici in 45/45 confronti**, con scarto numerico massimo zero.
Sono 30 confronti fra repliche e 15 fra originale/riordinato. Insieme dei massimi
stabile; nei casi grandi sono presenti pareggi o differenze entro 1e-6.
Non equivalgono a strategie accettate semanticamente. Tutti i 60 commit sono
VALID (blocchi 29–88), con write set verificati; 30/30 riletture complete da una
nuova sessione dopo ripristino del container originale.

## Tempi osservati

Millisecondi; ogni mediana RankGraph ha tre repliche. Store e somma cinque
chiamate aggregano sei osservazioni per grafo.

| Grafo | Nodi/archi | Store mediana | Rank originale mediana | Rank riordinato mediana | Rank min–max | Somma cinque chiamate mediana |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline-1 | 6/11 | 70.96 | 122.05 | 120.73 | 108.63–177.10 | 208.78 |
| baseline-2 | 8/20 | 71.19 | 152.28 | 155.52 | 140.06–160.42 | 242.13 |
| baseline-3 | 12/21 | 73.21 | 135.39 | 134.77 | 129.61–138.43 | 231.87 |
| baseline-4 | 24/43 | 76.00 | 181.24 | 190.21 | 178.34–203.10 | 280.99 |
| baseline-5 | 40/75 | 77.12 | 266.15 | 294.40 | 258.91–295.71 | 387.21 |

Sono tempi delle chiamate MCP complete: bridge/REST, caricamento OWL/core e
consenso Fabric. Non sono tempi puri C++ o overhead blockchain isolato. La somma
delle cinque chiamate non e il tempo del launcher multiagente. Prima StoreGraph
332,21 ms, incluso costo iniziale; nessun warm-up escluso. Corpus piccolo,
topologie diverse, host arm64 con immagine amd64: nessuna generalizzazione
statistica o conclusione sulla complessita asintotica.

## Limite emerso sulle spiegazioni

**Il ranking numerico e stabile, ma l'output completo non e invariante.**
Tutti i 60 cammini hanno archi orientati e prodotti corretti. Nei 30 cammini
degli originali la destinazione coincide con la candidata spiegata; nei 30 dei
riordinati la spiegazione e associata a un'altra candidata. Esempio baseline-1
riordinato: explanation sotto BlockchainCountermeasure, cammino verso
AutomatedCountermeasure. Il controllo completo passa per 15/15 originali e
fallisce per 15/15 riordinati. Nessuna rimappatura o correzione del core applicata.

Soltanto 30/186 occorrenze di candidate hanno cammini espliciti. Rimane anche
il limite su against: 12/60 cammini hanno etichetta against e prodotto positivo.
L'ipotesi di un problema interno di associazione/serializzazione non e una causa
attestata, perche Graph.cpp manca. L'equivalenza al paper resta non dimostrata.

## Copertura delle metriche della proposta

| ID | Esito attuale |
| --- | --- |
| R01 | Punteggi e pesi identici in 15/15 confronti originale/riordinato; output completo non invariante per le spiegazioni. |
| R02 | 30/30 grafi/ranking/annotati riletti dopo ripristino del processo; 60 commit VALID e write set corrispondenti. |
| R03 | 30/30 confronti fra repliche con stesso punteggio e insieme dei massimi; pareggi dichiarati. Nessuna accettazione semantica implicata. |
| R04 | Non valutata: il contratto esistente espone ID/tipi ed estremi, non pesi numerici modificabili. |
| R05 | Cinque dimensioni, sei osservazioni per dimensione (tre per rappresentazione); tempi descrittivi sul corpus fissato. |
| R06 | Prodotti e archi validi 60/60; associazione candidata valida 30/60. Limite aggiuntivo dei riordinamenti e 12/60 disaccordi con il segno semplice. |
| P06 | Latenza MCP StoreGraph osservata, incluso consenso/autenticazione quando necessari; tempo puro di scrittura non isolato. |
| P07 | Latenza MCP RankGraph nativa multi-candidata osservata, inclusi OWL/reasoner e consenso; C++ puro non isolato. |
| P11 | Non misurato: manca il percorso off-chain equivalente; nessuna sottrazione dal mock. |

Usata l'ontologia baseline originale (SHA 688c1944…), selezionata temporaneamente
nella stessa immagine immutabile del chaincode. Il container Logback originale e
ripristinato, con ID/binario/ontologia identici; questa serie non dimostra ranking
multi-candidata sull'ontologia generata C1/C4. Riletti anche C1 e le due
finalizzazioni C4: record/provenance/ricevute identici. 1.336 file protetti invariati,
repository esterni su costa-thesis, nessun reset di rete o test SaaS nello store live.
Dodici test del raccoglitore e Ruff passati.

[Report completo](../../output/native-ranking-benchmark-20261112-r1/report.md),
[protocollo](../../output/native-ranking-benchmark-20261112-r1/protocol.json),
[metriche JSON](../../output/native-ranking-benchmark-20261112-r1/metrics.json),
[latenze CSV](../../output/native-ranking-benchmark-20261112-r1/latencies.csv),
[diagnosi delle spiegazioni](../../output/native-ranking-benchmark-20261112-r1/explanation-diagnostics.json),
[verifica dei commit](../../output/native-ranking-benchmark-20261112-r1/ledger-commit-proofs.json).
Il [raccoglitore](../../evaluation/run_ranking_benchmark.py) riusa fixture,
contratti e procedura di deployment esistenti; svolge solo misura e audit.
L'inventario dell'8 novembre resta la fotografia storica: non ne cambiano i
conteggi per effetto di questa nuova campagna.
