# Inventario delle evidenze e copertura delle metriche

## Sintesi finale disponibile — 13 novembre 2026

Il riferimento corrente e la [valutazione finale](valutazione-finale.md), con
32 voci aggiornate nel [catalogo v2](../../config/metrics-evidence.v2.json),
227 timer, 45 confronti appaiati e 3293 file inventariati.
Il [pacchetto dei risultati](../../evaluation/final-results-v1/README.md)
conserva dati e ingressi per il ricalcolo offline. Inclusi sensibilita degli
archi, confronto nativo in memoria/MCP, coppie evaluate/invoke, Bonus e
contrazione reali e due confronti runtime/prima-dopo validazione circoscritti.
Le lacune restano esplicite; nessuna conformita globale o accettazione applicativa
artificiale. L'inventario v1 e le sezioni sotto restano fotografie storiche.

## Associazione delle spiegazioni verificata: 13 novembre 2026

[Nuova campagna dopo la correzione](correzione-spiegazioni-native.md): 30/30 prove,
60/60 corrispondenze cammino–candidata (prima 30/60), con prodotti/archi corretti.
Score e pesi identici nei 45 confronti e alla campagna precedente; 60 commit
VALID e 30 riletture indipendenti, 30 digest degli output nativi conservati.

Per R06 e chiuso il difetto di associazione nel corpus verificato; rimangono
copertura parziale, against positivo e scelta delle prove sensibile all'ordine
(6/15 coppie con explanation identiche per label). R01/R03 attestano stabilita
dei punteggi e dei massimi, non l'invarianza dell'intero output. Nuove latenze
MCP P06/P07 disponibili, con scrittura aggiuntiva di originale/audit; nessuna
conclusione di accelerazione o isolamento del core. R04/P11 e ablation runtime
restano non misurati. Inventario e raccolte precedenti conservati invariati.

## Benchmark nativo misurato: 12 novembre 2026

Disponibili i [risultati correnti del ranking](risultati-benchmark-ranking.md):
30/30 prove tecniche, cinque coppie di grafi, tre repliche per rappresentazione.
R01: punteggi/pesi identici nei 15 confronti originale/riordinato; R03: 30
confronti fra repliche con massimi stabili. R02: 60 commit VALID e 30 riletture
indipendenti. R05: serie misurata su 6–40 nodi; P06/P07: tempi delle chiamate
MCP StoreGraph/RankGraph, con consenso, senza isolamento C++ puro.

R06 resta parziale con un nuovo fallimento documentato: prodotti e archi validi
60/60, ma associazione della spiegazione alla candidata valida solo 30/60;
tutti i riordinati hanno destinazione diversa dalla candidata spiegata. Dodici
cammini against hanno prodotto positivo. La ripetibilita numerica non dimostra
invarianza dell'output completo. R04 non valutata per mancanza di pesi impostabili
nel contratto; P11 overhead equivalente non misurato. Nessuna nuova semantica,
no modifica dei risultati o del core. Ambiente baseline distinto da C1/C4.

La tabella e i conteggi dell'inventario dell'8 novembre, piu sotto, restano la
fotografia storica originale. Questa campagna e le metriche assistite successive
sono aggiornamenti separati, non una riclassificazione retroattiva delle 32 voci.

## Prima misura E01–E05 sui componenti: 12 novembre 2026

Calcolati i [risultati sul riferimento assistito v2](risultati-metriche-componenti.md):
precisione estrazione 87,50%, recall 70%, F1 77,78%; accuracy documentale 9/12;
matching CTI 13/16; versione tre classi 10/13 e binaria 7/8. Parser OTel di
produzione e sedici chiamate MCP reali, nessuna inferenza LLM o misura end-to-end.
Il corpus non e revisionato da un annotatore umano indipendente: le percentuali
non risolvono quel limite della proposta. Etichette/ingressi e esportazioni
dell'8 novembre restano immutati; la tabella storica sotto non e ricalcolata.

## Revisione delegata completata: 12 novembre 2026

L'assistente ha riesaminato i 28 casi sulle fonti e congelato la
[v2](../../evaluation/annotated-sample-v2/README.md), con
[esiti per caso](../../evaluation/annotated-sample-v2/review-report.md).
Nessuna etichetta o ingresso cambiato; precisati tre casi di policy e il fatto
che un errore tecnico non vale come unknown corretto. Il campione puo essere
usato per una valutazione controllata con annotazioni assistite verificate sulle
fonti. L'assenza di revisione umana indipendente resta una limitazione rispetto
alla proposta, senza richiedere all'utente di ripetere i controlli tecnici.
Nessuna nuova inferenza o metrica: prossimo passo raccolta delle predizioni.

## Campione preparato: 12 novembre 2026

Disponibile la [bozza annotata v1](../../evaluation/annotated-sample-v1/README.md)
per E01–E05: 12 documenti di estrazione (4 raccolte SDK originali, 8 variazioni
controllate) e 16 query CTI. Annotazioni proposte dalle fonti grezze, senza usare
le risposte del sistema come etichette; 33 confronti fra literal OWL e righe SQLite.
Il campione non e cieco e richiede revisione umana prima di misurare le metriche.
Sono pronti ingressi separati, riferimenti puntuali, scheda di revisione e manifest.
Nessuna nuova predizione o metrica calcolata; precisione, recall, F1 e accuracy
restano nulli. La tabella seguente e le esportazioni dell'8 novembre restano
la fotografia originale. Prossimo passo: revisionare e congelare le etichette,
poi raccogliere gli output mantenendo fissi protocollo e denominatori.

## Inventario iniziale: 8 novembre 2026

Raccolta dell'8 novembre 2026, basata sulle sezioni 15.1–15.5 della
[proposta iniziale](../riferimenti/proposta-agentic-cti.pdf). Il limite semantico
di C1 resta dichiarato: nessuna estensione dei profili di applicabilita, nuovo
run, test backend o accesso ai servizi e stato effettuato per questa raccolta.

## Risultati della raccolta

| Elemento | Risultato verificato |
| --- | --- |
| Evidenze inventariate | 698 file univoci, SHA-256 e dimensioni, 14 gruppi |
| Requisiti censiti | 32 voci, ricavate dalle cinque sezioni della proposta |
| Controlli di integrita | 42/42 coerenti con manifest e ricevute archiviate |
| Osservazioni temporali | 30 durate esplicite; altri 9 eventi senza timer isolato |
| Campagna Logback | 5 tentativi del launcher, 3 completati; 2 riprese della sola finalizzazione separate |
| Diagnostica precedente | 5 tentativi Log4j separati dalla campagna Logback |
| Valutazioni semantiche recuperate | C1-r2 e C4-r1, con esito del launcher mantenuto distinto |

La raccolta corrente e la revisione **r2**. La prima esportazione resta conservata
in `output/metrics-inventory-20261108/`; r2 aggiunge la tabella delle decisioni e
usa il raccoglitore consolidato. Non sono due nuove esecuzioni del prototipo.

- [Report completo e tabella di copertura](../../output/metrics-inventory-20261108-r2/report.md).
- Inventario: [JSON](../../output/metrics-inventory-20261108-r2/inventory.json),
  [CSV](../../output/metrics-inventory-20261108-r2/inventory.csv).
- Copertura: [JSON](../../output/metrics-inventory-20261108-r2/coverage.json),
  [CSV](../../output/metrics-inventory-20261108-r2/coverage.csv).
- Tentativi: [JSON](../../output/metrics-inventory-20261108-r2/runs.json),
  [CSV](../../output/metrics-inventory-20261108-r2/runs.csv).
- Latenze: [JSON](../../output/metrics-inventory-20261108-r2/latencies.json),
  [CSV](../../output/metrics-inventory-20261108-r2/latencies.csv).
- Decisioni prima/dopo validazione:
  [JSON](../../output/metrics-inventory-20261108-r2/decisions.json),
  [CSV](../../output/metrics-inventory-20261108-r2/decisions.csv).
- [Controlli](../../output/metrics-inventory-20261108-r2/checks.json) e
  [manifest della raccolta](../../output/metrics-inventory-20261108-r2/manifest.json).

I file in `output/` sono archivi locali esclusi da Git. Il
[catalogo versionato](../../config/metrics-evidence.v1.json) conserva requisiti,
perimetro dell'inventario, classificazioni e lacune. Il
[raccoglitore](../../evaluation/collect_inventory.py) permette di rigenerare
l'esportazione quando gli archivi originali sono disponibili.

## Tabella sintetica di copertura

**Disponibile** significa osservazione reale entro il perimetro dichiarato, non
validazione statistica generale. **Parziale** significa che mancano un confronto,
una misura isolata o una serie omogenea. **Test/mock** non dimostra il criterio
nel prototipo reale. Mancante e non eseguita non vengono convertiti in zero.

| Sezione | ID | Misura | Copertura |
| --- | --- | --- | --- |
| 15.1 | E01 | Precisione estrazione | Mancante: corpus indipendente |
| 15.1 | E02 | Recall estrazione | Mancante: corpus indipendente |
| 15.1 | E03 | F1 estrazione | Mancante: dipende da E01/E02 |
| 15.1 | E04 | Accuratezza matching prodotto | Parziale: casi controllati e probe |
| 15.1 | E05 | Accuratezza classificazione versioni | Parziale: due build e probe |
| 15.1 | E06 | Errori e casi rappresentativi | Disponibile, diagnostica |
| 15.2 | R01 | Determinismo con riordinamenti | Parziale: cinque coppie verificate offline |
| 15.2 | R02 | Persistenza grafi e risultati | Disponibile, prove archiviate |
| 15.2 | R03 | Stabilita del vincitore | Parziale: manca una serie corrente omogenea |
| 15.2 | R04 | Sensibilita ai pesi | Mancante: nessuno sweep controllato |
| 15.2 | R05 | Dimensioni crescenti | Parziale: benchmark pronti, campagna corrente assente |
| 15.2 | R06 | Spiegazioni del ranking | Parziale: prodotti verificati, limite su against |
| 15.3 | S01 | Graduatoria e decisione dopo validazione | Disponibile, C1 |
| 15.3 | S02 | Prima candidata accettata | Test/mock; caso reale non dimostrato |
| 15.3 | S03 | Candidata condizionata | Disponibile, C1 e artefatti parziali C4 |
| 15.3 | S04 | Rifiuto della candidata e fallback | Test/mock; clash di arco distinto dal rifiuto |
| 15.3 | S05 | Abduzione | Disponibile, output Tiny-ME reale |
| 15.3 | S06 | Bonus | Non eseguito nel percorso corrente |
| 15.3 | S07 | Contrazione | Test/mock; ramo non invocato da C1 |
| 15.4 | P01 | Ingestione telemetria | Parziale: timer gateway su export gia raccolto |
| 15.4 | P02 | Estrazione asset | Parziale: manca timer isolato dell'agente |
| 15.4 | P03 | Matching vulnerabilita | Disponibile, chiamata CTI MCP |
| 15.4 | P04 | Generazione OWL | Parziale: preparazione aggregata |
| 15.4 | P05 | Costruzione grafo | Parziale: preparazione aggregata |
| 15.4 | P06 | Memorizzazione grafo | Parziale: timer isolato assente |
| 15.4 | P07 | Ranking | Parziale: chiamata di dominio e convenzione singola candidata |
| 15.4 | P08 | Validazione semantica | Disponibile, chiamata di dominio MCP |
| 15.4 | P09 | Registrazione provenance | Parziale: finalizzazione aggregata |
| 15.4 | P10 | Durata end-to-end | Disponibile, singoli tentativi diagnostici |
| 15.4 | P11 | Overhead blockchain | Mancante: confronto equivalente assente |
| 15.5 | A01 | Con/senza evidenza runtime | Mancante: coppia controllata assente |
| 15.5 | A02 | Prima/dopo validazione | Parziale: confronto interno C1, non due run accoppiati |

Sono quindi 8 voci disponibili nel perimetro limitato, 14 parziali, 6 mancanti,
3 coperte solo da test/mock e 1 non eseguita. Non si ricava una percentuale
globale di conformita: i requisiti hanno significati e denominatori diversi.

## Confini delle misure recuperate

Per C1-r2 sono presenti, fra le altre, queste osservazioni singole:

| Operazione | Secondi | Interpretazione |
| --- | ---: | --- |
| `collect_telemetry` | 0.034799 | Richiesta al gateway su export SDK gia raccolto |
| `assess_software` | 0.112060 | Chiamata CTI MCP, non intero VulnerabilityAgent |
| `prepare_argumentation` | 191.289089 | Verifiche delle fonti, OWL, grafo e ALN insieme |
| `rank_remediations` | 0.744415 | Operazione SaaS aggregata, non tempo puro BWAF |
| `validate_countermeasure` | 0.302031 | Chiamata semantica/operativa tramite MCP |
| `finalize_recommendation` | 0.693981 | Validazioni, registrazione, commit e verifiche backend |
| Runner completo | 1274.172 | Include teardown dei gateway; singolo campione |

Ogni timer e collegato a file e riga nella tabella esportata. Il raccoglitore
legge solo gli eventi primari dei run; le copie annidate di lineage non producono
nuove osservazioni. Gli eventi senza `elapsed_seconds` restano nulli. Non si
usano mtime, nomi delle conversazioni LLM o differenze fra tentativi per inventare
durate mancanti. Il residuo rispetto al totale non e automaticamente tempo LLM.

C2/C3 completano l'assessment e saltano le fasi native non applicabili: la diversa
durata non misura un'accelerazione dello stesso workflow. C4-r1 resta fallito
anche se il record ledger e preservato. Le due riprese della finalizzazione
non contano come nuove repliche complete. Le revisioni del software e le
assunzioni della campagna diagnostica impediscono medie trasversali attendibili.

## Limiti confermati e prossimo lavoro

- Il protocollo v2 incorpora l'esito semantico osservato: riproduce il limite,
  senza fornire un oracle indipendente dell'applicabilita del rimedio.
- Il ranking di C1/C4 usa `single_candidate_convention_v1`: score 1 convenzionale,
  nessun peso BWAF calcolato, nessun confronto fra azioni o fallback reale.
- L'abduzione 38 e la classificazione operativa sono distinte. `bonusEvaluated=false`
  significa servizio non eseguito; contrazione 0 non dimostra quel ramo.
- I controlli di hash/ricevute verificano gli archivi. Non certificano lo stato
  attuale dei container o la disponibilita dei vecchi metadati SaaS eliminati.
- Il mock non e un oracle del ranking reale o una baseline equivalente per
  stimare overhead blockchain. I report Caliper legacy non misurano la tesi integrata.

Alla raccolta dell'8 novembre mancava il campione annotato per E01–E05;
la bozza preparata il 12 novembre e descritta all'inizio del documento.
Prima di nuovi run vanno fissate condizioni e ripetizioni, completato C4 e
verificata la fattibilita dei confronti sulle risorse gia esistenti. Il perimetro
semantico rimane invariato; i criteri non dimostrati restano espliciti.

## Riproduzione dell'inventario

Dalla radice del progetto, con Python 3.11 o successivo e gli archivi presenti:

```sh
python3 -B evaluation/collect_inventory.py \
  --output output/metrics-inventory-nuova-raccolta
```

La directory di destinazione deve essere nuova. `--pipeline` e `--ledger`
permettono di indicare copie locali diverse dei repository. Il raccoglitore usa
solo la libreria standard e Git in lettura; non importa agenti, non carica `.env`,
non esegue test e non contatta servizi. Il catalogo mantiene la data di riferimento
della campagna; il manifest registra separatamente HEAD e stato locale al momento
dell'inventario, senza attribuirli retroattivamente ai run storici.

[Stato del progetto](../stato-progetto.md),
[casi controllati](casi-controllati.md),
[contratto scientifico](consolidamento-scientifico-grafo.md).
