# Campione v2 — revisione tecnica sulle fonti

Revisione del 12 novembre 2026, effettuata dall'assistente su richiesta dell'utente.
I 28 casi e gli ingressi della bozza v1 sono conservati. Le etichette sono
confermate rispetto alle fonti e al protocollo dichiarato; sono precisate le
condizioni di scoring, senza osservare nuove predizioni del sistema.

Il campione e utilizzabile per una **valutazione controllata con annotazioni
assistite verificate sulle fonti**. Non richiede che l'utente ripeta i controlli
tecnici. Non e una doppia annotazione umana, una revisione da un altro autore o
un holdout cieco; non soddisfa da solo il requisito di annotazione manuale umana
della proposta. Questo limite va dichiarato quando si presentano i risultati.

## File da consultare

- [Esito dei controlli e decisioni sui casi](review-report.md).
- [Annotazioni congelate](annotations.json) e [scheda di revisione](review.csv).
- [Controlli e chiarimenti metodologici](review-findings.json).
- [Composizione e denominatori](summary.json).
- [Manifest e hash](manifest.json).
- `inputs/`: solo ingressi, identici alla v1, senza etichette o CVE suggerite.
- `sources/` ed `evidence-spans.json`: fonti originali e riferimenti ai literal.
- `metrics-template.json`: valori nulli; nessuna predizione o misura raccolta.

La [v1](../annotated-sample-v1/README.md) resta immutata, inclusa la sua scheda
di revisione pendente. Il nuovo manifest registra il suo hash come origine.

## Regole di misura confermate

Valgono le definizioni della v1 per tuple (prodotto, versione, vendor),
normalizzazione NFC/trim/casefold dei nomi, versione esatta con trim, deduplicazione
nel documento e separazione fra originali SDK e variazioni sintetiche.
Precision = TP/(TP+FP), recall = TP/(TP+FN), F1 = 2TP/(2TP+FP+FN).
Un denominatore nullo produce null/non definito; nessuna accuracy e calcolata
finche mancano le predizioni.

Denominatori fissati prima dell'esperimento:

| Misura | Denominatore |
| --- | ---: |
| Document exact-match accuracy dell'estrazione | 12 documenti |
| Accuracy matching dell'identita | 16 query |
| Accuracy versione a tre classi | 13 casi con identita gold univoca |
| Accuracy versione binaria | 8 casi determinati: 5 positivi, 3 negativi |

L'estrazione contiene 10 entita attese, incluse quelle con versione mancante;
questo e il riferimento del recall micro, non il denominatore della precisione,
che dipende da quante entita saranno effettivamente prodotte. I conteggi per campo
non possono ricombinare campi appartenenti a risorse diverse.

## Chiarimenti introdotti dopo il riesame

1. **C08, ambiguita:** lo snapshot contiene due identita letterali per `logback`.
   Il campione mantiene l'ambiguita in assenza di un alias curato. Non afferma
   che QOS.ch e QOS.CH Sarl siano necessariamente organizzazioni diverse.
2. **C11, alias:** `log4j-core` e ammesso per l'identita Apache indicata, sulla
   base della coordinata `org.apache.logging.log4j:log4j-core` nello snapshot.
   Non si estende questa equivalenza a nomi o vendor arbitrari.
3. **C16, vendor:** il vendor fornito e un vincolo dell'interrogazione. Il
   riferimento `not_found` significa nessuna identita accettabile sotto quel
   vincolo, non che il prodotto Logback-core sia assente dal database.
4. **Categorie del matching:** le etichette descrivono l'esito di risoluzione
   dell'identita, non una copia del campo `matching.status` del servizio. Si
   possono conservare candidati diagnostici senza considerarli una risoluzione.
5. **Unknown ed errori:** solo un risultato di dominio riuscito e non determinabile
   puo corrispondere al gold `unknown`. Timeout, errore tecnico, risposta assente,
   JSON invalido o identita errata contano come risposta non corretta anche nei
   cinque casi gold unknown; vengono inoltre riportati separatamente.
6. **Astensione nel matching:** C08 richiede l'ambiguita motivata dalle identita
   di riferimento; un'astensione generica o un errore non ottengono un successo.
7. **Etichette binarie:** unknown/not_evaluable non diventano negativi. Nessun
   filtro a posteriori dei matching falliti sui 13 o sugli 8 casi prefissati.

Le metriche di matching devono riportare anche il risultato separato dei tre
casi di policy C08/C11/C16 e dei tredici casi di identita diretta, mantenendo
il risultato primario sulle 16 query. Le regole sono fissate senza osservare
l'output del sistema, non adattate per migliorare i punteggi.

## Passo successivo

Raccogliere gli output tramite i componenti esistenti e calcolare le metriche con
questo protocollo, mantenendo le annotazioni fuori dagli ingressi del sistema.
La revisione non modifica agenti, KG, matcher, evaluator, semantica C1 o backend.
Le misure ottenute andranno qualificate come risultati su un piccolo campione
controllato con riferimento assistito, non come validazione generale del sistema.

La riproduzione della bozza resta disponibile nel preparatore della v1; questa
v2 conserva la decisione di revisione e i relativi hash. Modifiche successive
richiedono una nuova revisione prima di raccogliere nuove predizioni.
