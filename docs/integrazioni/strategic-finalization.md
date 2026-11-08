# Finalizzazione condivisa della raccomandazione

Aggiornamento: 5 novembre 2026. L'estensione autorizzata dopo l'ispezione completa
riusa `SaaSServiceAdapter`, `ProvenanceService`, il bridge MCP e il contratto
`ArgumentationContract`. Nessun servizio o chaincode autonomo aggiuntivo.

La selezione locale resta un checkpoint immutabile. La nuova fase Strategic
registra una raccomandazione per CVE e ne rilegge documento, provenance e ricevuta.
Conclude soltanto dopo il confronto completo. Lo switch applicativo rimane
`--backend-mode mockup|real`; il percorso `real` include ora otto nodi nel DAG.

## Contratti e responsabilita

| Passaggio | Contratto / operazione | Responsabilita |
| --- | --- | --- |
| Selezione | `native-strategic-recommendation-v1` | Prima `effectiveStatus=accepted` nell'ordine nativo; altrimenti astensione motivata |
| Richiesta condivisa | `shared-recommendation-finalization-v1` | Documento fisso per CVE; punteggi e tutte le validazioni originali |
| MCP | `finalize_recommendation(document_json)` | Trasferisce il JSON UTF-8 originale senza riserializzarne i numeri |
| SaaS | `POST /api/v1/decisions/:id/finalize` | Autentica il tenant, verifica ranking e validazioni effettivamente conservati dal backend |
| Ledger | `StoreRecommendation(documentJSON, provenanceJSON)` | Scrive nel contratto argumentation esistente, verifica MSP e ranking su ledger |
| Rilettura | `get_finalization(decision_id, finalization_id)` | Documento e PROV strutturata, digest e stato del commit originale |
| SaaS / ledger | `GET /api/v1/decisions/:id/finalizations/:finalizationId`, `ReadRecommendation` | Legge il record immutabile e interroga nuovamente Gateway per il commit |
| Pubblicazione | `native-strategic-finalization-v1` | Checkpoint finale dopo rilettura conforme per tutte le CVE |

Il client base continua ad autorizzare soltanto i quattro tool precedenti.
`SharedServicesClient(..., finalization=True)` autorizza anche i due nuovi tool;
la discovery reale del bridge ne espone 21, dei quali il framework ne usa sei.
Gli schemi aggiuntivi sono congelati in `data/shared-finalization-schemas-v1.json`.
I vecchi `get_decision` e `get_provenance` continuano a rappresentare il ranking.

Il documento lega run, asset, tenant autenticato, CVE, decisione di ranking,
**chiave GRAPH effettiva**, snapshot e digest ontologico. Conserva outcome,
ID selezionato o `null`, policy di selezione e ogni valutazione delle candidate.
Include i digest SHA-256 dei byte originali di otto sorgenti: evidenza runtime,
rapporto CTI, candidate, preparazione canonica, ranking, validazione, profilo
operativo e raccomandazione locale. Le sorgenti rimangono archiviate fuori dal
ledger; i loro digest nel manifesto non equivalgono a una firma dei produttori.

Le validazioni sono conservate atomicamente dal SaaS prima di rispondere al client,
insieme al contesto esatto. In finalizzazione vengono confrontate con quelle
ricevute: un report del client, da solo, non basta. Anche ranking e chiave del
grafo dispongono di evidenze backend persistenti, separate dalla cache in RAM.
I record storici che precedono queste evidenze non vengono completati con dati
inventati: richiedono un nuovo ranking e nuove validazioni.

## Idempotenza, errori e ricevuta

L'identita `FIN_<sha256>` deriva da tenant, run, asset, CVE e decisione di ranking,
concatenati con prefissi di lunghezza UTF-8. Il contenuto non modifica l'identita:
la stessa richiesta restituisce il record e la transazione originali; un contenuto
differente produce `FINALIZATION_CONFLICT` (409). Il confronto e sui JSON originali,
quindi anche una riserializzazione differente deve essere trattata come una nuova
richiesta incompatibile. Il documento originario e conservato nel run.

Un ranking non CURRENT non puo ricevere una nuova finalizzazione. Una finalizzazione
gia esistente rimane rileggibile come dato storico. Validazioni mancanti o ranking
precedenti al nuovo archivio producono `FINALIZATION_NOT_READY` (409). Tenant
estranei sono rifiutati; `x-tenant-id` non sostituisce l'MSP dell'identita autenticata.
Il namespace ledger `recommendation:` e riservato: i vecchi metodi generici dei
grafi non possono sovrascriverlo o aggirarne la lettura di dominio.

Il solo transaction ID non conclude il task. Il backend controlla lo stato tramite
la API pubblica del Fabric Gateway installato e rilegge il record dal ledger.
La risposta conserva transaction ID, numero di blocco come stringa decimale,
validation code 0 e `successful=true`. Il framework verifica questi campi, i digest
SHA-256 dei JSON e tutte le correlazioni; poi effettua un secondo tool di lettura.
Un timeout resta un guasto tecnico, anche quando la scrittura potrebbe essere gia
avvenuta. Non ci sono retry automatici: una ripresa esplicita con lo stesso documento
puo recuperare il commit originale senza riscrivere la raccomandazione.

## Provenance condivisa

La nuova PROV-O estende il builder esistente e collega artefatti dei produttori,
attivita, agenti, ranking, ogni validazione backend e selezione finale. Conserva
separatamente stato semantico, stato operativo e stato effettivo. Tiny-ME e la
policy operativa SaaS sono agenti distinti; la scelta registrata e quella del MAS,
anche quando differisce dalla testa del ranking. La vecchia entita di ranking
continua a descrivere correttamente la testa di quel ranking.

Le attivita non dimostrate non vengono create dal solo template: nessuna validazione
semantica senza report, nessuna costruzione SaaS per un grafo fornito dal framework.
Il riferimento al grafo e la chiave effettiva conservata dal backend. L'export
JSON-LD usa termini e riferimenti RDF espliciti, con un Bundle/named graph:
per rileggerlo integralmente con RDFLib usare `Dataset(default_union=True)`.

## Esecuzione e artefatti consultabili

Il launcher principale mantiene gli stessi comandi e profili della
[guida allo switch](strategic-selection-dag.md). In `real` conclude con
`finalization/native_strategic_finalization.json`; `execution.json` e `dag.json`
riportano il completamento della nuova fase soltanto dopo le riletture.
I checkpoint precedenti conservano i propri campi `pending`, corretti per quella fase.

Per completare un archivio di selezione gia verificabile con il backend aggiornato:

```bash
.venv/bin/python -m thesis_agents.strategic.finalization \
  --selection-run percorso/raccomandazione \
  --profile config/mcp.shared-stdio.example.json \
  --output output/finalizzazione --mode tool
```

`--mode camel` usa lo stesso ruolo Strategic e una policy che richiede chiamate
reali ai tool. L'LLM non sceglie ID, payload, comandi o destinatari di rete.
Ogni CVE conserva in `native/<CVE>/` il documento richiesto e le due risposte.
Input e copie vengono ricontrollati prima e dopo ciascun passaggio. Il guasto di
una CVE impedisce il checkpoint complessivo; eventuali commit gia completati per
altre CVE rimangono nelle diagnostiche e sul ledger, senza rollback globale.

## Livello di verifica e limiti

Le prove disponibili usano HTTP SaaS, MCP stdio, framework e persistenza effettivi,
con autenticazione, Fabric e Tiny-ME simulati. Sono verificati cinque esiti,
scelta alternativa, idempotenza, conflitti, riavvio reale del processo backend,
corruzione delle ricevute e blocco del DAG. I metodi Go sono collaudati anche con
Fabric contract-api e MockStub; il boundary CGO del reasoner e escluso nell'harness.
Queste prove non sono un deployment o un collaudo su una rete Fabric reale.

Il risultato dichiara `verification_scope=backend_reported_commit_and_readback`,
`deployment_verified=false`, `action_execution=not_performed`. Il framework si fida
della verifica del backend autenticato; non verifica autonomamente firme di blocco
o endorsement. Il record contiene contesti e risultati, non un'attestazione
crittografica indipendente del reasoner. Il ledger di canale non e un archivio
privato tra organizzazioni: i controlli tenant proteggono le API applicative.

Per usare la nuova fase dal vivo servono build aggiornate di SaaS/bridge e
aggiornamento del **chaincode argumentation esistente**, poi verifica di servizi,
identita, TLS, ontologia e IRI. Questa attivita resta rinviata alla fine della
progettazione, come richiesto. Nessuna remediation viene eseguita.

[Evidenze e report](../../output/shared-finalization-20261103/report.md),
[ispezione precedente](../../output/finalization-inspection-20261103/report.md).
