# Metriche dei componenti sul campione assistito v2

Misura del 12 novembre 2026. Fonte:
[campione congelato v2](../../evaluation/annotated-sample-v2/README.md),
con annotazioni assistite verificate sulle fonti e senza revisione umana
indipendente. Gli ingressi e le etichette non sono cambiati dopo la raccolta.

## Risultati

| Misura | Conteggi | Valore |
| --- | --- | ---: |
| Precisione estrazione, tuple esatte | 7 TP, 1 FP | 87,50% |
| Recall estrazione, tuple esatte | 7 TP, 3 FN | 70,00% |
| F1 estrazione | 2×7 / (2×7 + 1 + 3) | 77,78% |
| Accuracy documentale estrazione | 9/12 | 75,00% |
| Accuracy matching identita | 13/16 | 81,25% |
| Accuracy versione, tre classi | 10/13 | 76,92% |
| Accuracy versione, casi binari | 7/8 | 87,50% |

Tutte le 16 chiamate CTI reali e le elaborazioni dei 12 documenti sono riuscite,
senza errori tecnici. Le discrepanze di dominio rimangono nei denominatori.
I cinque riferimenti unknown non diventano negativi nella metrica binaria.
Il denominatore 13 comprende anche il matching fallito di C11.

## Che cosa e stato eseguito

L'estrazione misura la funzione di produzione `identify(resource, record)` del
gateway OTel, riutilizzata nel percorso del TelemetryAgent attuale. Gli ingressi
sono i log del campione; si deduplicano le identita ripetute nello stesso documento.
Il test isola l'identificazione, senza selezione della finestra/query e senza
inferenza CAMEL o LangExtract. Non e una misura della capacita generativa dell'LLM.

Matching e versioni usano sedici nuove richieste al servizio CTI reale attraverso
MCP, con il probe esistente, discovery, validazione di risposta e pin del dataset.
Gli hash dei quattro moduli del motore sono coerenti tra tutte le risposte e
con i file locali. La risoluzione segue la condizione del mapper esistente:
esattamente una candidata con confidenza high. Il nome osservato non viene corretto.

Non sono stati eseguiti ranking, Tiny-ME, Fabric o launcher completo; lo stato
di C1/C4 e la finalizzazione dei casi non cambia. I tempi di questa raccolta non
sono confrontabili con i 1274,172 secondi del launcher C1-r2.

## Stratificazione e discrepanze

Sui quattro documenti SDK originali: 4 TP, nessun FP/FN, quattro documenti esatti.
Sugli otto derivati controllati: 3 TP, 1 FP, 3 FN; precisione 75%, recall 50%,
F1 60%, cinque documenti esatti. Questa separazione impedisce di presentare il
campione sintetico come una raccolta di nuove osservazioni runtime indipendenti.

- **E05:** il parser omette il vendor esplicitamente aggiunto. La tupla e diversa
  dal riferimento e vale un FP piu un FN; prodotto/versione rimangono corretti.
- **E06/E12:** il parser richiede identita complete e non restituisce le tuple
  parziali previste dal riferimento quando la versione manca o non e una stringa.
- **C04/C05:** il valutatore restituisce not_vulnerable fuori dagli intervalli
  Logback, mentre il default dello snapshot e unknown. E un risultato piu certo
  di quanto supportato dal riferimento; non prova vulnerabilita reale delle versioni.
- **C11:** l'alias Maven resta ambiguo fra candidati lessicali. E un'astensione
  prudente che non risolve l'identita prevista dal benchmark.
- **C15/C16:** l'adapter conserva ambiguous invece di not_found rispettivamente
  per un nome sintetico e un vendor incompatibile. Nessuna identita e accettata:
  il disaccordo e di categoria, non un finding inventato.

Il matching sui tredici casi diretti e 12/13 (92,31%); sui tre casi di policy
C08/C11/C16 e 1/3 (33,33%). La misura primaria resta 13/16, senza rimuovere a
posteriori i casi difficili. Non sono state applicate correzioni ai backend per
ottenere un risultato migliore.

## Evidenze e verifiche

- [Report completo](../../output/component-metrics-20261112-r1/report.md).
- [Metriche JSON](../../output/component-metrics-20261112-r1/metrics.json) e
  [tabella sintetica CSV](../../output/component-metrics-20261112-r1/metrics-summary.csv).
- [Casi di estrazione](../../output/component-metrics-20261112-r1/extraction-cases.csv)
  e [casi CTI](../../output/component-metrics-20261112-r1/cti-cases.csv).
- [Protocollo fissato prima delle predizioni](../../output/component-metrics-20261112-r1/protocol.json).
- [Verifiche conclusive](../../output/component-metrics-20261112-r1/verification.json).
- [Raccoglitore e scorer](../../evaluation/run_metrics.py),
  [test dei conteggi](../../tests/test_evaluation_metrics.py).

La raccolta usa solo gli ingressi; gli altri file vengono hashati come byte per
controllare l'integrita. Lo scoring apre le annotazioni in un secondo passaggio,
verifica hash del campione, del codice fissato e dei risultati originali. Sei
test controllano formule, denominatori nulli, errori tecnici, identita errate e
ambiguita; i conteggi principali sono verificati anche con frazioni indipendenti.

Sono risultati circoscritti a due famiglie software e quattro build, con variazioni
correlate. La preparazione assistita non sostituisce il campione annotato manualmente
richiesto dalla proposta. Non si dichiarano accuratezza generale, variabilita LLM,
significativita statistica o completamento delle altre metriche della sezione 15.

[Inventario e copertura](valutazione-metriche.md),
[stato del progetto](../stato-progetto.md).
