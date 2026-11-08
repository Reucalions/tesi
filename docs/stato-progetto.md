# Stato del progetto

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
