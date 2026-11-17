# Stato del progetto

## Nuova estensione richiesta: ispezione conclusa — 16 novembre 2026

Disponibile l'[analisi D3FEND, testbed multi-tenant e conoscenza condivisa delle strategie](tecnica/ispezione-d3fend-conoscenza-condivisa.md),
con verifica delle revisioni remote di Principe e stima di effort. Sono proposte
di integrazione, non nuove funzioni già implementate o collaudate. La valutazione
e il report esistenti rimangono invariati; la chiusura sotto riguarda quel perimetro.

## Chiusura della valutazione — 13 novembre 2026

Raccolta e consolidamento conclusi nel perimetro concordato. Disponibili
[risultati finali](tecnica/valutazione-finale.md),
[matrice rispetto alla proposta](tecnica/conformita-proposta.md) e
[procedura riproducibile](tecnica/riproduzione-finale.md).
32 criteri aggiornati nel catalogo v2, 227 timer, 45 confronti appaiati,
3293 file inventariati. Risultati e ingressi compatti conservati in evaluation/final-results-v1.
Nuove prove: archi, off-chain nativo equivalente, evaluate/invoke, diagnostiche
semantiche e confronti runtime/prima-dopo validazione. Cinque finalizzazioni
rilette identiche. C1/C4 completi tecnicamente ma condizionati, nessuna azione.

Non e conformita integrale: riferimento assistito, pesi nodi non esposti,
nessuna accepted/fallback applicativa, spiegazioni parziali, ablation circoscritta,
ThreatAgent e nodi runtime espliciti mancanti. Nessuna nuova estensione o modifica
produttiva in questa fase; DOCX intatti e modifiche ancora da committare.
Gli aggiornamenti sotto sono cronologia e non sostituiscono il report finale.

## Correzione delle spiegazioni verificata: 13 novembre 2026

Distribuito l'adattamento nel chaincode Go esistente su costa-thesis: conserva
JSON nativo e audit con digest, e associa la spiegazione alla candidata raggiunta
solo dopo verifica di cammini/prodotti e destinazione univoca. Score, pesi,
ordine e libreria nativa invariati; nessun nuovo servizio/tool/agente.

Nuovo benchmark reale: 30/30 prove e riletture, 45 confronti con score/pesi
identici anche rispetto al 12 novembre, 60/60 cammini associati correttamente
(prima 30/60). Trenta digest nativi verificati, 60 commit VALID nei blocchi
89–148. Convenzione singola verificata separatamente, C1/C4 riletti identici,
1.662 file precedenti protetti invariati, diciassette test Go principali passati.

Restano against positivo e copertura parziale; l'intera explanation puo variare
nei riordinamenti (6/15 coppie identiche per label). Questo non riapre un cambio
del core: il task autorizzato di associazione e concluso nel corpus verificato.
Nuovo binario attivo con ontologia Logback, vecchio container conservato.
[Dettagli e limiti](tecnica/correzione-spiegazioni-native.md).
Le sezioni sotto conservano cronologia e benchmark precedente.

## Benchmark nativo concluso: 12 novembre 2026

30/30 prove tecniche su cinque coppie di grafi esistenti, tre repliche per input,
tramite MCP/Fabric reale. Punteggi e pesi identici in 45/45 confronti, massimi
stabili con pareggi espliciti. 60 commit VALID (blocchi 29–88), write set e
30/30 riletture indipendenti verificati dopo ripristino del container originale.

Limite sulle spiegazioni: archi e prodotti validi 60/60, associazione alla
candidata valida 30/60; tutti i 15 riordinati falliscono questo controllo pur
conservando score identici. Rimane against positivo in 12 cammini. Nessuna
correzione del core o estensione semantica. Tempi MCP nativi misurati su 6–40
nodi, non C++ puro; sensibilita ai pesi e overhead equivalente non misurati.

Usata temporaneamente l'ontologia baseline nella stessa immagine del core;
container Logback ripristinato, rete/ledger conservati. 1.336 file protetti e
record/provenance/ricevute C1/C4 invariati. Esterni costa-thesis, nessuna suite
SaaS nello store live. [Risultati e limiti](tecnica/risultati-benchmark-ranking.md).
Le sezioni sotto conservano gli stati storici, incluso il benchmark allora aperto.

## C4-r3: launcher integrale riuscito, 12 novembre 2026

C4-r3 ha completato tutti gli otto nodi del DAG originale nello stesso launcher
real/camel/pipeline: exit code 0, `dry_run_completed`, finalizzazione condivisa
`completed`, senza riprese da checkpoint esterni. Durata 1224,254 s, timeout
LLM 600 s. Restano tracciati i recuperi automatici CAMEL su qualita e binding.

Nuovo commit nel blocco 28, validation_code=0; verificati rilettura indipendente
MCP, record/provenance/ricevuta, grafi, digest e rinnovo credenziali. Salvati i tre
metadati SaaS reali; 789 file precedenti e metadati live C1/C4-r2 invariati.
Nessuna modifica dei componenti o della semantica.

Esito `requires_prerequisites`, nessuna candidata selezionata o applicata:
maintenance_window mancante, oltre al prerequisito testuale non riconciliato
`package_upgrade capability`; `package_upgrade` e disponibile. Tiny-ME abduzione
38, score 62. Il successo tecnico non attesta una contromisura accettata o un fallback.
[Report e limiti](../output/c4-collaudo-20261112-r2/report.md).
C1/C4 sono completi fino alla finalizzazione; C2/C3 restano assessment conclusi
con fasi native non applicabili. Le sezioni seguenti conservano gli stati storici.

## Ripresa della finalizzazione C4 verificata: 12 novembre 2026

C4-r2 ha completato sette nodi del DAG, poi e fallito per timeout Ollama dopo
il commit. Una ripresa CAMEL separata, con timeout LLM 600 s, ha completato
finalizzazione e rilettura con exit code 0, conservando lo stesso record e commit
nel blocco 25, validation_code=0. Il DAG originale resta failed: non e dimostrato
un unico launcher C4 end-to-end riuscito.

Esito `requires_prerequisites`, nessuna strategia selezionata; manca
`maintenance_window`. Tiny-ME abduzione 38, score 62. Verificati grafo canonico,
provenance, digest, rilettura indipendente MCP e rinnovo credenziali; salvati i
tre metadati SaaS originali. Nessuna modifica ai componenti o alla semantica.
[Report completo](../output/c4-collaudo-20261112-r1/report.md).
Le sezioni sotto conservano la cronologia; le metriche assistite restano separate.

## Metriche dei componenti calcolate: 12 novembre 2026

Sul campione v2 congelato: estrazione tramite identificatore OTel esistente,
precisione 87,50%, recall 70%, F1 77,78%, accuracy documentale 9/12. CTI reale
via MCP: matching 13/16 (81,25%), versione tre classi 10/13 (76,92%) e binaria
7/8 (87,50%). Nessun errore tecnico nelle 16 query e nei 12 documenti.
Riferimento assistito, senza revisione umana indipendente; due famiglie software.
Misura dei componenti, senza inferenza LLM o launcher completo. Nessuna modifica
di backend, etichette o semantica C1; C4 resta non completato.
[Report, discrepanze e limiti](tecnica/risultati-metriche-componenti.md).

## Revisione del campione: 12 novembre 2026

Su delega esplicita dell'utente, completata la [revisione tecnica v2](../evaluation/annotated-sample-v2/review-report.md)
dei 28 casi sulle fonti originali, con hash integrali OWL/SQLite ricontrollati e
33 campi grezzi concordanti. Nessuna etichetta o ingresso modificato; precisati
C08/C11/C16, significato delle categorie di matching e trattamento degli errori.
La v1 resta immutata. Campione congelato per una valutazione controllata con
riferimento assistito; revisione umana indipendente non effettuata e non attestata.
Non occorre far ripetere all'utente i controlli tecnici. Prossimo passo: raccolta
delle predizioni e metriche con i denominatori fissati; nessun punteggio ancora prodotto.

## Campione annotato: 12 novembre 2026

Preparata la [bozza v1](../evaluation/annotated-sample-v1/README.md): 12 documenti
per estrazione e 16 query per matching/versioni, con fonti SDK/OWL/SQLite, scheda
di revisione e denominatori espliciti. Quattro raccolte reali e otto variazioni
sintetiche sono distinte. Le annotazioni sono assistite e richiedono revisione
umana: nessun punteggio o nuovo esperimento e dichiarato. Il limite semantico
di C1 resta invariato; nessuna modifica ai backend o alle fonti originali.

## Inventario delle metriche: 8 novembre 2026

Completata la raccolta offline: 698 file con SHA-256, 32 requisiti della sezione 15
della proposta, 30 osservazioni temporali esplicite e 42 controlli di integrita
coerenti con gli archivi. Disponibili inventario, tabella di copertura e dati
JSON/CSV, con tentativi e riprese separati. Nessun nuovo run o accesso ai servizi.
Il limite semantico C1 resta nel perimetro concordato. Accuratezza su corpus
indipendente, repliche omogenee e confronti controllati rimangono da raccogliere.
[Risultati e lacune](tecnica/valutazione-metriche.md).

## Chiusura C1 verificata: 7 novembre 2026

C1-r2 ha completato il launcher reale CAMEL/Ollama e tutti gli otto nodi del DAG
con `dry_run_completed` e finalizzazione condivisa `completed`.
Esito decisionale: **requires_prerequisites**, con `selected_strategy_id=null`.
Tiny-ME restituisce abduzione 38 e score 62; il controllo operativo restituisce
`requires_review`. Il completamento tecnico non attesta una contromisura accettata.
C2/C3 restano completati; C4 e i suoi tentativi di ripresa restano non completati.

[Report corrente](../output/case-improvements-20261106/report-C1.md). Le sezioni datate sotto conservano la preparazione
e gli esiti precedenti; Logback e ora adottato nel protocollo v2.

Aggiornamento: 6 novembre 2026. Questo documento descrive lo stato verificato,
senza assumere che i servizi esterni siano attualmente accesi.

## Framework implementato

Quattro agenti CAMEL producono artefatti separati:

| Ruolo | Responsabilita |
| --- | --- |
| TelemetryAgent | Normalizza osservazioni e pubblica `RuntimeEvidence` |
| VulnerabilityAgent | Correlazione CTI e valutazione del pacchetto osservato |
| CountermeasureAgent | Candidate e richieste di verifica, mantenute distinte |
| StrategicAgent | Grafo, chiamate di ranking/validazione, scelta e provenance |

`ArtifactSession` e la fonte autorevole: verifica schemi Pydantic, prerequisiti,
immutabilita e corrispondenza tra artefatti. La memoria conversazionale degli
agenti non sostituisce gli output pubblicati. La scelta non applica la contromisura.

Un ulteriore ruolo CAMEL, SemanticPreparationAgent, opera come checkpoint autonomo
sui tre artefatti pubblicati: riusa i moduli Bottalico su costa-thesis e produce
OWL/ALN, mappa MAS/KG e grafi/richieste native per CVE. Il profilo nativo dello
Strategic consuma ora il checkpoint e pubblica ranking SaaS e due riletture per
CVE, con score originali e pin di tenant/snapshot/ontologia. Un secondo profilo
Strategic valida ora tutte le candidate con binding IRI espliciti e contesto
operativo: Tiny-ME e policy SaaS restano distinti. La selezione nativa sceglie ora
la prima candidata con effectiveStatus=accepted per CVE. Il comando principale
collega tutte le fasi in un DAG composto: Workforce dei produttori e agenti CAMEL
nativi avviati dopo la verifica dei prerequisiti. Lo switch applicativo
`--backend-mode mockup|real` e indipendente dall'inferenza e dai branch.
La [finalizzazione condivisa](integrazioni/strategic-finalization.md) e implementata:
commit e rilettura sono controllati dal backend, con prove su Fabric/Tiny-ME simulati.
Il primo collaudo live e stato avviato dopo la richiesta dell'utente: rete Fabric,
SaaS e bridge operativi, sei chiamate MCP reali sul primo grafo esistente passate.
Il percorso MAS completo fino alla finalizzazione non e ancora verificato live.
[Esiti e limiti](integrazioni/collaudo-reale.md).
L'[audit KG del 6 novembre](../output/kg-coverage-20261106/report.md) conferma
assenza di rimedi per le tre CVE del caso Log4j e individua Logback-core
1.5.24/1.5.25 come alternativa: CTI completo, upgrade esplicito e ALN verificati.
La coppia non e ancora adottata come nuovo caso osservato o collaudata nel MAS;
una sola candidata consente il controllo della manutenzione ma non un fallback.
[Contratti ed esecuzione](integrazioni/canonical-preparation.md).
[Strategic nativo](integrazioni/strategic-native.md).
[Vincoli e IRI](integrazioni/strategic-validation.md).
[Selezione, DAG e switch](integrazioni/strategic-selection-dag.md).

## Ingressi e percorsi collaudati

| Percorso | Stato |
| --- | --- |
| Mock locale e MCP mock | Fixture e inferenza CAMEL/Ollama collaudate |
| OTel e cve2owl | Snapshot registrati, log SDK e lookup MCP disponibili |
| Applicazione Java | SBOM e log della stessa build; CTI/OSV reali; caso negativo verificato |
| Apache/Ubuntu | Identita risolta e 120 classificazioni del pacchetto; condizioni runtime ancora non verificate |
| Apache strategico | Astensione MCP, PROV-O su file e rilettura verificati con Ollama |
| Servizi strategici condivisi | Mapping MAS/KG/IRI, ranking, validazione e selezione collegati nel DAG. Client stdio collaudato con bridge/SaaS effettivi e Fabric simulato; launcher completo collaudato con servizi e inferenza sintetici |

Il caso Apache piu recente conclude con `insufficient_evidence`: quattro
richieste pendenti, nessuna strategia selezionata. Non e una prova di assenza
di vulnerabilita e non esercita il ranking BWAF o Tiny-ME.

## Porting e indicazioni del professore

Il framework lavora su `full`. Nei due repository esterni su `costa-thesis`
sono stati importati il bridge MCP e il backend SaaS condivisi da `principe-thesis`.
Build, discovery di 19 tool e 66 test backend sono passati; i test simulano Fabric.
Revisioni e adattamenti sono nel [resoconto del porting](porting-principe-costa.md).

Il percorso principale previsto e Strategic -> MCP condiviso -> backend SaaS ->
servizi di argumentation, semantica e ledger. I dettagli Fabric rimangono nel backend.
Il gateway e il chaincode di provenance sperimentali conservati nel repository
non costituiscono il percorso principale da completare.

Individuata la pipeline ibrida Bottalico: ProductionExtractor esegue estrazione
LLM degli asset, mentre i moduli OWL/grafo/ALN costruiscono deterministicamente
le rappresentazioni successive. Versioni piu recenti trovate nei riferimenti
locali main/principe-thesis/origin-main. Non emerge un generatore LLM separato
di argomenti BWAF. [Ispezione e prove](../output/generator-inspection-20261031/report.md).
Il 3 novembre l'utente ha confermato di utilizzare questa pipeline ibrida
disponibile. Resta da chiarire l'eventuale dashboard decisionale diversa da Grafana.

## Lavoro aperto

Il primo collaudo reale del 5–6 novembre ha eseguito build CGO e due build Java
coerenti, avviato la configurazione Fabric originale dal costa-thesis e verificato
MCP -> SaaS -> ledger -> ranking nativo. Corretti due errori di compilazione Go e
il parametro di pinning del dataset CTI nel launcher. Suite Python: 654 passati.
I tentativi CAMEL/Ollama sulle fonti reali sono nel
[report](../output/real-cases-20261105-r1/report.md): non equivalgono a quattro
esecuzioni complete del launcher. Rimangono errori di pubblicazione delle candidate
e assenza di rimedi KG collegati alle tre CVE del caso vulnerabile; nessuna nuova
conoscenza introdotta per aggirare il problema. C2 negativo completato con no_findings.

Il [consolidamento scientifico offline](tecnica/consolidamento-scientifico-grafo.md)
ha verificato le cinque coppie di grafi, fissato aspettative qualitative indipendenti
e corretto controlli del client nativo e parsing ExplainAffinity. Verificati 652 test
Python, 167 SaaS, nove del client Go e tre del parser numerico; build SaaS e
collaudo HTTP/stdio con riavvio passati con servizi semantici/ledger simulati.
Non e una verifica numerica del core BWAF. Le quattro candidate della demo hanno
lo stesso profilo ALN; l'anello per ID resta una policy sperimentale. Il grafo
canonico include CVE e strategie, senza nodi runtime autonomi. Per dimostrare
preferenze applicative occorrono profili d'azione distinti, fonti e relazioni motivate.
L'utente ha deciso di concludere senza questa estensione: tali aspetti restano
limiti dichiarati e sviluppi futuri. Il lavoro residuo riguarda collaudo e risultati
del percorso disponibile, con sole correzioni necessarie al suo funzionamento.

1. Raccordo checkpoint -> Strategic -> ranking/riletture native implementato;
   collaudato con processo stdio e SaaS simulato, senza normalizzare gli score.
2. Contratto IRI/vincoli, validazione, selezione e DAG implementati e collaudati.
3. Prima accettata, alternativa, prerequisiti/revisione, nessuna valida e guasti
   distinti verificati con servizi sintetici. Contratto scientifico e casi attesi
   documentati offline; profili d'azione nuovi esclusi dal perimetro di chiusura.
   Verificare il comportamento del core disponibile senza attribuire alla topologia
   una validazione di dominio non ottenuta. Bonus non valutato nel percorso corrente.
4. Finalizzazione condivisa implementata dopo ispezione completa e autorizzazione:
   [contratti ed evidenze](integrazioni/strategic-finalization.md). Commit/rilettura,
   idempotenza, riavvio e PROV-O collaudati con Fabric/Tiny-ME simulati.
   [Ispezione precedente](../output/finalization-inspection-20261103/report.md).
5. Preparare quattro casi controllati con build, SBOM e runtime coerenti e dashboard.
6. Alla fine della progettazione verificare servizi disponibili, rete reale,
   binding, ExplainAffinity, ontologia/IRI e TLS; poi collaudo end-to-end,
   commit/rilettura e misure di correttezza, ripetibilita e latenza.

Per azioni e criteri di completamento leggere [prossime azioni](prossime-azioni.md).

## Percorso di studio

- [Architettura](architettura-implementata.md): figure e dipendenze.
- [Guida al codice](reading-guide.md): file e controlli.
- [Esperimenti](esperimenti.md): risultati e limiti delle prove eseguite.
- [Indice delle guide](README.md): dettagli per ogni integrazione.
- [Materiali della relazione](materiali/README.md): Word manuali, export e figure.
- [Fonti](fonti-e-scelte.md): attribuzioni e distinzione fra euristica mock e BWAF.
