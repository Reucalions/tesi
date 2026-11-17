# Campione annotato v1 — 12 novembre 2026

**Bozza assistita da fonti, da revisionare da un essere umano prima dello scoring.**
Questo campione prepara E01–E05 dell'inventario delle metriche. Non contiene
predizioni, risultati di precisione/recall/F1/accuracy o nuovi run del prototipo.
Le etichette sono motivate dalle sorgenti, senza copiare gli assessment CTI o
gli output degli agenti. Il disegno usa i casi diagnostici gia noti: non e un
test cieco, un holdout esterno o una doppia annotazione umana indipendente.

## Materiale preparato

- `annotations.json`: etichette proposte e motivazioni per ogni caso.
- `inputs/E*.otel.jsonl`: soli ingressi dell'estrazione, senza risposte attese.
- `inputs/cti-queries.jsonl`: query di identita/versione, senza CVE o etichette gold.
- `sources/`: quattro export SDK originali, manifest di build, righe SQLite
  grezze e asserzioni OWL con numeri di riga e digest del KG completo.
- `evidence-spans.json`: riferimenti JSON Pointer/numero di riga per i valori
  attesi nell'estrazione; nessun collegamento a output degli agenti.
- `review.csv`: 28 righe da revisionare, con autore/data/esito/correzioni vuoti.
- `summary.json`: composizione e denominatori previsti, senza risultati.
- `metrics-template.json`: valori non misurati mantenuti nulli.
- `manifest.json`: hash dei file del campione e delle fonti.

I dodici documenti di estrazione includono **quattro raccolte SDK originali**
(Logback 1.5.24/1.5.25 e Log4j Core 2.14.1/2.26.1), ciascuna con cinque record,
e **otto variazioni sintetiche dichiarate**. Cinque record della stessa build
non sono cinque asset indipendenti: l'identita ripetuta conta una volta per
documento. Le variazioni non provano nuove versioni caricate e non vanno fuse
con i risultati originali senza riportare lo strato di provenienza.

I sedici casi CTI riguardano due famiglie di prodotto e tre CVE dello snapshot
locale. Sono query curate, non sedici nuove osservazioni runtime. Coprono
identita esatte/alias espliciti, ambiguita, prodotto assente, vendor incompatibile,
estremi inclusivi/esclusivi, versioni assenti e copertura sconosciuta. Nessuna
conclusione di sicurezza generale o aggiornata oltre questo snapshot.

## Regole di annotazione dell'estrazione

Un'entita e una dipendenza software **osservata**, identificata negli attributi
`thesis.software.*`; il testo su un deploy pianificato non prova una libreria
caricata. `service.version` e la versione dell'applicazione, non della dipendenza.

Si annotano prodotto, versione e vendor solo quando espliciti negli ingressi.
Non si ricava un vendor da "Apache" nel nome, una versione dal POM o dall'hash
del JAR, o il suffisso `-core` dal contesto precedente. I manifest di build
servono a documentare la provenienza delle quattro fonti originali; non sono
input nascosti disponibili all'estrattore. Un campo assente o di tipo non
valido resta null; una versione isolata senza prodotto non crea un'entita.

La versione deve essere una stringa esplicita. Il caso E12 usa un `intValue`
valido per OTLP ma non valido come versione del software: non va trasformato
automaticamente in una versione stringa. Le identita parziali E06/E12 fanno
parte della valutazione del recupero di informazioni: un adapter che non puo
rappresentarle deve dichiarare l'astensione, senza introdurre valori fittizi.

Per il confronto esatto sono ammessi soltanto normalizzazione Unicode NFC,
trim e casefold dei nomi prodotto/vendor; le versioni sono stringhe esatte con
trim. Nessuna equivalenza semantica o fuzzy matching nell'estrazione. Le entita
si confrontano come insiemi di tuple (prodotto, versione, vendor), con null
espliciti e deduplicazione nel documento. Nel caso multi-entita E10 si conserva
l'associazione fra campi: non accoppiare nome di una risorsa e versione di un'altra.

## Precisione, recall, F1 e accuracy

### Estrazione: E01–E03 della matrice delle metriche

- TP: tuple attese presenti nell'output; FP: tuple prodotte non giustificate;
  FN: tuple attese omesse. Un valore errato nella tupla produce un FP e un FN.
- Precision = TP/(TP+FP); recall = TP/(TP+FN);
  F1 = 2TP/(2TP+FP+FN). Riportare prima i conteggi micro complessivi e poi gli
  strati originale/sintetico; non fare la media ingenua dei dodici rapporti.
- Denominatore nullo: valore null/non definito. Un documento senza entita e
  senza predizioni non ottiene automaticamente precision/recall pari a 1.
- Diagnostica aggiuntiva: conteggi per campo non nullo (prodotto/versione/vendor)
  associato alla risorsa corretta. Un vendor inventato e un FP anche quando il
  riferimento ha vendor null. I campi null non creano veri negativi artificiali.
- Document exact-match accuracy = documenti con insieme di tuple interamente
  corretto / 12. E distinta dall'accuracy di matching e dalle metriche per campo.
- Nessun numero di veri negativi per l'estrazione libera di entita.

### Matching prodotto: E04

Denominatore fissato a **16 query**, comprese quelle ambigue e senza corrispondenza.
Una risposta e corretta quando restituisce la categoria attesa e le identita
di riferimento appropriate. Per un caso univoco deve risolvere una sola identita
corretta; un candidato corretto in una lista irrisolta non vale come risoluzione.
Per C08 occorre mantenere l'ambiguita fra le due identita letterali presenti nel
KG, senza inventare un alias fra i vendor. Un errore tecnico o output mancante
conta come risposta non corretta nel denominatore fissato, e viene anche riportato
separatamente; non sparisce dalla statistica.

Le sole equivalenze curate sono casefold/trim per i nomi e l'alias `log4j-core`
verso il prodotto della coordinata Maven esplicita nella fonte. Il confronto usa
vendor/prodotto dei riferimenti in `annotations.json`; non importa il normalizzatore
o gli score euristici del matcher sotto valutazione.

### Classificazione versioni: E05

Il riferimento e la coppia **identita risolta, versione osservata, CVE fissata**.
La CVE gold non viene inviata al lookup come suggerimento: lo scoring selezionera
il suo risultato dall'assessment completo. Non si misura qui il recall di tutte
le CVE, la loro copertura globale o l'assenza universale di vulnerabilita.

- Accuracy a tre classi (`vulnerable`, `not_vulnerable`, `unknown`): **13 casi**
  con identita gold univoca, senza escludere a posteriori i matching falliti.
- Accuracy binaria: **8 casi** con riferimento determinato, 5 vulnerabili e
  3 non vulnerabili. `unknown` e `not_evaluable` non sono negativi binari.
- Nei cinque casi gold `unknown`, una risposta non determinabile e corretta;
  una risposta vulnerabile/non vulnerabile non giustificata e errata.
- Nei casi binari, astensione, identita errata, errore tecnico o risultato
  mancante contano come non corretti. Riportare copertura/astensioni insieme
  alla matrice di confusione, senza eliminare i casi difficili.
- I tre casi con identita ambigua/assente hanno `not_evaluable` e rimangono
  nella misura di matching, separati dal denominatore della versione.

Per Logback la regola affected ha estremi 0.9.20 e 1.5.24 inclusi, mentre la
sola 1.5.25 e esplicitamente unaffected. Il default e unknown: C04/C05 non
diventano negativi soltanto perche esterni all'intervallo. Per le due CVE
Log4j selezionate il default e unaffected; i limiti superiori sono esclusivi.
L'esame dei literal e delle inclusivita e manuale nella bozza: non viene
chiamato il VulnerabilityEvaluator per produrre queste etichette.

## Revisione e congelamento prima della misura

1. Aprire `review.csv`, `annotations.json` e le fonti richiamate per ogni caso.
2. Verificare identita, estremi, default, ambiguita e policy dei campi mancanti.
3. Registrare una persona reale, data, esito e correzioni motivate. Non compilare
   automaticamente questi campi come revisione umana effettuata.
4. Risolvere le correzioni nelle annotazioni e fissare una nuova revisione/hash
   approvata **prima** di raccogliere predizioni. Questa v1 rimane la bozza iniziale.
5. Separare gli ingressi dalle annotazioni durante l'esecuzione e riportare che
   il campione e piccolo, controllato e gia informato dalla diagnostica precedente.

Non e necessaria una nuova architettura, un nuovo KG o una campagna Fabric per
preparare questo materiale. La classificazione delle metriche non diventa
"misurata" fino a revisione e raccolta degli output. Le esportazioni delle
metriche dell'8 novembre rimangono immutate.

## Rigenerazione e verifica

`evaluation/prepare_annotated_sample.py` prepara ingressi/fonti/tabelle da questa
bozza e dai dati originali senza importare componenti del prototipo. La creazione
non sovrascrive un campione gia dotato di manifest. Per ricrearlo usare una copia
nuova di `annotations.json` e README con `--directory <nuova-directory>`.

```sh
python3 -B evaluation/prepare_annotated_sample.py --check
```

Il controllo verifica hash, puntatori e conteggi; non approva scientificamente
le etichette, non esegue il sistema e non calcola metriche su predizioni inesistenti.
