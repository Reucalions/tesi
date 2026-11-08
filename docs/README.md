# Documentazione del progetto

## Percorso di lettura

| Documento | Scopo |
| --- | --- |
| [Stato del progetto](stato-progetto.md) | Funzioni implementate e limiti verificati |
| [Architettura](architettura-implementata.md) | Schema dei componenti e dei percorsi collaudati |
| [Guida al codice](reading-guide.md) | Responsabilita e file da studiare |
| [Prossime azioni](prossime-azioni.md) | Ordine delle integrazioni e criteri di completamento |
| [Esperimenti](esperimenti.md) | Risultati, limiti e posizione delle evidenze |
| [Porting dei servizi](porting-principe-costa.md) | Revisioni importate e verifiche del trasferimento |

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
| Primo collaudo reale | [Avvio Fabric dal costa-thesis, MCP effettivo e tentativi dei casi controllati](integrazioni/collaudo-reale.md) |

## Approfondimenti tecnici

- [Contratti e invarianti](tecnica/architecture.md).
- [Contratto scientifico del grafo](tecnica/consolidamento-scientifico-grafo.md):
  significato di nodi/archi, scale, casi attesi e limiti della proiezione ALN.
- [Quattro casi controllati](tecnica/casi-controllati.md): riuso delle demo mock,
  aspettative distinte per il percorso reale e preparazione delle fonti.
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
