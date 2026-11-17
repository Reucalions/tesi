# Documentazione del progetto

Disponibile anche il [report accademico completo](materiali/report-finale/README.md),
in [PDF di 29 pagine](materiali/report-finale/report.pdf) e
[Word modificabile](materiali/report-finale/report.docx), con diagrammi e tabelle
per mockup, architettura completa e valutazione. Il capitolo 5 esplicita il
flusso semantico della run completa C1, con asserzioni e risultati verificati.

Raccolta finale conclusa il 13 novembre 2026:
[risultati e copertura](tecnica/valutazione-finale.md),
[conformita e contributi](tecnica/conformita-proposta.md),
[riproduzione offline e demo](tecnica/riproduzione-finale.md).
I [dati essenziali](../evaluation/final-results-v1/README.md) sono conservati
nel repository e ricalcolabili senza servizi. Le sezioni storiche riportano
anche stati e misure precedenti, ora superati dalla sintesi finale.

Correzione del 13 novembre: [associazione delle spiegazioni native e nuovo collaudo](tecnica/correzione-spiegazioni-native.md).
Trenta prove concluse, 60/60 cammini associati correttamente e punteggi invariati.
Il [benchmark del 12 novembre](tecnica/risultati-benchmark-ranking.md) resta conservato;
significato di against e scelta dei cammini sensibile all'ordine restano limitazioni.

## Percorso di lettura

| Documento | Scopo |
| --- | --- |
| [Stato del progetto](stato-progetto.md) | Funzioni implementate e limiti verificati |
| [Architettura](architettura-implementata.md) | Schema dei componenti e dei percorsi collaudati |
| [Guida al codice](reading-guide.md) | Responsabilita e file da studiare |
| [Prossime azioni](prossime-azioni.md) | Ordine delle integrazioni e criteri di completamento |
| [Esperimenti](esperimenti.md) | Risultati, limiti e posizione delle evidenze |
| [Porting dei servizi](porting-principe-costa.md) | Revisioni importate e verifiche del trasferimento |
| [D3FEND e conoscenza condivisa](tecnica/ispezione-d3fend-conoscenza-condivisa.md) | Ispezione aggiornata di Principe, testbed multi-tenant, visibilità, feedback delle strategie ed effort proposto |

## Guide di integrazione

| Area | Documenti |
| --- | --- |
| Telemetria | [OTel](integrazioni/opentelemetry-integration.md), [Apache registrato](integrazioni/apache-recorded-integration.md) |
| CTI | [cve2owl](integrazioni/owl-cti-integration.md), [Workforce](integrazioni/cti-workforce.md), [identita Apache v2](integrazioni/cti-identity-resolution-v2.md) |
| Ubuntu | [Applicabilita del pacchetto](integrazioni/ubuntu-package-applicability.md), [VulnerabilityAgent](integrazioni/ubuntu-vulnerability-agent.md), [CountermeasureAgent](integrazioni/ubuntu-countermeasure-agent.md) |
| SBOM e caso controllato | [SBOM/OSV](integrazioni/sbom-osv-integration.md), [applicazione osservata](integrazioni/observed-app-integration.md) |
| MCP | [Lookup](integrazioni/mcp-lookup.md), [tool strategici mock](integrazioni/mcp-strategic.md), [astensione Apache e PROV-O](integrazioni/apache-strategic-agent.md) |
| Preparazione canonica | [Ruolo agente, riuso Bottalico, OWL/ALN e richieste per CVE](integrazioni/canonical-preparation.md) |
| Strategic nativo | [Checkpoint canonico, ranking SaaS per CVE e riletture MCP stdio](integrazioni/strategic-native.md) |
| Validazione operativa | [Binding IRI, contesto operativo e validazione SaaS/Tiny-ME](integrazioni/strategic-validation.md) |
| Selezione e percorso completo | [Candidata accettabile per CVE, DAG e switch mockup/reale](integrazioni/strategic-selection-dag.md) |
| Collaudo reale | [Avvio Fabric dal costa-thesis, MCP effettivo e launcher completi C1/C4](integrazioni/collaudo-reale.md) |

## Approfondimenti tecnici

- [Contratti e invarianti](tecnica/architecture.md).
- [Contratto scientifico del grafo](tecnica/consolidamento-scientifico-grafo.md):
  significato di nodi/archi, scale, casi attesi e limiti della proiezione ALN.
- [Quattro casi controllati](tecnica/casi-controllati.md): riuso delle demo mock,
  aspettative distinte per il percorso reale e preparazione delle fonti.
- [C4-r3: launcher integrale riuscito](../output/c4-collaudo-20261112-r2/report.md):
  otto nodi nella stessa esecuzione, finalizzazione, riletture e limiti verificati.
- [Ripresa C4 verificata](../output/c4-collaudo-20261112-r1/report.md):
  commit e rilettura conservati, completamento dell'ultima fase e limite del launcher fallito.
- [Inventario evidenze e copertura metriche](tecnica/valutazione-metriche.md):
  requisiti della proposta, dati recuperati, latenze e misure ancora mancanti.
- [Campione annotato indipendente, bozza v1](../evaluation/annotated-sample-v1/README.md):
  ingressi, etichette motivate dalle fonti, denominatori e revisione umana pendente.
- [Campione v2 e revisione tecnica](../evaluation/annotated-sample-v2/README.md):
  28 casi verificati dall'assistente sulle fonti, policy precisate e limiti delle annotazioni assistite.
- [Metriche misurate dei componenti](tecnica/risultati-metriche-componenti.md):
  precisione, recall, F1, accuratezze, errori e limiti del campione assistito v2.
- [Spiegazioni derivate dagli artefatti](tecnica/artifact-explanations.md).
- [Tool e pubblicazioni per fase](tecnica/agent-tool-phases.md).
- [Budget, memoria e verifiche LLM](tecnica/ollama-contract-tests.md).
- [Runner della demo](tecnica/demo-runner.md) e [scenari](tecnica/demo-scenarios.md).

## Relazione, fonti e storia

- [Materiali della relazione](materiali/README.md): documenti manuali, export e figure.
- [Proposta e bibliografia](riferimenti/README.md).
- [Fonti e attribuzioni](fonti-e-scelte.md).
- [Archivio](archivio/README.md): sorgente della relazione mockup, vecchio schema,
  resolver v1 e integrazione Fabric sperimentale, superati come percorso principale.

I resoconti cronologici ridondanti sono confluiti in `esperimenti.md`; il vecchio
piano MCP e confluito nella roadmap. Le versioni integrali precedenti sono nella
cronologia Git, alla revisione `32e6dbc311cf01af4d80519fde9eadd351097b12`.
Esempio: `git show 32e6dbc:docs/apache-ollama-use-case.md`.
Le evidenze sperimentali in `output/` restano conservate e non sono incluse in un clone nuovo.


- [Finalizzazione condivisa e provenance della raccomandazione](integrazioni/strategic-finalization.md):
  contratti SaaS/MCP/ledger, idempotenza, ricevute, riletture e limiti delle prove.
