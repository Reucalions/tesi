# Correzione dell'associazione delle spiegazioni native

Implementata e verificata il 13 novembre 2026 nel chaincode esistente su
costa-thesis. Nessun nuovo agente, servizio, tool MCP o algoritmo di ranking.

| Proprieta | Prima (12 novembre) | Dopo (13 novembre) |
| --- | ---: | ---: |
| Prove native completate | 30/30 | 30/30 |
| Confronti score/pesi identici | 45/45 | 45/45 |
| Archi e prodotti dei cammini validi | 60/60 | 60/60 |
| Cammini associati alla candidata raggiunta | 30/60 | 60/60 |
| Prove con tutte le associazioni valide | 15/30 | 30/30 |
| Cammini against con prodotto positivo | 12/60 | 12/60 |
| Occorrenze di candidate con cammini espliciti | 30/186 | 30/186 |

La modifica risiede nel chaincode Go esistente `chaincode-argumentation`, sul
branch costa-thesis. Il punto RankGraph applica il controllo al JSON restituito
dal core e salva i dati nella stessa transazione Fabric. Non vengono creati
agenti, servizi, tool MCP o algoritmi di ranking.

Il controllo richiede nodi/label e candidate univoci, corrispondenza della topologia
con l'ingresso, pesi finiti in [-1,1], cammini orientati esistenti e prodotto
entro tolleranza assoluta 1e-5. Tutti i cammini della stessa spiegazione devono
concordare su un'unica candidata raggiunta. Due spiegazioni concorrenti sulla
stessa destinazione sono considerate ambigue, senza sovrascritture o fusioni.

L'associazione cambia soltanto quando la destinazione e verificata senza
ambiguita. Score, nomi e ordine delle candidate, nodi, archi, pesi, cammini,
prodotti e categorie favor/against restano quelli nativi. Una spiegazione non
validabile e esclusa dal ranking esposto e segnalata nell'audit con il motivo;
rimane integralmente nell'output originale. `validated` riguarda questi controlli,
non la correttezza matematica dell'intero algoritmo o l'accettazione semantica.

| Chiave ledger | Contenuto |
| --- | --- |
| `<graphKey>_native_output` | Stringa JSON esatta restituita dal core, prima dell'associazione |
| `<graphKey>_explanation_audit` | Metodo, digest del JSON originale, chiavi, esiti e motivi |
| `<graphKey>_rank` | Ranking esistente con associazioni verificate |
| `<graphKey>_annotated_graph` | Grafo nativo invariato |

Le quattro chiavi sono scritte dalla stessa transazione RankGraph. L'audit usa
`native-explanation-destination-v1`, con stato validated, unvalidated oppure
no_explanations; le singole associazioni valide sono unchanged o reassociated.
Il JSON originale e verificabile tramite raw_output_sha256, senza riserializzarlo.

La convenzione Bottalico a candidata singola resta separata dal core e invariata.
Se una chiave gia usata per il nativo viene riutilizzata per la candidata singola,
le vecchie evidenze native vengono eliminate, per non farle apparire correnti.
I record storici di questa campagna e delle precedenti non sono riscritti.

## Esiti e limiti

Nuovo benchmark MCP/Fabric con tre repliche per cinque originali/riordinati:
30/30 prove riuscite, 15 associazioni riordinate corrette e 15 originali
conservate, 60/60 cammini verificati. Score, ordine delle candidate e grafi
identici agli output nativi e alla campagna precedente. 60 commit VALID nei
blocchi 89–148, 30 riletture indipendenti e 30 digest nativi verificati.

Diciassette test Go principali con sottocasi passati, inclusi dieci output
reali archiviati e i casi ambigui/malformati. Verificata anche la convenzione
singola in un controllo live separato. C1/C4-r2/C4-r3 riletti identici; 1.662
file precedenti protetti invariati. Nessuna suite SaaS nello store live.

La correzione chiude il difetto di associazione nei casi verificati. L'invarianza
dell'intera explanation non e garantita: solo 6/15 confronti originale/riordinato
hanno spiegazioni identiche dopo aver normalizzato gli indici tramite le label.
Sono i casi 1 e 2; nei casi 3–5 puo variare il cammino scelto o la candidata a
cui il core fornisce una prova. Per esempio nel caso 3 il favor raggiunge la
stessa candidata con lo stesso prodotto, ma parte da una vulnerabilita diversa.
Entrambi i cammini sono presenti e validi. Non si sceglie artificialmente un
cammino comune per ottenere uguaglianza.

Rimangono 12 cammini against con prodotto positivo, e 156/186 occorrenze di
candidate senza cammini espliciti. Non vengono rinominate categorie o inventate
spiegazioni mancanti. Graph.cpp non disponibile e corrispondenza al paper non
attestata: questa e una verifica/adattamento dell'output, non una patch interna
della libreria. Sensibilita ai pesi impostabili, overhead off-chain equivalente
e ablation runtime restano non misurati.

La serie usa l'ontologia baseline originale, distinta dalla proiezione Logback
C1/C4; non dimostra ranking multi-candidata sulla proiezione generata per quei
casi. Tempi MCP comprendono bridge/REST, controlli, salvataggio di JSON/audit,
caricamento OWL/core e consenso. Non isolano il C++ e non dimostrano accelerazioni
rispetto al 12 novembre: campioni piccoli e lavoro aggiuntivo esplicitamente diverso.

Il nuovo binario resta attivo con l'ontologia Logback originale; il container
precedente e conservato per rollback. I sorgenti esterni sono esclusivamente
su costa-thesis. SHA binario: `272f2780a2b83b019bd24e39680805355232244989e65f49b516597f8311ff92`.
L'assurance SaaS non e aggiornata artificialmente a verified=true: l'impronta
effettiva e verificata separatamente.

## Dove verificare

- [Report dell'implementazione](../../output/native-explanation-fix-20261113-r1/report.md).
- [Nuova campagna completa](../../output/native-explanation-benchmark-20261113-r1/report.md).
- [Verifiche e conteggi](../../output/native-explanation-benchmark-20261113-r1/verification.json).
- [Audit e digest originali](../../output/native-explanation-benchmark-20261113-r1/adapter-verification.json).
- [Diagnosi dei cammini](../../output/native-explanation-benchmark-20261113-r1/explanation-diagnostics.json).
- [Protocollo](../../output/native-explanation-benchmark-20261113-r1/adapter-protocol.json).
- [Benchmark precedente conservato](../../output/native-ranking-benchmark-20261112-r1/report.md).

Per R06 la corrispondenza cammino–candidata e verificata nel corpus; restano
parziali copertura e interpretazione semantica delle spiegazioni. R01/R03
confermano i punteggi, non l'uguaglianza dell'intero oggetto explanation.
